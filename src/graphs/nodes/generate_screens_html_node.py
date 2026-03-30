"""
Screens和HTML生成节点：将产品功能发送至项目生成对应的screens及html，若异常则使用默认资源
"""
import os
import requests
import logging
import threading
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import GenerateScreensHtmlInput, GenerateScreensHtmlOutput

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
        raise TimeoutException(f"操作超时（{timeout}秒）")
    
    if exception is not None:
        raise exception
    
    return result


def generate_screens_html_via_mcp(project_id, confirmed_scheme):
    """通过MCP生成Screens和HTML（用于在子线程中执行）"""
    payload = {
        "method": "projects.generate_screens_html",
        "params": {
            "project_id": project_id,
            "scheme": confirmed_scheme,
            "generate_screens": True,
            "generate_html": True
        }
    }
    
    logger.info(f"正在调用 MCP 生成 Screens 和 HTML: {project_id}")
    
    # 调用 MCP API
    response = requests.post(
        MCP_URL,
        json=payload,
        headers=MCP_HEADERS,
        timeout=60
    )
    
    # 检查响应状态
    if response.status_code == 200:
        result = response.json()
        logger.info(f"MCP 响应: {result}")
        
        screens_url = result.get("screens_url", "")
        html_url = result.get("html_url", "")
        
        if screens_url and html_url:
            return {
                "screens_generated": True,
                "html_generated": True,
                "screens_url": screens_url,
                "html_url": html_url
            }
        else:
            raise Exception("MCP API 返回成功但缺少必要的 URL")
    else:
        logger.error(f"MCP API 调用失败: HTTP {response.status_code}")
        logger.error(f"响应内容: {response.text}")
        raise Exception(f"MCP API 调用失败: HTTP {response.status_code}")


def generate_screens_html_node(
    state: GenerateScreensHtmlInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> GenerateScreensHtmlOutput:
    """
    title: Screens和HTML生成
    desc: 将产品功能发送至项目生成对应的screens及html，超时（1分钟）或异常则使用默认资源
    integrations: stitch mcp
    """
    ctx = runtime.context

    # 如果上游已经发生异常或标记使用默认资源，直接返回默认本地路径
    if state.error_occurred or state.use_default_resource:
        logger.warning("上游发生异常或标记使用默认资源，直接使用默认本地路径")
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=True
        )

    # 只有当project_id存在且没有异常时，才调用MCP生成
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
        # 使用新的超时机制（60秒）
        result_dict: dict = run_with_timeout(
            generate_screens_html_via_mcp,
            args=(state.project_id, state.confirmed_scheme),
            timeout=60
        )
        
        if result_dict is None:
            raise Exception("run_with_timeout returned None unexpectedly")
        
        return GenerateScreensHtmlOutput(
            screens_generated=result_dict.get("screens_generated", False),
            html_generated=result_dict.get("html_generated", False),
            screens_url=result_dict.get("screens_url", ""),
            html_url=result_dict.get("html_url", ""),
            error_occurred=False
        )
            
    except TimeoutException as e:
        logger.warning(f"Screens和HTML生成超时: {e}，使用默认资源")
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=True
        )
    except Exception as e:
        # 其他异常，使用默认资源
        logger.error(f"生成Screens和HTML失败: {e}，使用默认资源", exc_info=True)
        return GenerateScreensHtmlOutput(
            screens_generated=False,
            html_generated=False,
            screens_local_path=state.screens_local_path,
            html_local_path=state.html_local_path,
            error_occurred=True
        )
