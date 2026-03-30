"""
恢复节点：当 generate_screens_html 失败后，允许用户输入/补充 project_id 并从 Stitch 拉取资源链接。
支持：早期断开后的 5 分钟等待 + 总共 5 分钟恢复期（每 30 秒检查一次）
"""

import logging
import os
import time
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from graphs.state import GenerateScreensHtmlInput, GenerateScreensHtmlOutput
from graphs.stitch_mcp import get_project_assets_via_mcp
from utils.interaction_store import interaction_store

logger = logging.getLogger(__name__)

# 恢复节点配置
RECOVER_INITIAL_WAIT_S = 300  # 早期断开后的初始等待：5 分钟
RECOVER_TOTAL_WAIT_S = 300    # 恢复阶段总等待时间：5 分钟
RECOVER_CHECK_INTERVAL_S = 30  # 每 30 秒检查一次
RECOVER_CHECK_QUICK_TIMEOUT_S = 10  # 每次快速检查超时：10 秒


def recover_stitch_assets_node(
    state: GenerateScreensHtmlInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> GenerateScreensHtmlOutput:
    """
    title: 交互恢复 Screens/HTML
    desc: 当 Screens/HTML 生成失败时，交互获取 project_id 并从 Stitch 项目拉取资源链接。
          如果是早期断开，先等待 5 分钟；然后在总共 5 分钟的恢复期内，每 30 秒快速检查一次资源是否可用。
    integrations: stitch mcp, web interaction
    """
    ctx = runtime.context
    run_id = getattr(ctx, "run_id", None) or "workflow"

    # 1. 获取 project_id
    project_id = (state.project_id or "").strip()
    if not project_id:
        timeout_s = int(os.getenv("USER_INPUT_TIMEOUT", "300") or 300)
        interaction_store.set_pending_project_id(run_id=run_id, suggested_project_id="")
        user_input = interaction_store.wait_user_input(run_id, timeout_s=timeout_s)
        if not user_input or user_input.get("action") != "set_project_id":
            interaction_store.clear(run_id)
            logger.error("等待用户填写 project_id 超时或动作不匹配")
            return GenerateScreensHtmlOutput(
                screens_generated=False,
                html_generated=False,
                screens_local_path=state.screens_local_path,
                html_local_path=state.html_local_path,
                error_occurred=True,
            )
        project_id = str(user_input.get("project_id", "") or "").strip()
        interaction_store.clear(run_id)

    # 2. 如果是早期断开，先等待 5 分钟（让 Stitch 服务器完成生成）
    if getattr(state, 'wait_before_recover', False) or getattr(state, 'early_disconnect', False):
        logger.info("早期断开 detected，等待 %d 秒让 Stitch 完成生成...", RECOVER_INITIAL_WAIT_S)
        time.sleep(RECOVER_INITIAL_WAIT_S)
        logger.info("初始等待结束，开始恢复流程")

    # 3. 在总共 5 分钟的恢复期内，每 30 秒快速检查一次
    logger.info("开始恢复期：总共 %d 秒，每 %d 秒检查一次", RECOVER_TOTAL_WAIT_S, RECOVER_CHECK_INTERVAL_S)
    
    deadline = time.monotonic() + RECOVER_TOTAL_WAIT_S
    check_count = 0
    
    while time.monotonic() < deadline:
        check_count += 1
        remaining = int(deadline - time.monotonic())
        logger.info("第 %d 次检查（剩余 %d 秒）...", check_count, remaining)
        
        try:
            # 快速检查：只等待 10 秒，看资源是否已可用
            out = get_project_assets_via_mcp(
                project_id=project_id,
                run_id=run_id,
                wait_s=RECOVER_CHECK_QUICK_TIMEOUT_S,
                poll_interval_s=5,  # 快速轮询间隔
            )
            
            if out.get("ok"):
                logger.info("恢复成功！第 %d 次检查获取到 screens_url 和 html_url", check_count)
                return GenerateScreensHtmlOutput(
                    screens_generated=True,
                    html_generated=True,
                    screens_url=out.get("screens_url", ""),
                    html_url=out.get("html_url", ""),
                    error_occurred=False,
                )
            
            # 本次检查未获取到资源，记录原因
            logger.debug("第 %d 次检查未获取到资源: %s", check_count, out.get("message", "资源未就绪"))
            
        except Exception as e:
            logger.warning("第 %d 次检查发生异常: %s", check_count, e)
        
        # 计算下次检查时间
        next_check_in = RECOVER_CHECK_INTERVAL_S
        # 如果剩余时间不足，调整为剩余时间
        time_left = deadline - time.monotonic()
        if time_left <= 0:
            break
        if time_left < next_check_in:
            next_check_in = max(0, int(time_left))
        
        if next_check_in > 0:
            logger.info("等待 %d 秒后进行下次检查...", next_check_in)
            time.sleep(next_check_in)
    
    # 4. 恢复期结束仍未获取到资源
    total_elapsed = RECOVER_INITIAL_WAIT_S + RECOVER_TOTAL_WAIT_S if (getattr(state, 'wait_before_recover', False) or getattr(state, 'early_disconnect', False)) else RECOVER_TOTAL_WAIT_S
    logger.error("恢复失败：经过 %d 秒恢复期（%d 次检查）仍未获取到资源", total_elapsed, check_count)
    return GenerateScreensHtmlOutput(
        screens_generated=False,
        html_generated=False,
        screens_local_path=state.screens_local_path,
        html_local_path=state.html_local_path,
        error_occurred=True,
    )

