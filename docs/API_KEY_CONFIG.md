# API 密钥配置指南

## 问题描述

运行工作流时出现以下错误：
```
error: "The api_key client option must be set either by passing api_key to the client or by setting the OPEN..."
```

## 解决方案

### 方案1：设置环境变量（推荐）

```bash
# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"

# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"

# Windows CMD
set OPENAI_API_KEY=your-api-key-here
```

或者在 `.env` 文件中添加：
```bash
OPENAI_API_KEY=your-api-key-here
```

### 方案2：修改配置文件

编辑配置文件，将 `{{OPENAI_API_KEY}}` 替换为真实的 API 密钥：

#### config/function_design_llm_cfg.json
```json
{
  "config": {
    "model": "gpt-4",
    "temperature": 0.8,
    "api_key": "your-actual-api-key-here"
  }
}
```

#### config/scheme_confirm_llm_cfg.json
```json
{
  "config": {
    "model": "gpt-4",
    "temperature": 0.0,
    "api_key": "your-actual-api-key-here"
  }
}
```

#### config/uniapp_page_generate_llm_cfg.json
```json
{
  "config": {
    "model": "gpt-4",
    "temperature": 0.3,
    "api_key": "your-actual-api-key-here"
  }
}
```

### 方案3：使用 Coze 平台提供的模型

如果您使用的是 Coze 平台，可以使用平台提供的模型而不是 OpenAI：

#### 方法1：修改配置文件使用 Coze 模型

```json
{
  "config": {
    "model": "coze:your-model-id",
    "temperature": 0.8,
    "api_key": "your-coze-api-key"
  }
}
```

#### 方法2：使用 Coze SDK

修改节点代码，使用 Coze SDK 而不是 LangChain OpenAI：

```python
from coze_coding_utils.skill.skill import SkillCaller

def function_design_node(state, config, runtime):
    ctx = runtime.context
    skill_caller = SkillCaller(ctx)
    
    result = skill_caller.call(
        "llm",
        {
            "model": "your-model-id",
            "messages": [
                {"role": "system", "content": sp},
                {"role": "user", "content": prompt}
            ]
        }
    )
    
    return FunctionDesignOutput(...)
```

## 验证配置

运行以下命令验证配置是否正确：

```bash
# 检查环境变量
echo $OPENAI_API_KEY

# 测试 Python 环境
python -c "import os; print('API Key:', os.getenv('OPENAI_API_KEY', 'NOT SET'))"
```

## 常见问题

### Q1: API 密钥从哪里获取？

**A1**: 
- OpenAI: https://platform.openai.com/api-keys
- Coze 平台: 从 Coze 工作台获取
- 其他模型提供商: 查看对应的文档

### Q2: 为什么每个节点都需要 API 密钥？

**A2**: 当前设计为每个节点独立配置，以便：
- 使用不同的模型进行不同任务
- 更灵活的成本控制
- 便于测试和调试

### Q3: 能否使用统一的 API 密钥配置？

**A3**: 可以！只需要在所有配置文件中设置相同的环境变量占位符 `{{OPENAI_API_KEY}}`，然后设置一个环境变量即可。

### Q4: 如何保护 API 密钥安全？

**A4**:
- ✅ 使用环境变量（推荐）
- ✅ 使用 `.env` 文件并添加到 `.gitignore`
- ❌ 不要将 API 密钥提交到代码仓库
- ❌ 不要在日志中打印 API 密钥

## 推荐配置

创建 `.env` 文件（添加到 `.gitignore`）：

```bash
# OpenAI API 密钥
OPENAI_API_KEY=sk-your-actual-key-here

# Coze API 密钥（如果使用）
COZE_API_KEY=your-coze-key-here

# 其他配置
ENABLE_INTERACTIVE_MODE=false
USER_INTERACTION_TYPE=web
```

在 Python 代码中加载：

```python
from dotenv import load_dotenv
load_dotenv()  # 从 .env 文件加载环境变量

api_key = os.getenv("OPENAI_API_KEY")
```

## 测试

配置完成后，重新运行工作流：

```bash
# 确保设置了环境变量
export OPENAI_API_KEY="your-api-key"

# 运行测试
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

预期结果：不再出现 API 密钥错误，成功生成功能设计方案。
