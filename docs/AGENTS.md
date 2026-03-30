## 项目概述
- **名称**: 产品功能设计到UniApp页面开发工作流
- **功能**: 自动化实现从产品功能设计到UniApp页面生成的完整流程，包括功能设计方案生成、方案确认、项目创建、Screens和HTML生成、文件下载、Git分支切换和UniApp页面生成

## 前置要求

### 1. API 密钥配置

**使用火山方舟大模型**，模型调用通过集成配置自动完成：

- **模型**: `doubao-seed-2-0-pro-260215`
- **调用方式**: 通过 `integration-volcano-ark` 集成自动获取 API Key
- **无需手动配置**: 用户无需设置任何环境变量或 API 密钥

### 2. 依赖安装

```bash
pip install -r requirements.txt
```

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| function_design | `nodes/function_design_node.py` | agent | 根据产品名称生成三套不同的功能设计方案 | - | `config/function_design_llm_cfg.json` |
| scheme_confirm | `nodes/scheme_confirm_node.py` | agent | 方案确认和修改（支持自动和交互两种模式） | - | `config/scheme_confirm_llm_cfg.json` |
| project_create | `nodes/project_create_node.py` | task | 调用stitch mcp工具创建项目，超时1分钟则自动失败 | - | - |
| generate_screens_html | `nodes/generate_screens_html_node.py` | task | 生成Screens和HTML，超时1分钟则自动失败 | - | - |
| file_download | `nodes/file_download_node.py` | task | 下载Screens和HTML到本地uniapp/example目录 | - | - |
| git_branch_switch | `nodes/git_branch_switch_node.py` | task | 根据产品分组和名称切换Git分支 | - | - |
| uniapp_page_generate | `nodes/uniapp_page_generate_node.py` | agent | 根据example目录下的png和html文件生成对应的UniApp页面代码 | - | `config/uniapp_page_generate_llm_cfg.json` |
| result_format | `graph.py` | task | 整理工作流最终输出结果 | - | - |
| should_skip_to_git | `graph.py` | condition | 判断项目创建是否失败/超时 | "直接切换Git分支"→git_branch_switch, "生成Screens和HTML"→generate_screens_html | - |
| should_skip_git_from_generate | `graph.py` | condition | 判断Screens生成是否失败/超时 | "直接切换Git分支"→git_branch_switch, "使用生成资源"→file_download | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 子图清单
无子图

## 技能使用
- 节点`function_design`使用**app-function-designer**技能（遵循完整的功能设计规范）
  - 严格遵循技能文档的应用类型识别规则
  - 生成三套不同风格的方案（标准实用型、创新交互型、简洁高效型）
  - 包含完整的应用类型识别、功能模块设计、应用页面设计、合规性检查
  - 使用 **火山方舟 doubao-seed-2-0-pro-260215 模型**
- 节点`scheme_confirm`使用大语言模型技能
  - 支持自动模式和交互模式
  - 支持用户修改要求处理
  - 使用 **火山方舟 doubao-seed-2-0-pro-260215 模型**
- 节点`uniapp_page_generate`使用大语言模型技能
  - 读取example目录下的页面设计文件（screen.png + code.html）
  - 调用多模态大模型分析设计稿和HTML代码
  - 在uniapp/pages目录下生成对应的UniApp Vue页面代码
  - 支持批量生成多个页面（home, list, statics, mine等）
  - 使用 **火山方舟 doubao-seed-2-0-pro-260215 模型**

## Stitch MCP 配置
- MCP URL: `https://stitch.googleapis.com/mcp`
- API Key: 已配置在节点代码中（`X-Goog-Api-Key`）

## 工作流流程
1. **function_design**: 用户输入产品名称，使用 **app-function-designer** 技能生成三套不同的功能设计方案（标准实用型、创新交互型、简洁高效型）
   - 智能识别应用类型（实体型、关系型、通用型）
   - 使用 **火山方舟 doubao-seed-2-0-pro-260215 模型**
2. **scheme_confirm**: 用户从三套方案中选择一套
   - **自动模式**（默认）：自动选择第一个方案，适用于自动化测试
   - **交互模式**：等待用户通过Web界面/CLI/消息队列进行选择或提出修改要求
   - 配置环境变量：`ENABLE_INTERACTIVE_MODE=true` 启用交互模式
   - 使用 **火山方舟 doubao-seed-2-0-pro-260215 模型**
3. **project_create**: 调用 stitch mcp 工具创建项目
   - MCP URL: `https://stitch.googleapis.com/mcp`
   - 使用配置的 API Key 进行认证
   - **超时设置**: 60秒超时，超时后自动失败
   - **如果失败或超时**: 直接跳转到 **git_branch_switch**
4. **generate_screens_html**: 生成Screens和HTML设计文件
   - 使用 stitch mcp 接口（仅当项目创建成功时）
   - **超时设置**: 60秒超时，超时后自动失败
   - **如果失败或超时**: 直接跳转到 **git_branch_switch**
5. **should_skip_git_from_generate**: 判断是否跳过到Git分支切换
   - 如果Screens和HTML生成失败或超时，直接跳到 **git_branch_switch**
   - 否则使用MCP生成的资源URL
6. **file_download**: 将Screens和HTML下载到本地uniapp/example目录
7. **git_branch_switch**: 根据产品分组和名称自动切换Git分支（如：七组猪猪来财 → g7/zhuzhulaicai）
8. **uniapp_page_generate**: 根据example目录下的png和html文件生成对应的UniApp页面代码
   - 遍历example目录下的所有子目录（home, list, statics, mine等）
   - 读取每个目录下的screen.png和code.html文件
   - 调用多模态大模型分析设计稿和HTML代码
   - 在uniapp/pages目录下生成对应的Vue页面文件
   - 使用 **火山方舟 doubao-seed-2-0-pro-260215 模型**
9. **result_format**: 整理工作流最终输出结果

## 默认资源配置
- **默认HTML路径**: `uniapp/example/design.html`
- **默认Screen路径**: `uniapp/example/screen.png`
- **使用场景**: 当 project_create 或 generate_screens_html 节点失败/超时时，在 git_branch_switch 节点中使用

## 输入参数
- `product_name`: 产品名称（如：猪猪来财、好运茶馆等）
- `product_group`: 产品分组（如：七组、八组等，用于确定分支名称）

## 输出参数
- `success`: 整个工作流是否成功
- `final_result`: 最终结果摘要（包含页面数量等信息）
- `generated_pages`: 生成的UniApp页面文件列表
- `error_message`: 错误信息（如果有）
