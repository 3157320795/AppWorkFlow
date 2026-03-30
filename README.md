# AppWorkFlow：产品功能到 UniApp 页面自动化工作流

`AppWorkFlow` 是一个面向产品原型与页面研发的自动化流水线。  
输入产品名称与分组后，系统会自动完成方案生成、设计资源生成、下载、分支切换以及 UniApp 页面代码产出，适合用于低成本验证、批量页面生成与标准化开发流程落地。

## 应用简介

在传统流程中，产品方案、设计稿、前端页面常常由多角色串行协作，沟通成本高、迭代周期长。  
本项目将“产品构思 → 页面代码”串联为一个可执行工作流，核心价值包括：

- 降低从需求到可运行页面的时间成本
- 统一页面生成与分支管理规范
- 在失败场景下自动回退默认资源，保障流程可继续执行
- 支持 HTTP API 与可视化界面两种使用方式

## 项目概述

- **项目名称**：`AppWorkFlow`
- **技术基座**：`LangGraph` + `Coze` + `Google Stitch MCP`
- **目标输出**：`uniapp/pages` 下的页面 `.vue` 文件
- **典型场景**：
  - 业务组按产品名批量生成页面初稿
  - 设计验证阶段快速打通原型与代码
  - 自动化测试场景下稳定复现页面生成链路

## 项目架构

### 架构分层

- **工作流编排层**：`src/graphs/graph.py` 定义节点编排与条件分支
- **节点执行层**：`src/graphs/nodes/` 承载业务节点
- **MCP 调用层**：`src/graphs/stitch_mcp.py` 负责 Stitch 工具调用
- **服务接口层**：`src/main.py` 暴露 HTTP 接口（`/run`、`/stream_run` 等）
- **前端展示层**：`web/` 提供流程可视化控制台

### 目录结构

```text
AppWorkFlow/
├── src/
│   ├── main.py
│   ├── graphs/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── stitch_mcp.py
│   │   └── nodes/
│   ├── utils/
│   └── storage/
├── web/
├── scripts/
├── config/
├── uniapp/
├── .env
├── requirements.txt
└── README.md
```

## 工作流程图（保留）

```text
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

## 详细流程说明

### 1) `function_design` 功能设计

- 输入：`product_name`
- 输出：三套方案（标准实用型 / 创新交互型 / 简洁高效型）
- 目标：生成结构化、可后续执行的功能设计描述

### 2) `scheme_confirm` 方案确认

- 自动模式：默认选择第一套方案
- 交互模式：可由前端/接口触发人工选择或修改
- 输出：`confirmed_scheme`

### 3) `project_create` 创建 Stitch 项目

- 调用 Stitch MCP 工具：`create_project`
- 成功返回：`project_id`
- 失败回退：标记 `use_default_resource=true`

### 4) `generate_screens_html` 生成设计资源

- 调用工具：`generate_screen_from_text`
- 轮询工具：`list_screens`
- 目标产物：页面截图 URL + HTML URL

### 5) `file_download` 下载资源

- 将截图与 HTML 下载到本地 `uniapp/example`
- 供后续页面生成节点消费

### 6) `git_branch_switch` 切换分支

- 基于 `product_group + product_name` 规范化生成分支名
- 将工作目录切换到对应业务分支

### 7) `uniapp_page_generate` 产出页面代码

- 读取 `example` 目录资源，生成对应 `uniapp/pages/*.vue`
- 常见页面：`home`、`list`、`statics`、`mine`

### 8) `result_format` 整理输出

- 输出 `success`、`final_result`、`generated_pages`、`error_message`

## 环境配置

### 1. 系统与运行环境

- Python 3.10+
- macOS / Linux（Windows 建议 WSL）
- 可访问 `integration.coze.cn` 与 `stitch.googleapis.com`

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 `.env`

推荐最小配置如下：

```bash
COZE_WORKLOAD_IDENTITY_API_KEY="your-coze-workload-key"
COZE_INTEGRATION_BASE_URL="https://integration.coze.cn"
COZE_INTEGRATION_MODEL_BASE_URL="https://integration.coze.cn/api/v3"
COZE_WORKSPACE_PATH="/absolute/path/to/AppWorkFlow"

GOOGLE_STITCH_API_KEY="your-stitch-key"

# 默认禁用代理场景下可保留
NO_PROXY=localhost,127.0.0.1,::1,integration.coze.cn,*.coze.cn
```

### 4. 密钥可用性自检（建议）

- 启动前先确保 `GOOGLE_STITCH_API_KEY` 可调用 Stitch MCP（例如 `list_projects` 返回 200）
- 若接口返回 401/鉴权错误，优先更换 key 而不是修改流程代码

## 后端启动

### 方式 A：HTTP 服务（推荐）

```bash
# 默认端口
bash scripts/http_run.sh

# 指定端口
bash scripts/http_run.sh -p 8000

# 启用代理（仅海外链路需要）
bash scripts/http_run.sh -p 8000 -x true
```

启动后可访问：

- 健康检查：`GET http://localhost:8000/health`
- 可视化控制台：`http://localhost:8000/workflow-ui/`

### 方式 B：本地命令执行

```bash
# 全流程
bash scripts/local_run.sh -m flow -i '{"product_name":"猪猪来财","product_group":"七组"}'

# 单节点
bash scripts/local_run.sh -m node -n function_design -i '{"product_name":"猪猪来财"}'
```

## 前端启动（工作流可视化页面）

本项目 `web/` 为静态页面，由后端统一托管。你只需启动后端后直接访问：

```text
http://localhost:<端口>/workflow-ui/
```

说明：

- 页面通过 `POST /stream_run`（SSE）实时展示节点开始/结束、结果和耗时
- 调试模式可携带请求头：`x-workflow-stream-mode: debug`

## 单个接口介绍（HTTP API）

### 1. `POST /run`：执行完整工作流

- 用途：一次请求执行完整链路，返回最终结果
- 请求体：

```json
{
  "product_name": "猪猪来财",
  "product_group": "七组"
}
```

- 返回字段（核心）：
  - `success`
  - `final_result`
  - `generated_pages`
  - `error_message`

### 2. `POST /stream_run`：流式执行工作流

- 用途：前端实时查看节点执行进度
- 请求头（可选）：
  - `x-run-id`
  - `x-workflow-stream-mode: debug`
- 响应：SSE 事件流

### 3. `POST /node_run/{node_id}`：运行单个节点

- 用途：单节点调试或能力验证
- 示例：`POST /node_run/function_design`

### 4. `POST /cancel/{run_id}`：取消任务

- 用途：中断正在执行的工作流
- 适合搭配 `x-run-id` 使用

### 5. `GET /graph_parameter`：查看图参数定义

- 用途：获取输入输出 JSON Schema，便于接口对接

### 6. `POST /v1/chat/completions`：OpenAI 兼容接口

- 用途：兼容已有 OpenAI SDK 客户端接入方式

### 7. `GET /health`：健康检查

- 用途：服务存活探针、部署检查

## 调用示例

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -H "x-run-id: test-$(date +%s)" \
  -d '{"product_name":"猪猪来财","product_group":"七组"}'
```

## 关键输入输出

### 输入参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `product_name` | string | 是 | 产品名称 |
| `product_group` | string | 是 | 产品分组（用于分支命名） |

### 输出参数

| 参数 | 类型 | 说明 |
|---|---|---|
| `success` | boolean | 工作流是否成功 |
| `final_result` | object | 汇总结果 |
| `generated_pages` | array | 生成页面文件列表 |
| `error_message` | string | 失败原因（失败时） |

## 常见问题

### 1) `project_create` 鉴权失败（401）

- 检查 `GOOGLE_STITCH_API_KEY` 是否有效
- 确保服务重启后加载了新的 `.env`
- 优先通过最小调用（`list_projects`）验证密钥可用性

### 2) 生成超时

- 检查网络与代理
- 适当提高生成等待配置（如 `STITCH_POLL_WAIT_SECONDS`）
- 查看 `stream_run` 调试流定位卡点节点

### 3) 自动模式与交互模式怎么选

- 自动模式：批量执行和回归测试
- 交互模式：方案需人工确认/调整

## 相关文档

- [README_INTERACTION.md](README_INTERACTION.md)：交互模式说明
- [QUICK_FIX.md](QUICK_FIX.md)：常见故障排查
- [.env.example](.env.example)：环境变量模板
- [web/ARCHITECTURE.md](web/ARCHITECTURE.md)：控制台前端架构