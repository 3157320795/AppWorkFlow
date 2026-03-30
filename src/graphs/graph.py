"""
主图编排：产品功能设计到UniApp页面开发工作流
"""
import logging
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

logger = logging.getLogger(__name__)

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    ShouldUseDefaultResource,
    ResultFormatInput
)

# 导入所有节点
from graphs.nodes.function_design_node import function_design_node
from graphs.nodes.scheme_confirm_node import scheme_confirm_node
from graphs.nodes.project_create_node import project_create_node
from graphs.nodes.generate_screens_html_node import generate_screens_html_node
from graphs.nodes.file_download_node import file_download_node
from graphs.nodes.git_branch_switch_node import git_branch_switch_node
from graphs.nodes.uniapp_page_generate_node import uniapp_page_generate_node


# ==================== 条件判断函数 ====================

def should_skip_to_git(state: ShouldUseDefaultResource) -> str:
    """
    title: 是否跳过到Git分支切换
    desc: 判断项目创建是否失败，如果失败或超时则直接跳到Git分支切换
    """
    if state.error_occurred or state.use_default_resource:
        logger.info("项目创建失败或超时，直接跳转到Git分支切换")
        return "直接切换Git分支"
    else:
        return "生成Screens和HTML"


def should_skip_git_from_generate(state: ShouldUseDefaultResource) -> str:
    """
    title: Screens生成后是否跳过到Git分支切换
    desc: 判断Screens和HTML生成是否异常，如果异常则直接跳到Git分支切换
    """
    if state.error_occurred:
        logger.info("Screens和HTML生成失败或超时，直接跳转到Git分支切换")
        return "直接切换Git分支"
    else:
        return "使用生成资源"


# ==================== 结果整理节点 ====================
def result_format_node(
    state: ResultFormatInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> GraphOutput:
    """
    title: 结果整理
    desc: 整理工作流最终输出结果
    """
    # 计算是否成功
    success = state.pages_generated and len(state.generated_pages) > 0 and not state.error_occurred
    
    # 构造结果摘要
    final_result = {
        "pages_count": len(state.generated_pages),
        "error": state.error_message if state.error_message else None
    }
    
    return GraphOutput(
        success=success,
        final_result=final_result,
        generated_pages=state.generated_pages,
        error_message=state.error_message
    )


# 创建状态图
builder = StateGraph(GlobalState, input_schema=GraphInput, output_schema=GraphOutput)

# ==================== 添加节点 ====================

# 节点1：功能设计
builder.add_node(
    "function_design",
    function_design_node,
    metadata={"type": "agent", "llm_cfg": "config/function_design_llm_cfg.json"}
)

# 节点2：方案确认
builder.add_node(
    "scheme_confirm",
    scheme_confirm_node,
    metadata={"type": "agent", "llm_cfg": "config/scheme_confirm_llm_cfg.json"}
)

# 节点3：项目创建
builder.add_node(
    "project_create",
    project_create_node,
    metadata={"type": "task"}
)

# 节点4：Screens和HTML生成
builder.add_node(
    "generate_screens_html",
    generate_screens_html_node,
    metadata={"type": "task"}
)

# 节点5：文件下载
builder.add_node(
    "file_download",
    file_download_node,
    metadata={"type": "task"}
)

# 节点6：Git分支切换
builder.add_node(
    "git_branch_switch",
    git_branch_switch_node,
    metadata={"type": "task"}
)

# 节点7：UniApp页面生成
builder.add_node(
    "uniapp_page_generate",
    uniapp_page_generate_node,
    metadata={"type": "agent", "llm_cfg": "config/uniapp_page_generate_llm_cfg.json"}
)

# 节点8：结果整理
builder.add_node(
    "result_format",
    result_format_node,
    metadata={"type": "task"}
)

# ==================== 设置入口点和边 ====================

# 设置入口点
builder.set_entry_point("function_design")

# 添加边（主流程）
builder.add_edge("function_design", "scheme_confirm")
builder.add_edge("scheme_confirm", "project_create")

# 添加条件分支：判断是否跳过到Git分支切换（项目创建失败或超时时）
builder.add_conditional_edges(
    source="project_create",
    path=should_skip_to_git,
    path_map={
        "直接切换Git分支": "git_branch_switch",
        "生成Screens和HTML": "generate_screens_html"
    }
)

# 添加条件分支：判断是否跳过到Git分支切换（Screens和HTML生成失败或超时时）
builder.add_conditional_edges(
    source="generate_screens_html",
    path=should_skip_git_from_generate,
    path_map={
        "直接切换Git分支": "git_branch_switch",
        "使用生成资源": "file_download"
    }
)

# 添加后续边
builder.add_edge("file_download", "git_branch_switch")
builder.add_edge("git_branch_switch", "uniapp_page_generate")
builder.add_edge("uniapp_page_generate", "result_format")
builder.add_edge("result_format", END)

# ==================== 编译图 ====================
main_graph = builder.compile()
