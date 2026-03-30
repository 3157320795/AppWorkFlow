# 快速修复指南：API 密钥错误

## 当前问题

运行工作流时出现错误：
```
error: "The api_key client option must be set either by passing api_key to the client or by setting the OPEN..."
```

## 立即修复（三种方式）

### 方式1：设置环境变量（最快）

```bash
export OPENAI_API_KEY="your-actual-api-key"
```

然后重新运行：
```bash
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

### 方式2：使用 .env 文件（推荐）

```bash
# 1. 创建 .env 文件
cat > .env <<EOF
OPENAI_API_KEY=your-actual-api-key
EOF

# 2. 在 Python 代码中加载（如果还没有的话）
# 已在代码中自动支持，直接运行即可

# 3. 运行工作流
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

### 方式3：修改配置文件

编辑以下文件，将 `{{OPENAI_API_KEY}}` 替换为真实密钥：

- `config/function_design_llm_cfg.json`
- `config/scheme_confirm_llm_cfg.json`
- `config/uniapp_page_generate_llm_cfg.json`

## 临时解决方案（仅用于测试）

如果您暂时没有 API 密钥，可以启用测试模式：

修改 `src/graphs/nodes/function_design_node.py`，添加测试模式：

```python
# 在 function_design_node 开头添加
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

if TEST_MODE:
    logger.info("测试模式：使用模拟数据")
    design_schemes = generate_default_schemes(state.product_name, "Test mode")
    return FunctionDesignOutput(
        design_schemes=design_schemes,
        product_name=state.product_name
    )

# 正常逻辑...
```

运行测试模式：
```bash
export TEST_MODE=true
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

## 获取 API 密钥

### OpenAI API 密钥
1. 访问 https://platform.openai.com/api-keys
2. 登录您的 OpenAI 账户
3. 创建新的 API 密钥
4. 复制密钥（格式：`sk-...`）

### Coze 平台 API 密钥
1. 访问 Coze 工作台
2. 创建应用或使用现有应用
3. 获取 API 密钥

## 验证配置

```bash
# 检查环境变量
echo $OPENAI_API_KEY

# 应该显示类似：sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 如果为空，说明没有设置
```

## 常见错误

### 错误1：`OPENAI_API_KEY` 为空
**解决**：确保正确设置了环境变量

### 错误2：API 密钥格式错误
**解决**：确保密钥以 `sk-` 开头

### 错误3：API 密钥无效
**解决**：检查密钥是否正确，或重新生成密钥

## 下一步

配置完成后，运行完整测试：
```bash
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

预期输出：
```json
{
  "success": true,
  "generated_pages": [
    "/workspace/projects/uniapp/pages/index.vue",
    ...
  ]
}
```

## 详细文档

更多详细信息请参考：
- [API 密钥配置指南](docs/API_KEY_CONFIG.md)
- [用户交互实现指南](docs/USER_INTERACTION_GUIDE.md)
