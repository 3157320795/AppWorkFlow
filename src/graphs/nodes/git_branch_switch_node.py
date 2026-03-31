"""
Git分支切换节点：根据产品名称及产品分组自动切换分支
"""
import os
import subprocess
import logging
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import GitBranchSwitchInput, GitBranchSwitchOutput

logger = logging.getLogger(__name__)


def git_branch_switch_node(
    state: GitBranchSwitchInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> GitBranchSwitchOutput:
    """
    title: Git分支切换
    desc: 根据产品名称及产品分组自动切换分支至对应分支（如：七组猪猪来财 -> g7/zhuzhulaicai）
    integrations: 
    """
    ctx = runtime.context
    
    try:
        # 确定分支名称
        # 例如：七组猪猪来财 -> g7/zhuzhulaicai
        group_number = extract_group_number(state.product_group)
        product_pinyin = convert_to_pinyin(state.product_name)
        branch_name = f"{group_number}/{product_pinyin}"
        
        # 确定 uniapp 项目路径
        base_path = os.getenv("COZE_WORKSPACE_PATH", ".")
        uniapp_path = os.path.join(base_path, "uniapp")
        
        # 切换到 uniapp 目录
        os.chdir(uniapp_path)
        
        # 获取当前分支
        result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        current_branch = result.stdout.strip()
        logger.info(f"当前分支: {current_branch}")
        
        # 检查目标分支是否存在
        result = subprocess.run(["git", "branch", "-a"], capture_output=True, text=True)
        all_branches = result.stdout
        
        if branch_name in all_branches:
            # 分支存在，切换分支
            subprocess.run(["git", "checkout", branch_name], check=True)
            logger.info(f"切换到分支: {branch_name}")
        else:
            # 分支不存在，创建并切换
            subprocess.run(["git", "checkout", "-b", branch_name], check=True)
            logger.info(f"创建并切换到新分支: {branch_name}")
        
        # 确定 pages 目录路径
        pages_path = os.path.join(uniapp_path, "pages")
        
        return GitBranchSwitchOutput(
            branch_switched=True,
            branch_name=branch_name,
            pages_path=pages_path
        )
        
    except Exception as e:
        logger.error(f"Git分支切换失败: {e}")
        return GitBranchSwitchOutput(
            branch_switched=False,
            branch_name="",
            pages_path=""
        )


def extract_group_number(product_group: str) -> str:
    """从产品分组中提取组号，例如：七组/7组 -> g7，一组/1组 -> g1"""
    import re

    # 中文数字映射
    cn_num_map = {
        "一": "1", "二": "2", "三": "3", "四": "4",
        "五": "5", "六": "6", "七": "7", "八": "8",
        "九": "9", "十": "10",
        "1": "1", "2": "2", "3": "3", "4": "4",
        "5": "5", "6": "6", "7": "7", "8": "8",
        "9": "9", "0": "0"
    }

    # 先尝试匹配中文数字
    for cn, num in cn_num_map.items():
        if len(cn) == 1 and cn in product_group:
            # 确保是独立的数字（前后不是数字）
            pattern = f"{re.escape(cn)}[^\\d]"
            if re.search(pattern, product_group) or product_group.endswith(cn):
                return f"g{num}"

    # 如果没有匹配到中文数字，尝试直接提取阿拉伯数字
    match = re.search(r'(\d+)', product_group)
    if match:
        return f"g{match.group(1)}"

    # 默认返回 g1
    return "g1"


def convert_to_pinyin(text: str) -> str:
    """将中文转换为拼音（常用汉字映射）"""
    import re

    # 常用汉字拼音映射表
    pinyin_map = {
        # 动物
        "猪": "zhu", "牛": "niu", "羊": "yang", "鸡": "ji", "鸭": "ya",
        "鱼": "yu", "猫": "mao", "狗": "gou", "兔": "tu", "马": "ma",
        # 动作/状态
        "来": "lai", "去": "qu", "倒": "dao", "倒": "dao", "流": "liu",
        "走": "zou", "跑": "pao", "飞": "fei", "游": "you", "跳": "tiao",
        # 自然/物质
        "水": "shui", "火": "huo", "土": "tu", "木": "mu", "金": "jin",
        "石": "shi", "山": "shan", "河": "he", "海": "hai", "天": "tian",
        "地": "di", "风": "feng", "雨": "yu", "雪": "xue", "云": "yun",
        "日": "ri", "月": "yue", "星": "xing",
        # 物品/场所
        "车": "che", "房": "fang", "馆": "guan", "店": "dian", "场": "chang",
        "室": "shi", "厅": "ting", "园": "yuan", "院": "yuan", "楼": "lou",
        "门": "men", "窗": "chuang", "墙": "qiang", "路": "lu", "桥": "qiao",
        # 商业/财务
        "财": "cai", "钱": "qian", "银": "yin", "币": "bi", "货": "huo",
        "商": "shang", "品": "pin", "卖": "mai", "买": "mai", "租": "zu",
        "赁": "lin", "价": "jia", "格": "ge", "本": "ben", "利": "li",
        "益": "yi", "收": "shou", "入": "ru", "出": "chu", "支": "zhi",
        # 品质/感受
        "好": "hao", "坏": "huai", "美": "mei", "丑": "chou", "大": "da",
        "小": "xiao", "高": "gao", "低": "di", "长": "chang", "短": "duan",
        "新": "xin", "旧": "jiu", "快": "kuai", "慢": "man",
        # 抽象概念
        "运": "yun", "气": "qi", "福": "fu", "喜": "xi", "乐": "le",
        "吉": "ji", "祥": "xiang", "富": "fu", "贵": "gui", "宝": "bao",
        "玉": "yu", "珠": "zhu", "珍": "zhen",
        # 饮食
        "茶": "cha", "酒": "jiu", "饭": "fan", "菜": "cai", "肉": "rou",
        "米": "mi", "面": "mian", "糖": "tang", "油": "you", "盐": "yan",
        "酱": "jiang", "醋": "cu",
        # 量词/辅助
        "个": "ge", "只": "zhi", "条": "tiao", "张": "zhang", "本": "ben",
        "辆": "liang", "件": "jian", "份": "fen", "次": "ci", "遍": "bian",
        # 人/身份
        "人": "ren", "员": "yuan", "工": "gong", "客": "ke", "户": "hu",
        "主": "zhu", "公": "gong", "司": "si", "店": "dian", "家": "jia",
        # 方位
        "上": "shang", "下": "xia", "左": "zuo", "右": "you", "前": "qian",
        "后": "hou", "中": "zhong", "内": "nei", "外": "wai", "里": "li",
        # 数字
        "一": "yi", "二": "er", "三": "san", "四": "si", "五": "wu",
        "六": "liu", "七": "qi", "八": "ba", "九": "jiu", "十": "shi",
        "百": "bai", "千": "qian", "万": "wan", "亿": "yi",
        # 其他常用
        "的": "de", "了": "le", "是": "shi", "在": "zai", "有": "you",
        "我": "wo", "你": "ni", "他": "ta", "她": "ta", "它": "ta",
        "和": "he", "与": "yu", "或": "huo", "而": "er", "但": "dan",
        "为": "wei", "因": "yin", "所": "suo", "以": "yi", "及": "ji",
        "第": "di", "之": "zhi", "其": "qi", "他": "ta", "这": "zhe",
        "那": "na", "就": "jiu", "都": "dou", "很": "hen", "最": "zui",
        "更": "geng", "太": "tai", "极": "ji", "非": "fei", "常": "chang",
        "比": "bi", "较": "jiao", "相": "xiang", "当": "dang", "于": "yu",
        "等": "deng", "待": "dai", "候": "hou", "迎": "ying", "送": "song",
        "接": "jie", "受": "shou", "理": "li", "管": "guan", "控": "kong",
        "制": "zhi", "查": "cha", "看": "kan", "见": "jian", "到": "dao",
        "得": "de", "失": "shi", "成": "cheng", "功": "gong", "败": "bai",
        "胜": "sheng", "负": "fu", "输": "shu", "赢": "ying",
        "管": "guan", "理": "li", "统": "tong", "计": "ji", "录": "lu",
        "记": "ji", "存": "cun", "储": "chu", "备": "bei", "份": "fen",
        "恢": "hui", "复": "fu", "删": "shan", "除": "chu", "增": "zeng",
        "加": "jia", "减": "jian", "少": "shao", "修": "xiu", "改": "gai",
        "编": "bian", "辑": "ji", "更": "geng", "新": "xin", "建": "jian",
        "立": "li", "设": "she", "置": "zhi", "配": "pei", "安": "an",
        "装": "zhuang", "启": "qi", "动": "dong", "停": "ting", "止": "zhi",
        "开": "kai", "关": "guan", "启": "qi", "退": "tui", "出": "chu",
        "进": "jin", "入": "ru", "返": "fan", "回": "hui", "退": "tui",
        "消": "xiao", "确": "que", "认": "ren", "选": "xuan", "择": "ze",
        "填": "tian", "写": "xie", "输": "shu", "入": "ru", "提": "ti",
        "交": "jiao", "上": "shang", "传": "chuan", "下": "xia", "载": "zai",
        "导": "dao", "出": "chu", "导": "dao", "入": "ru", "打": "da",
        "印": "yin", "发": "fa", "布": "bu", "展": "zhan", "示": "shi",
        "播": "bo", "放": "fang", "停": "ting", "暂": "zan", "换": "huan",
        "切": "qie", "转": "zhuan", "调": "tiao", "整": "zheng", "设": "she",
        "配": "pei", "合": "he", "协": "xie", "调": "tiao", "帮": "bang",
        "助": "zhu", "支": "zhi", "持": "chi", "服": "fu", "务": "wu",
        "咨": "zi", "询": "xun", "问": "wen", "答": "da", "解": "jie",
        "答": "da", "回": "hui", "复": "fu", "反": "fan", "馈": "kui",
        "建": "jian", "议": "yi", "意": "yi", "见": "jian", "评": "ping",
        "价": "jia", "分": "fen", "析": "xi", "判": "pan", "断": "duan",
        "决": "jue", "策": "ce", "规": "gui", "划": "hua", "计": "ji",
        "划": "hua", "安": "an", "排": "pai", "布": "bu", "局": "ju",
        "组": "zu", "织": "zhi", "调": "diao", "度": "du", "指": "zhi",
        "挥": "hui", "令": "ling", "命": "ming", "任": "ren", "务": "wu",
        "工": "gong", "作": "zuo", "业": "ye", "操": "cao", "作": "zuo",
        "行": "xing", "动": "dong", "执": "zhi", "行": "xing", "完": "wan",
        "成": "cheng", "结": "jie", "束": "shu", "终": "zhong", "止": "zhi",
        "开": "kai", "始": "shi", "初": "chu", "始": "shi", "起": "qi",
        "源": "yuan", "来": "lai", "源": "yuan", "根": "gen", "源": "yuan",
        "本": "ben", "质": "zhi", "核": "he", "心": "xin", "重": "zhong",
        "要": "yao", "主": "zhu", "次": "ci", "辅": "fu", "助": "zhu",
        "备": "bei", "附": "fu", "属": "shu", "依": "yi", "附": "fu",
        "赖": "lai", "靠": "kao", "依": "yi", "托": "tuo", "凭": "ping",
        "借": "jie", "根": "gen", "据": "ju", "基": "ji", "础": "chu",
        "条": "tiao", "件": "jian", "环": "huan", "境": "jing", "背": "bei",
        "景": "jing", "情": "qing", "况": "kuang", "状": "zhuang", "态": "tai",
        "形": "xing", "势": "shi", "局": "ju", "面": "mian", "景": "jing",
        "象": "xiang", "气": "qi", "氛": "fen", "色": "se", "彩": "cai",
        "光": "guang", "明": "ming", "黑": "hei", "暗": "an", "亮": "liang",
        "清": "qing", "楚": "chu", "明": "ming", "白": "bai", "懂": "dong",
        "知": "zhi", "道": "dao", "了": "liao", "解": "jie", "认": "ren",
        "识": "shi", "熟": "shu", "悉": "xi", "掌": "zhang", "握": "wo",
        "会": "hui", "能": "neng", "够": "gou", "可": "ke", "以": "yi",
        "行": "xing", "能": "neng", "力": "li", "量": "liang", "实": "shi",
        "力": "li", "势": "shi", "力": "li", "权": "quan", "威": "wei",
        "影": "ying", "响": "xiang", "力": "li", "号": "hao", "召": "zhao",
        "力": "li", "说": "shuo", "服": "fu", "力": "li", "感": "gan",
        "染": "ran", "力": "li", "亲": "qin", "和": "he", "力": "li",
        "领": "ling", "导": "dao", "力": "li", "执": "zhi", "行": "xing",
        "力": "li", "创": "chuang", "造": "zao", "力": "li", "想": "xiang",
        "象": "xiang", "力": "li", "思": "si", "维": "wei", "能": "neng",
        "力": "li", "判": "pan", "断": "duan", "力": "li", "决": "jue",
        "策": "ce", "力": "li", "沟": "gou", "通": "tong", "能": "neng",
        "力": "li", "协": "xie", "调": "tiao", "能": "neng", "力": "li",
        "组": "zu", "织": "zhi", "能": "neng", "力": "li", "管": "guan",
        "理": "li", "能": "neng", "力": "li", "学": "xue", "习": "xi",
        "能": "neng", "力": "li", "适": "shi", "应": "ying", "能": "neng",
        "力": "li", "创": "chuang", "新": "xin", "能": "neng", "力": "li",
        "应": "ying", "变": "bian", "能": "neng", "力": "li", "承": "cheng",
        "压": "ya", "能": "neng", "力": "li", "抗": "kang", "压": "ya",
        "能": "neng", "力": "li", "自": "zi", "控": "kong", "能": "neng",
        "力": "li", "自": "zi", "律": "lv", "能": "neng", "力": "li",
        "反": "fan", "思": "si", "能": "neng", "力": "li", "总": "zong",
        "结": "jie", "能": "neng", "力": "li", "表": "biao", "达": "da",
        "能": "neng", "力": "li", "演": "yan", "讲": "jiang", "能": "neng",
        "力": "li", "写": "xie", "作": "zuo", "能": "neng", "力": "li",
        "阅": "yue", "读": "du", "能": "neng", "力": "li", "倾": "qing",
        "听": "ting", "能": "neng", "力": "li", "观": "guan", "察": "cha",
        "能": "neng", "力": "li", "分": "fen", "析": "xi", "能": "neng",
        "力": "li", "解": "jie", "决": "jue", "问": "wen", "题": "ti",
        "能": "neng", "力": "li", "处": "chu", "理": "li", "能": "neng",
        "力": "li", "应": "ying", "对": "dui", "能": "neng", "力": "li"
    }

    result = ""
    for char in text:
        if char in pinyin_map:
            result += pinyin_map[char]
        elif char.isalpha():
            result += char.lower()
        elif char.isdigit():
            result += char
        # 跳过标点和其他特殊字符

    # 如果没有转换成功（结果为空或全是数字），返回原始文本的小写形式
    if not result or result.isdigit():
        # 移除特殊字符，只保留字母数字
        result = re.sub(r'[^a-zA-Z0-9]', '', text.lower())

    return result if result else "branch"
