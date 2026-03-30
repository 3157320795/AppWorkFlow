"""
MCP Stitch 节点 - 使用 MCP 工具调用 Google Stitch API
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import McpStitchInput, McpStitchOutput

# 配置日志
logger = logging.getLogger(__name__)

def _extract_project_id_from_create_project_response(r1: Dict[str, Any]) -> str:
    """
    Stitch create_project 返回结构可能变化，这里做尽量兼容的提取。
    """
    result = r1.get("result") or {}

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        name = structured.get("name")
        if isinstance(name, str) and name.startswith("projects/"):
            return name.split("/")[-1]

    project = result.get("project")
    if isinstance(project, dict):
        name = project.get("name")
        if isinstance(name, str) and name.startswith("projects/"):
            return name.split("/")[-1]
        pid = project.get("projectId") or project.get("project_id")
        if isinstance(pid, str) and pid.strip():
            return pid.strip()

    # 兜底：解析 content[0].text（里面可能是 JSON）
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str) and text.strip().startswith("{"):
                try:
                    obj = json.loads(text)
                    name = obj.get("name")
                    if isinstance(name, str) and name.startswith("projects/"):
                        return name.split("/")[-1]
                except Exception:
                    pass
    return ""

def _extract_screen_ref_from_obj(obj: Any) -> str:
    """
    从任意嵌套对象中提取形如 projects/{p}/screens/{s} 的字符串引用。
    """
    screen_name = ""

    def walk(x: Any):
        nonlocal screen_name
        if screen_name:
            return
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for it in x:
                walk(it)
        elif isinstance(x, str):
            if x.startswith("projects/") and "/screens/" in x:
                screen_name = x

    walk(obj)
    return screen_name

def _file_ref_summarize(file_obj: Any) -> Dict[str, Any]:
    """
    File 资源的摘要：优先返回 downloadUrl 与 mimeType；base64 只标记是否存在。
    """
    if not isinstance(file_obj, dict):
        return {}
    out: Dict[str, Any] = {}
    if isinstance(file_obj.get("downloadUrl"), str):
        out["downloadUrl"] = file_obj["downloadUrl"]
    if isinstance(file_obj.get("mimeType"), str):
        out["mimeType"] = file_obj["mimeType"]
    if isinstance(file_obj.get("fileContentBase64"), str):
        out["hasBase64"] = True
    return out

def _extract_design_url(result: Dict[str, Any]) -> str:
    """
    Stitch MCP 的返回可能在不同层级携带 URL，尽量兼容提取。
    """
    if not isinstance(result, dict):
        return ""

    # 常见：{"result": {"url": "..."}}
    result_data = result.get("result")
    if isinstance(result_data, dict):
        for k in ("url", "design_url", "designUrl", "link"):
            v = result_data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()

    # 兜底：顶层 url
    for k in ("url", "design_url", "designUrl", "link"):
        v = result.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()

    return ""

def _mcp_post(
    client: httpx.Client,
    *,
    url: str,
    headers: Dict[str, str],
    method: str,
    rpc_id: str,
    params: Dict[str, Any],
) -> Tuple[int, Dict[str, Any]]:
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "method": method,
        "params": params,
    }
    resp = client.post(url, headers=headers, json=payload)
    status = resp.status_code
    try:
        data = resp.json()
    except Exception:
        data = {"raw_text": resp.text}
    return status, data

def _mcp_tools_call(
    client: httpx.Client,
    *,
    url: str,
    headers: Dict[str, str],
    name: str,
    arguments: Dict[str, Any],
    rpc_id: str,
) -> Tuple[int, Dict[str, Any]]:
    return _mcp_post(
        client,
        url=url,
        headers=headers,
        method="tools/call",
        rpc_id=rpc_id,
        params={
            "name": name,
            "arguments": arguments,
        },
    )

def mcp_stitch_node(
    state: McpStitchInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> McpStitchOutput:
    """
    title: MCP Stitch 提交
    desc: 使用 MCP 协议调用 Google Stitch API 提交产品设计
    integrations: MCP, Google Stitch API
    """
    ctx = runtime.context
    logger.info("[MCP Stitch] 启动 MCP 工具调用...")
    
    # 获取 API Key（优先运行时参数，其次环境变量）
    api_key: str = ""
    if state.api_key and state.api_key != "YOUR-API-KEY":
        api_key = state.api_key
    else:
        env_key = os.getenv("GOOGLE_STITCH_API_KEY")
        if env_key:
            api_key = env_key
    
    # API Key 缺失检测
    if not api_key:
        logger.warning("[MCP Stitch] 未配置 API Key")
        return McpStitchOutput(
            success=False,
            message="❌ 未配置 Google Stitch API Key\n\n请通过以下方式配置：\n\n【方式1】环境变量:\nexport GOOGLE_STITCH_API_KEY=\"your-key\"\n\n【方式2】运行时传参:\nmain_graph.invoke({\"product_name\": \"xxx\", \"api_key\": \"your-key\"})",
            design_url=""
        )
    
    # MCP 请求配置
    mcp_url: str = "https://stitch.googleapis.com/mcp"
    headers: Dict[str, str] = {
        "X-Goog-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    logger.info(f"[MCP Stitch] 调用 API: {mcp_url}")
    
    # 发送 HTTP 请求
    try:
        run_id = getattr(ctx, "run_id", None) or "stitch-request"
        response_data: Dict[str, Any] = {"calls": []}
        saved_files: list[str] = []

        # Stitch MCP 暴露的工具中没有 create_design。
        # 这里采用：create_project -> generate_screen_from_text
        # stitch 生成类工具可能返回体较大，使用较明确的超时避免卡死
        # 生成屏幕可能需要较长时间；read 超时放宽，但 connect/write 保持较短以避免卡死
        with httpx.Client(timeout=httpx.Timeout(connect=20.0, read=420.0, write=30.0, pool=10.0)) as client:
            # 1) create_project
            st1, r1 = _mcp_tools_call(
                client,
                url=mcp_url,
                headers=headers,
                name="create_project",
                arguments={"title": "产品设计 - " + (state.product_info.splitlines()[0].strip()[:40] if state.product_info else "未命名")},
                rpc_id=f"{run_id}:create_project",
            )
            response_data["calls"].append({"tool": "create_project", "http_status": st1, "response": r1})
            if st1 != 200 or (isinstance(r1, dict) and r1.get("error")):
                return McpStitchOutput(
                    success=False,
                    message=f"❌ Stitch create_project 失败\n\n响应: {json.dumps(r1, ensure_ascii=False)[:900]}",
                    design_url="",
                    response_data=response_data,
                )

            project_id: str = _extract_project_id_from_create_project_response(r1)

            if not project_id:
                return McpStitchOutput(
                    success=False,
                    message="❌ 已创建项目但无法从响应解析 projectId，请查看 response_data",
                    design_url="",
                    response_data=response_data,
                )

            # 2) generate_screen_from_text
            prompt_full = state.product_info or ""
            # 生成接口 prompt 过长时可能触发断连/卡死；这里从更激进的截断开始重试
            prompt_candidates = [
                prompt_full[:2500],
                prompt_full[:1200],
            ]
            st2: int = 0
            r2: Dict[str, Any] = {}
            last_exc: Optional[Exception] = None
            for i, p in enumerate(prompt_candidates):
                try:
                    if not p.strip():
                        continue
                    st2, r2 = _mcp_tools_call(
                        client,
                        url=mcp_url,
                        headers=headers,
                        name="generate_screen_from_text",
                        arguments={
                            "projectId": project_id,
                            "prompt": p,
                            # deviceType/modelId 为可选字段；去掉以降低请求体与潜在兼容性问题
                        },
                        rpc_id=f"{run_id}:generate_screen_from_text:try{i}",
                    )
                    response_data["calls"].append(
                        {"tool": "generate_screen_from_text", "http_status": st2, "response": r2, "prompt_len": len(p)}
                    )
                    if st2 == 200 and isinstance(r2, dict) and not r2.get("error"):
                        break
                    # HTTP 200 但 JSON-RPC error 的情况，直接返回（不再重试，避免重复创建/资源）
                    if st2 == 200 and isinstance(r2, dict) and r2.get("error"):
                        return McpStitchOutput(
                            success=False,
                            message=f"❌ Stitch generate_screen_from_text 返回 JSON-RPC 错误\n\n响应: {json.dumps(r2, ensure_ascii=False)[:900]}",
                            design_url="",
                            response_data=response_data,
                        )
                except httpx.RemoteProtocolError as e:
                    last_exc = e
                    # 继续下一轮更短 prompt 重试
                    continue
            else:
                return McpStitchOutput(
                    success=False,
                    message=f"❌ Stitch generate_screen_from_text 多次重试仍失败：{str(last_exc) if last_exc else ''}",
                    design_url="",
                    response_data=response_data,
                )

            if st2 != 200 or (isinstance(r2, dict) and r2.get("error")):
                return McpStitchOutput(
                    success=False,
                    message=f"❌ Stitch generate_screen_from_text 失败\n\n响应: {json.dumps(r2, ensure_ascii=False)[:900]}",
                    design_url="",
                    response_data=response_data,
                    saved_files=saved_files,
                )

            # 3) list_screens/get_screen: 拉取资源并保存到本地
            # 默认最多等待 stitch_wait_seconds（默认 300s），期间每 10s 轮询一次 list_screens
            wait_s = int(getattr(state, "stitch_wait_seconds", 300) or 300)
            wait_s = max(0, min(wait_s, 900))
            poll_interval_s = 10

            st3: int = 0
            r3: Dict[str, Any] = {}
            start_ts = runtime.context.loop_time if hasattr(runtime.context, "loop_time") else None
            # 由于节点函数是同步的，这里用 time.monotonic 进行轮询计时
            import time as _time
            deadline = _time.monotonic() + wait_s

            while True:
                try:
                    st3, r3 = _mcp_tools_call(
                        client,
                        url=mcp_url,
                        headers=headers,
                        name="list_screens",
                        arguments={"projectId": project_id},
                        rpc_id=f"{run_id}:list_screens",
                    )
                    response_data["calls"].append({"tool": "list_screens", "http_status": st3, "response": r3})
                except httpx.RemoteProtocolError as e:
                    return McpStitchOutput(
                        success=False,
                        message=f"❌ Stitch list_screens 远端断连：{str(e)}",
                        design_url="",
                        response_data=response_data,
                        saved_files=saved_files,
                    )

                # 如果已经拿到 screens 且包含 screenshot/htmlCode downloadUrl，则退出轮询
                got_assets = False
                if st3 == 200 and isinstance(r3, dict) and not r3.get("error"):
                    res3 = r3.get("result") or {}
                    screens = res3.get("screens") or []
                    if isinstance(screens, list) and screens:
                        for s in screens[-3:]:
                            if not isinstance(s, dict):
                                continue
                            sc = (s.get("screenshot") or {}).get("downloadUrl") or ""
                            hc = (s.get("htmlCode") or {}).get("downloadUrl") or ""
                            if sc or hc:
                                got_assets = True
                                break

                if got_assets:
                    break
                if _time.monotonic() >= deadline:
                    break
                _time.sleep(poll_interval_s)

            screenshot_download_url = ""
            htmlcode_download_url = ""
            screens_summary: Dict[str, Any] = {}

            if st3 == 200 and isinstance(r3, dict) and not r3.get("error"):
                res3 = r3.get("result") or {}
                screens = res3.get("screens") or []
                if isinstance(screens, list) and screens:
                    gen_screen_ref = _extract_screen_ref_from_obj(r2)  # 优先匹配本次生成的那一页
                    chosen = None
                    if gen_screen_ref and "/screens/" in gen_screen_ref:
                        gen_screen_id = gen_screen_ref.split("/screens/")[-1]
                        for s in screens:
                            if not isinstance(s, dict):
                                continue
                            sid = s.get("id") or s.get("screenId") or s.get("name")
                            if isinstance(sid, str) and "/screens/" in sid:
                                sid = sid.split("/screens/")[-1]
                            if sid == gen_screen_id:
                                chosen = s
                                break
                    if chosen is None:
                        chosen = screens[-1]  # 兜底：取最后一个（通常是最新生成）

                    if isinstance(chosen, dict):
                        screens_summary["chosenScreen"] = chosen.get("name", "")
                        screenshot_download_url = (chosen.get("screenshot") or {}).get("downloadUrl") or ""
                        htmlcode_download_url = (chosen.get("htmlCode") or {}).get("downloadUrl") or ""
                        screens_summary["screenshot"] = _file_ref_summarize(chosen.get("screenshot"))
                        screens_summary["htmlCode"] = _file_ref_summarize(chosen.get("htmlCode"))

                        # 下载并保存到本地（优先 downloadUrl）
                        base_dir = Path(getattr(state, "save_dir", "assets/stitch") or "assets/stitch")
                        screen_name = chosen.get("name", "")
                        screen_id = ""
                        if isinstance(screen_name, str) and "/screens/" in screen_name:
                            screen_id = screen_name.split("/screens/")[-1]
                        out_dir = base_dir / project_id / (screen_id or "screen")
                        out_dir.mkdir(parents=True, exist_ok=True)

                        def _download_to(url: str, path: Path) -> bool:
                            if not url:
                                return False
                            try:
                                r = client.get(url, timeout=httpx.Timeout(connect=20.0, read=60.0, write=30.0, pool=10.0))
                                if r.status_code != 200:
                                    return False
                                path.write_bytes(r.content)
                                saved_files.append(str(path))
                                return True
                            except Exception:
                                return False

                        if screenshot_download_url:
                            _download_to(screenshot_download_url, out_dir / "screenshot.png")
                        if htmlcode_download_url:
                            _download_to(htmlcode_download_url, out_dir / "screen.html")

            # Stitch MCP 未必直接给出设计 URL，这里尽量提取；并回传 projectId 方便你在控制台定位
            design_url: str = _extract_design_url(r2) or _extract_design_url(r1)
            msg = f"✅ 已提交到 Google Stitch（projectId={project_id}）"
            if design_url:
                msg += f"\n\n设计链接: {design_url}"
            if screenshot_download_url:
                msg += f"\n\n页面图片(downloadUrl): {screenshot_download_url}"
            if htmlcode_download_url:
                msg += f"\n\n页面代码(downloadUrl): {htmlcode_download_url}"
            if not (screenshot_download_url or htmlcode_download_url):
                msg += "\n\n提示：未在 list_screens 中拿到页面图片/代码下载链接，请查看 response_data.calls 里的 r3。"

            if screens_summary:
                response_data["screens"] = screens_summary

            return McpStitchOutput(
                success=True,
                message=msg,
                design_url=design_url,
                response_data=response_data,
                saved_files=saved_files,
            )
    
    except httpx.TimeoutException:
        logger.error("[MCP Stitch] 请求超时")
        return McpStitchOutput(
            success=False,
            message="❌ 请求超时，请检查网络连接后重试",
            design_url="",
            response_data=locals().get("response_data"),
            saved_files=locals().get("saved_files") or [],
        )
    
    except httpx.ConnectError as e:
        logger.error(f"[MCP Stitch] 连接失败: {e}")
        return McpStitchOutput(
            success=False,
            message=f"❌ 无法连接到 MCP 服务器\n\n错误: {str(e)}\n\n提示: 请检查网络或配置代理",
            design_url="",
            response_data=locals().get("response_data"),
            saved_files=locals().get("saved_files") or [],
        )
    
    except httpx.RemoteProtocolError as e:
        logger.error(f"[MCP Stitch] 远端协议错误/断连: {e}")
        return McpStitchOutput(
            success=False,
            message=f"❌ 远端连接中断（RemoteProtocolError）: {str(e)}",
            design_url="",
            response_data=locals().get("response_data"),
            saved_files=locals().get("saved_files") or [],
        )

    except Exception as e:
        logger.error(f"[MCP Stitch] 异常: {e}", exc_info=True)
        return McpStitchOutput(
            success=False,
            message=f"❌ MCP 调用异常: {str(e)}",
            design_url="",
            response_data=locals().get("response_data"),
            saved_files=locals().get("saved_files") or [],
        )
