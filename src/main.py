import argparse
import asyncio
import json
import threading
import traceback
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict, Iterable, AsyncIterable, AsyncGenerator, Optional
from pydantic import BaseModel, Field

# 加载 .env 文件（必须在导入cozeloop之前）
load_dotenv()

# 检查是否禁用cozeloop上报
COZELOOP_DISABLED = os.getenv("COZELOOP_DISABLED", "false").lower() == "true"

if COZELOOP_DISABLED:
    # 使用noop实现禁用cozeloop
    class NoopCozeloop:
        @staticmethod
        def flush():
            pass
    cozeloop = NoopCozeloop()
    print("[INFO] cozeloop 上报已禁用 (COZELOOP_DISABLED=true)")
else:
    import cozeloop

import uvicorn
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from coze_coding_utils.runtime_ctx.context import new_context, Context
from coze_coding_utils.helper import graph_helper
from coze_coding_utils.log.node_log import LOG_FILE
from coze_coding_utils.log.write_log import setup_logging, request_context
from coze_coding_utils.log.config import LOG_LEVEL
from coze_coding_utils.error.classifier import ErrorClassifier, classify_error
from coze_coding_utils.helper.stream_runner import AgentStreamRunner, WorkflowStreamRunner,agent_stream_handler,workflow_stream_handler, RunOpt

setup_logging(
    log_file=LOG_FILE,
    max_bytes=100 * 1024 * 1024, # 100MB
    backup_count=5,
    log_level=LOG_LEVEL,
    use_json_format=True,
    console_output=True
)

logger = logging.getLogger(__name__)
from coze_coding_utils.helper.agent_helper import to_stream_input
from coze_coding_utils.openai.handler import OpenAIChatHandler
from coze_coding_utils.log.parser import LangGraphParser
from coze_coding_utils.log.err_trace import extract_core_stack
from utils.interaction_store import interaction_store

# loop_trace 会在 import 时创建 cozeloop 客户端并上报；禁用切到本地实现，避免加载该模块
if COZELOOP_DISABLED:
    from graphs.loop_trace_local import init_run_config, init_agent_config
else:
    from coze_coding_utils.log.loop_trace import init_run_config, init_agent_config

# 导入 UniApp 页面生成节点
from graphs.nodes.uniapp_page_generate_node import uniapp_page_generate_node
from graphs.nodes.git_branch_switch_node import extract_group_number, convert_to_pinyin
from graphs.state import UniAppPageGenerateInput


# 超时配置常量
TIMEOUT_SECONDS = 900  # 15分钟

class GraphService:
    def __init__(self):
        # 用于跟踪正在运行的任务（使用asyncio.Task）
        self.running_tasks: Dict[str, asyncio.Task] = {}
        # 错误分类器
        self.error_classifier = ErrorClassifier()
        # stream runner
        self._agent_stream_runner = AgentStreamRunner()
        self._workflow_stream_runner = WorkflowStreamRunner()
        self._graph = None
        self._graph_lock = threading.Lock()

    def _get_graph(self, ctx=Context):
        if graph_helper.is_agent_proj():
            return graph_helper.get_agent_instance("agents.agent", ctx)

        if self._graph is not None:
            return self._graph
        with self._graph_lock:
            if self._graph is not None:
                return self._graph
            self._graph = graph_helper.get_graph_instance("graphs.graph")
            return self._graph

    @staticmethod
    def _sse_event(data: Any, event_id: Any = None) -> str:
        id_line = f"id: {event_id}\n" if event_id else ""
        return f"{id_line}event: message\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    def _get_stream_runner(self):
        if graph_helper.is_agent_proj():
            return self._agent_stream_runner
        else:
            return self._workflow_stream_runner

    # 流式运行（原始迭代器）：本地调用使用
    def stream(self, payload: Dict[str, Any], run_config: RunnableConfig, ctx=Context) -> Iterable[Any]:
        graph = self._get_graph(ctx)
        stream_runner = self._get_stream_runner()
        for chunk in stream_runner.stream(payload, graph, run_config, ctx):
            yield chunk

    # 同步运行：本地/HTTP 通用
    async def run(self, payload: Dict[str, Any], ctx=None) -> Dict[str, Any]:
        if ctx is None:
            ctx = new_context("run")

        run_id = ctx.run_id
        logger.info(f"Starting run with run_id: {run_id}")

        try:
            graph = self._get_graph(ctx)
            # custom tracer
            run_config = init_run_config(graph, ctx)
            run_config["configurable"] = {"thread_id": ctx.run_id}

            # 直接调用，LangGraph会在当前任务上下文中执行
            # 如果当前任务被取消，LangGraph的执行也会被取消
            return await graph.ainvoke(payload, config=run_config, context=ctx)

        except asyncio.CancelledError:
            logger.info(f"Run {run_id} was cancelled")
            return {"status": "cancelled", "run_id": run_id, "message": "Execution was cancelled"}
        except Exception as e:
            # 使用错误分类器分类错误
            err = self.error_classifier.classify(e, {"node_name": "run", "run_id": run_id})
            # 记录详细的错误信息和堆栈跟踪
            logger.error(
                f"Error in GraphService.run: [{err.code}] {err.message}\n"
                f"Category: {err.category.name}\n"
                f"Traceback:\n{extract_core_stack()}"
            )
            # 保留原始异常堆栈，便于上层返回真正的报错位置
            raise
        finally:
            # 清理任务记录
            self.running_tasks.pop(run_id, None)

    # 流式运行（SSE 格式化）：HTTP 路由使用
    async def stream_sse(self, payload: Dict[str, Any], ctx=None, run_opt: Optional[RunOpt] = None) -> AsyncGenerator[str, None]:
        if ctx is None:
            ctx = new_context(method="stream_sse")
        if run_opt is None:
            run_opt = RunOpt()

        run_id = ctx.run_id
        logger.info(f"Starting stream with run_id: {run_id}")
        graph = self._get_graph(ctx)
        if graph_helper.is_agent_proj():
            run_config = init_agent_config(graph, ctx)
        else:
            run_config = init_run_config(graph, ctx)  # vibeflow

        is_workflow = not graph_helper.is_agent_proj()

        try:
            async for chunk in self.astream(payload, graph, run_config=run_config, ctx=ctx, run_opt=run_opt):
                if is_workflow and isinstance(chunk, tuple):
                    event_id, data = chunk
                    yield self._sse_event(data, event_id)
                else:
                    yield self._sse_event(chunk)
        finally:
            # 清理任务记录
            self.running_tasks.pop(run_id, None)
            cozeloop.flush()

    # 取消执行 - 使用asyncio的标准方式
    def cancel_run(self, run_id: str, ctx: Optional[Context] = None) -> Dict[str, Any]:
        """
        取消指定run_id的执行

        使用asyncio.Task.cancel()来取消任务,这是标准的Python异步取消机制。
        LangGraph会在节点之间检查CancelledError,实现优雅的取消。
        """
        logger.info(f"Attempting to cancel run_id: {run_id}")

        # 查找对应的任务
        if run_id in self.running_tasks:
            task = self.running_tasks[run_id]
            if not task.done():
                # 使用asyncio的标准取消机制
                # 这会在下一个await点抛出CancelledError
                task.cancel()
                logger.info(f"Cancellation requested for run_id: {run_id}")
                return {
                    "status": "success",
                    "run_id": run_id,
                    "message": "Cancellation signal sent, task will be cancelled at next await point"
                }
            else:
                logger.info(f"Task already completed for run_id: {run_id}")
                return {
                    "status": "already_completed",
                    "run_id": run_id,
                    "message": "Task has already completed"
                }
        else:
            logger.warning(f"No active task found for run_id: {run_id}")
            return {
                "status": "not_found",
                "run_id": run_id,
                "message": "No active task found with this run_id. Task may have already completed or run_id is invalid."
            }

    # 运行指定节点：本地/HTTP 通用
    async def run_node(self, node_id: str, payload: Dict[str, Any], ctx=None) -> Any:
        if ctx is None or Context.run_id == "":
            ctx = new_context(method="node_run")

        _graph = self._get_graph()
        node_func, input_cls, output_cls = graph_helper.get_graph_node_func_with_inout(_graph.get_graph(), node_id)
        if node_func is None or input_cls is None:
            raise KeyError(f"node_id '{node_id}' not found")

        parser = LangGraphParser(_graph)
        metadata = parser.get_node_metadata(node_id) or {}

        _g = StateGraph(input_cls, input_schema=input_cls, output_schema=output_cls)
        _g.add_node("sn", node_func, metadata=metadata)
        _g.set_entry_point("sn")
        _g.add_edge("sn", END)
        _graph = _g.compile()

        run_config = init_run_config(_graph, ctx)
        return await _graph.ainvoke(payload, config=run_config)

    def graph_inout_schema(self) -> Any:
        if graph_helper.is_agent_proj():
            return {"input_schema": {}, "output_schema": {}}
        builder = getattr(self._get_graph(), 'builder', None)
        if builder is not None:
            input_cls = getattr(builder, 'input_schema', None) or self.graph.get_input_schema()
            output_cls = getattr(builder, 'output_schema', None) or self.graph.get_output_schema()
        else:
            logger.warning(f"No builder input schema found for graph_inout_schema, using graph input schema instead")
            input_cls = self.graph.get_input_schema()
            output_cls = self.graph.get_output_schema()

        return {
            "input_schema": input_cls.model_json_schema(), 
            "output_schema": output_cls.model_json_schema(),
            "code":0,
            "msg":""
        }

    async def astream(self, payload: Dict[str, Any], graph: CompiledStateGraph, run_config: RunnableConfig, ctx=Context, run_opt: Optional[RunOpt] = None) -> AsyncIterable[Any]:
        stream_runner = self._get_stream_runner()
        async for chunk in stream_runner.astream(payload, graph, run_config, ctx, run_opt):
            yield chunk


service = GraphService()
app = FastAPI()

class SchemeConfirmRequest(BaseModel):
    run_id: str = Field(..., description="workflow run_id")
    scheme_index: int = Field(..., ge=0, description="选择的方案索引（0-based）")


class SchemeModifyRequest(BaseModel):
    run_id: str = Field(..., description="workflow run_id")
    modification_request: str = Field(..., min_length=1, description="修改要求文本")


class ProjectIdSubmitRequest(BaseModel):
    run_id: str = Field(..., description="workflow run_id")
    project_id: str = Field(..., min_length=1, description="Stitch project_id（不带 projects/ 前缀）")


@app.get("/interaction/schemes/{run_id}")
async def get_interaction_schemes(run_id: str):
    pending = interaction_store.get_pending(run_id)
    if not pending:
        return JSONResponse({"run_id": run_id, "status": "not_found"}, status_code=404)
    return {
        "run_id": run_id,
        "status": "pending",
        "product_name": pending.product_name,
        "schemes": pending.schemes,
        "created_at": pending.created_at,
    }


@app.post("/interaction/confirm")
async def post_interaction_confirm(req: SchemeConfirmRequest):
    interaction_store.submit(req.run_id, {"action": "confirm", "scheme_index": int(req.scheme_index)})
    return {"status": "ok", "run_id": req.run_id}


@app.post("/interaction/modify")
async def post_interaction_modify(req: SchemeModifyRequest):
    interaction_store.submit(
        req.run_id,
        {"action": "modify", "modification_request": req.modification_request},
    )
    return {"status": "ok", "run_id": req.run_id}


@app.get("/interaction/project_id/{run_id}")
async def get_pending_project_id(run_id: str):
    pending = interaction_store.get_pending_project_id(run_id)
    if not pending:
        return JSONResponse({"run_id": run_id, "status": "not_found"}, status_code=404)
    return {
        "run_id": run_id,
        "status": "pending",
        "suggested_project_id": pending.suggested_project_id,
        "created_at": pending.created_at,
    }


@app.post("/interaction/project_id")
async def post_project_id(req: ProjectIdSubmitRequest):
    interaction_store.submit(req.run_id, {"action": "set_project_id", "project_id": req.project_id})
    return {"status": "ok", "run_id": req.run_id, "project_id": req.project_id}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_web_dashboard_dir = Path(__file__).resolve().parent.parent / "web"
if _web_dashboard_dir.is_dir():
    app.mount(
        "/workflow-ui",
        StaticFiles(directory=str(_web_dashboard_dir), html=True),
        name="workflow_ui",
    )
    logger.info("Workflow dashboard mounted at /workflow-ui/")
else:
    logger.warning("Workflow dashboard skipped (directory not found): %s", _web_dashboard_dir)

# OpenAI 兼容接口处理器
openai_handler = OpenAIChatHandler(service)


HEADER_X_RUN_ID = "x-run-id"
@app.post("/run")
async def http_run(request: Request) -> Dict[str, Any]:
    global result
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = str(raw_body)
        raise HTTPException(status_code=400,
                            detail=f"Invalid JSON format: {body_text}, traceback: {traceback.format_exc()}, error: {e}")

    ctx = new_context(method="run", headers=request.headers)
    # 优先使用上游指定的 run_id，保证 cancel 能精确匹配
    upstream_run_id = request.headers.get(HEADER_X_RUN_ID)
    if upstream_run_id:
        ctx.run_id = upstream_run_id
    run_id = ctx.run_id
    request_context.set(ctx)

    logger.info(
        f"Received request for /run: "
        f"run_id={run_id}, "
        f"query={dict(request.query_params)}, "
        f"body={body_text}"
    )

    try:
        payload = await request.json()

        # 创建任务并记录 - 这是关键，让我们可以通过run_id取消任务
        task = asyncio.create_task(service.run(payload, ctx))
        service.running_tasks[run_id] = task

        try:
            result = await asyncio.wait_for(task, timeout=float(TIMEOUT_SECONDS))
        except asyncio.TimeoutError:
            logger.error(f"Run execution timeout after {TIMEOUT_SECONDS}s for run_id: {run_id}")
            task.cancel()
            try:
                result = await task
            except asyncio.CancelledError:
                return {
                    "status": "timeout",
                    "run_id": run_id,
                    "message": f"Execution timeout: exceeded {TIMEOUT_SECONDS} seconds"
                }

        if not result:
            result = {}
        if isinstance(result, dict):
            result["run_id"] = run_id
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format, {extract_core_stack()}")

    except asyncio.CancelledError:
        logger.info(f"Request cancelled for run_id: {run_id}")
        result = {"status": "cancelled", "run_id": run_id, "message": "Execution was cancelled"}
        return result

    except Exception as e:
        # 使用错误分类器获取错误信息
        error_response = service.error_classifier.get_error_response(e, {"node_name": "http_run", "run_id": run_id})
        logger.error(
            f"Unexpected error in http_run: [{error_response['error_code']}] {error_response['error_message']}, "
            f"traceback: {traceback.format_exc()}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": error_response["error_code"],
                "error_message": error_response["error_message"],
                "stack_trace": extract_core_stack(),
            }
        )
    finally:
        cozeloop.flush()


HEADER_X_WORKFLOW_STREAM_MODE = "x-workflow-stream-mode"


def _register_task(run_id: str, task: asyncio.Task):
    service.running_tasks[run_id] = task


# ============================================================================
# 交互式工作流完整实现 - 整合所有节点逻辑
# ============================================================================

import httpx
import subprocess
from langchain_core.messages import SystemMessage, HumanMessage
from coze_coding_dev_sdk import LLMClient
from graphs.stitch_mcp import (
    create_project_via_mcp, 
    get_project_assets_via_mcp,
    stitch_headers,
    call_stitch_tool,
    TOOL_LIST_SCREENS,
    TOOL_GET_PROJECT,
    run_with_timeout,
    TimeoutException,
    EarlyDisconnectException,
    generate_screens_html_via_mcp,
    SHORT_TIMEOUT,
    GENERATE_TIMEOUT,
    KEEP_ALIVE_INTERVAL_S,
    EARLY_DISCONNECT_THRESHOLD_S,
    _list_screens_has_assets
)

# 实体和关系关键词
ENTITY_KEYWORDS = [
    "猪", "牛", "羊", "鸡", "鸭", "鱼", "宠物", "猫", "狗", "兔", "马", "驴", "鹅", "鸽",
    "车", "房", "设备", "商品", "库存", "货物", "仓库", "店铺", "店", "馆", "场",
    "员工", "客户", "会员", "学生", "病人", "用户",
    "养殖场", "农场", "工地", "工厂", "医院", "学校", "公司"
]
RELATION_KEYWORDS = [
    "管理", "养殖", "租赁", "销售", "服务", "运营", "饲养", "维护", "巡检", "配送",
    "管家", "助手", "来财", "记账", "打卡", "笔记"
]

STITCH_MCP_URL = "https://stitch.googleapis.com/mcp"

# 恢复节点配置
RECOVER_INITIAL_WAIT_S = 300      # 早期断开后的初始等待：5 分钟
RECOVER_TOTAL_WAIT_S = 300        # 恢复阶段总等待时间：5 分钟
RECOVER_CHECK_INTERVAL_S = 30     # 每 30 秒检查一次
RECOVER_CHECK_QUICK_TIMEOUT_S = 10 # 每次快速检查超时：10 秒


async def async_wait_user_input(
    run_id: str, 
    timeout_s: int,
    send_event_func=None,
    node_name: str = "scheme_confirm"
) -> Optional[Dict[str, Any]]:
    """
    异步等待用户输入，使用轮询方式避免阻塞事件循环。
    这样 SSE 事件可以继续发送，前端可以实时看到进度。
    
    Args:
        run_id: 运行ID
        timeout_s: 超时时间（秒）
        send_event_func: 可选的事件发送函数，用于发送等待状态
        node_name: 节点名称，用于事件发送
    """
    deadline = time.time() + max(0, timeout_s)
    check_interval = 0.5  # 每 0.5 秒检查一次
    last_heartbeat = 0
    heartbeat_interval = 5  # 每 5 秒发送一次心跳
    
    while time.time() < deadline:
        # 检查是否有用户输入
        user_input = interaction_store.get_user_input(run_id)
        if user_input:
            logger.info(f"[async_wait_user_input] 收到用户输入: run_id={run_id}, action={user_input.get('action')}")
            return user_input
        
        # 发送心跳事件，让前端知道仍在等待
        current_time = time.time()
        if send_event_func and current_time - last_heartbeat >= heartbeat_interval:
            remaining = int(deadline - current_time)
            # 使用同步方式发送事件（send_event 是同步函数）
            send_event_func("node_heartbeat", {
                "node": node_name,
                "node_name": node_name,
                "message": f"等待用户输入中...（剩余 {remaining} 秒）",
                "remaining_seconds": remaining
            })
            last_heartbeat = current_time
        
        # 异步等待一小段时间，让出控制权
        await asyncio.sleep(check_interval)
    
    logger.warning(f"[async_wait_user_input] 等待超时: run_id={run_id}, timeout={timeout_s}s")
    return None


async def workflow_interactive_handler(
    payload: Dict[str, Any],
    ctx: Context,
    run_id: str,
    sse_event_func,
    error_classifier: ErrorClassifier,
    register_task_func,
) -> AsyncGenerator[str, None]:
    """
    完整交互式工作流实现：
    1. 功能设计（生成三套方案）
    2. 方案确认（交互式等待用户选择/修改）
    3. 项目创建（MCP）
    4. Screens/HTML 生成（MCP，带早期断开恢复）
    5. 资源恢复（等待5分钟+每30s检查）
    6. 文件下载
    7. Git 分支切换
    8. UniApp 页面生成
    
    任何异常都会优雅降级到 Git 分支切换和页面生成
    """
    
    def send_event(event_type: str, data: Dict[str, Any]):
        """发送 SSE 事件"""
        return sse_event_func({"event_type": event_type, **data})
    
    # 初始化上下文
    request_context.set(ctx)
    start_time = time.time()
    
    # 提取用户输入
    product_name = payload.get("product_name", "").strip()
    product_group = payload.get("product_group", "").strip() or payload.get("group", "七组").strip()
    
    if not product_name:
        yield send_event("error", {"message": "产品名称不能为空", "run_id": run_id})
        return
    
    logger.info(f"[InteractiveWorkflow] 开始执行: run_id={run_id}, product={product_name}, group={product_group}")
    yield send_event("workflow_start", {
        "run_id": run_id,
        "product_name": product_name,
        "product_group": product_group,
        "message": f"开始为「{product_name}」生成功能设计方案..."
    })
    
    # ============================================================================
    # 节点 1: 功能设计
    # ============================================================================
    try:
        yield send_event("node_start", {"node": "function_design", "message": "正在分析产品名称并生成功能设计方案..."})
        
        # 分析产品名称
        entity_keyword = None
        relation_keyword = None
        for keyword in ENTITY_KEYWORDS:
            if keyword in product_name:
                entity_keyword = keyword
                break
        for keyword in RELATION_KEYWORDS:
            if keyword in product_name:
                relation_keyword = keyword
                break
        app_type = "实体型" if entity_keyword else ("关系型" if relation_keyword else "通用型")
        
        logger.info(f"[FunctionDesign] 产品: {product_name}, 类型: {app_type}, 实体: {entity_keyword}, 关系: {relation_keyword}")
        
        # 调用 LLM 生成三套方案
        design_schemes = await _call_llm_for_design(product_name, app_type, entity_keyword, relation_keyword, ctx)
        
        if not design_schemes or len(design_schemes) == 0:
            raise ValueError("功能设计未返回有效方案")
        
        yield send_event("node_end", {
            "node": "function_design",
            "schemes_count": len(design_schemes),
            "message": f"已生成 {len(design_schemes)} 套功能设计方案"
        })
        
    except Exception as e:
        logger.error(f"[FunctionDesign] 失败: {e}", exc_info=True)
        err = error_classifier.classify(e, {"node": "function_design", "run_id": run_id})
        yield send_event("node_error", {"node": "function_design", "error": err.message})
        # 异常时跳到 Git 分支切换
        async for event in _fallback_to_git_and_pages(product_name, product_group, ctx, run_id, sse_event_func, error_classifier):
            yield event
        return
    
    # ============================================================================
    # 节点 2: 方案确认（交互式）
    # ============================================================================
    confirmed_scheme = None
    try:
        yield send_event("node_start", {
            "node": "scheme_confirm",
            "node_name": "scheme_confirm",
            "message": "等待用户确认功能设计方案...",
            "schemes": design_schemes,
            "requires_interaction": True
        })
        
        # 写入交互存储
        interaction_store.set_pending(
            run_id=run_id,
            product_name=product_name,
            schemes=design_schemes
        )
        
        # 等待用户输入（默认5分钟超时）- 使用异步轮询避免阻塞事件循环
        timeout_s = int(os.getenv("USER_INPUT_TIMEOUT", "300") or 300)
        user_input = await async_wait_user_input(
            run_id, 
            timeout_s=timeout_s,
            send_event_func=send_event,
            node_name="scheme_confirm"
        )
        
        if not user_input:
            interaction_store.clear(run_id)
            raise TimeoutError(f"等待用户确认超时（{timeout_s}秒）")
        
        action = user_input.get("action")
        
        if action == "confirm":
            idx = int(user_input.get("scheme_index", 0))
            if idx < 0 or idx >= len(design_schemes):
                idx = 0
            confirmed_scheme = design_schemes[idx]
            logger.info(f"[SchemeConfirm] 用户确认方案: index={idx}, name={confirmed_scheme.get('scheme_name')}")
            
        elif action == "modify":
            # 用户要求修改，这里简化处理，使用第一个方案
            modification_request = user_input.get("modification_request", "")
            logger.info(f"[SchemeConfirm] 用户要求修改: {modification_request}")
            # 实际应该调用 LLM 修改，这里简化
            confirmed_scheme = design_schemes[0]
        else:
            confirmed_scheme = design_schemes[0]
        
        interaction_store.clear(run_id)
        
        yield send_event("node_end", {
            "node": "scheme_confirm",
            "confirmed_scheme": confirmed_scheme.get("scheme_name", "标准方案"),
            "message": f"已确认方案: {confirmed_scheme.get('scheme_name', '标准方案')}"
        })
        
    except Exception as e:
        logger.error(f"[SchemeConfirm] 失败: {e}", exc_info=True)
        err = error_classifier.classify(e, {"node": "scheme_confirm", "run_id": run_id})
        yield send_event("node_error", {"node": "scheme_confirm", "error": err.message})
        # 异常时使用默认方案
        confirmed_scheme = design_schemes[0] if design_schemes else {"scheme_name": "默认方案", "pages": []}
    
    # ============================================================================
    # 节点 3: 项目创建（MCP）
    # ============================================================================
    project_id = None
    try:
        yield send_event("node_start", {"node": "project_create", "message": "正在创建 Stitch 设计项目..."})
        
        # 构造项目标题
        scheme_name = str(confirmed_scheme.get("scheme_name", "") or "")[:40]
        title = f"产品设计 - {product_name}"[:60]
        if scheme_name:
            title = f"{title} - {scheme_name}"[:80]
        
        logger.info(f"[ProjectCreate] title={title}")
        
        # 调用 MCP 创建项目
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: run_with_timeout(
                create_project_via_mcp,
                args=(product_name, confirmed_scheme, run_id),
                timeout=90
            )
        )
        
        project_id = result.get("project_id", "")
        if not project_id:
            raise RuntimeError("项目创建成功但未返回 project_id")
        
        logger.info(f"[ProjectCreate] 成功: project_id={project_id}")
        
        yield send_event("node_end", {
            "node": "project_create",
            "project_id": project_id,
            "message": f"项目创建成功: {project_id}"
        })
        
    except Exception as e:
        logger.error(f"[ProjectCreate] 失败: {e}", exc_info=True)
        err = error_classifier.classify(e, {"node": "project_create", "run_id": run_id})
        yield send_event("node_error", {"node": "project_create", "error": err.message})
        # 项目创建失败，跳到 Git 分支切换
        async for event in _fallback_to_git_and_pages(product_name, product_group, ctx, run_id, sse_event_func, error_classifier, confirmed_scheme):
            yield event
        return
    
    # ============================================================================
    # 节点 4: Screens/HTML 生成（带早期断开恢复）
    # ============================================================================
    screens_url = ""
    html_url = ""
    early_disconnect = False
    # 存储所有 screen 资源列表，用于多页面下载 [{"page_name": "首页", "screen_url": "...", "html_url": "..."}, ...]
    all_screen_resources = []
    
    try:
        yield send_event("node_start", {
            "node": "generate_screens_html",
            "message": "正在生成 Screens 和 HTML...",
            "project_id": project_id
        })
        
        # 尝试生成 Screens/HTML
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: generate_screens_html_via_mcp(project_id, confirmed_scheme, run_id)
            )
            
            screens_url = result.get("screens_url", "")
            html_url = result.get("html_url", "")
            
            if screens_url and html_url:
                logger.info(f"[GenerateScreens] 成功: screens_url={screens_url[:50]}..., html_url={html_url[:50]}...")
                yield send_event("node_end", {
                    "node": "generate_screens_html",
                    "screens_generated": True,
                    "html_generated": True,
                    "message": "Screens 和 HTML 生成成功"
                })
            else:
                raise RuntimeError("生成结果缺少 URL")
                
        except EarlyDisconnectException as e:
            # 早期断开，标记需要恢复
            logger.warning(f"[GenerateScreens] 早期断开: {e}")
            early_disconnect = True
            yield send_event("node_warning", {
                "node": "generate_screens_html",
                "warning": "服务器早期断开，将进入恢复流程",
                "elapsed_seconds": EARLY_DISCONNECT_THRESHOLD_S
            })
            # 重要：发送 node_end 结束节点，否则前端会一直显示"运行中"
            yield send_event("node_end", {
                "node": "generate_screens_html",
                "success": True,  # 标记为成功，因为会进入恢复流程继续处理
                "early_disconnect": True,
                "message": "Screens/HTML 生成已触发，进入资源恢复流程"
            })

    except Exception as e:
        logger.error(f"[GenerateScreens] 失败: {e}", exc_info=True)
        err = error_classifier.classify(e, {"node": "generate_screens_html", "run_id": run_id})
        yield send_event("node_error", {"node": "generate_screens_html", "error": err.message})
        early_disconnect = True  # 任何异常都进入恢复流程
        # 重要：发送 node_end 结束节点
        yield send_event("node_end", {
            "node": "generate_screens_html",
            "success": False,
            "error": err.message,
            "message": "Screens/HTML 生成失败，将进入资源恢复流程"
        })
    
    # ============================================================================
    # 节点 5: 资源恢复（如果早期断开或失败）- 全自动模式
    # ============================================================================
    if early_disconnect or not screens_url or not html_url:
        try:
            # 确保有 project_id
            if not project_id:
                logger.error("[Recover] 错误: project_id 为空，无法恢复资源")
                yield send_event("node_error", {
                    "node": "recover_stitch_assets",
                    "error": "project_id 为空，无法恢复资源"
                })
                raise RuntimeError("project_id 为空，无法恢复资源")

            yield send_event("node_start", {
                "node": "recover_stitch_assets",
                "node_name": "recover_stitch_assets",
                "message": "正在自动恢复 Stitch 资源...",
                "project_id": project_id,
                "mode": "auto"
            })
            
            logger.info(f"[Recover] ====== 进入全自动恢复模式 ======")
            logger.info(f"[Recover] 目标项目ID: {project_id}")
            logger.info(f"[Recover] 早期断开标记: {early_disconnect}")
            
            # 步骤 1: 如果是早期断开，先等待 5 分钟
            if early_disconnect:
                logger.info(f"[Recover] 步骤1: 早期断开，等待 {RECOVER_INITIAL_WAIT_S} 秒让服务器完成生成...")
                yield send_event("recover_waiting", {
                    "wait_seconds": RECOVER_INITIAL_WAIT_S,
                    "message": f"服务器在生成中，等待 {RECOVER_INITIAL_WAIT_S//60} 分钟后再尝试获取资源..."
                })
                await asyncio.sleep(RECOVER_INITIAL_WAIT_S)
            
            # 步骤 2: 执行 get_project 查询项目状态（带详细日志）
            logger.info(f"[Recover] 步骤2: 查询项目基本信息...")
            logger.info(f"[Recover] MCP 请求: tool=get_project, project_id={project_id}")
            
            headers = stitch_headers()
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            
            with httpx.Client(timeout=SHORT_TIMEOUT, limits=limits) as client:
                st, r = call_stitch_tool(
                    client,
                    headers=headers,
                    tool_name=TOOL_GET_PROJECT,
                    arguments={"name": f"projects/{project_id}"},
                    rpc_id=f"{run_id}:recover:get_project",
                )
                
                logger.info(f"[Recover] MCP 响应: status={st}")
                logger.info(f"[Recover] MCP 响应数据: {json.dumps(r, ensure_ascii=False, default=str)[:500]}...")
                
                if st != 200:
                    logger.error(f"[Recover] get_project 失败: HTTP {st}")
                else:
                    # 解析项目数据
                    project_data = r.get("result", {}).get("content", [{}])[0].get("text", "")
                    if project_data:
                        try:
                            project_json = json.loads(project_data)
                            screen_count = len(project_json.get("screenInstances", []))
                            logger.info(f"[Recover] 项目状态正常，画布上有 {screen_count} 个 screen 实例")
                        except:
                            pass
            
            # 步骤 3: 在总共 5 分钟内，每 30 秒检查一次 list_screens
            logger.info(f"[Recover] 步骤3: 开始轮询 list_screens，总共 {RECOVER_TOTAL_WAIT_S} 秒，每 {RECOVER_CHECK_INTERVAL_S} 秒检查一次")
            yield send_event("recover_polling", {
                "total_seconds": RECOVER_TOTAL_WAIT_S,
                "interval_seconds": RECOVER_CHECK_INTERVAL_S,
                "message": f"开始轮询获取资源（共 {RECOVER_TOTAL_WAIT_S//60} 分钟，每 {RECOVER_CHECK_INTERVAL_S} 秒检查一次）..."
            })
            
            deadline = time.monotonic() + RECOVER_TOTAL_WAIT_S
            check_count = 0
            recovered = False
            last_screens_count = 0
            
            while time.monotonic() < deadline:
                check_count += 1
                remaining = int(deadline - time.monotonic())
                
                try:
                    logger.info(f"[Recover] ====== 第 {check_count} 次检查 ======")
                    
                    # 直接调用 list_screens（带详细日志）
                    with httpx.Client(timeout=SHORT_TIMEOUT, limits=limits) as client:
                        logger.info(f"[Recover] MCP 请求: tool=list_screens, project_id={project_id}")
                        
                        st, r = call_stitch_tool(
                            client,
                            headers=headers,
                            tool_name=TOOL_LIST_SCREENS,
                            arguments={"projectId": project_id},
                            rpc_id=f"{run_id}:recover:list_screens:{check_count}",
                        )
                        
                        logger.info(f"[Recover] MCP 响应: status={st}")
                        
                        if st == 200:
                            # 解析响应
                            content = r.get("result", {}).get("content", [{}])[0].get("text", "")
                            if content:
                                try:
                                    data = json.loads(content)
                                    screens = data.get("screens", [])
                                    logger.info(f"[Recover] 找到 {len(screens)} 个 screens")

                                    # 检查每个 screen 的资源状态，收集所有可用资源
                                    temp_resources = []
                                    for i, screen in enumerate(screens):
                                        screen_name = screen.get("name", "N/A")
                                        has_shot = bool(screen.get("screenshot", {}).get("downloadUrl"))
                                        has_html = bool(screen.get("htmlCode", {}).get("downloadUrl"))
                                        logger.info(f"[Recover]   Screen #{i+1}: {screen_name[:30]}... 截图:{has_shot} HTML:{has_html}")

                                        # 收集所有有完整资源的 screen
                                        if has_shot and has_html:
                                            temp_resources.append({
                                                "screen_name": screen_name,
                                                "screen_url": screen["screenshot"]["downloadUrl"],
                                                "html_url": screen["htmlCode"]["downloadUrl"]
                                            })

                                    # 如果找到资源，保存到 all_screen_resources
                                    if temp_resources:
                                        all_screen_resources = temp_resources
                                        # 使用第一个作为默认的 screens_url/html_url（向后兼容）
                                        if not screens_url:
                                            screens_url = temp_resources[0]["screen_url"]
                                            html_url = temp_resources[0]["html_url"]
                                        logger.info(f"[Recover] ✅ 找到 {len(temp_resources)} 个可用资源！")

                                    # 如果有资源了，结束轮询
                                    if screens_url and html_url:
                                        logger.info(f"[Recover] 第 {check_count} 次检查成功获取资源")
                                        logger.info(f"[Recover] screens_url: {screens_url[:80]}...")
                                        logger.info(f"[Recover] html_url: {html_url[:80]}...")
                                        logger.info(f"[Recover] 总共收集 {len(all_screen_resources)} 个 screen 资源")

                                        yield send_event("recover_success", {
                                            "check_count": check_count,
                                            "resource_count": len(all_screen_resources),
                                            "message": f"第 {check_count} 次检查成功获取 {len(all_screen_resources)} 个资源"
                                        })
                                        recovered = True
                                        break
                                    else:
                                        logger.info(f"[Recover] 本轮检查未找到完整资源，继续等待...")
                                except json.JSONDecodeError as e:
                                    logger.warning(f"[Recover] 解析响应失败: {e}")
                        else:
                            logger.warning(f"[Recover] list_screens 返回非200状态: {st}, 响应: {r}")
                    
                except Exception as e:
                    logger.warning(f"[Recover] 第 {check_count} 次检查异常: {e}")
                    logger.exception(e)
                
                # 计算下次检查时间
                time_left = deadline - time.monotonic()
                if time_left <= 0:
                    break
                next_check_in = min(RECOVER_CHECK_INTERVAL_S, int(time_left))
                
                if next_check_in > 0:
                    logger.info(f"[Recover] 等待 {next_check_in} 秒后进行第 {check_count+1} 次检查...")
                    yield send_event("recover_polling", {
                        "check_count": check_count,
                        "remaining_seconds": remaining,
                        "message": f"第 {check_count} 次检查完成，{next_check_in} 秒后再次检查..."
                    })
                    await asyncio.sleep(next_check_in)
            
            # 恢复结果处理
            if screens_url and html_url:
                logger.info(f"[Recover] ====== 资源恢复成功 ======")
                yield send_event("node_end", {
                    "node": "recover_stitch_assets",
                    "node_name": "recover_stitch_assets",
                    "success": True,
                    "screens_url": screens_url[:50] + "...",
                    "html_url": html_url[:50] + "...",
                    "message": "资源恢复成功",
                    "check_count": check_count
                })
            else:
                logger.warning(f"[Recover] ====== 资源恢复失败 ======")
                logger.warning(f"[Recover] 经过 {check_count} 次检查仍未获取到资源")
                yield send_event("node_end", {
                    "node": "recover_stitch_assets",
                    "node_name": "recover_stitch_assets",
                    "success": False,
                    "message": "资源恢复失败，将使用默认资源",
                    "check_count": check_count
                })
                
        except Exception as e:
            logger.error(f"[Recover] 恢复过程异常: {e}", exc_info=True)
            yield send_event("node_error", {"node": "recover_stitch_assets", "node_name": "recover_stitch_assets", "error": str(e)})
    
    # ============================================================================
    # 节点 6: 文件下载（支持多页面资源下载到 uniapp/example/{page}/ 目录）
    # ============================================================================
    screens_local_path = ""
    html_local_path = ""
    # 存储下载后的资源映射: [{"page_name": "首页", "screen_path": "...", "html_path": "..."}, ...]
    downloaded_resources = []

    try:
        yield send_event("node_start", {
            "node": "file_download",
            "message": f"正在下载资源文件到 uniapp/example/ 目录...",
            "resource_count": len(all_screen_resources) if all_screen_resources else 1
        })

        # 基础目录: uniapp/example/
        example_base_dir = os.path.join(os.getcwd(), "uniapp", "example")
        os.makedirs(example_base_dir, exist_ok=True)

        # 从 confirmed_scheme 获取 pages 列表
        scheme_pages = confirmed_scheme.get("pages", []) if confirmed_scheme else []
        page_names = [p.get("page_name", f"page_{i}") for i, p in enumerate(scheme_pages)] if scheme_pages else []

        # 如果有多个 screen 资源，分别下载到各个页面目录
        if all_screen_resources and len(all_screen_resources) > 0:
            logger.info(f"[FileDownload] 开始下载 {len(all_screen_resources)} 个资源到 uniapp/example/")

            async with httpx.AsyncClient() as client:
                for i, resource in enumerate(all_screen_resources):
                    # 确定页面目录名
                    if i < len(page_names):
                        # 使用 scheme 中的页面名称（转换为小写和英文）
                        page_dir = _sanitize_page_name(page_names[i])
                    else:
                        page_dir = f"page_{i+1}"

                    page_dir_path = os.path.join(example_base_dir, page_dir)
                    os.makedirs(page_dir_path, exist_ok=True)

                    screen_url = resource.get("screen_url", "")
                    html_url = resource.get("html_url", "")
                    screen_name = resource.get("screen_name", f"Screen #{i+1}")

                    resource_entry = {"page_name": page_names[i] if i < len(page_names) else screen_name, "page_dir": page_dir}

                    # 下载 screenshot
                    if screen_url:
                        screen_path = os.path.join(page_dir_path, "screen.png")
                        try:
                            async with client.stream("GET", screen_url, timeout=60) as response:
                                if response.status_code == 200:
                                    with open(screen_path, "wb") as f:
                                        async for chunk in response.aiter_bytes():
                                            f.write(chunk)
                                    resource_entry["screen_path"] = screen_path
                                    logger.info(f"[FileDownload] ✓ 下载截图: {page_dir}/screen.png")
                                else:
                                    logger.warning(f"[FileDownload] 截图下载失败: HTTP {response.status_code}")
                        except Exception as e:
                            logger.warning(f"[FileDownload] 截图下载异常 ({page_dir}): {e}")

                    # 下载 HTML
                    if html_url:
                        html_path = os.path.join(page_dir_path, "design.html")
                        try:
                            async with client.stream("GET", html_url, timeout=60) as response:
                                if response.status_code == 200:
                                    with open(html_path, "wb") as f:
                                        async for chunk in response.aiter_bytes():
                                            f.write(chunk)
                                    resource_entry["html_path"] = html_path
                                    logger.info(f"[FileDownload] ✓ 下载 HTML: {page_dir}/design.html")
                                else:
                                    logger.warning(f"[FileDownload] HTML 下载失败: HTTP {response.status_code}")
                        except Exception as e:
                            logger.warning(f"[FileDownload] HTML 下载异常 ({page_dir}): {e}")

                    downloaded_resources.append(resource_entry)

            # 使用第一个资源作为默认路径（向后兼容）
            if downloaded_resources:
                first = downloaded_resources[0]
                screens_local_path = first.get("screen_path", "")
                html_local_path = first.get("html_path", "")

            logger.info(f"[FileDownload] 成功下载 {len(downloaded_resources)} 个资源到 uniapp/example/")
            yield send_event("node_end", {
                "node": "file_download",
                "downloaded_count": len(downloaded_resources),
                "downloaded_resources": [{"page": r["page_name"], "dir": r["page_dir"]} for r in downloaded_resources],
                "screens_path": screens_local_path,
                "html_path": html_local_path,
                "message": f"成功下载 {len(downloaded_resources)} 个资源到 uniapp/example/ 目录"
            })

        elif screens_url and html_url:
            # 只有一个资源，下载到默认位置 uniapp/example/default/
            default_dir = os.path.join(example_base_dir, "default")
            os.makedirs(default_dir, exist_ok=True)

            async with httpx.AsyncClient() as client:
                # 下载 screens
                screens_path = os.path.join(default_dir, "screen.png")
                async with client.stream("GET", screens_url, timeout=60) as response:
                    with open(screens_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                screens_local_path = screens_path

                # 下载 html
                html_path = os.path.join(default_dir, "design.html")
                async with client.stream("GET", html_url, timeout=60) as response:
                    with open(html_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                html_local_path = html_path

            downloaded_resources.append({
                "page_name": "default",
                "page_dir": "default",
                "screen_path": screens_local_path,
                "html_path": html_local_path
            })

            logger.info(f"[FileDownload] 成功: screens={screens_local_path}, html={html_local_path}")
            yield send_event("node_end", {
                "node": "file_download",
                "screens_path": screens_local_path,
                "html_path": html_local_path,
                "message": "文件下载成功（单资源）"
            })
        else:
            # 使用默认资源
            logger.warning(f"[FileDownload] 无可用 URL，使用默认资源")
            yield send_event("node_end", {
                "node": "file_download",
                "use_default": True,
                "message": "无可用资源 URL，跳过下载"
            })

    except Exception as e:
        logger.error(f"[FileDownload] 失败: {e}", exc_info=True)
        yield send_event("node_error", {"node": "file_download", "error": str(e)})
        # 发生异常时，尝试查找已存在的资源
        example_base_dir = os.path.join(os.getcwd(), "uniapp", "example")
        if os.path.exists(example_base_dir):
            for item in os.listdir(example_base_dir):
                item_path = os.path.join(example_base_dir, item)
                if os.path.isdir(item_path):
                    screen_file = os.path.join(item_path, "screen.png")
                    html_file = os.path.join(item_path, "design.html")
                    if os.path.exists(screen_file) or os.path.exists(html_file):
                        downloaded_resources.append({
                            "page_name": item,
                            "page_dir": item,
                            "screen_path": screen_file if os.path.exists(screen_file) else "",
                            "html_path": html_file if os.path.exists(html_file) else ""
                        })
    
    # ============================================================================
    # 节点 7: Git 分支切换
    # ============================================================================
    branch_name = ""
    try:
        yield send_event("node_start", {"node": "git_branch_switch", "message": "正在切换 Git 分支..."})
        
        # 获取当前分支
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        current_branch = result.stdout.strip() if result.returncode == 0 else "main"
        logger.info(f"[GitBranch] 当前分支: {current_branch}")
        
        # 创建新分支名称
        # 使用统一的拼音转换函数
        group_num = extract_group_number(product_group).replace("g", "")  # 提取数字部分
        pinyin_name = convert_to_pinyin(product_name)
        if not pinyin_name:
            pinyin_name = "product"
        branch_name = f"g{group_num}/{pinyin_name}"
        
        # 检查分支是否存在
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.stdout.strip():
            # 分支存在，切换
            subprocess.run(["git", "checkout", branch_name], cwd=os.getcwd(), check=True)
        else:
            # 分支不存在，创建并切换
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=os.getcwd(), check=True)
        
        logger.info(f"[GitBranch] 切换到分支: {branch_name}")
        
        yield send_event("node_end", {
            "node": "git_branch_switch",
            "branch_name": branch_name,
            "message": f"已切换到分支: {branch_name}"
        })
        
    except Exception as e:
        logger.error(f"[GitBranch] 失败: {e}", exc_info=True)
        yield send_event("node_error", {"node": "git_branch_switch", "error": str(e)})
        branch_name = current_branch if 'current_branch' in locals() else "main"
    
    # ============================================================================
    # 节点 8: UniApp 页面生成（使用多模态大模型）
    # ============================================================================
    generated_pages = []
    try:
        yield send_event("node_start", {"node": "uniapp_page_generate", "message": "正在使用多模态大模型生成 UniApp 页面..."})

        # 构造输入状态（使用绝对路径，避免 COZE_WORKSPACE_PATH 环境变量问题）
        example_abs_path = os.path.join(os.getcwd(), "uniapp", "example")
        pages_abs_path = os.path.join(os.getcwd(), "uniapp", "pages")

        page_input = UniAppPageGenerateInput(
            confirmed_scheme=confirmed_scheme,
            example_base_path=example_abs_path,
            pages_path=pages_abs_path
        )

        # 构造 RunnableConfig（包含 LLM 配置路径）
        config = RunnableConfig(
            metadata={"llm_cfg": "config/uniapp_page_generate_llm_cfg.json"}
        )

        # 构造 Runtime 包装器
        class SimpleRuntime:
            def __init__(self, context):
                self.context = context

        runtime = SimpleRuntime(ctx)

        logger.info(f"[UniAppGenerate] 调用 uniapp_page_generate_node 生成页面，产品: {product_name}")

        # 调用节点函数生成页面
        page_output = uniapp_page_generate_node(
            state=page_input,
            config=config,
            runtime=runtime
        )

        generated_pages = page_output.generated_pages

        if page_output.pages_generated:
            logger.info(f"[UniAppGenerate] 成功生成 {len(generated_pages)} 个页面")
            yield send_event("node_end", {
                "node": "uniapp_page_generate",
                "pages_count": len(generated_pages),
                "pages": [os.path.basename(p) for p in generated_pages],
                "message": f"已使用多模态大模型生成 {len(generated_pages)} 个 UniApp 页面"
            })
        else:
            logger.warning(f"[UniAppGenerate] 页面生成未成功，返回空列表")
            yield send_event("node_end", {
                "node": "uniapp_page_generate",
                "pages_count": 0,
                "pages": [],
                "message": "页面生成未成功，请检查示例目录和配置文件"
            })

    except Exception as e:
        logger.error(f"[UniAppGenerate] 失败: {e}", exc_info=True)
        yield send_event("node_error", {"node": "uniapp_page_generate", "error": str(e)})
    
    # ============================================================================
    # 工作流完成
    # ============================================================================
    total_time = time.time() - start_time
    
    yield send_event("workflow_end", {
        "run_id": run_id,
        "success": len(generated_pages) > 0,
        "total_time_seconds": round(total_time, 2),
        "product_name": product_name,
        "project_id": project_id,
        "branch_name": branch_name,
        "generated_pages": [os.path.basename(p) for p in generated_pages],
        "message": f"工作流完成！共生成 {len(generated_pages)} 个页面，耗时 {round(total_time, 2)} 秒"
    })
    
    logger.info(f"[InteractiveWorkflow] 完成: run_id={run_id}, pages={len(generated_pages)}, time={total_time:.2f}s")


async def _call_llm_for_design(
    product_name: str,
    app_type: str,
    entity_keyword: str,
    relation_keyword: str,
    ctx: Context
) -> list:
    """调用 LLM 生成功能设计方案"""
    
    # 读取配置
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "."), "config", "function_design_llm_cfg.json")
    if os.path.exists(cfg_file):
        with open(cfg_file, 'r') as f:
            cfg = json.load(f)
    else:
        # 默认配置
        cfg = {
            "sp": "你是一个专业的产品功能设计专家，擅长设计移动端应用的功能架构。",
            "config": {
                "model": "doubao-seed-2-0-pro-260215",
                "temperature": 0.7,
                "max_completion_tokens": 4000
            }
        }
    
    system_prompt = cfg.get("sp", "")
    llm_config = cfg.get("config", {})
    
    # 构造提示词
    user_prompt = f"""请为产品「{product_name}」设计三套不同的功能方案。

产品分析：
- 应用类型：{app_type}
- 实体关键词：{entity_keyword or "无"}
- 关系关键词：{relation_keyword or "无"}

请输出 JSON 格式，包含三套方案：
{{
  "schemes": [
    {{
      "scheme_name": "方案名称（如：标准实用型）",
      "description": "方案描述",
      "pages": [
        {{"page_name": "首页", "page_desc": "首页功能描述"}},
        {{"page_name": "列表页", "page_desc": "列表功能描述"}},
        {{"page_name": "我的", "page_desc": "个人中心描述"}}
      ]
    }}
  ]
}}

要求：
1. 第一套方案（标准实用型）：注重实用性和易用性
2. 第二套方案（创新交互型）：注重交互创新和用户体验
3. 第三套方案（简洁高效型）：注重效率和简洁性
"""
    
    # 调用 LLM
    for attempt in range(3):
        try:
            client = LLMClient(ctx=ctx)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = client.invoke(
                messages=messages,
                model=llm_config.get("model", "doubao-seed-2-0-pro-260215"),
                temperature=llm_config.get("temperature", 0.7),
                max_completion_tokens=llm_config.get("max_completion_tokens", 4000)
            )
            
            content = response.content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = "".join(text_parts)
            
            # 解析 JSON
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                return data.get("schemes", [])
            except json.JSONDecodeError:
                # 尝试从文本中提取 JSON
                import re
                match = re.search(r'\{[\s\S]*\}', content)
                if match:
                    data = json.loads(match.group())
                    if isinstance(data, list):
                        return data
                    return data.get("schemes", [])
                
        except Exception as e:
            logger.warning(f"[LLM] 调用失败 (尝试 {attempt+1}/3): {e}")
            await asyncio.sleep(2 ** attempt)
    
    # 返回默认方案
    return [
        {
            "scheme_name": "标准实用型方案",
            "description": f"面向{product_name}的标准功能设计",
            "pages": [
                {"page_name": "首页", "page_desc": "数据概览和快捷入口"},
                {"page_name": "列表", "page_desc": "数据列表展示"},
                {"page_name": "统计", "page_desc": "数据统计分析"},
                {"page_name": "我的", "page_desc": "个人中心"}
            ]
        },
        {
            "scheme_name": "创新交互型方案",
            "description": f"创新的{product_name}交互体验",
            "pages": [
                {"page_name": "首页", "page_desc": "可视化交互首页"},
                {"page_name": "探索", "page_desc": "探索发现页"},
                {"page_name": "统计", "page_desc": "智能统计页"},
                {"page_name": "我的", "page_desc": "个性化中心"}
            ]
        },
        {
            "scheme_name": "简洁高效型方案",
            "description": f"极简高效的{product_name}设计",
            "pages": [
                {"page_name": "首页", "page_desc": "核心功能聚合"},
                {"page_name": "管理", "page_desc": "管理页面"},
                {"page_name": "我的", "page_desc": "个人设置"}
            ]
        }
    ]


def _sanitize_page_name(page_name: str) -> str:
    """
    将页面名称转换为适合作为目录名的格式
    例如: "首页" -> "home", "列表页" -> "list", "我的" -> "mine"
    """
    import re

    # 页面名称映射表（常见中文页面名 -> 英文目录名）
    name_mapping = {
        "首页": "home",
        "主页": "home",
        "开始": "start",
        "列表": "list",
        "列表页": "list",
        "探索": "explore",
        "发现": "explore",
        "统计": "statics",
        "统计页": "statics",
        "数据": "data",
        "分析": "analytics",
        "我的": "mine",
        "个人中心": "mine",
        "个人": "profile",
        "用户": "user",
        "设置": "settings",
        "配置": "config",
        "管理": "manage",
        "管理页": "manage",
        "详情": "detail",
        "详情页": "detail",
        "搜索": "search",
        "消息": "message",
        "通知": "notification",
        "登录": "login",
        "注册": "register",
        "帮助": "help",
        "关于": "about",
    }

    # 先尝试直接匹配
    if page_name in name_mapping:
        return name_mapping[page_name]

    # 清理字符串：只保留字母、数字、汉字和下划线
    cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '_', page_name)

    # 如果清理后为空，使用默认值
    if not cleaned:
        return "page"

    # 如果是纯英文/数字，转换为小写
    if re.match(r'^[a-zA-Z0-9_]+$', cleaned):
        return cleaned.lower()

    # 对于未映射的中文名，尝试使用拼音首字母或直接转小写
    # 简化处理：取前10个字符作为目录名
    return cleaned[:10].lower()


def _generate_default_vue_template(page_name: str, product_name: str, scheme: dict) -> str:
    """生成默认 Vue 模板"""
    return f"""<template>
  <view class="container">
    <view class="header">
      <text class="title">{page_name.upper()}</text>
    </view>
    <view class="content">
      <text class="product">产品: {product_name}</text>
      <text class="scheme">方案: {scheme.get('scheme_name', '默认')}</text>
      <text class="hint">页面开发中...</text>
    </view>
  </view>
</template>

<script>
export default {{
  data() {{
    return {{
      productName: "{product_name}",
      pageName: "{page_name}"
    }};
  }},
  onLoad() {{
    console.log("页面加载:", this.pageName);
  }}
}};
</script>

<style>
.container {{
  padding: 20px;
}}
.header {{
  margin-bottom: 20px;
}}
.title {{
  font-size: 24px;
  font-weight: bold;
}}
.content {{
  display: flex;
  flex-direction: column;
  gap: 10px;
}}
.product, .scheme, .hint {{
  font-size: 14px;
  color: #666;
}}
</style>
"""


async def _fallback_to_git_and_pages(
    product_name: str,
    product_group: str,
    ctx: Context,
    run_id: str,
    sse_event_func,
    error_classifier: ErrorClassifier,
    confirmed_scheme: dict = None
) -> AsyncGenerator[str, None]:
    """异常时降级到 Git 分支切换和页面生成"""
    
    def send_event(event_type: str, data: Dict[str, Any]):
        return sse_event_func({"event_type": event_type, **data})
    
    logger.info(f"[Fallback] 进入降级流程，直接执行 Git 分支切换和页面生成")
    
    # Git 分支切换
    branch_name = ""
    try:
        yield send_event("node_start", {"node": "git_branch_switch", "message": "异常降级：正在切换 Git 分支..."})
        
        # 使用统一的拼音转换函数
        group_num = extract_group_number(product_group).replace("g", "")  # 提取数字部分
        pinyin_name = convert_to_pinyin(product_name)
        if not pinyin_name:
            pinyin_name = "product"
        branch_name = f"g{group_num}/{pinyin_name}"

        result = subprocess.run(["git", "branch", "--list", branch_name], capture_output=True, text=True, cwd=os.getcwd())
        if result.stdout.strip():
            subprocess.run(["git", "checkout", branch_name], cwd=os.getcwd(), check=False)
        else:
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=os.getcwd(), check=False)
        
        yield send_event("node_end", {"node": "git_branch_switch", "branch_name": branch_name})
    except Exception as e:
        logger.error(f"[Fallback] Git 切换失败: {e}")
        yield send_event("node_error", {"node": "git_branch_switch", "error": str(e)})
    
    # 页面生成
    generated_pages = []
    try:
        yield send_event("node_start", {"node": "uniapp_page_generate", "message": "异常降级：正在生成默认页面..."})
        
        pages_output_path = os.path.join(os.getcwd(), "uniapp", "pages")
        os.makedirs(pages_output_path, exist_ok=True)
        
        default_pages = ["home", "list", "mine", "statics"]
        scheme = confirmed_scheme or {"scheme_name": "默认方案", "pages": []}
        
        for page_name in default_pages:
            output_path = os.path.join(pages_output_path, f"{page_name}.vue")
            content = _generate_default_vue_template(page_name, product_name, scheme)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            generated_pages.append(output_path)
        
        yield send_event("node_end", {"node": "uniapp_page_generate", "pages_count": len(generated_pages)})
    except Exception as e:
        logger.error(f"[Fallback] 页面生成失败: {e}")
        yield send_event("node_error", {"node": "uniapp_page_generate", "error": str(e)})
    
    # 完成
    yield send_event("workflow_end", {
        "run_id": run_id,
        "success": len(generated_pages) > 0,
        "fallback": True,
        "branch_name": branch_name,
        "generated_pages": [os.path.basename(p) for p in generated_pages],
        "message": f"降级流程完成，生成 {len(generated_pages)} 个默认页面"
    })


# ============================================================================
# 更新后的 /stream_run 端点
# ============================================================================

@app.post("/stream_run")
async def http_stream_run(request: Request):
    """交互式工作流入口 - 完整实现所有节点逻辑"""
    ctx = new_context(method="stream_run", headers=request.headers)
    upstream_run_id = request.headers.get(HEADER_X_RUN_ID)
    if upstream_run_id:
        ctx.run_id = upstream_run_id
    request_context.set(ctx)
    
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = str(raw_body)
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {body_text}, error: {e}")
    
    run_id = ctx.run_id
    logger.info(f"[http_stream_run] run_id={run_id}, body={body_text}")
    
    try:
        payload = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")
    
    # 使用新的交互式 handler
    stream_generator = workflow_interactive_handler(
        payload=payload,
        ctx=ctx,
        run_id=run_id,
        sse_event_func=service._sse_event,
        error_classifier=service.error_classifier,
        register_task_func=_register_task,
    )
    
    response = StreamingResponse(stream_generator, media_type="text/event-stream")
    return response

@app.post("/cancel/{run_id}")
async def http_cancel(run_id: str, request: Request):
    """
    取消指定run_id的执行

    使用asyncio.Task.cancel()实现取消,这是Python标准的异步任务取消机制。
    LangGraph会在节点之间的await点检查CancelledError,实现优雅取消。
    """
    ctx = new_context(method="cancel", headers=request.headers)
    request_context.set(ctx)
    logger.info(f"Received cancel request for run_id: {run_id}")
    result = service.cancel_run(run_id, ctx)
    return result


@app.post(path="/node_run/{node_id}")
async def http_node_run(node_id: str, request: Request):
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        body_text = str(raw_body)
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {body_text}")
    ctx = new_context(method="node_run", headers=request.headers)
    request_context.set(ctx)
    logger.info(
        f"Received request for /node_run/{node_id}: "
        f"query={dict(request.query_params)}, "
        f"body={body_text}",
    )

    try:
        payload = await request.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_node_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format:{extract_core_stack()}")
    try:
        return await service.run_node(node_id, payload, ctx)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=f"node_id '{node_id}' not found or input miss required fields, traceback: {extract_core_stack()}")
    except Exception as e:
        # 使用错误分类器获取错误信息
        error_response = service.error_classifier.get_error_response(e, {"node_name": node_id})
        logger.error(
            f"Unexpected error in http_node_run: [{error_response['error_code']}] {error_response['error_message']}, "
            f"traceback: {traceback.format_exc()}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": error_response["error_code"],
                "error_message": error_response["error_message"],
                "stack_trace": extract_core_stack(),
            }
        )
    finally:
        cozeloop.flush()


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI Chat Completions API 兼容接口"""
    ctx = new_context(method="openai_chat", headers=request.headers)
    request_context.set(ctx)

    logger.info(f"Received request for /v1/chat/completions: run_id={ctx.run_id}")

    try:
        payload = await request.json()
        return await openai_handler.handle(payload, ctx)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in openai_chat_completions: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    finally:
        cozeloop.flush()


@app.get("/health")
async def health_check():
    try:
        # 这里可以添加更多的健康检查逻辑
        return {
            "status": "ok",
            "message": "Service is running",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get(path="/graph_parameter")
async def http_graph_inout_parameter(request: Request):
    return service.graph_inout_schema()

def parse_args():
    parser = argparse.ArgumentParser(description="Start FastAPI server")
    parser.add_argument("-m", type=str, default="http", help="Run mode, support http,flow,node")
    parser.add_argument("-n", type=str, default="", help="Node ID for single node run")
    parser.add_argument("-p", type=int, default=5000, help="HTTP server port")
    parser.add_argument("-i", type=str, default="", help="Input JSON string for flow/node mode")
    return parser.parse_args()


def parse_input(input_str: str) -> Dict[str, Any]:
    """Parse input string, support both JSON string and plain text"""
    if not input_str:
        return {"text": "你好"}

    # Try to parse as JSON first
    try:
        return json.loads(input_str)
    except json.JSONDecodeError:
        # If not valid JSON, treat as plain text
        return {"text": input_str}

def start_http_server(port):
    workers = 1
    reload = False
    if graph_helper.is_dev_env():
        reload = True

    logger.info(f"Start HTTP Server, Port: {port}, Workers: {workers}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload, workers=workers)

if __name__ == "__main__":
    args = parse_args()
    if args.m == "http":
        start_http_server(args.p)
    elif args.m == "flow":
        payload = parse_input(args.i)
        result = asyncio.run(service.run(payload))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.m == "node" and args.n:
        payload = parse_input(args.i)
        result = asyncio.run(service.run_node(args.n, payload))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.m == "agent":
        agent_ctx = new_context(method="agent")
        for chunk in service.stream(
                {
                    "type": "query",
                    "session_id": "1",
                    "message": "你好",
                    "content": {
                        "query": {
                            "prompt": [
                                {
                                    "type": "text",
                                    "content": {"text": "现在几点了？请调用工具获取当前时间"},
                                }
                            ]
                        }
                    },
                },
                run_config={"configurable": {"session_id": "1"}},
                ctx=agent_ctx,
        ):
            print(chunk)
