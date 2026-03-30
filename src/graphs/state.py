"""
工作流状态定义
产品功能设计到UniApp页面开发工作流
"""
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field
from utils.file.file import File


# ==================== 全局状态 ====================
class GlobalState(BaseModel):
    """全局状态定义"""
    # 用户输入
    product_name: str = Field(default="", description="产品名称")
    product_group: str = Field(default="", description="产品分组（如：七组、八组等）")
    
    # 功能设计方案
    design_schemes: List[Dict] = Field(default=[], description="三套功能设计方案")
    confirmed_scheme_index: int = Field(default=0, description="用户确认的方案索引（0,1,2）")
    confirmed_scheme: Dict = Field(default={}, description="用户确认的方案内容")
    modification_requests: List[str] = Field(default=[], description="用户修改要求列表")
    
    # 项目创建相关
    project_created: bool = Field(default=False, description="项目是否创建成功")
    project_name: str = Field(default="", description="创建的项目名称")
    project_id: str = Field(default="", description="项目ID")
    
    # Screens和HTML生成
    screens_generated: bool = Field(default=False, description="Screens是否生成成功")
    html_generated: bool = Field(default=False, description="HTML是否生成成功")
    screens_url: str = Field(default="", description="Screens下载URL")
    html_url: str = Field(default="", description="HTML下载URL")
    generated_files: List[str] = Field(default=[], description="生成的文件列表")
    
    # 文件下载
    files_downloaded: bool = Field(default=False, description="文件是否下载成功")
    download_path: str = Field(default="", description="下载路径")
    
    # Git分支切换
    branch_switched: bool = Field(default=False, description="分支是否切换成功")
    branch_name: str = Field(default="", description="切换的分支名称")
    pages_path: str = Field(default="uniapp/pages", description="pages目录路径")
    
    # UniApp页面生成
    example_base_path: str = Field(default="uniapp/example", description="示例文件基础路径")
    pages_generated: bool = Field(default=False, description="UniApp页面是否生成成功")
    generated_pages: List[str] = Field(default=[], description="生成的页面文件列表")
    
    # 异常处理
    error_occurred: bool = Field(default=False, description="是否发生异常")
    error_message: str = Field(default="", description="错误信息")
    
    # 早期断开恢复标记
    wait_before_recover: bool = Field(default=False, description="是否需要等待5分钟后进入恢复节点")
    early_disconnect: bool = Field(default=False, description="是否是早期断开（未满5分钟）")
    
    # 默认资源（本地文件路径，用于异常情况）
    default_html_path: str = Field(default="uniapp/example/design.html", description="默认HTML本地路径")
    default_screen_path: str = Field(default="uniapp/example/screen.png", description="默认Screen本地路径")
    use_default_resource: bool = Field(default=False, description="是否使用默认资源")
    
    # 下载后的本地路径
    screens_local_path: str = Field(default="", description="Screens本地文件路径")
    html_local_path: str = Field(default="", description="HTML本地文件路径")


# ==================== 工作流输入输出 ====================
class GraphInput(BaseModel):
    """工作流输入"""
    product_name: str = Field(..., description="产品名称（如：猪猪来财、好运茶馆等）")
    product_group: str = Field(..., description="产品分组（如：七组、八组等，用于确定分支名称）")


class GraphOutput(BaseModel):
    """工作流输出"""
    success: bool = Field(..., description="整个工作流是否成功")
    final_result: Dict = Field(default={}, description="最终结果摘要")
    generated_pages: List[str] = Field(default=[], description="生成的UniApp页面文件列表")
    error_message: str = Field(default="", description="错误信息（如果有）")


# ==================== 节点出入参定义 ====================

# 节点1：功能设计节点
class FunctionDesignInput(BaseModel):
    """功能设计节点输入"""
    product_name: str = Field(..., description="产品名称")


class FunctionDesignOutput(BaseModel):
    """功能设计节点输出"""
    design_schemes: List[Dict] = Field(..., description="三套功能设计方案")
    product_name: str = Field(..., description="产品名称")


# 节点2：方案确认节点
class SchemeConfirmInput(BaseModel):
    """方案确认节点输入"""
    design_schemes: List[Dict] = Field(..., description="三套功能设计方案")
    product_name: Optional[str] = Field(default="", description="产品名称（从上游传递）")


class SchemeConfirmOutput(BaseModel):
    """方案确认节点输出"""
    confirmed_scheme_index: int = Field(..., description="用户确认的方案索引")
    confirmed_scheme: Dict = Field(..., description="确认的方案内容")
    needs_modification: bool = Field(default=False, description="是否需要修改")
    modification_request: str = Field(default="", description="修改要求")
    product_name: str = Field(default="", description="产品名称")
    user_interaction_type: str = Field(default="automatic", description="用户交互类型：interactive/automatic")
    user_input_source: str = Field(default="auto_selection", description="用户输入来源：real_user_input/simulated/auto_selection")
    error: Optional[str] = Field(default="", description="错误信息（如果有）")


# 节点3：项目创建节点
class ProjectCreateInput(BaseModel):
    """项目创建节点输入"""
    product_name: str = Field(..., description="产品名称")
    confirmed_scheme: Dict = Field(..., description="确认的功能方案")
    default_screen_path: str = Field(default="", description="默认Screen本地路径")
    default_html_path: str = Field(default="", description="默认HTML本地路径")


class ProjectCreateOutput(BaseModel):
    """项目创建节点输出"""
    project_created: bool = Field(..., description="项目是否创建成功")
    project_name: str = Field(default="", description="项目名称")
    project_id: str = Field(default="", description="项目ID")
    error_occurred: bool = Field(default=False, description="是否发生异常")
    use_default_resource: bool = Field(default=False, description="是否使用默认资源")
    screens_local_path: str = Field(default="", description="Screens本地路径（当使用默认资源时）")
    html_local_path: str = Field(default="", description="HTML本地路径（当使用默认资源时）")


# 节点4：Screens和HTML生成节点
class GenerateScreensHtmlInput(BaseModel):
    """Screens和HTML生成节点输入"""
    project_id: str = Field(default="", description="项目ID")
    confirmed_scheme: Dict = Field(..., description="确认的功能方案")
    error_occurred: bool = Field(default=False, description="上游是否发生异常")
    use_default_resource: bool = Field(default=False, description="是否使用默认资源")
    screens_local_path: str = Field(default="", description="Screens本地路径（当使用默认资源时）")
    html_local_path: str = Field(default="", description="HTML本地路径（当使用默认资源时）")


class GenerateScreensHtmlOutput(BaseModel):
    """Screens和HTML生成节点输出"""
    screens_generated: bool = Field(..., description="Screens是否生成成功")
    html_generated: bool = Field(..., description="HTML是否生成成功")
    screens_url: str = Field(default="", description="Screens下载URL（正常生成时）")
    html_url: str = Field(default="", description="HTML下载URL（正常生成时）")
    screens_local_path: str = Field(default="", description="Screens本地路径（使用默认资源时）")
    html_local_path: str = Field(default="", description="HTML本地路径（使用默认资源时）")
    error_occurred: bool = Field(default=False, description="是否发生异常")
    wait_before_recover: bool = Field(default=False, description="是否需要等待5分钟后进入恢复节点")
    early_disconnect: bool = Field(default=False, description="是否是早期断开（未满5分钟）")


# 节点5：文件下载节点
class FileDownloadInput(BaseModel):
    """文件下载节点输入"""
    screens_url: str = Field(..., description="Screens下载URL")
    html_url: str = Field(..., description="HTML下载URL")
    screens_local_path: str = Field(default="", description="Screens本地路径（当使用默认资源时）")
    html_local_path: str = Field(default="", description="HTML本地路径（当使用默认资源时）")
    product_name: str = Field(..., description="产品名称")
    use_default_resource: bool = Field(default=False, description="是否使用默认资源")


class FileDownloadOutput(BaseModel):
    """文件下载节点输出"""
    files_downloaded: bool = Field(..., description="文件是否下载成功")
    download_path: str = Field(..., description="下载路径")
    screens_local_path: str = Field(default="", description="Screens本地路径")
    html_local_path: str = Field(default="", description="HTML本地路径")
    downloaded_files: List[str] = Field(default=[], description="下载的文件列表")


# 节点6：Git分支切换节点
class GitBranchSwitchInput(BaseModel):
    """Git分支切换节点输入"""
    product_group: str = Field(..., description="产品分组（如：七组、八组）")
    product_name: str = Field(..., description="产品名称")


class GitBranchSwitchOutput(BaseModel):
    """Git分支切换节点输出"""
    branch_switched: bool = Field(..., description="分支是否切换成功")
    branch_name: str = Field(..., description="切换的分支名称（如：g7/zhuzhulaicai）")
    pages_path: str = Field(default="", description="pages目录路径")


# 节点7：UniApp页面生成节点
class UniAppPageGenerateInput(BaseModel):
    """UniApp页面生成节点输入"""
    confirmed_scheme: Dict = Field(..., description="确认的功能方案")
    example_base_path: str = Field(default="uniapp/example", description="示例文件基础路径")
    pages_path: str = Field(default="uniapp/pages", description="pages目录路径")


class UniAppPageGenerateOutput(BaseModel):
    """UniApp页面生成节点输出"""
    pages_generated: bool = Field(..., description="页面是否生成成功")
    generated_pages: List[str] = Field(default=[], description="生成的页面文件列表（完整路径列表）")
    example_pages_count: int = Field(default=0, description="示例页面数量")


# ==================== 条件节点出入参 ====================
class ShouldUseDefaultResource(BaseModel):
    """是否使用默认资源的条件判断输入"""
    error_occurred: bool = Field(default=False, description="是否发生异常")
    use_default_resource: bool = Field(default=False, description="是否使用默认资源")


class ResultFormatInput(BaseModel):
    """结果整理节点输入"""
    pages_generated: bool = Field(default=False, description="页面是否生成成功")
    generated_pages: List[str] = Field(default=[], description="生成的页面列表")
    error_message: str = Field(default="", description="错误信息")
    error_occurred: bool = Field(default=False, description="是否发生异常")


class UseDefaultResourceInput(BaseModel):
    """使用默认资源节点输入"""
    default_html_path: str = Field(..., description="默认HTML本地路径")
    default_screen_path: str = Field(..., description="默认Screen本地路径")
    error_occurred: bool = Field(default=False, description="是否发生异常")


class UseDefaultResourceOutput(BaseModel):
    """使用默认资源节点输出"""
    screens_local_path: str = Field(..., description="Screens本地路径")
    html_local_path: str = Field(..., description="HTML本地路径")
    error_occurred: bool = Field(default=True, description="标记为使用默认资源")
