#!/bin/bash

# 快速配置脚本
# 帮助用户快速配置项目

echo "=========================================="
echo "项目快速配置"
echo "=========================================="
echo ""

# 1. 检查 .env 文件
if [ ! -f .env ]; then
    echo "1. 创建 .env 文件..."
    cp .env.example .env
    echo "   ✅ .env 文件已创建"
else
    echo "1. .env 文件已存在"
fi

# 2. 询问用户是否要配置 API 密钥
echo ""
echo "2. 配置 OpenAI API 密钥"
echo "   获取方式：https://platform.openai.com/api-keys"
echo ""
read -p "   您现在要配置 API 密钥吗？(y/n): " configure_api

if [ "$configure_api" = "y" ]; then
    read -p "   请输入您的 OpenAI API 密钥 (格式: sk-...): " api_key
    
    if [[ $api_key == sk-* ]]; then
        # 更新 .env 文件
        sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
        echo "   ✅ API 密钥已配置"
    else
        echo "   ❌ API 密钥格式不正确，应该以 sk- 开头"
        echo "   您可以稍后手动编辑 .env 文件"
    fi
else
    echo "   ⏭️  跳过 API 密钥配置"
    echo "   注意：工作流将使用测试模式"
fi

# 3. 安装依赖
echo ""
echo "3. 安装依赖..."
pip install -q python-dotenv langchain-openai langgraph
echo "   ✅ 依赖已安装"

# 4. 运行配置检查
echo ""
echo "4. 检查配置..."
python scripts/check_config.py

# 5. 提供下一步操作
echo ""
echo "=========================================="
echo "配置完成！"
echo "=========================================="
echo ""
echo "下一步操作："
echo "1. 如果配置了 API 密钥，可以运行完整工作流："
echo '   python -m src.main.py -m flow -i '"'"'{"product_name": "猪猪来财", "product_group": "七组"}'"'"''
echo ""
echo "2. 如果未配置 API 密钥，工作流将使用测试模式"
echo ""
echo "3. 随时可以编辑 .env 文件配置 API 密钥："
echo "   nano .env"
echo ""
