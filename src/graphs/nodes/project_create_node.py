"""
项目创建节点：调用 stitch mcp 工具创建对应名称的项目
"""
import os
import requests
import logging
import threading
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import ProjectCreateInput, ProjectCreateOutput

logger = logging.getLogger(__name__)


# MCP 请求配置
MCP_URL = "https://stitch.googleapis.com/mcp"
MCP_HEADERS = {
    "X-Goog-Api-Key": "AQ.Ab8RN6J3ydkw2EWwp-XtY9TPwwt8KooPdw2_Z0G0DL94tymgZA",
    "Content-Type": "application/json"
}


# 超时异常
class TimeoutError(Exception):
    pass


class TimeoutException(Exception):
    """超时异常"""
    pass


def run_with_timeout(func, args=(), kwargs=None, timeout=60):
    """在子线程中运行函数，支持超时"""
    if kwargs is None:
        kwargs = {}
    
    result = None
    exception = None
    
    def worker():
        nonlocal result, exception
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            exception = e
    
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        # 线程仍在运行，表示超时
        # 注意：Python线程无法强制杀死，但我们可以标记为超时
        raise TimeoutException(f"操作超时（{timeout}秒）")
    
    if exception is not None:
        raise exception
    
    return result


def create_project_via_mcp(product_name, confirmed_scheme):
    """通过MCP创建项目（用于在子线程中执行）"""
    payload = {
        "method": "projects.create",
        "params": {
            "project_name": product_name,
            "description": f"基于功能设计创建的项目：{confirmed_scheme.get('scheme_name', '')}",
            "type": "uniapp"
        }
    }
    
    logger.info(f"正在调用 MCP 创建项目: {product_name}")
    logger.info(f"MCP URL: {MCP_URL}")
    
    # 调用 MCP API
    response = requests.post(
        MCP_URL,
        json=payload,
        headers=MCP_HEADERS,
        timeout=30
    )
    
    # 检查响应状态
    if response.status_code == 200:
        result = response.json()
        logger.info(f"MCP 响应: {result}")
        
        project_id = result.get("project_id") or result.get("id") or f"proj_{product_name}"
        project_name = result.get("project_name") or result.get("name") or product_name
        
        return {
            "project_created": True,
            "project_name": project_name,
            "project_id": project_id
        }
    else:
        logger.error(f"MCP API 调用失败: HTTP {response.status_code}")
        logger.error(f"响应内容: {response.text}")
        raise Exception(f"MCP API 调用失败: HTTP {response.status_code}")


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
    
    try:
        # 使用新的超时机制（60秒）
        result_dict: dict = run_with_timeout(
            create_project_via_mcp,
            args=(state.product_name, state.confirmed_scheme),
            timeout=60
        )
        
        if result_dict is None:
            raise Exception("run_with_timeout returned None unexpectedly")
        
        return ProjectCreateOutput(
            project_created=result_dict.get("project_created", False),
            project_name=result_dict.get("project_name", state.product_name),
            project_id=result_dict.get("project_id", "")
        )
            
    except TimeoutException as e:
        logger.warning(f"项目创建超时: {e}，使用默认资源")
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
        # 其他异常
        logger.error(f"创建项目失败: {e}", exc_info=True)
        return ProjectCreateOutput(
            project_created=False,
            project_name=state.product_name,
            project_id="",
            error_occurred=True,
            use_default_resource=True,
            screens_local_path=state.default_screen_path,
            html_local_path=state.default_html_path
        )
