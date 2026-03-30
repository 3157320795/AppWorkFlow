"""
Git分支切换节点：根据产品名称及产品分组自动切换分支
"""
import os
import subprocess
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import GitBranchSwitchInput, GitBranchSwitchOutput

logger = logging.getLogger(__name__)


def git_branch_switch_node(
    state: GitBranchSwitchInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> GitBranchSwitchOutput:
    """
    title: Git分支切换
    desc: 根据产品名称及产品分组自动切换分支至对应分支（如：七组猪猪来财 -> g7/zhuzhulaicai）
    integrations: 
    """
    ctx = runtime.context
    
    try:
        # 确定分支名称
        # 例如：七组猪猪来财 -> g7/zhuzhulaicai
        group_number = extract_group_number(state.product_group)
        product_pinyin = convert_to_pinyin(state.product_name)
        branch_name = f"{group_number}/{product_pinyin}"
        
        # 确定 uniapp 项目路径
        base_path = os.getenv("COZE_WORKSPACE_PATH", ".")
        uniapp_path = os.path.join(base_path, "uniapp")
        
        # 切换到 uniapp 目录
        os.chdir(uniapp_path)
        
        # 获取当前分支
        result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        current_branch = result.stdout.strip()
        logger.info(f"当前分支: {current_branch}")
        
        # 检查目标分支是否存在
        result = subprocess.run(["git", "branch", "-a"], capture_output=True, text=True)
        all_branches = result.stdout
        
        if branch_name in all_branches:
            # 分支存在，切换分支
            subprocess.run(["git", "checkout", branch_name], check=True)
            logger.info(f"切换到分支: {branch_name}")
        else:
            # 分支不存在，创建并切换
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            logger.info(f"创建并切换到新分支: {branch_name}")
        
        # 确定 pages 目录路径
        pages_path = os.path.join(uniapp_path, "pages")
        
        return GitBranchSwitchOutput(
            branch_switched=True,
            branch_name=branch_name,
            pages_path=pages_path
        )
        
    except Exception as e:
        logger.error(f"Git分支切换失败: {e}")
        return GitBranchSwitchOutput(
            branch_switched=False,
            branch_name="",
            pages_path=""
        )


def extract_group_number(product_group: str) -> str:
    """从产品分组中提取组号，例如：七组 -> g7"""
    # 中文数字映射
    cn_num_map = {
        "一": "1", "二": "2", "三": "3", "四": "4",
        "五": "5", "六": "6", "七": "7", "八": "8",
        "九": "9", "十": "10"
    }
    
    for cn, num in cn_num_map.items():
        if cn in product_group:
            return f"g{num}"
    
    # 如果没有匹配到，尝试直接提取数字
    import re
    match = re.search(r'\d+', product_group)
    if match:
        return f"g{match.group()}"
    
    # 默认返回 g1
    return "g1"


def convert_to_pinyin(text: str) -> str:
    """将中文转换为拼音（简化版本）"""
    # 这里使用简化版本，实际应该使用专业的拼音库
    # 例如：猪猪来财 -> zhuzhulaicai
    
    # 简化映射（仅作示例）
    common_map = {
        "猪": "zhu",
        "来": "lai",
        "财": "cai",
        "茶": "cha",
        "馆": "guan",
        "好": "hao",
        "运": "yun",
        "车": "che",
        "辆": "liang",
        "租": "zu",
        "赁": "lin"
    }
    
    result = ""
    for char in text:
        if char in common_map:
            result += common_map[char]
        elif char.isalpha():
            result += char.lower()
    
    return result if result else text.lower()
