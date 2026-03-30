"""
Google Stitch HTTP MCP：JSON-RPC tools/call。

按用户要求仅使用 API Key，不走 OAuth（Bearer/ADC）重试。
调用工具与 Cursor 内置 Stitch MCP 工具语义对齐：
create_project / generate_screen_from_text / list_screens
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple

import httpx
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

STITCH_MCP_URL = "https://stitch.googleapis.com/mcp"
# 与 test.py 保持一致：create_project/generate/list_screens 使用 read=420 超时策略
SHORT_TIMEOUT = httpx.Timeout(connect=20.0, read=420.0, write=30.0, pool=10.0)
GENERATE_TIMEOUT = httpx.Timeout(connect=20.0, read=420.0, write=30.0, pool=10.0)

# Keep-alive 配置：每 25 秒发送一次 keep-alive 请求（服务器 30 秒断开）
KEEP_ALIVE_INTERVAL_S = 25
EARLY_DISCONNECT_THRESHOLD_S = 300  # 5 分钟


class TimeoutException(Exception):
    """子线程执行超时。"""


class EarlyDisconnectException(Exception):
    """
    Stitch 服务器在 5 分钟之前断开连接。
    上游应等待 5 分钟后进入 recover_stitch_assets_node 进行恢复。
    """
    def __init__(self, message: str, project_id: str = ""):
        super().__init__(message)
        self.project_id = project_id


def run_with_timeout(func, args=(), kwargs=None, timeout=60):
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
        raise TimeoutException(f"操作超时（{timeout}秒）")
    if exception is not None:
        raise exception
    return result


def get_stitch_api_key() -> str:
    return (os.getenv("GOOGLE_STITCH_API_KEY") or "").strip()


def stitch_headers(api_key: Optional[str] = None) -> Dict[str, str]:
    """仅使用 API Key 构造 Stitch 请求头。"""
    key = (api_key or get_stitch_api_key()).strip()
    if not key:
        raise ValueError("未配置 GOOGLE_STITCH_API_KEY")
    logger.info("Stitch auth mode: api_key")
    return {
        "X-Goog-Api-Key": key,
        "Content-Type": "application/json",
    }


def mcp_response_has_error(body: Any) -> bool:
    """HTTP 200 时仍可能在 result.isError / content 中返回工具错误。"""
    if not isinstance(body, dict):
        return False
    if body.get("error"):
        return True
    res = body.get("result")
    if isinstance(res, dict) and res.get("isError"):
        return True
    return False


def mcp_error_summary(body: Dict[str, Any], max_len: int = 500) -> str:
    """从 MCP 错误响应中提取可读摘要（用于日志/异常）。"""
    res = body.get("result") or {}
    parts: list[str] = []
    if isinstance(res.get("content"), list):
        for item in res["content"][:3]:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"])[:max_len])
    err = body.get("error")
    if isinstance(err, dict) and err.get("message"):
        parts.append(str(err["message"])[:max_len])
    return " | ".join(parts) if parts else json.dumps(body, ensure_ascii=False)[:max_len]


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
    return status, data if isinstance(data, dict) else {"raw": data}


def mcp_tools_call(
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
        params={"name": name, "arguments": arguments},
    )


TOOL_CREATE_PROJECT = "create_project"
TOOL_GENERATE_SCREEN_FROM_TEXT = "generate_screen_from_text"
TOOL_LIST_SCREENS = "list_screens"
TOOL_GET_PROJECT = "get_project"


def call_stitch_tool(
    client: httpx.Client,
    *,
    headers: Dict[str, str],
    tool_name: str,
    arguments: Dict[str, Any],
    rpc_id: str,
) -> Tuple[int, Dict[str, Any]]:
    """封装 Stitch MCP 工具调用（与 Cursor 内置工具调用语义一致）。"""
    return mcp_tools_call(
        client,
        url=STITCH_MCP_URL,
        headers=headers,
        name=tool_name,
        arguments=arguments,
        rpc_id=rpc_id,
    )


def _get_stitch_api_key(override: str = "") -> str:
    return (override or os.getenv("GOOGLE_STITCH_API_KEY") or "").strip()


def _stitch_result_structured(body: Dict[str, Any]) -> Any:
    """
    Stitch MCP 结果的结构化内容提取（尽量兼容不同返回）。
    """
    if not isinstance(body, dict):
        return {}
    res = body.get("result") or {}
    if isinstance(res, dict):
        if isinstance(res.get("structuredContent"), (dict, list)):
            return res.get("structuredContent")
        if isinstance(res.get("project"), dict):
            return res.get("project")
    return res


def get_project_assets_via_mcp(
    *,
    project_id: str,
    run_id: str,
    api_key: str = "",
    wait_s: int = 60,
    poll_interval_s: int = 2,
) -> Dict[str, Any]:
    """
    根据 project_id 调用 Stitch MCP 获取该项目 screens/html 下载链接。
    仅使用 API Key；返回可用于 file_download 的 screens_url/html_url。
    """
    pid = (project_id or "").strip()
    if not pid:
        raise ValueError("project_id is required")
    key = _get_stitch_api_key(api_key)
    if not key:
        raise ValueError("GOOGLE_STITCH_API_KEY missing")

    headers = stitch_headers(key)
    wait_s = max(int(wait_s), 0)
    poll_interval_s = max(int(poll_interval_s), 1)

    with httpx.Client(timeout=GENERATE_TIMEOUT) as client:
        # 1) get_project（用于校验 project 是否存在/可访问）
        st0, r0 = call_stitch_tool(
            client,
            headers=headers,
            tool_name=TOOL_GET_PROJECT,
            arguments={"name": f"projects/{pid}"},
            rpc_id=f"{run_id}:get_project:{pid}",
        )
        if st0 != 200 or (isinstance(r0, dict) and r0.get("error")):
            return {"ok": False, "step": "get_project", "http_status": st0, "response": r0}

        # 2) list_screens 轮询直到出现 assets
        deadline = time.monotonic() + wait_s
        st3, r3 = 0, {}
        while True:
            st3, r3 = call_stitch_tool(
                client,
                headers=headers,
                tool_name=TOOL_LIST_SCREENS,
                arguments={"projectId": pid},
                rpc_id=f"{run_id}:list_screens",
            )
            if st3 != 200 or (isinstance(r3, dict) and r3.get("error")):
                return {"ok": False, "step": "list_screens", "http_status": st3, "response": r3}
            if _list_screens_has_assets(r3):
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(poll_interval_s)

        res3 = r3.get("result") or {}
        screens = res3.get("screens") or []
        # 兜底：从末尾往前找最近一个同时具备 screenshot/htmlCode 的 screen
        shot_url, html_url = "", ""
        if isinstance(screens, list) and screens:
            for s in reversed(screens):
                if not isinstance(s, dict):
                    continue
                sc = ((s.get("screenshot") or {}).get("downloadUrl") or "").strip()
                hc = ((s.get("htmlCode") or {}).get("downloadUrl") or "").strip()
                if sc and hc:
                    shot_url, html_url = sc, hc
                    break
        if not (shot_url and html_url):
            # 保持兼容：仍尝试原 pick 逻辑（可能某些返回结构不同）
            shot_url2, html_url2 = _pick_screen_assets(screens, "")
            shot_url = shot_url or shot_url2
            html_url = html_url or html_url2
        if not (shot_url and html_url):
            return {
                "ok": False,
                "step": "pick_assets",
                "message": "list_screens 未返回可用 screens 资源（可能尚未生成 Screens/HTML，或项目下暂无 screens）",
                "raw_list_screens": r3,
            }
        return {
            "ok": True,
            "project_id": pid,
            "project": _stitch_result_structured(r0),
            "screens_url": shot_url,
            "html_url": html_url,
            "raw_get_project": r0,
            "raw_list_screens": r3,
        }


async def get_stitch_project(project_id: str, request: Request) -> Dict[str, Any]:
    """
    根据项目 ID 使用 Stitch MCP 获取项目信息，并提取 screens/html 下载链接。

    - project_id: Stitch 项目 ID（不带 projects/ 前缀）
    - api_key: 可通过 query param 或 header X-Stitch-Api-Key 传入
    """
    api_key = (request.query_params.get("api_key", "") or "").strip()
    if not api_key:
        api_key = (request.headers.get("X-Stitch-Api-Key", "") or "").strip()
    api_key = _get_stitch_api_key(api_key)

    if not api_key:
        raise HTTPException(status_code=400, detail="GOOGLE_STITCH_API_KEY missing")
    pid = (project_id or "").strip()
    if not pid:
        raise HTTPException(status_code=400, detail="project_id is required")

    wait_seconds_raw = request.query_params.get("wait_seconds", "12")
    poll_interval_raw = request.query_params.get("poll_interval_seconds", "2")
    try:
        wait_seconds = max(int(wait_seconds_raw), 0)
    except Exception:
        wait_seconds = 12
    try:
        poll_interval_seconds = max(int(poll_interval_raw), 1)
    except Exception:
        poll_interval_seconds = 2

    run_id = request.headers.get("x-run-id", "") or f"http-{int(time.time()*1000)}"
    out = get_project_assets_via_mcp(
        project_id=pid,
        run_id=run_id,
        api_key=api_key,
        wait_s=wait_seconds,
        poll_interval_s=poll_interval_seconds,
    )
    return out


def extract_project_id_from_create_response(body: Dict[str, Any]) -> str:
    result = body.get("result") or {}
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


def extract_screen_ref_from_obj(obj: Any) -> str:
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


def create_project_via_mcp(
    product_name: str,
    confirmed_scheme: Dict[str, Any],
    run_id: str,
) -> Dict[str, Any]:
    scheme_name = ""
    if isinstance(confirmed_scheme, dict):
        scheme_name = str(confirmed_scheme.get("scheme_name") or "")[:40]
    title = f"产品设计 - {product_name.strip()}"[:60]
    if scheme_name:
        title = f"{title} - {scheme_name}"[:80]

    logger.info("Stitch MCP create_project: title=%s", title)
    headers = stitch_headers()

    with httpx.Client(timeout=SHORT_TIMEOUT) as client:
        st, r = call_stitch_tool(
            client,
            headers=headers,
            tool_name=TOOL_CREATE_PROJECT,
            arguments={"title": title},
            rpc_id=f"{run_id}:create_project",
        )
        logger.info("create_project HTTP %s keys=%s", st, list(r.keys()) if isinstance(r, dict) else type(r))
        # 与 test.py 对齐：仅顶层 r["error"] 视为 JSON-RPC 工具失败
        if st != 200 or (isinstance(r, dict) and r.get("error")):
            raise RuntimeError(
                f"create_project 失败: {json.dumps(r, ensure_ascii=False)[:800]}"
            )
        project_id = extract_project_id_from_create_response(r)
        if not project_id:
            raise RuntimeError(
                "create_project 成功但无法解析 projectId，请查看原始响应: "
                + json.dumps(r, ensure_ascii=False)[:600]
            )
        return {
            "project_created": True,
            "project_name": product_name,
            "project_id": project_id,
        }


def _pick_screen_assets(
    screens: Any,
    gen_screen_ref: str,
) -> Tuple[str, str]:
    if not isinstance(screens, list) or not screens:
        return "", ""
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
        chosen = screens[-1]
    if not isinstance(chosen, dict):
        return "", ""
    shot = (chosen.get("screenshot") or {}).get("downloadUrl") or ""
    html = (chosen.get("htmlCode") or {}).get("downloadUrl") or ""
    if isinstance(shot, str) and isinstance(html, str):
        return shot, html
    return "", ""


def _list_screens_has_assets(body: Dict[str, Any]) -> bool:
    # 与 test.py 对齐：仅顶层 error 视为失败
    #（某些场景会把错误放在 result.isError 内，这里交由后续解析/兜底处理）
    if not isinstance(body, dict) or body.get("error"):
        return False
    res3 = body.get("result") or {}
    screens = res3.get("screens") or []
    if not isinstance(screens, list) or not screens:
        return False
    for s in screens[-3:]:
        if not isinstance(s, dict):
            continue
        sc = (s.get("screenshot") or {}).get("downloadUrl") or ""
        hc = (s.get("htmlCode") or {}).get("downloadUrl") or ""
        if sc or hc:
            return True
    return False


def generate_screens_html_via_mcp(
    project_id: str,
    confirmed_scheme: Dict[str, Any],
    run_id: str,
) -> Dict[str, Any]:
    """
    生成 Screens/HTML，带 keep-alive 机制和早期断开检测。
    
    如果服务器在 5 分钟之前断开（EarlyDisconnectException），
    上游应等待 5 分钟后进入 recover_stitch_assets_node 进行恢复。
    """
    product_info = json.dumps(confirmed_scheme, ensure_ascii=False, indent=2) if confirmed_scheme else ""
    prompt = product_info[:2500]
    wait_s = int(os.getenv("STITCH_POLL_WAIT_SECONDS", "300") or 300)
    wait_s = max(0, min(wait_s, 900))
    poll_interval_s = 10

    headers = stitch_headers()
    logger.info("Stitch MCP generate_screen_from_text project_id=%s", project_id)

    start_time = time.monotonic()
    
    # 使用连接池配置以支持 keep-alive
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    
    with httpx.Client(timeout=GENERATE_TIMEOUT, limits=limits) as client:
        if not prompt.strip():
            raise ValueError("confirmed_scheme 为空，无法生成 Screens/HTML（prompt 为空）")

        # 1) 调用 generate_screen_from_text
        try:
            st2, r2 = call_stitch_tool(
                client,
                headers=headers,
                tool_name=TOOL_GENERATE_SCREEN_FROM_TEXT,
                arguments={"projectId": project_id, "prompt": prompt},
                rpc_id=f"{run_id}:generate_screen_from_text",
            )
        except httpx.RemoteProtocolError as e:
            elapsed = time.monotonic() - start_time
            logger.warning("generate_screen_from_text 连接断开，已耗时 %.1f 秒", elapsed)
            if elapsed < EARLY_DISCONNECT_THRESHOLD_S:
                raise EarlyDisconnectException(
                    f"服务器在 {elapsed:.1f} 秒时断开（未满 5 分钟），需要等待 5 分钟后恢复",
                    project_id=project_id
                ) from e
            raise RuntimeError(f"generate_screen_from_text 远端断连：{e}") from e

        logger.info(
            "generate_screen_from_text HTTP=%s err=%s",
            st2,
            (r2 or {}).get("error") if isinstance(r2, dict) else None,
        )

        if st2 != 200 or (isinstance(r2, dict) and r2.get("error")):
            raise RuntimeError(
                f"generate_screen_from_text 失败: "
                f"{json.dumps(r2, ensure_ascii=False)[:900] if isinstance(r2, dict) else json.dumps(r2)[:900]}"
            )

        gen_screen_ref = extract_screen_ref_from_obj(r2)
        deadline = time.monotonic() + wait_s
        st3, r3 = 0, {}
        last_keep_alive = time.monotonic()
        
        # 2) 轮询 list_screens，带 keep-alive
        while True:
            try:
                st3, r3 = call_stitch_tool(
                    client,
                    headers=headers,
                    tool_name=TOOL_LIST_SCREENS,
                    arguments={"projectId": project_id},
                    rpc_id=f"{run_id}:list_screens",
                )
                
                # Keep-alive：定期发送轻量级请求保持连接
                if time.monotonic() - last_keep_alive >= KEEP_ALIVE_INTERVAL_S:
                    try:
                        # 发送 get_project 作为 keep-alive（比 list_screens 更轻量）
                        call_stitch_tool(
                            client,
                            headers=headers,
                            tool_name=TOOL_GET_PROJECT,
                            arguments={"name": f"projects/{project_id}"},
                            rpc_id=f"{run_id}:keep_alive",
                        )
                        last_keep_alive = time.monotonic()
                        logger.debug("Keep-alive 请求已发送")
                    except Exception as ke:
                        logger.debug("Keep-alive 请求失败（非关键）：%s", ke)
                
            except httpx.RemoteProtocolError as e:
                elapsed = time.monotonic() - start_time
                logger.warning("list_screens 连接断开，已耗时 %.1f 秒", elapsed)
                if elapsed < EARLY_DISCONNECT_THRESHOLD_S:
                    raise EarlyDisconnectException(
                        f"服务器在 {elapsed:.1f} 秒时断开（未满 5 分钟），需要等待 5 分钟后恢复",
                        project_id=project_id
                    ) from e
                raise RuntimeError(f"list_screens 远端断连：{e}") from e

            if st3 != 200 or (isinstance(r3, dict) and r3.get("error")):
                raise RuntimeError(
                    f"list_screens 失败: "
                    f"{json.dumps(r3, ensure_ascii=False)[:900] if isinstance(r3, dict) else json.dumps(r3)[:900]}"
                )
            if _list_screens_has_assets(r3):
                break
            if time.monotonic() >= deadline:
                # 与 test.py 对齐：到时间就退出轮询，由后续解析/兜底处理
                break
            time.sleep(poll_interval_s)

        res3 = r3.get("result") or {}
        screens = res3.get("screens") or []
        shot_url, html_url = _pick_screen_assets(screens, gen_screen_ref)
        if not (shot_url and html_url):
            raise RuntimeError("list_screens 结果中缺少 screenshot 与 htmlCode 的 downloadUrl")

        return {
            "screens_generated": True,
            "html_generated": True,
            "screens_url": shot_url,
            "html_url": html_url,
        }
