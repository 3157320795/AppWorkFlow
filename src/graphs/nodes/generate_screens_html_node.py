"""
Screens和HTML生成节点：通过 Stitch MCP 的 generate_screen_from_text + list_screens 获取资源 URL
"""
import logging
import os
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import GenerateScreensHtmlInput, GenerateScreensHtmlOutput
from graphs.stitch_mcp import generate_screens_html_via_mcp, run_with_timeout, TimeoutException, EarlyDisconnectException

logger = logging.getLogger(__name__)

# create_project + 生成 + 轮询 list_screens，默认可达 10 分钟以上
_GENERATE_NODE_TIMEOUT = int(os.getenv("STITCH_GENERATE_NODE_TIMEOUT_SECONDS", "720"))


def generate_screens_html_node(
    state: GenerateScreensHtmlInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> GenerateScreensHtmlOutput:
    """
    title: Screens和HTML生成
    desc: 将产品功能发送至项目生成对应的screens及html，超时或异常则使用默认资源
    integrations: stitch mcp
    """
    ctx = runtime.context
    run_id = getattr(ctx, "run_id", None) or "workflow"

    if state.error_occurred or state.use_default_resource:
        logger.warning("上游发生异常或标记使用默认资源，直接使用默认本地路径")
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=True
        )

    if not state.project_id:
        logger.warning("project_id为空，使用默认资源")
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=True
        )

    try:
        result_dict: dict = run_with_timeout(
            generate_screens_html_via_mcp,
            args=(state.project_id, state.confirmed_scheme, run_id),
            timeout=max(60, _GENERATE_NODE_TIMEOUT)
        )
        if result_dict is None:
            raise RuntimeError("run_with_timeout returned None unexpectedly")
        if not isinstance(result_dict, dict):
            raise RuntimeError(f"generate_screens_html 返回类型异常: {type(result_dict)}")

        screens_generated = bool(True)
        html_generated = bool(result_dict.get("html_generated", False))
        screens_url = str(result_dict.get("screens_url", "") or "").strip()
        html_url = str(result_dict.get("html_url", "") or "").strip()

        # 参考 test.py 中 MCP 调用：工具返回成功后，必须校验关键结果字段是否齐全。
        if screens_generated and not screens_url:
            raise RuntimeError("generate_screens_html 返回 screens_generated=True 但缺少 screens_url")
        if html_generated and not html_url:
            raise RuntimeError("generate_screens_html 返回 html_generated=True 但缺少 html_url")
        if not (screens_generated and html_generated):
            raise RuntimeError(
                f"generate_screens_html 未完整生成资源: {result_dict}"
            )

        return GenerateScreensHtmlOutput(
            screens_generated=screens_generated,
            html_generated=html_generated,
            screens_url=screens_url,
            html_url=html_url,
            error_occurred=False
        )

    except EarlyDisconnectException as e:
        logger.warning("Screens和HTML生成早期断开（未满5分钟）: %s，标记等待5分钟后恢复", e)
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=False,  # 不是错误，是特殊状态
            wait_before_recover=True,
            early_disconnect=True
        )
    except TimeoutException as e:
        logger.warning("Screens和HTML生成超时: %s，使用默认资源", e)
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=True
        )
    except Exception as e:
        logger.error("生成Screens和HTML失败: %s，使用默认资源", e, exc_info=True)
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=True
        )
