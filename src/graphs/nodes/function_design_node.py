"""
功能设计节点 - 根据产品名称使用app-function-designer技能设计功能
"""
import os
import json
import re
import logging
from typing import Dict, Any, List
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage
from graphs.state import FunctionDesignInput, FunctionDesignOutput

logger = logging.getLogger(__name__)

# 实体关键词列表
ENTITY_KEYWORDS = [
    # 动物类
    "猪", "牛", "羊", "鸡", "鸭", "鱼", "宠物", "猫", "狗", "兔", "马", "驴", "鹅", "鸽",
    # 物品类
    "车", "房", "设备", "商品", "库存", "货物", "仓库", "店铺", "店", "馆", "场",
    # 人物类
    "员工", "客户", "会员", "学生", "病人", "用户",
    # 场所类
    "养殖场", "农场", "工地", "工厂", "医院", "学校", "公司"
]

# 关系关键词列表
RELATION_KEYWORDS = [
    "管理", "养殖", "租赁", "销售", "服务", "运营", "饲养", "维护", "巡检", "配送",
    "管家", "助手", "来财", "记账", "打卡", "笔记"
]


def analyze_product_name(product_name: str) -> Dict[str, Any]:
    """
    分析产品名称，识别实体和关系关键词
    """
    entity_keyword = None
    relation_keyword = None
    
    # 检查实体关键词
    for keyword in ENTITY_KEYWORDS:
        if keyword in product_name:
            entity_keyword = keyword
            break
    
    # 检查关系关键词
    for keyword in RELATION_KEYWORDS:
        if keyword in product_name:
            relation_keyword = keyword
            break
    
    # 判断应用类型
    if entity_keyword:
        app_type = "实体型"
    elif relation_keyword:
        app_type = "关系型"
    else:
        app_type = "通用型"
    
    return {
        "entity_keyword": entity_keyword or "无",
        "relation_keyword": relation_keyword or "无",
        "app_type": app_type
    }


def extract_json(content: str) -> Dict[str, Any]:
    """从响应中提取JSON"""
    try:
        # 尝试直接解析
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 尝试提取JSON块
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # 尝试提取花括号内容
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # 返回默认结构
    return {}


def call_llm(system_prompt: str, user_prompt: str, config: dict, ctx: Context, max_retries: int = 3) -> str:
    """
    调用火山方舟大模型 (doubao-seed-2-0-pro-260215)
    使用 coze_coding_dev_sdk 的 LLMClient，带重试机制
    """
    import time
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # 初始化LLM客户端
            client = LLMClient(ctx=ctx)
            
            # 构造消息
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            logger.info(f"调用火山方舟模型 (尝试 {attempt + 1}/{max_retries})...")
            
            # 调用模型
            response = client.invoke(
                messages=messages,
                model=config.get("model", "doubao-seed-2-0-pro-260215"),
                temperature=config.get("temperature", 0.7),
                max_completion_tokens=config.get("max_completion_tokens", 8192)
            )
            
            # 处理响应
            content = response.content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = "".join(text_parts)
            
            logger.info(f"火山方舟模型调用成功")
            return content
            
        except Exception as e:
            last_error = e
            logger.warning(f"调用火山方舟模型失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                logger.error(f"调用火山方舟模型最终失败: {e}")
    
    raise last_error


def function_design_node(
    state: FunctionDesignInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> FunctionDesignOutput:
    """
    title: 功能设计
    desc: 使用app-function-designer技能，根据产品名称智能分析类型，生成三套完全不同的功能设计方案
    integrations: 火山方舟大模型, app-function-designer技能
    """
    ctx = runtime.context
    product_name = state.product_name
    
    # 读取大模型配置
    cfg_file = os.path.join(os.getenv("COZE_WORKSPACE_PATH"), config['metadata']['llm_cfg'])
    with open(cfg_file, 'r') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    
    # 使用jinja2模板渲染用户提示词
    up_tpl = Template(_cfg.get("up", ""))
    user_prompt_content = up_tpl.render({"product_name": product_name})
    
    logger.info(f"[功能设计] 产品名称: {product_name}")
    
    try:
        # 步骤1：分析产品名称
        analysis = analyze_product_name(product_name)
        logger.info(f"[功能设计] 应用类型: {analysis['app_type']}")
        logger.info(f"[功能设计] 实体关键词: {analysis['entity_keyword']}")
        logger.info(f"[功能设计] 关系关键词: {analysis['relation_keyword']}")
        
        # 步骤2：调用大模型生成三套方案
        logger.info(f"[功能设计] 调用火山方舟模型生成三套方案...")
        result = call_llm(sp, user_prompt_content, llm_config, ctx)
        
        # 步骤3：解析返回结果
        design_schemes = []
        
        try:
            result_data = extract_json(result)
            design_schemes = result_data.get("schemes", [])
            
            # 验证方案数量
            if len(design_schemes) != 3:
                logger.warning(f"返回的方案数量不是3个，实际返回: {len(design_schemes)}")
            
            # 记录每个方案的关键信息
            for scheme in design_schemes:
                logger.info(f"方案 {scheme.get('scheme_id')}: {scheme.get('scheme_name')} - {scheme.get('description')}")
            
            # 补充分析信息到每个方案
            for scheme in design_schemes:
                if "content" not in scheme:
                    scheme["content"] = {}
                scheme["content"]["analysis"] = analysis
            
            return FunctionDesignOutput(
                design_schemes=design_schemes,
                product_name=product_name
            )
            
        except Exception as e:
            logger.error(f"解析大模型返回结果失败: {e}")
            logger.error(f"原始返回: {result[:1000]}...")
            
            # 如果解析失败，构造默认方案
            design_schemes = generate_default_schemes(product_name, analysis, e)
            return FunctionDesignOutput(
                design_schemes=design_schemes,
                product_name=product_name
            )
            
    except Exception as e:
        logger.error(f"生成功能设计方案失败: {e}", exc_info=True)
        
        # 分析产品名称，生成默认方案
        analysis = analyze_product_name(product_name)
        design_schemes = generate_default_schemes(product_name, analysis, e)
        return FunctionDesignOutput(
            design_schemes=design_schemes,
            product_name=product_name
        )


def generate_default_schemes(product_name: str, analysis: Dict[str, Any], error: Exception) -> List[Dict[str, Any]]:
    """生成默认方案（当大模型调用失败时使用）"""
    logger.warning(f"使用默认方案生成，错误: {error}")
    
    app_type = analysis["app_type"]
    entity_keyword = analysis["entity_keyword"]
    
    # 根据应用类型生成不同的默认方案
    if app_type == "实体型":
        return generate_entity_default_schemes(product_name, entity_keyword)
    elif app_type == "关系型":
        return generate_relation_default_schemes(product_name)
    else:
        return generate_general_default_schemes(product_name)


def generate_entity_default_schemes(product_name: str, entity_keyword: str) -> List[Dict[str, Any]]:
    """生成实体型应用的默认方案"""
    entity = entity_keyword or "实体"
    
    return [
        {
            "scheme_id": 1,
            "scheme_name": "标准实用型方案",
            "description": "基于标准规范的功能设计，注重实用性和易用性",
            "content": {
                "app_type": "实体型",
                "app_position": f"{product_name}单机工具应用",
                "main_functions": {
                    "type": "entity",
                    "modules": [
                        {"module_name": f"{entity}档案", "core_functions": f"{entity}基本信息管理、{entity}状态查询"},
                        {"module_name": f"{entity}订单", "core_functions": f"{entity}交易记录、订单管理"},
                        {"module_name": f"{entity}饲养/维护", "core_functions": f"日常养护记录、维护计划"},
                        {"module_name": f"{entity}居所/位置", "core_functions": f"位置信息管理、场所维护"},
                        {"module_name": "客户管理", "core_functions": "客户信息、联系人管理"},
                        {"module_name": "员工管理", "core_functions": "员工信息、权限管理"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "首页", "sections": [{"section_name": "数据展示区", "content": f"{entity}核心数据统计"}, {"section_name": "功能入口区", "content": "快捷功能入口"}]},
                        {"page_name": f"{entity}列表", "sections": [{"section_name": f"{entity}列表", "content": "展示所有实体项"}]},
                        {"page_name": "统计", "sections": [{"section_name": "统计图表", "content": "数据可视化展示"}]},
                        {"page_name": "我的", "sections": [{"section_name": "个人设置", "content": "用户相关设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True,
                    "local_storage_only": True
                },
                "design_highlights": [f"专注于{entity}的实用管理功能", "界面简洁易用"]
            }
        },
        {
            "scheme_id": 2,
            "scheme_name": "创新交互型方案",
            "description": "注重交互创新和用户体验的设计",
            "content": {
                "app_type": "实体型",
                "design_style": "创新交互",
                "main_functions": {
                    "type": "entity",
                    "modules": [
                        {"module_name": f"{entity}看板", "core_functions": "可视化看板、智能筛选"},
                        {"module_name": f"{entity}工作台", "core_functions": "操作中心、任务管理"},
                        {"module_name": "数据洞察", "core_functions": "智能分析、趋势预测"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "看板", "sections": [{"section_name": "可视化看板", "content": "核心数据可视化"}]},
                        {"page_name": "工作台", "sections": [{"section_name": "工作区", "content": "主要操作区域"}]},
                        {"page_name": "我的", "sections": [{"section_name": "个人中心", "content": "用户设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True
                }
            }
        },
        {
            "scheme_id": 3,
            "scheme_name": "简洁高效型方案",
            "description": "注重效率和简洁性的设计方案",
            "content": {
                "app_type": "实体型",
                "design_style": "简洁高效",
                "main_functions": {
                    "type": "entity",
                    "modules": [
                        {"module_name": f"{entity}管理", "core_functions": f"{entity}增删改查"},
                        {"module_name": "统计分析", "core_functions": "数据统计、图表展示"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "首页", "sections": [{"section_name": "快速操作", "content": "主要功能入口"}]},
                        {"page_name": "列表", "sections": [{"section_name": f"{entity}列表", "content": "所有实体项"}]},
                        {"page_name": "统计", "sections": [{"section_name": "数据统计", "content": "统计数据展示"}]},
                        {"page_name": "我的", "sections": [{"section_name": "设置", "content": "系统设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True
                }
            }
        }
    ]


def generate_relation_default_schemes(product_name: str) -> List[Dict[str, Any]]:
    """生成关系型应用的默认方案"""
    return [
        {
            "scheme_id": 1,
            "scheme_name": "标准实用型方案",
            "description": "基于标准规范的功能设计，注重实用性和易用性",
            "content": {
                "app_type": "关系型",
                "app_position": f"{product_name}单机工具应用",
                "main_functions": {
                    "type": "relation",
                    "modules": [
                        {"module_name": "档案管理", "core_functions": "基础档案管理"},
                        {"module_name": "业务管理", "core_functions": "核心业务操作"},
                        {"module_name": "统计分析", "core_functions": "数据统计与分析"},
                        {"module_name": "异常管理", "core_functions": "异常情况记录"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "首页", "sections": [{"section_name": "数据展示区", "content": "核心数据展示"}]},
                        {"page_name": "列表", "sections": [{"section_name": "数据列表", "content": "展示所有数据项"}]},
                        {"page_name": "统计", "sections": [{"section_name": "统计图表", "content": "数据可视化"}]},
                        {"page_name": "我的", "sections": [{"section_name": "个人设置", "content": "用户设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True
                }
            }
        },
        {
            "scheme_id": 2,
            "scheme_name": "创新交互型方案",
            "description": "注重交互创新和用户体验的设计",
            "content": {
                "app_type": "关系型",
                "design_style": "创新交互",
                "main_functions": {
                    "type": "relation",
                    "modules": [
                        {"module_name": "智能看板", "core_functions": "智能可视化"},
                        {"module_name": "工作台", "core_functions": "统一操作中心"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "看板", "sections": [{"section_name": "智能看板", "content": "可视化展示"}]},
                        {"page_name": "工作台", "sections": [{"section_name": "工作区", "content": "操作区域"}]},
                        {"page_name": "我的", "sections": [{"section_name": "个人中心", "content": "用户设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True
                }
            }
        },
        {
            "scheme_id": 3,
            "scheme_name": "简洁高效型方案",
            "description": "注重效率和简洁性的设计方案",
            "content": {
                "app_type": "关系型",
                "design_style": "简洁高效",
                "main_functions": {
                    "type": "relation",
                    "modules": [
                        {"module_name": "档案管理", "core_functions": "档案增删改查"},
                        {"module_name": "业务操作", "core_functions": "业务操作流程"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "首页", "sections": [{"section_name": "快速操作", "content": "主要功能入口"}]},
                        {"page_name": "列表", "sections": [{"section_name": "数据列表", "content": "所有数据项"}]},
                        {"page_name": "统计", "sections": [{"section_name": "数据统计", "content": "统计数据展示"}]},
                        {"page_name": "我的", "sections": [{"section_name": "设置", "content": "系统设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True
                }
            }
        }
    ]


def generate_general_default_schemes(product_name: str) -> List[Dict[str, Any]]:
    """生成通用型应用的默认方案"""
    return [
        {
            "scheme_id": 1,
            "scheme_name": "标准实用型方案",
            "description": "基于标准规范的功能设计，注重实用性和易用性",
            "content": {
                "app_type": "通用型",
                "app_position": f"{product_name}单机工具应用",
                "main_functions": {
                    "type": "general",
                    "modules": [
                        {"module_name": "数据管理", "core_functions": "数据录入、查询、编辑、删除"},
                        {"module_name": "统计分析", "core_functions": "数据统计、图表展示、报表导出"},
                        {"module_name": "个人中心", "core_functions": "用户信息、系统设置、数据备份"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "首页", "sections": [{"section_name": "数据展示区", "content": "展示核心数据"}]},
                        {"page_name": "列表", "sections": [{"section_name": "数据列表", "content": "展示所有数据项"}]},
                        {"page_name": "统计", "sections": [{"section_name": "统计图表", "content": "数据统计可视化"}]},
                        {"page_name": "我的", "sections": [{"section_name": "个人设置", "content": "用户相关设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True,
                    "local_storage_only": True
                },
                "design_highlights": [f"为{product_name}设计的标准实用型方案"]
            }
        },
        {
            "scheme_id": 2,
            "scheme_name": "创新交互型方案",
            "description": "注重交互创新和用户体验的设计",
            "content": {
                "app_type": "通用型",
                "design_style": "创新交互",
                "main_functions": {
                    "type": "general",
                    "modules": [
                        {"module_name": "智能管理", "core_functions": "智能数据处理"},
                        {"module_name": "数据洞察", "core_functions": "智能分析与展示"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "看板", "sections": [{"section_name": "智能看板", "content": "数据可视化"}]},
                        {"page_name": "管理", "sections": [{"section_name": "工作区", "content": "主要操作区域"}]},
                        {"page_name": "我的", "sections": [{"section_name": "个人中心", "content": "用户设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True
                }
            }
        },
        {
            "scheme_id": 3,
            "scheme_name": "简洁高效型方案",
            "description": "注重效率和简洁性的设计方案",
            "content": {
                "app_type": "通用型",
                "design_style": "简洁高效",
                "main_functions": {
                    "type": "general",
                    "modules": [
                        {"module_name": "数据管理", "core_functions": "数据增删改查"},
                        {"module_name": "统计分析", "core_functions": "基础数据统计"}
                    ]
                },
                "page_design": {
                    "pages": [
                        {"page_name": "首页", "sections": [{"section_name": "快速操作", "content": "主要功能入口"}]},
                        {"page_name": "列表", "sections": [{"section_name": "数据列表", "content": "所有数据项"}]},
                        {"page_name": "统计", "sections": [{"section_name": "数据统计", "content": "统计数据展示"}]},
                        {"page_name": "我的", "sections": [{"section_name": "设置", "content": "系统设置"}]}
                    ]
                },
                "compliance_check": {
                    "offline_only": True,
                    "no_network_features": True
                }
            }
        }
    ]
