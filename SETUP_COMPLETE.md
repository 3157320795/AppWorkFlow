# 项目配置完成指南

## ✅ 已为您完成的配置

### 1. 创建了 .env 文件
位置：`/workspace/projects/.env`

### 2. 更新了代码以支持 .env 文件
在 `src/main.py` 中添加了环境变量加载

### 3. 创建了配置检查脚本
`scripts/check_config.py` - 用于检查配置是否正确

### 4. 创建了快速配置脚本
`scripts/quick_setup.sh` - 用于快速配置项目

## ⚠️ 重要：需要您配置 API 密钥

### 方法1：快速配置（推荐）

运行快速配置脚本：
```bash
bash scripts/quick_setup.sh
```

### 方法2：手动配置

编辑 `.env` 文件：
```bash
nano .env
```

找到这一行：
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

替换为您的真实密钥：
```
OPENAI_API_KEY=sk-您的真实密钥
```

### 方法3：环境变量

在运行前设置环境变量：
```bash
export OPENAI_API_KEY="sk-您的真实密钥"
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

## 🧪 测试配置

运行配置检查：
```bash
python scripts/check_config.py
```

确保所有检查都显示 ✅

## 🚀 运行工作流

### 完整模式（需要 API 密钥）
```bash
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'
```

### 测试模式（无需 API 密钥）
如果未配置 API 密钥，工作流将自动使用测试模式，生成模拟数据。

## 📝 配置文件说明

### .env 文件内容
```
# OpenAI API 配置
OPENAI_API_KEY=sk-your-actual-api-key-here

# Coze API 配置
COZE_API_KEY=your-coze-api-key-here

# 工作流配置
ENABLE_INTERACTIVE_MODE=false
USER_INTERACTION_TYPE=web

# Stitch MCP 配置
STITCH_API_URL=http://localhost:8080/api

# 其他配置
WORKFLOW_TIMEOUT=3600
USER_INPUT_TIMEOUT=300
```

## 🔍 常见问题

### Q1: 我没有 OpenAI API 密钥怎么办？

**A1**: 
1. 访问 https://platform.openai.com/api-keys
2. 注册或登录 OpenAI 账户
3. 创建新的 API 密钥
4. 复制密钥到 .env 文件

### Q2: 可以使用其他模型吗？

**A2**: 可以！修改配置文件中的 model 字段：
```json
{
  "config": {
    "model": "gpt-3.5-turbo",
    ...
  }
}
```

### Q3: 如何使用测试模式？

**A3**: 工作流会自动检测 API 密钥：
- 如果有有效的 API 密钥 → 使用真实模型
- 如果没有或密钥无效 → 使用测试模式（模拟数据）

### Q4: 测试模式会产生什么结果？

**A4**: 测试模式会生成预定义的模拟数据，但不会调用真实的 API，因此：
- ✅ 可以验证工作流流程
- ✅ 可以测试数据流转
- ❌ 生成的设计方案不是基于真实模型的

## 📚 相关文档

- [API 密钥配置指南](docs/API_KEY_CONFIG.md)
- [用户交互实现指南](docs/USER_INTERACTION_GUIDE.md)
- [快速修复指南](QUICK_FIX.md)

## ✅ 检查清单

在运行工作流前，请确认：

- [ ] 已配置 .env 文件
- [ ] 已填入真实的 OPENAI_API_KEY（或使用测试模式）
- [ ] 已运行 `python scripts/check_config.py` 确认配置正确
- [ ] 已安装所有依赖（pip install -r requirements.txt）

## 🎯 快速开始

```bash
# 1. 运行配置检查
python scripts/check_config.py

# 2. 如果配置正确，运行工作流
python -m src.main.py -m flow -i '{"product_name": "猪猪来财", "product_group": "七组"}'

# 3. 查看结果
# 工作流将输出生成的页面文件列表
```
