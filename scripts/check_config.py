#!/usr/bin/env python3
"""
配置检查脚本
检查项目中必需的配置是否正确设置
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_env_file():
    """检查 .env 文件是否存在"""
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    if not env_file.exists():
        print("❌ .env 文件不存在")
        print(f"   正在从 .env.example 创建 .env 文件...")
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ .env 文件已创建")
            print(f"   请编辑 {env_file}，填入您的 API 密钥")
        else:
            print("❌ .env.example 文件也不存在")
            return False
    else:
        print("✅ .env 文件存在")
    return True

def check_openai_api_key():
    """检查 OpenAI API 密钥"""
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        print("❌ OPENAI_API_KEY 未设置")
        print("   请在 .env 文件中设置：OPENAI_API_KEY=sk-your-actual-api-key")
        return False

    if api_key == "sk-your-actual-api-key-here" or api_key == "your-actual-api-key-here":
        print("⚠️  OPENAI_API_KEY 使用的是默认占位符")
        print("   请在 .env 文件中填入真实的 API 密钥")
        return False

    if not api_key.startswith("sk-"):
        print("⚠️  OPENAI_API_KEY 格式可能不正确")
        print("   OpenAI API 密钥应该以 'sk-' 开头")
        return False

    print(f"✅ OPENAI_API_KEY 已设置（{api_key[:8]}...{api_key[-4:]}）")
    return True

def check_python_dependencies():
    """检查 Python 依赖"""
    print("\n检查 Python 依赖...")

    required_packages = [
        ("langchain_openai", "langchain-openai"),
        ("python_dotenv", "python-dotenv"),
        ("langgraph", "langgraph"),
    ]

    all_ok = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✅ {package_name} 已安装")
        except ImportError:
            print(f"❌ {package_name} 未安装")
            print(f"   请运行: pip install {package_name}")
            all_ok = False

    return all_ok

def check_config_files():
    """检查配置文件"""
    print("\n检查配置文件...")

    config_files = [
        "config/function_design_llm_cfg.json",
        "config/scheme_confirm_llm_cfg.json",
        "config/uniapp_page_generate_llm_cfg.json",
    ]

    all_ok = True
    for config_file in config_files:
        config_path = project_root / config_file
        if config_path.exists():
            print(f"✅ {config_file} 存在")
        else:
            print(f"❌ {config_file} 不存在")
            all_ok = False

    return all_ok

def provide_setup_instructions():
    """提供设置说明"""
    print("\n" + "="*80)
    print("配置设置说明")
    print("="*80)

    print("\n1. 获取 OpenAI API 密钥")
    print("   - 访问: https://platform.openai.com/api-keys")
    print("   - 登录您的 OpenAI 账户")
    print("   - 创建新的 API 密钥")
    print("   - 复制密钥（格式：sk-...）")

    print("\n2. 编辑 .env 文件")
    print(f"   - 文件位置: {project_root}/.env")
    print("   - 找到: OPENAI_API_KEY=sk-your-actual-api-key-here")
    print("   - 替换为: OPENAI_API_KEY=sk-您的真实密钥")

    print("\n3. 验证配置")
    print("   - 运行: python scripts/check_config.py")
    print("   - 确保所有检查都显示 ✅")

    print("\n4. 测试工作流")
    print('   - 运行: python -m src.main.py -m flow -i \'{"product_name": "测试产品", "product_group": "测试组"}\'')

def main():
    print("="*80)
    print("项目配置检查")
    print("="*80)

    checks = [
        check_env_file,
        check_openai_api_key,
        check_config_files,
        check_python_dependencies,
    ]

    results = []
    for check_func in checks:
        print("\n" + "-"*80)
        result = check_func()
        results.append(result)

    print("\n" + "="*80)
    print("检查结果")
    print("="*80)

    if all(results):
        print("\n✅ 所有检查通过！项目配置正确。")
        print("\n可以运行工作流了：")
        print('python -m src.main.py -m flow -i \'{"product_name": "猪猪来财", "product_group": "七组"}\'')
        return 0
    else:
        print("\n❌ 存在配置问题，请按照说明进行修复。")
        provide_setup_instructions()
        return 1

if __name__ == "__main__":
    sys.exit(main())
