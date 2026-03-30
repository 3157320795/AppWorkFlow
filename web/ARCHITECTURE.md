# 工作流可视化控制台 — 前端架构

## 目标

- 交互式触发全流程（与 `/stream_run` 对齐）。
- 展示**每个节点的运行结果摘要**与**耗时**（依赖后端 `x-workflow-stream-mode: debug`）。
- 同域部署：静态页由 FastAPI 挂载，避免 SSE + CORS 问题。

## 分层

| 层 | 职责 | 技术 |
|----|------|------|
| **表现** | 表单、时间线、节点卡片、输出折叠/弹窗 | HTML + CSS |
| **流式协议** | `fetch` + ReadableStream 解析 SSE（`data: {...}`） | 原生 JS |
| **状态** | `runId`、节点状态机、事件日志、AbortController | 内存单例模块 |
| **后端契约** | `POST /stream_run`，Header：`Content-Type: application/json`、`x-workflow-stream-mode: debug`、`x-run-id` | FastAPI |

## 事件模型（来自 `WorkflowStreamRunner`）

- `workflow_start` / `workflow_end`：整图起止；`workflow_end` 含总耗时 `time_cost_ms`。
- `node_start`：`node_name`、`input`（debug）。
- `node_end`：`node_name`、`output`、`time_cost_ms`。
- `error` / `ping`：错误与心跳。

前端按 `node_name` 更新卡片：进行中 → 完成 + 耗时；异常时标红。

## 扩展（后续迭代）

- WebSocket 或 NDJSON 多路复用；离线重放日志文件。
- 基于同一套事件驱动 **Mermaid/流程图** 高亮边（需维护与 `graph.py` 一致的拓扑元数据）。
- 与 `/run` 非流式结果对比视图。

## 访问路径

服务启动后：`http://<host>:<port>/workflow-ui/`
