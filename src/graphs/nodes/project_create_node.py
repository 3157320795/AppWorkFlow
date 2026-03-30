"""
项目创建节点：通过 Stitch MCP（JSON-RPC tools/call）创建项目
"""
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import ProjectCreateInput, ProjectCreateOutput
from graphs.stitch_mcp import create_project_via_mcp, run_with_timeout, TimeoutException

logger = logging.getLogger(__name__)


def project_create_node(
    state: ProjectCreateInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ProjectCreateOutput:
    """
    title: 项目创建
    desc: 调用 stitch mcp 工具创建对应名称的项目，超时（1分钟）或失败则使用默认资源
    integrations: stitch mcp
    """
    ctx = runtime.context
    run_id = getattr(ctx, "run_id", None) or "workflow"

    try:
        if not state.product_name or not state.product_name.strip():
            raise ValueError("product_name 为空，无法调用 create_project")

        result_dict: dict = run_with_timeout(
            create_project_via_mcp,
            args=(state.product_name, state.confirmed_scheme, run_id),
            timeout=90
        )
        if result_dict is None:
            raise RuntimeError("run_with_timeout returned None unexpectedly")
        if not isinstance(result_dict, dict):
            raise RuntimeError(f"create_project 返回类型异常: {type(result_dict)}")

        project_created = bool(result_dict.get("project_created", False))
        project_id = str(result_dict.get("project_id", "") or "").strip()
        if not project_created or not project_id:
            raise RuntimeError(
                f"create_project 返回数据不完整: {result_dict}"
            )

        return ProjectCreateOutput(
            project_created=project_created,
            project_name=result_dict.get("project_name", state.product_name),
            project_id=project_id
        )

    except TimeoutException as e:
        logger.warning("项目创建超时: %s，使用默认资源", e)
        return ProjectCreateOutput(
            project_created=False,
            project_name=state.product_name,
            project_id="",
            error_occurred=True,
            use_default_resource=True,
            screens_local_path=state.default_screen_path,
            html_local_path=state.default_html_path
        )
    except Exception as e:
        logger.error("创建项目失败: %s", e, exc_info=True)
        return ProjectCreateOutput(
            project_created=False,
            project_name=state.product_name,
            project_id="",
            error_occurred=True,
            use_default_resource=True,
            screens_local_path=state.default_screen_path,
            html_local_path=state.default_html_path
        )
