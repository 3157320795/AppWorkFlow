# 用户交互实现指南

## 当前实现说明

当前工作流中实现了两种模式：

### 1. 自动模式（默认）
```bash
# 默认启用自动模式
# 工作流会自动选择第一个方案
ENABLE_INTERACTIVE_MODE=false
```

**用途**：自动化测试、批量处理、CI/CD流程

### 2. 交互模式
```bash
# 启用交互模式
ENABLE_INTERACTIVE_MODE=true
```

**当前状态**：
- ✅ 框架已实现
- ✅ 支持模式切换
- ⚠️ 当前使用模拟选择（需要接入真实交互系统）

## 如何实现真正的用户交互

### 方案1：Web界面集成

```python
# src/graphs/nodes/scheme_confirm_node.py

def handle_interactive_mode(
    state: SchemeConfirmInput,
    system_prompt: str,
    ctx: Context
) -> SchemeConfirmOutput:
    """
    处理交互模式：展示方案并等待用户确认
    """
    # 1. 将方案信息保存到数据库或缓存
    session_id = ctx.run_id
    cache.set(f"workflow:{session_id}:schemes", state.design_schemes)
    cache.set(f"workflow:{session_id}:status", "awaiting_user_confirmation")

    # 2. 触发前端展示
    notify_frontend(session_id, {
        "type": "scheme_confirmation",
        "schemes": state.design_schemes,
        "product_name": state.product_name
    })

    # 3. 暂停工作流，等待用户输入
    # 使用LangGraph的暂停机制或自定义等待机制
    return await_user_input(session_id)


async def await_user_input(session_id: str) -> SchemeConfirmOutput:
    """
    等待用户输入
    """
    # 轮询或使用消息队列等待用户响应
    while True:
        user_input = cache.get(f"workflow:{session_id}:user_input")
        if user_input:
            break
        await asyncio.sleep(1)

    # 处理用户输入
    if user_input.get("action") == "confirm":
        scheme_index = user_input.get("scheme_index")
        confirmed_scheme = state.design_schemes[scheme_index]
        return SchemeConfirmOutput(
            confirmed_scheme_index=scheme_index,
            confirmed_scheme=confirmed_scheme,
            needs_modification=False,
            product_name=state.product_name,
            user_interaction_type="interactive",
            user_input_source="real_user_input"
        )
    elif user_input.get("action") == "modify":
        # 调用修改逻辑
        return handle_user_modification(...)
```

### 方案2：命令行交互

```python
def handle_interactive_mode(
    state: SchemeConfirmInput,
    system_prompt: str,
    ctx: Context
) -> SchemeConfirmOutput:
    """
    命令行交互模式
    """
    print("\n" + "="*80)
    print(f"请为产品 '{state.product_name}' 选择功能设计方案")
    print("="*80)

    # 展示方案
    for scheme in state.design_schemes:
        print(f"\n方案 {scheme.get('scheme_id')}: {scheme.get('scheme_name')}")
        print(f"  描述: {scheme.get('description')}")

    # 等待用户输入
    while True:
        user_input = input("\n请选择方案（1/2/3），或输入 'm' 提出修改要求: ").strip()

        if user_input in ['1', '2', '3']:
            scheme_index = int(user_input) - 1
            confirmed_scheme = state.design_schemes[scheme_index]
            return SchemeConfirmOutput(
                confirmed_scheme_index=scheme_index,
                confirmed_scheme=confirmed_scheme,
                needs_modification=False,
                product_name=state.product_name,
                user_interaction_type="interactive",
                user_input_source="real_user_input"
            )
        elif user_input.lower() == 'm':
            modification = input("请输入修改要求: ").strip()
            return handle_user_modification(state, modification, system_prompt, ctx)
        else:
            print("无效输入，请重新选择")
```

### 方案3：消息队列集成

```python
import redis
import json

def handle_interactive_mode(
    state: SchemeConfirmInput,
    system_prompt: str,
    ctx: Context
) -> SchemeConfirmOutput:
    """
    消息队列交互模式
    """
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    session_id = ctx.run_id

    # 发布方案信息
    redis_client.publish(
        f"workflow:{session_id}:schemes",
        json.dumps(state.design_schemes)
    )

    # 订阅用户响应
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f"workflow:{session_id}:response")

    # 等待用户响应（带超时）
    for message in pubsub.listen():
        if message['type'] == 'message':
            user_input = json.loads(message['data'])
            # 处理用户输入
            ...
            break

    pubsub.close()
    return ...
```

## 部署配置

### 环境变量配置

```bash
# .env 文件
ENABLE_INTERACTIVE_MODE=true
USER_INTERACTION_TYPE=web  # web | cli | message_queue
WORKFLOW_TIMEOUT=3600  # 工作流超时时间（秒）
USER_INPUT_TIMEOUT=300  # 用户输入超时时间（秒）
```

### 数据库表设计

```sql
-- 工作流会话表
CREATE TABLE workflow_sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    product_name VARCHAR(255),
    schemes JSON,
    status VARCHAR(50),  -- running, awaiting_user_confirmation, completed, failed
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- 用户输入表
CREATE TABLE user_inputs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64),
    input_type VARCHAR(50),  -- confirm, modify
    content JSON,
    created_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES workflow_sessions(session_id)
);
```

## 前端集成示例

### Vue.js 组件

```vue
<template>
  <div class="scheme-confirmation">
    <h2>请选择功能设计方案</h2>

    <div v-for="scheme in schemes" :key="scheme.scheme_id" class="scheme-card">
      <h3>方案 {{ scheme.scheme_id }}: {{ scheme.scheme_name }}</h3>
      <p>{{ scheme.description }}</p>

      <div class="scheme-details">
        <h4>主要功能</h4>
        <ul>
          <li v-for="module in scheme.content.main_functions.modules" :key="module.module_name">
            {{ module.module_name }}: {{ module.core_functions }}
          </li>
        </ul>
      </div>

      <button @click="confirmScheme(scheme.scheme_id)">选择此方案</button>
    </div>

    <div class="modification-area">
      <h3>提出修改要求</h3>
      <textarea v-model="modificationText" placeholder="请输入您的修改要求..."></textarea>
      <button @click="submitModification">提交修改</button>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      schemes: [],
      modificationText: ''
    }
  },
  methods: {
    async confirmScheme(schemeId) {
      await this.$http.post('/api/workflow/confirm', {
        session_id: this.sessionId,
        action: 'confirm',
        scheme_index: schemeId - 1
      })
      this.$router.push('/workflow/status')
    },
    async submitModification() {
      await this.$http.post('/api/workflow/modify', {
        session_id: this.sessionId,
        action: 'modify',
        modification_request: this.modificationText
      })
      this.$router.push('/workflow/status')
    }
  },
  async created() {
    const response = await this.$http.get(`/api/workflow/schemes/${this.sessionId}`)
    this.schemes = response.data.schemes
  }
}
</script>
```

## API接口设计

### 获取方案列表
```
GET /api/workflow/schemes/{session_id}
Response:
{
  "session_id": "...",
  "product_name": "猪猪来财",
  "schemes": [...]
}
```

### 提交方案确认
```
POST /api/workflow/confirm
Body:
{
  "session_id": "...",
  "action": "confirm",
  "scheme_index": 0
}
```

### 提交修改要求
```
POST /api/workflow/modify
Body:
{
  "session_id": "...",
  "action": "modify",
  "modification_request": "我希望增加一个数据导出功能"
}
```

## 总结

### 当前实现优势
✅ 框架完整，易于扩展
✅ 支持多种交互模式
✅ 提供了清晰的集成接口
✅ 自动模式支持自动化流程

### 需要接入的部分
⚠️ 前端界面开发
⚠️ 用户输入收集
⚠️ 消息传递机制
⚠️ 会话管理

### 建议的部署步骤
1. 选择合适的交互方案（Web界面推荐）
2. 开发前端组件
3. 实现后端API
4. 配置消息队列或数据库
5. 测试完整的用户交互流程
6. 部署到生产环境
