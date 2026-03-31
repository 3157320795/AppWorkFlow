"""
UniApp页面生成节点：根据example目录下的png和html文件生成对应的UniApp页面
"""
import os
import json
import logging
import base64
from pathlib import Path
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from langchain_core.messages import SystemMessage, HumanMessage
from coze_coding_dev_sdk import LLMClient
from graphs.state import UniAppPageGenerateInput, UniAppPageGenerateOutput

logger = logging.getLogger(__name__)


def image_to_base64(image_path: str) -> str:
    """将本地图片转换为base64编码"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"


def uniapp_page_generate_node(
    state: UniAppPageGenerateInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> UniAppPageGenerateOutput:
    """
    title: UniApp页面生成
    desc: 根据example目录下的png和html文件，使用多模态大模型分析设计并生成对应的UniApp页面代码
    integrations: 火山方舟多模态大模型
    """
    ctx = runtime.context

    # 读取大模型配置
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r') as fd:
        _cfg = json.load(fd)

    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")

    # 确定路径
    example_base_path = state.example_base_path
    pages_path = state.pages_path

    # 获取工作目录并构建绝对路径
    # 如果传入的是绝对路径则直接使用，否则基于 COZE_WORKSPACE_PATH 构建
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")

    if os.path.isabs(example_base_path):
        example_path = example_base_path
    else:
        example_path = os.path.join(workspace_path, example_base_path)

    if os.path.isabs(pages_path):
        pages_abs_path = pages_path
    else:
        pages_abs_path = os.path.join(workspace_path, pages_path)

    logger.info(f"[页面生成] 开始生成UniApp页面")
    logger.info(f"[页面生成] 示例目录: {example_path}")
    logger.info(f"[页面生成] 输出目录: {pages_abs_path}")

    try:
        # 确保pages目录存在
        if not os.path.exists(pages_abs_path):
            os.makedirs(pages_abs_path, exist_ok=True)
            logger.info(f"[页面生成] 创建pages目录: {pages_abs_path}")

        # 遍历example目录下的所有子目录
        example_dir = Path(example_path)
        if not example_dir.exists():
            logger.error(f"[页面生成] 示例目录不存在: {example_path}")
            return UniAppPageGenerateOutput(
                pages_generated=False,
                generated_pages=[],
                example_pages_count=0
            )

        # 获取所有子目录（每个目录代表一个页面）
        page_dirs = [d for d in example_dir.iterdir() if d.is_dir()]
        logger.info(f"[页面生成] 发现 {len(page_dirs)} 个示例页面目录: {[d.name for d in page_dirs]}")

        generated_pages = []

        for page_dir in page_dirs:
            page_name = page_dir.name
            screen_file = page_dir / "screen.png"
            # 支持 code.html 或 design.html
            html_file = page_dir / "code.html"
            if not html_file.exists():
                html_file = page_dir / "design.html"

            # 检查文件是否存在
            if not screen_file.exists():
                logger.warning(f"[页面生成] 页面 {page_name} 缺少截图文件，跳过")
                continue
            if not html_file.exists():
                logger.warning(f"[页面生成] 页面 {page_name} 缺少HTML文件，跳过")
                continue

            # 确定输出文件路径
            vue_file_path = os.path.join(pages_abs_path, f"{page_name}.vue")
            is_update = os.path.exists(vue_file_path)
            action = "重新设计" if is_update else "新建"

            logger.info(f"[页面生成] 正在处理页面: {page_name} ({action})")

            try:
                # 读取HTML内容作为设计参考
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # 将图片转换为base64编码
                screen_url = image_to_base64(str(screen_file))
                logger.info(f"[页面生成] 页面 {page_name} 图片已转换，base64长度: {len(screen_url)}")

                # 使用jinja2模板渲染用户提示词
                up_tpl = Template(_cfg.get("up", ""))
                user_prompt = up_tpl.render({
                    "confirmed_scheme": json.dumps(state.confirmed_scheme, ensure_ascii=False, indent=2),
                    "page_name": page_name,
                    "html_content": html_content
                })

                # 调用多模态大模型分析设计并生成页面代码
                logger.info(f"[页面生成] 调用大模型生成 {page_name} 页面...")
                result = call_multimodal_model(sp, user_prompt, screen_url, llm_config, ctx)

                # 解析返回结果
                vue_code = extract_vue_code(result)

                if vue_code:
                    # 保存Vue文件（覆盖或新建）
                    with open(vue_file_path, 'w', encoding='utf-8') as f:
                        f.write(vue_code)

                    generated_pages.append(vue_file_path)
                    action_text = "重新设计完成" if is_update else "新建完成"
                    logger.info(f"[页面生成] 页面 {page_name} {action_text}: {vue_file_path}")
                else:
                    logger.warning(f"[页面生成] 页面 {page_name} 的大模型返回结果为空，跳过")

            except Exception as e:
                logger.error(f"[页面生成] 生成页面 {page_name} 失败: {e}", exc_info=True)
                continue

        pages_generated = len(generated_pages) > 0
        failed_count = len(page_dirs) - len(generated_pages)

        if generated_pages:
            logger.info(f"[页面生成] 完成！成功生成 {len(generated_pages)} 个页面: {[os.path.basename(p) for p in generated_pages]}")
        if failed_count > 0:
            logger.warning(f"[页面生成] 有 {failed_count} 个页面生成失败，请检查日志了解详情")

        return UniAppPageGenerateOutput(
            pages_generated=pages_generated,
            generated_pages=generated_pages,
            example_pages_count=len(page_dirs)
        )

    except Exception as e:
        logger.error(f"[页面生成] UniApp页面生成失败: {e}", exc_info=True)
        return UniAppPageGenerateOutput(
            pages_generated=False,
            generated_pages=[],
            example_pages_count=0
        )


def extract_vue_code(result: str) -> str:
    """从大模型返回结果中提取Vue代码"""
    try:
        # 尝试解析JSON
        result_data = json.loads(result)
        vue_code = result_data.get("vue_code", "")
        
        if vue_code:
            return vue_code
    except json.JSONDecodeError:
        logger.warning("无法解析JSON格式，尝试提取代码块")
    
    # 如果JSON解析失败，尝试提取代码块
    import re
    code_block_match = re.search(r'```vue\s*\n(.*?)\n```', result, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1)
    
    # 如果没有vue代码块，尝试提取普通代码块
    code_block_match = re.search(r'```\s*\n(.*?)\n```', result, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1)
    
    return ""


def call_multimodal_model(
    system_prompt: str,
    user_prompt: str,
    image_url: str,
    llm_config: dict,
    ctx: Context,
    max_retries: int = 3
) -> str:
    """
    调用火山方舟多模态大模型 (doubao-seed-2-0-pro-260215)
    使用 coze_coding_dev_sdk 的 LLMClient，带重试机制
    """
    import time

    last_error = None
    for attempt in range(max_retries):
        try:
            # 初始化LLM客户端
            client = LLMClient(ctx=ctx)

            # 构造多模态消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=[
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ])
            ]

            logger.info(f"[页面生成] 调用火山方舟多模态模型 (尝试 {attempt + 1}/{max_retries})...")

            # 调用模型
            response = client.invoke(
                messages=messages,
                model=llm_config.get("model", "doubao-seed-2-0-pro-260215"),
                temperature=llm_config.get("temperature", 0.5),
                max_completion_tokens=llm_config.get("max_completion_tokens", 8192)
            )

            # 处理响应
            content = response.content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = "".join(text_parts)

            logger.info(f"[页面生成] 火山方舟多模态模型调用成功")
            return content

        except Exception as e:
            last_error = e
            logger.warning(f"[页面生成] 调用火山方舟多模态模型失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                logger.info(f"[页面生成] 等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error(f"[页面生成] 调用火山方舟多模态模型最终失败: {e}")

    raise last_error
