"""
方案确认和修改节点：展示三套方案给用户确认，等待用户选择或提出修改要求
"""
import json
import os
import logging
from typing import Any, Dict, List
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from langchain_core.messages import SystemMessage, HumanMessage
from coze_coding_dev_sdk import LLMClient
from graphs.state import SchemeConfirmInput, SchemeConfirmOutput
from utils.interaction_store import interaction_store

logger = logging.getLogger(__name__)


def scheme_confirm_node(
    state: SchemeConfirmInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SchemeConfirmOutput:
    """
    title: 方案确认和修改
    desc: 展示三套方案给用户确认，等待用户选择或提出修改要求
    integrations: Coze大模型
    """
    ctx = runtime.context
    
    # 检查是否启用交互模式（默认启用）
    interactive_mode = os.getenv("ENABLE_INTERACTIVE_MODE", "true").lower() == "true"
    
    # 读取大模型配置
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r') as fd:
        _cfg = json.load(fd)
    
    sp = _cfg.get("sp", "")
    
    if interactive_mode:
        # 交互模式：等待用户输入
        logger.info("启用交互模式，等待用户确认方案...")
        return handle_interactive_mode(state, sp, ctx)
    else:
        # 自动模式：默认选择第一个方案
        logger.info("启用自动模式，自动选择第一个方案...")
        return handle_auto_mode(state, ctx)


def handle_interactive_mode(
    state: SchemeConfirmInput,
    system_prompt: str,
    ctx: Context
) -> SchemeConfirmOutput:
    """
    处理交互模式：展示方案并等待用户确认
    """
    run_id = getattr(ctx, "run_id", None) or "workflow"
    logger.info("启用交互模式：run_id=%s，等待用户确认/修改方案", run_id)

    schemes: List[Dict[str, Any]] = list(state.design_schemes or [])
    if not schemes:
        raise ValueError("交互模式下 design_schemes 为空，无法展示给用户确认")

    # 将方案写入交互存储，供 Web 前端拉取
    interaction_store.set_pending(run_id=run_id, product_name=state.product_name, schemes=schemes)

    timeout_s = int(os.getenv("USER_INPUT_TIMEOUT", "300") or 300)
    user_input = interaction_store.wait_user_input(run_id, timeout_s=timeout_s)
    if not user_input:
        interaction_store.clear(run_id)
        raise TimeoutError(f"等待用户确认超时（{timeout_s}s），run_id={run_id}")

    action = user_input.get("action")
    if action == "confirm":
        idx = int(user_input.get("scheme_index", 0))
        if idx < 0 or idx >= len(schemes):
            interaction_store.clear(run_id)
            raise ValueError(f"scheme_index 越界: {idx}，schemes_len={len(schemes)}")
        confirmed_scheme_index = idx
        confirmed_scheme = schemes[confirmed_scheme_index]
        interaction_store.clear(run_id)
        logger.info("用户已确认方案：index=%s name=%s", confirmed_scheme_index, confirmed_scheme.get("scheme_name"))
        return SchemeConfirmOutput(
            confirmed_scheme_index=confirmed_scheme_index,
            confirmed_scheme=confirmed_scheme,
            needs_modification=False,
            modification_request="",
            product_name=state.product_name,
            user_interaction_type="interactive",
            user_input_source="real_user_input",
        )

    if action == "modify":
        modification_request = str(user_input.get("modification_request", "") or "").strip()
        if not modification_request:
            interaction_store.clear(run_id)
            raise ValueError("modification_request 为空")
        logger.info("用户提交修改要求：%s", modification_request[:200])
        out = handle_user_modification(state, modification_request, system_prompt, ctx)
        interaction_store.clear(run_id)
        return out

    interaction_store.clear(run_id)
    raise ValueError(f"未知用户动作: {action}")


def handle_auto_mode(
    state: SchemeConfirmInput,
    ctx: Context
) -> SchemeConfirmOutput:
    """
    处理自动模式：直接选择第一个方案
    """
    if not state.design_schemes:
        raise ValueError("design_schemes 为空：上游 function_design 未产出可用的三套方案")
    confirmed_scheme_index = 0
    confirmed_scheme = state.design_schemes[confirmed_scheme_index]
    
    logger.info(f"自动选择方案 {confirmed_scheme_index}: {confirmed_scheme.get('scheme_name')}")
    
    return SchemeConfirmOutput(
        confirmed_scheme_index=confirmed_scheme_index,
        confirmed_scheme=confirmed_scheme,
        needs_modification=False,
        modification_request="",
        product_name=state.product_name,
        user_interaction_type="automatic",
        user_input_source="auto_selection"
    )


def handle_user_modification(
    state: SchemeConfirmInput,
    modification_request: str,
    system_prompt: str,
    ctx: Context
) -> SchemeConfirmOutput:
    """
    处理用户提出的修改要求
    """
    try:
        # 读取配置
        cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), "config/scheme_confirm_llm_cfg.json")
        with open(cfg_file, 'r') as fd:
            _cfg = json.load(fd)
        
        llm_config = _cfg.get("config", {})
        # 构造修改提示词
        prompt = f"""用户对功能设计方案提出了以下修改要求：

{modification_request}

请根据用户的要求，修改当前的功能设计方案，并返回修改后的完整方案内容。

当前方案：
{json.dumps(state.design_schemes, ensure_ascii=False, indent=2)}

请返回修改后的方案，保持原有的JSON格式。"""

        # 调用火山方舟模型
        result = call_openai_llm_for_modification(system_prompt, prompt, llm_config, ctx)
        
        # 解析修改后的方案
        try:
            modified_schemes = json.loads(result)
            
            confirmed_scheme_index = 0
            confirmed_scheme = modified_schemes[confirmed_scheme_index]
            
            return SchemeConfirmOutput(
                confirmed_scheme_index=confirmed_scheme_index,
                confirmed_scheme=confirmed_scheme,
                needs_modification=False,
                modification_request="",
                product_name=state.product_name,
                user_interaction_type="interactive",
                user_input_source="real_user_input"
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"解析修改后的方案失败: {e}")
            return SchemeConfirmOutput(
                confirmed_scheme_index=0,
                confirmed_scheme=state.design_schemes[0],
                needs_modification=True,
                modification_request=modification_request,
                product_name=state.product_name,
                user_interaction_type="interactive",
                user_input_source="real_user_input",
                error=f"修改失败: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"处理用户修改要求失败: {e}", exc_info=True)
        return SchemeConfirmOutput(
            confirmed_scheme_index=0,
            confirmed_scheme=state.design_schemes[0],
            needs_modification=True,
            modification_request=modification_request,
            product_name=state.product_name,
            user_interaction_type="interactive",
            user_input_source="real_user_input",
            error=f"修改失败: {str(e)}"
        )


def call_openai_llm_for_modification(
    system_prompt: str, 
    user_prompt: str, 
    llm_config: dict, 
    ctx: Context,
    max_retries: int = 3
) -> str:
    """调用火山方舟大模型处理修改要求，带重试机制"""
    import time
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # 初始化LLM客户端
            client = LLMClient(ctx=ctx)
            
            # 构造消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            logger.info(f"调用火山方舟模型处理修改 (尝试 {attempt + 1}/{max_retries})...")
            
            # 调用模型
            response = client.invoke(
                messages=messages,
                model=llm_config.get("model", "doubao-seed-2-0-pro-260215"),
                temperature=llm_config.get("temperature", 0.3),
                max_completion_tokens=llm_config.get("max_completion_tokens", 4000)
            )
            
            # 处理响应
            content = response.content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = "".join(text_parts)
            
            logger.info(f"火山方舟模型调用成功")
            return content
            
        except Exception as e:
            last_error = e
            logger.warning(f"调用火山方舟模型失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error(f"调用火山方舟模型最终失败: {e}")
    
    raise last_error
