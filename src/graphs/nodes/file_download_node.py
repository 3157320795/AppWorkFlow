"""
文件下载节点：将对应的screens及html下载至本地uniapp/example目录下
"""
import os
import requests
import logging
from pathlib import Path
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import FileDownloadInput, FileDownloadOutput

logger = logging.getLogger(__name__)


def file_download_node(
    state: FileDownloadInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FileDownloadOutput:
    """
    title: 文件下载
    desc: 将对应的screens及html下载至本地uniapp/example目录下
    integrations: 
    """
    ctx = runtime.context
    
    try:
        # 确定下载目录
        base_path = os.getenv("COZE_WORKSPACE_PATH", ".")
        download_dir = os.path.join(base_path, "uniapp", "example")
        os.makedirs(download_dir, exist_ok=True)
        
        downloaded_files = []
        
        # 下载 screens
        if state.screens_url:
            screen_filename = f"{state.product_name}_screen.png"
            screen_path = os.path.join(download_dir, screen_filename)
            
            response = requests.get(state.screens_url, timeout=30)
            with open(screen_path, 'wb') as f:
                f.write(response.content)
            downloaded_files.append(screen_path)
            logger.info(f"Screens下载成功: {screen_path}")
        
        # 下载 html
        if state.html_url:
            html_filename = f"{state.product_name}_design.html"
            html_path = os.path.join(download_dir, html_filename)
            
            response = requests.get(state.html_url, timeout=30)
            with open(html_path, 'wb') as f:
                f.write(response.content)
            downloaded_files.append(html_path)
            logger.info(f"HTML下载成功: {html_path}")
        
        return FileDownloadOutput(
            files_downloaded=True,
            download_path=download_dir,
            downloaded_files=downloaded_files
        )
        
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return FileDownloadOutput(
            files_downloaded=False,
            download_path="",
            downloaded_files=[]
        )
