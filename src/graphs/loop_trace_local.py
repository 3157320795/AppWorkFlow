"""
禁用 CozeLoop / traces 上报时使用。

coze_coding_utils.log.loop_trace 在 import 时就会执行 cozeloop.new_client()
并向 api.coze.cn 上报，与 main 里对 cozeloop 的 Noop 无关。
因此 COZELOOP_DISABLED=true 时不得导入该模块；改由本文件提供等价的 init_*，
仅保留 LangGraph Logger 回调（本地日志），不注册 LoopTracer。
"""
from langchain_core.runnables import RunnableConfig

from coze_coding_utils.log.node_log import Logger


def init_run_config(graph, ctx):
    tracer = Logger(graph, ctx)
    tracer.on_chain_start = tracer.on_chain_start_graph
    tracer.on_chain_end = tracer.on_chain_end_graph
    return RunnableConfig(callbacks=[tracer])


def init_agent_config(graph, ctx):
    # 与 loop_trace.init_agent_config 一致：原实现仅挂 LoopTracer；禁用时不传远程上报
    return RunnableConfig(callbacks=[])
