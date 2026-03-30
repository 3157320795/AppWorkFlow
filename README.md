# 产品功能设计到UniApp页面开发工作流

这是一个自动化工作流项目，实现从产品功能设计到UniApp页面生成的完整流程。基于LangGraph构建，集成了Coze平台和Google Stitch MCP服务。

## 项目概述

**项目名称**: AppWorkFlow  
**功能**: 自动化实现从产品功能设计到UniApp页面生成的完整流程  
**架构**: LangGraph工作流 + Coze平台 + Google Stitch MCP

## 核心功能

1. **功能设计方案生成** - 根据产品名称生成三套不同的功能设计方案（标准实用型、创新交互型、简洁高效型）
2. **方案确认** - 支持自动和交互两种模式进行方案选择和修改
3. **项目创建** - 调用Stitch MCP工具创建设计项目
4. **Screens和HTML生成** - 自动生成设计稿和HTML代码
5. **文件下载** - 将设计资源下载到本地
6. **Git分支切换** - 根据产品分组和名称自动切换Git分支
7. **UniApp页面生成** - 根据设计稿和HTML代码生成对应的UniApp Vue页面

## 项目结构

```
AppWorkFlow/
├── src/
│   ├── main.py                 # 主入口，包含HTTP服务和本地运行逻辑
│   ├── graphs/
│   │   ├── graph.py            # 工作流图定义和节点编排
│   │   ├── state.py            # 状态定义（输入输出、全局状态）
│   │   └── nodes/              # 工作流节点实现
│   │       ├── function_design_node.py      # 功能设计节点（Agent）
│   │       ├── scheme_confirm_node.py       # 方案确认节点（Agent）
│   │       ├── project_create_node.py       # 项目创建节点（Task）
│   │       ├── generate_screens_html_node.py  # Screens/HTML生成节点（Task）
│   │       ├── file_download_node.py         # 文件下载节点（Task）
│   │       ├── git_branch_switch_node.py     # Git分支切换节点（Task）
│   │       └── uniapp_page_generate_node.py  # UniApp页面生成节点（Agent）
│   ├── utils/                  # 工具类
│   └── storage/                # 存储相关
├── scripts/
│   ├── local_run.sh            # 本地运行脚本
│   ├── http_run.sh             # HTTP服务启动脚本
│   ├── setup.sh                # 项目初始化脚本
│   └── load_env.sh             # 环境变量加载脚本
├── config/                     # LLM配置文件
│   ├── function_design_llm_cfg.json
│   ├── scheme_confirm_llm_cfg.json
│   └── uniapp_page_generate_llm_cfg.json
├── .env                        # 环境变量配置
├── requirements.txt            # Python依赖
└── README.md                   # 项目说明文档
```

## 节点清单

| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 |
|-------|---------|------|---------|---------|
| function_design | `nodes/function_design_node.py` | agent | 根据产品名称生成三套不同的功能设计方案 | - |
| scheme_confirm | `nodes/scheme_confirm_node.py` | agent | 方案确认和修改（支持自动和交互两种模式） | - |
| project_create | `nodes/project_create_node.py` | task | 调用Stitch MCP工具创建项目，超时1分钟则自动失败 | - |
| generate_screens_html | `nodes/generate_screens_html_node.py` | task | 生成Screens和HTML，超时1分钟则自动失败 | - |
| file_download | `nodes/file_download_node.py` | task | 下载Screens和HTML到本地uniapp/example目录 | - |
| git_branch_switch | `nodes/git_branch_switch_node.py` | task | 根据产品分组和名称切换Git分支 | - |
| uniapp_page_generate | `nodes/uniapp_page_generate_node.py` | agent | 根据example目录下的png和html文件生成对应的UniApp页面代码 | - |
| result_format | `graph.py` | task | 整理工作流最终输出结果 | - |
| should_skip_to_git | `graph.py` | condition | 判断项目创建是否失败/超时 | "直接切换Git分支"→git_branch_switch, "生成Screens和HTML"→generate_screens_html |
| should_skip_git_from_generate | `graph.py` | condition | 判断Screens生成是否失败/超时 | "直接切换Git分支"→git_branch_switch, "使用生成资源"→file_download |

## 工作流流程

```
┌─────────────────┐
│  function_design│  (生成三套功能设计方案)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  scheme_confirm │  (选择/确认方案)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  project_create │  (创建Stitch项目)
└────────┬────────┘
         │
    ┌────┴────┐
    │ 失败/超时 │ ────────────────┐
    └────┬────┘                  │
         │ 成功                  │
         ▼                      ▼
┌─────────────────┐     ┌─────────────────┐
│generate_screens_│     │ git_branch_     │
│     html        │     │    switch       │
└────────┬────────┘     └─────────────────┘
         │
    ┌────┴────┐
    │ 失败/超时 │ ────────────────┐
    └────┬────┘                  │
         │ 成功                  │
         ▼                      │
┌─────────────────┐             │
│  file_download  │             │
└────────┬────────┘             │
         │                      │
         ▼                      │
┌─────────────────┐             │
│ git_branch_     │◄─────────────┘
│    switch       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ uniapp_page_    │  (生成UniApp页面)
│    generate     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  result_format  │  (整理输出结果)
└─────────────────┘
```

## 启动方式

### 1. 本地运行完整工作流

```bash
bash scripts/local_run.sh -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

### 2. 运行单个节点

```bash
bash scripts/local_run.sh -m node -n function_design -i '{"product_name": "猪猪来财"}'
```

### 3. 启动HTTP服务

```bash
# 默认端口5000
bash scripts/http_run.sh

# 指定端口
bash scripts/http_run.sh -p 8000
```

## HTTP API接口

### 1. 执行工作流

**接口**: `POST /run`

**请求头**:
- `x-run-id`: 可选，指定运行ID（用于取消任务）

**请求体**:
```json
{
  "product_name": "猪猪来财",
  "product_group": "七组"
}
```

**响应**:
```json
{
  "success": true,
  "final_result": {
    "pages_count": 5
  },
  "generated_pages": [
    "/path/to/uniapp/pages/index.vue",
    "/path/to/uniapp/pages/list.vue"
  ],
  "run_id": "uuid-xxxx"
}
```

### 2. 流式执行工作流

**接口**: `POST /stream_run`

**请求头**:
- `x-run-id`: 可选，指定运行ID
- `x-workflow-stream-mode`: 可选，设置为 `debug` 启用调试模式

**请求体**: 同上

**响应**: SSE流式响应

```
event: message
data: {"event": "start", "run_id": "xxx"}

event: message
data: {"event": "node_start", "node": "function_design"}

event: message
data: {"event": "node_end", "node": "function_design"}
...
```

### 3. 取消任务

**接口**: `POST /cancel/{run_id}`

**响应**:
```json
{
  "status": "success",
  "run_id": "uuid-xxxx",
  "message": "Cancellation signal sent"
}
```

### 4. 运行单个节点

**接口**: `POST /node_run/{node_id}`

**示例**: `POST /node_run/function_design`

**请求体**:
```json
{
  "product_name": "猪猪来财"
}
```

### 5. OpenAI兼容接口

**接口**: `POST /v1/chat/completions`

支持OpenAI Chat Completions API格式，可用于集成到支持OpenAI API的客户端。

### 6. 获取图参数

**接口**: `GET /graph_parameter`

**响应**: 返回输入和输出参数的JSON Schema定义

### 7. 健康检查

**接口**: `GET /health`

**响应**:
```json
{
  "status": "ok",
  "message": "Service is running"
}
```

## 输入输出参数

### 输入参数

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| product_name | string | 是 | 产品名称（如：猪猪来财、好运茶馆等） |
| product_group | string | 是 | 产品分组（如：七组、八组等，用于确定分支名称） |

### 输出参数

| 参数名 | 类型 | 描述 |
|-------|------|------|
| success | boolean | 整个工作流是否成功 |
| final_result | object | 最终结果摘要（包含页面数量等信息） |
| generated_pages | array | 生成的UniApp页面文件列表 |
| error_message | string | 错误信息（如果有） |

## 前置要求

### 1. API密钥配置

项目使用以下API密钥（已配置在 `.env` 文件中）：

- **Coze Workload Identity API Key**: 用于Coze平台认证
- **Google Stitch API Key**: 用于调用Stitch MCP服务

### 2. 环境变量

```bash
# .env 文件
COZE_WORKLOAD_IDENTITY_API_KEY="xxx"
COZE_INTEGRATION_BASE_URL="https://integration.coze.cn"
COZE_INTEGRATION_MODEL_BASE_URL="https://integration.coze.cn/api/v3"
GOOGLE_STITCH_API_KEY="xxx"
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

## 运行模式

### 自动模式（默认）

自动选择第一个方案，适用于自动化测试和批量处理：

```bash
export ENABLE_INTERACTIVE_MODE=false
bash scripts/local_run.sh -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

### 交互模式

等待用户确认或修改方案（需要接入前端界面）：

```bash
export ENABLE_INTERACTIVE_MODE=true
export USER_INTERACTION_TYPE=web  # web/cli/message_queue
bash scripts/http_run.sh -p 5000
```

## 技能使用

### app-function-designer 技能

`function_design` 节点使用 **app-function-designer** 技能，严格遵循以下规范：

1. **应用类型识别**:
   - 实体型应用：包含实体关键词（猪、牛、羊、茶馆等）
   - 关系型应用：包含关系关键词（养殖、租赁、管理等）
   - 通用型应用：无明确实体或关系关键词

2. **功能模块设计**:
   - 实体型：6-8个模块（{实体}档案、{实体}订单等）
   - 关系型：6-8个模块
   - 通用型：2-4个模块，6-8个功能点

3. **应用页面设计**:
   - 3-5个页面（首页、实体页、统计页、我的）
   - 包含数据展示区、内容展示区、功能入口区等

4. **合规性检查**:
   - 单机工具类应用
   - 严禁所有联网功能
   - 数据仅本地存储
   - 避免金融、游戏等内容

5. **生成三套方案**:
   - 方案1：标准实用型
   - 方案2：创新交互型
   - 方案3：简洁高效型

## 注意事项

1. **超时设置**: project_create 和 generate_screens_html 节点设置了60秒超时
2. **失败处理**: 如果项目创建或Screens生成失败，会自动跳过到Git分支切换节点
3. **默认资源**: 异常情况会使用默认的本地HTML和Screen资源
4. **Git分支**: 根据 `product_group` 和 `product_name` 自动生成分支名称（如：七组猪猪来财 → g7/zhuzhulaicai）

### 代理配置（重要）

**默认禁用代理** - 火山方舟API为国内服务，默认直接连接：

```bash
# 启动HTTP服务（默认禁用代理）
bash scripts/http_run.sh -p 8080

# 如果需要启用代理（海外API需要）
bash scripts/http_run.sh -p 8080 -x true

# 本地运行工作流（默认禁用代理）
bash scripts/local_run.sh -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'

# 如果需要启用代理
ENABLE_PROXY=true bash scripts/local_run.sh -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

**手动控制代理**：

```bash
# 禁用代理
unset HTTP_PROXY
unset HTTPS_PROXY
export NO_PROXY="*"

# 启用代理
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
```

## 相关文档

- [交互模式说明](README_INTERACTION.md) - 用户交互实现详情
- [快速修复指南](QUICK_FIX.md) - API密钥问题排查
- [环境配置示例](.env.example) - 环境变量配置模板