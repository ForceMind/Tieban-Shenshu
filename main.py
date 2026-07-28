import os
import sys
import csv
import datetime
import traceback
import pandas as pd
import urllib.request
import json

DEBUG_SERVER_URL = "http://127.0.0.1:47234/event"

def report_log(level, event_type, data):
    try:
        payload = json.dumps({"level": level, "type": event_type, "data": data}).encode()
        req = urllib.request.Request(DEBUG_SERVER_URL, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except: pass

# 尝试导入 cnlunar
try:
    import cnlunar
except ImportError:
    print("【严重错误】: 未找到 'cnlunar' 模块，请运行: pip install cnlunar")
    sys.exit(1)

# ==============================================================================
# 0. 全局工具函数
# ==============================================================================
def input_datetime(desc_str):
    """处理用户输入的日期时间"""
    while True:
        try:
            dt_str = input(f"请输入{desc_str} (格式 YYYY-MM-DD HH:MM): ").strip()
            parts = dt_str.split()
            if len(parts) != 2:
                print("格式错误，日期和时间之间请用空格隔开。")
                continue
            date_str, time_str = parts
            year, month, day = map(int, date_str.split('-'))
            hour, minute = map(int, time_str.split(':'))
            if hour >= 23:
                print(f"  [提示] {hour}:{minute} 为晚子时，系统已自动按次日早子时排盘。")
                dt = datetime.datetime(year, month, day) + datetime.timedelta(days=1)
                return datetime.datetime(dt.year, dt.month, dt.day, 0, minute)
            return datetime.datetime(year, month, day, hour, minute)
        except ValueError:
            print("输入无效，请重新输入 (示例: 1951-10-14 18:00)")

def convert_to_bazi_info(dt_obj):
    """将公历转为八字信息"""
    try:
        a = cnlunar.Lunar(dt_obj, godType='8char')
        try: lm, ld = int(a.lunarMonth), int(a.lunarDay)
        except: lm, ld = 1, 1 
        return {
            "lunar_month": lm, "lunar_day": ld, "is_leap": "闰" in a.lunarMonthCn,
            "bazi": {"year": a.year8Char, "month": a.month8Char, "day": a.day8Char, "time": a.twohour8Char},
            "date_str": dt_obj.strftime("%Y-%m-%d %H:%M"),
            "lunar_str": f"{a.lunarYearCn}年 {a.lunarMonthCn}{a.lunarDayCn}"
        }
    except Exception as e:
        print(f"八字转换失败: {e}")
        return None

# ==============================================================================
# 1. 静态算法常量
# ==============================================================================

# ==============================================================================
# 1. 天干地支基础数据
# ==============================================================================

TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
SHENG_XIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

WU_XING = ["金", "水", "木", "火", "土"]

GAN_ZHI_60 = [
    "甲子", "乙丑", "丙寅", "丁卯", "戊辰", "己巳", "庚午", "辛未", "壬申", "癸酉",
    "甲戌", "乙亥", "丙子", "丁丑", "戊寅", "己卯", "庚辰", "辛巳", "壬午", "癸未",
    "甲申", "乙酉", "丙戌", "丁亥", "戊子", "己丑", "庚寅", "辛卯", "壬辰", "癸巳",
    "甲午", "乙未", "丙申", "丁酉", "戊戌", "己亥", "庚子", "辛丑", "壬寅", "癸卯",
    "甲辰", "乙巳", "丙午", "丁未", "戊申", "己酉", "庚戌", "辛亥", "壬子", "癸丑",
    "甲寅", "乙卯", "丙辰", "丁巳", "戊午", "己未", "庚申", "辛酉", "壬戌", "癸亥"
]

TIAN_GAN_ORDER = {g: i + 1 for i, g in enumerate(TIAN_GAN)}
DI_ZHI_ORDER = {z: i + 1 for i, z in enumerate(DI_ZHI)}


# ==============================================================================
# 2. 纳音五行（六十甲子纳音映射）
# ==============================================================================

NAYIN_WUXING = {
    "甲子": "金", "乙丑": "金", "丙寅": "火", "丁卯": "火", "戊辰": "木", "己巳": "木",
    "庚午": "土", "辛未": "土", "壬申": "金", "癸酉": "金", "甲戌": "火", "乙亥": "火",
    "丙子": "水", "丁丑": "水", "戊寅": "土", "己卯": "土", "庚辰": "金", "辛巳": "金",
    "壬午": "木", "癸未": "木", "甲申": "水", "乙酉": "水", "丙戌": "土", "丁亥": "土",
    "戊子": "火", "己丑": "火", "庚寅": "木", "辛卯": "木", "壬辰": "水", "癸巳": "水",
    "甲午": "金", "乙未": "金", "丙申": "火", "丁酉": "火", "戊戌": "木", "己亥": "木",
    "庚子": "土", "辛丑": "土", "壬寅": "金", "癸卯": "金", "甲辰": "火", "乙巳": "火",
    "丙午": "水", "丁未": "水", "戊申": "土", "己酉": "土", "庚戌": "金", "辛亥": "金",
    "壬子": "木", "癸丑": "木", "甲寅": "水", "乙卯": "水", "丙辰": "土", "丁巳": "土",
    "戊午": "火", "己未": "火", "庚申": "木", "辛酉": "木", "壬戌": "水", "癸亥": "水"
}

NAYIN_FULL = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城头土", "己卯": "城头土",
    "庚辰": "白蜡金", "辛巳": "白蜡金", "壬午": "杨柳木", "癸未": "杨柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "长流水", "癸巳": "长流水", "甲午": "沙中金", "乙未": "沙中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "覆灯火", "乙巳": "覆灯火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "沙中土", "丁巳": "沙中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水"
}

NAYIN_NUMBER = {"金": 4, "木": 3, "水": 1, "火": 2, "土": 5}

FIVE_SOUNDS = {
    "水": "羽",
    "火": "徵",
    "木": "角",
    "金": "商",
    "土": "宫"
}


# ==============================================================================
# 3. 天干地支取数（多种取数体系）
# ==============================================================================

TIAN_GAN_NUMBER_A = {
    "甲": 1, "乙": 2, "丙": 3, "丁": 4, "戊": 5,
    "己": 6, "庚": 7, "辛": 8, "壬": 9, "癸": 0
}

TIAN_GAN_NUMBER_B = {
    "甲": 6, "乙": 2, "丙": 8, "丁": 7, "戊": 1,
    "己": 9, "庚": 3, "辛": 4, "壬": 6, "癸": 2
}

TIAN_GAN_NUMBER_C = {
    "甲": 1, "乙": 6, "丙": 2, "丁": 7, "戊": 3,
    "己": 8, "庚": 4, "辛": 9, "壬": 5, "癸": 0
}

DI_ZHI_NUMBER = {
    "子": 1, "丑": 5, "寅": 3, "卯": 8, "辰": 5, "巳": 2,
    "午": 7, "未": 5, "申": 4, "酉": 9, "戌": 5, "亥": 4
}


# ==============================================================================
# 4. 太玄数（核心取数体系）
# ==============================================================================

TAIXUAN_NUMBER = {
    "甲": 9, "己": 9, "乙": 8, "庚": 8,
    "丙": 7, "辛": 7, "丁": 6, "壬": 6,
    "戊": 5, "癸": 5,
    "子": 9, "午": 9, "丑": 8, "未": 8,
    "寅": 7, "申": 7, "卯": 6, "酉": 6,
    "辰": 5, "戌": 5, "巳": 4, "亥": 4
}

DI_ZHI_TAIXUAN = {
    "子": 4, "午": 4, "卯": 4, "酉": 4,
    "辰": 5, "戌": 5, "丑": 5, "未": 5,
    "寅": 6, "申": 6, "巳": 6, "亥": 6
}


# ==============================================================================
# 5. 八卦数据
# ==============================================================================

XIAN_TIAN_GUA_NUM = {
    "乾": 1, "兑": 2, "离": 3, "震": 4,
    "巽": 5, "坎": 6, "艮": 7, "坤": 8
}

HOU_TIAN_GUA_NUM = {
    "坎": 1, "坤": 2, "震": 3, "巽": 4,
    "中": 5, "乾": 6, "兑": 7, "艮": 8, "离": 9
}

BA_GUA = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]

GUA_WUXING = {
    "乾": "金", "兑": "金", "离": "火", "震": "木",
    "巽": "木", "坎": "水", "艮": "土", "坤": "土"
}

GUA_DIRECTION = {
    "坎": "北", "坤": "西南", "震": "东", "巽": "东南",
    "中": "中", "乾": "西北", "兑": "西", "艮": "东北", "离": "南"
}


# ==============================================================================
# 6. 天干地支配卦
# ==============================================================================

TIAN_GAN_TO_GUA = {
    "壬": "乾", "甲": "乾",
    "乙": "坤", "癸": "坤",
    "庚": "震",
    "辛": "巽",
    "己": "离",
    "戊": "坎",
    "丙": "艮",
    "丁": "兑"
}

DI_ZHI_TO_GUA = {
    "亥": "坎", "子": "坎",
    "寅": "震",
    "巳": "离", "午": "离",
    "丑": "坤",
    "卯": "乾", "酉": "乾",
    "辰": "兑",
    "未": "艮", "申": "艮",
    "戌": "巽"
}


# ==============================================================================
# 7. 秘数常数
# ==============================================================================

SECRET_NUMBERS_99_1 = [9, 18, 27, 36, 45, 54, 63, 72, 81]
SECRET_NUMBERS_99_2 = [9, 19, 29, 39, 49, 59, 69, 79, 89, 99]

SECRET_NUMBERS_BASIC = {
    "六七八九": [6, 7, 8, 9],
    "十二秘数": 12,
    "二十四秘数": 24,
    "三十六秘数": 36,
    "七十二秘数": 72,
    "六十四秘数": 64,
    "九十六秘数": 96,
    "铁板神数核心秘数": 48
}

# ==============================================================================
# 7.1 刻干数映射与八刻细分规则（铁板神数核心算法）
# ==============================================================================

# 刻干数映射：八刻对应天干数（甲=1,乙=2,丙=3,丁=4,戊=5,己=6,庚=7,辛=8）
KE_GAN_NUMBER = {
    "初刻": 1,    # 甲
    "一刻": 2,    # 乙
    "二刻": 3,    # 丙
    "三刻": 4,    # 丁
    "四刻": 5,    # 戊
    "五刻": 6,    # 己
    "六刻": 7,    # 庚
    "正刻": 8     # 辛
}

# 八刻时间细分（一时辰=2小时=8刻，每刻15分钟）
# 子时范围：23:00-01:00
# 每刻对应分钟区间
EIGHT_KE_TIME_RANGE = {
    "初刻": (0, 15),    # 0-15分
    "一刻": (15, 30),   # 15-30分
    "二刻": (30, 45),   # 30-45分
    "三刻": (45, 60),   # 45-60分
    "四刻": (60, 75),   # 60-75分
    "五刻": (75, 90),   # 75-90分
    "六刻": (90, 105),  # 90-105分
    "正刻": (105, 120)  # 105-120分
}

# 铁板神数核心公式：终局条文数 = 本命基数 + 刻干数 × 48
TIEBAN_CORE_SECRET = 48

DIRECTION_NUMBER = {
    "乾": 6, "坎": 1, "艮": 8, "震": 3,
    "巽": 4, "离": 9, "坤": 2, "兑": 7, "中": 5
}

HOUR_NUMBER = {
    "子": 1, "丑": 2, "寅": 3, "卯": 4, "辰": 5, "巳": 6,
    "午": 7, "未": 8, "申": 9, "酉": 10, "戌": 11, "亥": 12
}


# ==============================================================================
# 8. 天地数规则
# ==============================================================================

TIAN_SHU_BASE = 25
DI_SHU_BASE = 30

ODD_NUMBERS = [1, 3, 5, 7, 9]
EVEN_NUMBERS = [2, 4, 6, 8, 10]


# ==============================================================================
# 9. 三元九运时间界定
# ==============================================================================

SAN_YUAN_PERIODS = {
    "上元": (1864, 1923),
    "中元": (1924, 1983),
    "下元": (1984, 2043)
}

WU_SHU_JI_GONG = {
    "上元": {"男": "艮", "女": "坤"},
    "中元": {"阳男阴女": "艮", "阴男阳女": "坤"},
    "下元": {"男": "离", "女": "兑"}
}


# ==============================================================================
# 10. 辅助工具函数
# ==============================================================================

def get_nayin(gz):
    return NAYIN_WUXING.get(gz, "")

def get_nayin_full(gz):
    return NAYIN_FULL.get(gz, "")

def get_taixuan(g, z=None):
    if z is None:
        return TAIXUAN_NUMBER.get(g, 0)
    return TAIXUAN_NUMBER.get(g, 0) + TAIXUAN_NUMBER.get(z, 0)

def get_gua_number(gua, use_houtian=True):
    if use_houtian:
        return HOU_TIAN_GUA_NUM.get(gua, 0)
    return XIAN_TIAN_GUA_NUM.get(gua, 0)

def get_tian_di_numbers(odd_sum, even_sum):
    if odd_sum > TIAN_SHU_BASE:
        tian = (odd_sum - TIAN_SHU_BASE) % 10
    else:
        tian = odd_sum % 10

    if even_sum > DI_SHU_BASE:
        di = (even_sum - DI_SHU_BASE) % 10
    else:
        di = even_sum % 10

    return tian, di

def get_gua_from_number(num):
    reverse_hou = {v: k for k, v in HOU_TIAN_GUA_NUM.items()}
    return reverse_hou.get(num, "")


# ==============================================================================
# 10.1 八刻细分与刻干计算函数（铁板神数核心算法）
# ==============================================================================

def get_eight_ke_from_time(dt_obj):
    """根据出生时间计算八刻细分
    
    一时辰=2小时=120分钟=8刻，每刻15分钟
    
    返回：刻别名称（初刻/一刻/.../正刻）
    """
    hour = dt_obj.hour
    minute = dt_obj.minute
    
    # 将时间转换为时辰内的分钟数（0-120）
    # 子时范围：23:00-01:00，对应分钟0-120
    if hour == 23:
        minutes_in_ke = minute
    elif hour == 0:
        minutes_in_ke = 60 + minute
    else:
        # 其他时辰，直接计算该小时内的分钟 + 60分钟
        minutes_in_ke = (hour % 2) * 60 + minute
    
    # 根据分钟查找对应的刻别
    for ke_name, (start, end) in EIGHT_KE_TIME_RANGE.items():
        if start <= minutes_in_ke < end:
            return ke_name
    
    # 默认返回正刻
    return "正刻"


def get_ke_gan_number(ke_name):
    """根据刻别获取刻干数
    
    甲=1,乙=2,丙=3,丁=4,戊=5,己=6,庚=7,辛=8
    """
    return KE_GAN_NUMBER.get(ke_name, 8)  # 默认正刻=辛=8


def calculate_tieban_fortune(base_num, ke_gan_num):
    """铁板神数核心公式：终局条文数 = 本命基数 + 刻干数 × 48
    
    参数：
        base_num - 本命基数
        ke_gan_num - 刻干数（1-8）
    
    返回：终局条文数
    """
    return base_num + ke_gan_num * TIEBAN_CORE_SECRET


def get_san_yuan_period(year):
    """根据年份确定三元九运的元期
    
    上元：1864-1923年（男1-60岁，女1-60岁）
    中元：1924-1983年
    下元：1984-2043年
    """
    if 1864 <= year <= 1923:
        return "上元"
    elif 1924 <= year <= 1983:
        return "中元"
    elif 1984 <= year <= 2043:
        return "下元"
    # 超出范围时，根据规律推算
    elif year > 2043:
        cycle = (year - 1864) // 120
        offset = (year - 1864) % 120
        if offset < 60:
            return "上元"
        elif offset < 120:
            return "中元" if offset < 120 else "上元"
    return "下元"


def get_wu_shu_ji_gong_gua(san_yuan, gender, is_yang):
    """根据元期和性别获取五数寄宫的卦
    
    上元：男艮女坤
    中元：阳男阴女用艮，阴男阳女用坤
    下元：男离女兑
    """
    if san_yuan == "上元":
        return "艮" if gender == "男" else "坤"
    elif san_yuan == "中元":
        if (gender == "男" and is_yang) or (gender == "女" and not is_yang):
            return "艮"  # 阳男阴女
        else:
            return "坤"  # 阴男阳女
    elif san_yuan == "下元":
        return "离" if gender == "男" else "兑"
    return "坤"


def get_bagua_jiaze_start(hex_name):
    """根据卦名获取八卦加则的起始数
    
    乾卦六为头：乾卦从36开始
    兑为后少女：兑卦从3开始
    其他卦从30开始
    """
    if hex_name == "乾":
        return 36
    elif hex_name == "兑":
        return 3
    else:
        return 30


def apply_bagua_jiaze_rule(current_num, hex_name, iteration=1):
    """应用八卦加则规则进行数字演变
    
    规则：
    - 遇十当不用：任何加法结果≥10时，只取个位数
    - 变知六八止：数字演变到6或8时停止
    
    参数：
    - current_num: 当前数字
    - hex_name: 卦名
    - iteration: 当前迭代次数（用于追踪）
    
    返回：(最终数字, 是否停止, 迭代次数)
    """
    # 获取起始数
    start = get_bagua_jiaze_start(hex_name)
    
    # 第一次迭代：起始数 + 当前数
    result = start + current_num
    
    # 遇十当不用：≥10只取个位
    if result >= 10:
        result = result % 10
    
    # 检查是否停止（6或8）
    if result == 6 or result == 8:
        return result, True, iteration
    
    # 如果还没停止，继续迭代
    if iteration < 10:  # 安全限制，防止无限循环
        return apply_bagua_jiaze_rule(result, hex_name, iteration + 1)
    
    return result, False, iteration


# ==============================================================================
# 11. 铁板神数八卦加则核心口诀
# ==============================================================================

BA_GUA_JIA_ZHE = {
    "乾": {"start": 36, "desc": "乾卦六为头，初爻从36起"},
    "兑": {"start": 3, "desc": "兑为后少女，初爻从3起"},
    "default": {"start": 30, "desc": "爻从三十起，其他卦从30起"},
    "rule_yu_10": "遇十当不用：任何加法结果≥10时，只取个位数",
    "rule_stop": "变知六八止：数字演变到6或8时停止"
}


# ==============================================================================
# 12. 条文检索基数取整规则
# ==============================================================================

def get_article_base(sum_value):
    if sum_value < 1000:
        return (sum_value // 100) * 100
    return (sum_value // 100) * 100


# ==============================================================================
# 13. 六亲宫位
# ==============================================================================

SIX_QIN_PILLARS = {
    "年柱": "父母宫",
    "月柱": "兄弟宫",
    "日柱": "夫妻宫",
    "时柱": "子女宫"
}

SIX_QIN = ["父母", "兄弟", "妻财", "官鬼", "子孙", "己身"]

# ==============================================================================
# 2. 数据加载器
# ==============================================================================
class TieBanDataLoader:
    def __init__(self, db_folder="./DB"):
        self.db_folder = db_folder
        self.tables = {} 
        self.rule_tables = []
        
        # 卦象映射表 - 支持按 (刻别, 本命数) 查找卦名
        self.HEXAGRAM_MAP = {}          # 兼容原有逻辑：仅按本命数查找（取优先匹配）
        self.HEXAGRAM_DETAIL_MAP = {}   # 完整映射：(刻别, 本命数) -> 卦名
        
        self.DESTINY_DATA = {}
        self.LIUNIAN_START = {}
        self.LIUNIAN_SEQ = {}
        self.MARKER_TABLE = {}
        self.LETTER_TABLE = {}
        self.SECRET_NUM_TABLE = {}
        
        # 14-14相关映射表
        self.DATA_BY_LETTER = {}        # (字母, 岁数) -> (基数, 加数, 条文校正数)
        self.DATA_BY_CORRECTION = {}    # (条文校正数, 岁数) -> (基数, 加数) 用于校正后查找
        self.CORRECTION_TO_LETTER = {}  # (条文校正数, 岁数) -> 字母 反向映射
        
        # 新增：条文断词映射表
        self.FORTUNE_DUANYU_MAP = {}    # 条文数字 -> (断语, 对应年龄)
        self.FORTUNE_DUANYU_RAW = []    # 原始断词数据
        
        # 新增：六亲考刻数据结构
        self.SIX_QIN_FORTUNES = {}      # (六亲类型, 刻别) -> 条文数列表
        self.SIX_QIN_VERIFY = {}        # 六亲考刻验证数据
        
        print(f">>> 正在加载数据库 ({os.path.abspath(db_folder)})...")
        if os.path.exists(db_folder):
            self._load_all()
        else:
            print("【错误】数据库文件夹不存在！")

    def _read_csv_robust(self, filename, header_option=0):
        """健壮的读取函数，自动尝试多种编码"""
        path = os.path.join(self.db_folder, filename)
        if not os.path.exists(path): return None
        
        encodings = ['utf-8-sig', 'gbk', 'gb18030', 'utf-16']
        for enc in encodings:
            try:
                return pd.read_csv(path, header=header_option, encoding=enc)
            except Exception as e:
                continue
        return None

    def _read_csv_as_dicts(self, filename):
        """读取为字典列表 (带表头)"""
        df = self._read_csv_robust(filename, header_option=0)
        if df is not None:
            return df.to_dict('records')
        return []

    def _clean_key(self, val):
        if pd.isna(val) or val is None: return ""
        return str(val).strip().replace('\ufeff', '')
    
    def _is_numeric(self, value):
        """判断值是否可以转换为数字"""
        if pd.isna(value):
            return False
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _load_all(self):
        # 1. 基础表 (14-1 ~ 14-6)
        self.tables['14-1'] = {self._clean_key(r.get('农历月份')): int(r.get('数值', 0)) for r in self._read_csv_as_dicts("14-1.csv")}
        self.tables['14-2'] = {self._clean_key(r.get('时支')): int(r.get('数值', 0)) for r in self._read_csv_as_dicts("14-2.csv")}
        for r in self._read_csv_as_dicts("14-3.csv"):
            if r.get('先天命数'):
                for n in r['先天命数'].split('|'): self.tables.setdefault('14-3', {})[int(n)] = {self._clean_key(k): v for k, v in r.items()}
        self.tables['14-4'] = {self._clean_key(r.get('五音')): int(r.get('数值', 0)) for r in self._read_csv_as_dicts("14-4.csv")}
        for r in self._read_csv_as_dicts("14-5.csv"):
            nayin = self._clean_key(r.get('日柱纳音'))
            self.tables.setdefault('14-5', {})[nayin] = {self._clean_key(k): int(v) for k, v in r.items() if k.strip() != '日柱纳音'}
        self.tables['14-6'] = {self._clean_key(r.get('时柱纳音')): int(r.get('数值', 0)) for r in self._read_csv_as_dicts("14-6.csv")}
        
        # 14-7 规则表
        self.rule_tables = self._read_csv_as_dicts("14-7.csv")
        
        # 14-8 简化卦象表（权威默认映射）
        for r in self._read_csv_as_dicts("14-8.csv"):
            try:
                num = int(r['本命数'])
                hex_name = self._clean_key(r['卦名'])
                self.HEXAGRAM_MAP[num] = hex_name
            except Exception:
                pass
        print(f"  > 加载 14-8.csv 成功，共 {len(self.HEXAGRAM_MAP)} 条数据")
        
        # 2. 卦象表加载 (14-9.csv)
        df_14_9 = self._read_csv_robust("14-9.csv", header_option=None)
        if df_14_9 is not None and not df_14_9.empty:
            col_count = len(df_14_9.columns)
            print(f"  > 加载 14-9.csv 成功，共 {len(df_14_9)} 条数据，列数：{col_count}")
            
            if col_count >= 3:
                invalid_rows = 0
                valid_rows = 0
                
                for idx, row in df_14_9.iterrows():
                    try:
                        # 第一列：刻别（初刻/正刻）
                        kebie = self._clean_key(row[0])
                        if kebie not in ["初刻", "正刻"]:
                            invalid_rows += 1
                            if invalid_rows <= 3:
                                print(f"    提示: 第 {idx+1} 行刻别无效 ({kebie})，已跳过")
                            continue
                        
                        # 第二列：本命数
                        benming_num = row[1]
                        if not self._is_numeric(benming_num):
                            invalid_rows += 1
                            if invalid_rows <= 3:
                                print(f"    提示: 第 {idx+1} 行本命数非数值 ({benming_num})，已跳过")
                            continue
                        num = int(float(benming_num))
                        
                        # 第三列：卦名
                        hex_name = self._clean_key(row[2])
                        if not hex_name or hex_name == 'nan':
                            invalid_rows += 1
                            if invalid_rows <= 3:
                                print(f"    提示: 第 {idx+1} 行卦名为空，已跳过")
                            continue
                        
                        # 构建映射（只添加详细映射，简化映射保持14-8的数据）
                        self.HEXAGRAM_DETAIL_MAP[(kebie, num)] = hex_name
                        
                        valid_rows += 1
                        if valid_rows <= 10:
                            print(f"    调试: {kebie} {num} -> {hex_name}")
                            
                    except Exception as e:
                        invalid_rows += 1
                        continue
                
                print(f"  > 14-9.csv 解析完成：有效行数 {valid_rows}，无效行数 {invalid_rows}")
                print(f"  > 成功解析 {len(self.HEXAGRAM_DETAIL_MAP)} 条详细卦象数据")
                if len(self.HEXAGRAM_DETAIL_MAP) == 0:
                    print("  [警告] 14-9.csv 中未找到有效卦象数据！")
        else:
            print("  [警告] 无法读取 14-9.csv，请检查文件是否存在！")

        # 14-10: 卦象详情
        for r in self._read_csv_as_dicts("14-10.csv"):
            try:
                gua = r['十二辟卦']
                base = int(r['基数'])
                seq = int(r['序数'])
                def parse_offsets(s):
                    return [int(x) for x in str(s).replace('，','|').replace('\n','|').split('|') if x.strip().isdigit()]
                offsets = {
                    "性格": parse_offsets(r.get('性格') or r.get(' 性格', '')),
                    "才能前程": parse_offsets(r.get('才能前程', '')),
                    "财运": parse_offsets(r.get('财运', '')),
                    "兄弟个数": parse_offsets(r.get('兄弟个数', ''))
                }
                data_pack = {"base": base, "seq": seq, "offsets": offsets}

                # 初刻
                if r.get('初刻生人先天命数'):
                    for n in str(r['初刻生人先天命数']).split('|'):
                        if n.strip().isdigit():
                            self.DESTINY_DATA[(gua, "Initial", int(n))] = data_pack
                # 正刻
                if r.get('正刻生人先天命数'):
                    for n in str(r['正刻生人先天命数']).split('|'):
                        if n.strip().isdigit():
                            self.DESTINY_DATA[(gua, "Main", int(n))] = data_pack
            except Exception: pass
            
        # 3. 流年相关 (14-11 ~ 14-14)
        for r in self._read_csv_as_dicts("14-11-1.csv"):
            try:
                num = int(r['先天命数']) if '先天命数' in r else 'generic'
                if r.get('年支组') and r.get('性别'):
                    self.LIUNIAN_START[(num, self._clean_key(r['年支组']), self._clean_key(r['性别']))] = int(r.get('起始数', 0))
            except: pass
            
        for r in self._read_csv_as_dicts("14-11-2.csv"):
            try:
                num = int(r.get('先天命数', 0))
                gan = self._clean_key(r.get('天干') or r.get('年干组'))
                seq = []
                if '1' in r and '12' in r:
                    seq = [self._clean_key(r.get(str(i))) for i in range(1, 13)]
                elif '原始序列' in r:
                    seq = [x.strip() for x in r['原始序列'].replace(',', '|').replace(' ', '|').split('|') if x.strip()]
                if num and gan and seq: self.LIUNIAN_SEQ[(num, gan)] = seq
            except: pass
            
        for r in self._read_csv_as_dicts("14-12.csv"):
            try:
                zhi = self._clean_key(r.get('流年地支'))
                num = int(r.get('后天命数', 0))
                marker = self._clean_key(r.get('流年标记'))
                if zhi and num and marker: self.MARKER_TABLE.setdefault(zhi, {})[num] = marker
            except: pass
            
        for r in self._read_csv_as_dicts("14-13.csv"):
            try:
                moment = self._clean_key(r.get('考刻'))
                parity = self._clean_key(r.get('日命数加时运数的奇偶性'))
                tone_val = self._clean_key(r.get('流年天四声'))
                marker = self._clean_key(r.get('流年标记'))
                letter = self._clean_key(r.get('流年字母'))
                if moment and parity and tone_val and marker and letter:
                     self.LETTER_TABLE[(moment, parity, tone_val, marker)] = letter
            except: pass
        
        # 14-14 流年条文表
        df_14_14 = self._read_csv_robust("14-14.csv", header_option=0)
        if df_14_14 is not None and not df_14_14.empty:
            print(f"  > 加载 14-14.csv 成功，共 {len(df_14_14)} 条数据")
            
            # 获取列名并清洗
            columns = [self._clean_key(col) for col in df_14_14.columns]
            print(f"    14-14.csv 列名: {columns}")
            
            # 查找关键列的索引
            col_mapping = {}
            for idx, col in enumerate(columns):
                if '流年字母' in col:
                    col_mapping['letter'] = idx
                elif '流年岁数' in col:
                    col_mapping['age'] = idx
                elif '基数' in col:
                    col_mapping['base'] = idx
                elif '加数' in col:
                    col_mapping['add'] = idx
                elif '条文校正数' in col or '流年叫正文' in col:
                    col_mapping['correction'] = idx
            
            # 验证必要列是否存在
            required_cols = ['letter', 'age', 'base', 'add', 'correction']
            missing_cols = [col for col in required_cols if col not in col_mapping]
            if missing_cols:
                print(f"    [警告] 14-14.csv 缺少必要列: {missing_cols}")
            else:
                # 读取数据
                for idx, row in df_14_14.iterrows():
                    try:
                        letter = self._clean_key(row.iloc[col_mapping['letter']])
                        age = int(float(row.iloc[col_mapping['age']]))
                        base = int(float(row.iloc[col_mapping['base']]))
                        add = int(float(row.iloc[col_mapping['add']]))
                        correction = int(float(row.iloc[col_mapping['correction']]))
                        
                        if letter and age > 0:
                            # 主映射：(字母, 岁数) -> (基数, 加数, 条文校正数)
                            self.DATA_BY_LETTER[(letter, age)] = (base, add, correction)
                            # 校正映射：(条文校正数, 岁数) -> (基数, 加数)
                            self.DATA_BY_CORRECTION[(correction, age)] = (base, add)
                            # 反向映射：(条文校正数, 岁数) -> 字母
                            self.CORRECTION_TO_LETTER[(correction, age)] = letter
                            
                    except Exception as e:
                        continue
                
                print(f"    成功加载 {len(self.DATA_BY_LETTER)} 条流年条文数据")
        else:
            print("  [警告] 无法读取 14-14.csv，请检查文件是否存在！")
        
        # 新增：加载List.csv (已重命名为List.csv)
        duanyu_file = "List.csv"
        df_duanyu = self._read_csv_robust(duanyu_file, header_option=0)
        if df_duanyu is not None and not df_duanyu.empty:
            print(f"  > 加载 {duanyu_file} 成功，共 {len(df_duanyu)} 条数据")
            
            # 获取列名并清洗
            columns = [self._clean_key(col) for col in df_duanyu.columns]
            print(f"    {duanyu_file} 列名: {columns}")
            
            # 查找关键列的索引
            col_mapping = {}
            for idx, col in enumerate(columns):
                if '条文数字' in col or '条文数' in col or '数字' in col:
                    col_mapping['num'] = idx
                elif '断语' in col or '断词' in col or '内容' in col or '吉凶断词' in col:
                    col_mapping['duanyu'] = idx
                elif '年龄' in col or '对应年龄' in col or '岁数' in col:
                    col_mapping['age'] = idx
            
            # 读取数据
            valid_count = 0
            for idx, row in df_duanyu.iterrows():
                try:
                    # 获取条文数字
                    if 'num' in col_mapping:
                        fortune_num = row.iloc[col_mapping['num']]
                        if self._is_numeric(fortune_num):
                            fortune_num = int(float(fortune_num))
                        else:
                            continue
                    else:
                        continue
                    
                    # 获取断语
                    duanyu = ""
                    if 'duanyu' in col_mapping:
                        duanyu = self._clean_key(row.iloc[col_mapping['duanyu']])
                    
                    # 获取对应年龄
                    duanyu_age = ""
                    if 'age' in col_mapping:
                        duanyu_age = self._clean_key(row.iloc[col_mapping['age']])
                    
                    # 构建映射
                    if fortune_num > 0:
                        self.FORTUNE_DUANYU_MAP[fortune_num] = (duanyu, duanyu_age)
                        self.FORTUNE_DUANYU_RAW.append({
                            'num': fortune_num,
                            'duanyu': duanyu,
                            'age': duanyu_age
                        })
                        valid_count += 1
                        
                except Exception as e:
                    continue
            
            print(f"    成功加载 {valid_count} 条条文断语数据")
            if valid_count > 0:
                # 打印前5条作为示例
                print(f"    示例数据: {list(self.FORTUNE_DUANYU_MAP.items())[:5]}")
                
                # 构建六亲考刻数据
                self._build_six_qin_data()
        else:
            print(f"  [警告] 无法读取 {duanyu_file}，断语功能将不可用！")
    
    def _build_six_qin_data(self):
        """构建六亲考刻数据
        
        通过分析断语内容，将条文分类到不同的六亲类型
        """
        # 六亲关键词匹配规则
        six_qin_keywords = {
            "父母": ["父母", "父", "母", "双亲", "严父", "慈母", "椿萱"],
            "兄弟": ["兄弟", "兄", "弟", "手足", "同袍", "同胞", "姊", "妹"],
            "妻财": ["妻", "财", "妻子", "夫人", "配偶", "姻缘", "婚姻", "财富", "财运"],
            "官鬼": ["官", "鬼", "功名", "仕途", "官职", "灾祸", "凶事", "疾病"],
            "子孙": ["子", "孙", "子女", "后代", "儿女", "子嗣", "晚辈"]
        }
        
        # 分析每条断语，归类到六亲类型
        for fortune_num, (duanyu, age) in self.FORTUNE_DUANYU_MAP.items():
            matched_types = []
            for qin_type, keywords in six_qin_keywords.items():
                for keyword in keywords:
                    if keyword in duanyu:
                        matched_types.append(qin_type)
                        break  # 匹配到一个关键词就够了
            
            if matched_types:
                for qin_type in matched_types:
                    # 为每个刻别构建条文列表
                    for kebie in ["初刻", "正刻"]:
                        key = (qin_type, kebie)
                        if key not in self.SIX_QIN_FORTUNES:
                            self.SIX_QIN_FORTUNES[key] = []
                        self.SIX_QIN_FORTUNES[key].append({
                            "num": fortune_num,
                            "duanyu": duanyu,
                            "age": age
                        })
        
        print(f"  > 构建六亲考刻数据完成，共 {len(self.SIX_QIN_FORTUNES)} 组六亲条文")
    
    def get_six_qin_fortunes(self, qin_type, kebie=None):
        """获取指定六亲类型和刻别的条文
        
        参数：
            qin_type: 六亲类型 (父母/兄弟/妻财/官鬼/子孙)
            kebie: 刻别 (初刻/正刻，可选，None则返回所有刻别)
        
        返回：
            条文列表
        """
        if kebie:
            return self.SIX_QIN_FORTUNES.get((qin_type, kebie), [])
        else:
            result = []
            for (qt, kb), fortunes in self.SIX_QIN_FORTUNES.items():
                if qt == qin_type:
                    result.extend(fortunes)
            return result
    
    def get_fortune_duanyu(self, fortune_num):
        """
        根据条文数字获取对应的断语和年龄
        返回：(断语, 对应年龄)
        """
        if not fortune_num or fortune_num == "":
            return ("", "")
        
        try:
            num = int(float(fortune_num))
            return self.FORTUNE_DUANYU_MAP.get(num, ("未找到断语", "未知"))
        except:
            return ("", "")
    
    def verify_kebie_by_six_qin(self, known_info, possible_kebies=None):
        """通过已知六亲信息验证刻别（简化版，只处理父母生肖）
        
        参数：
            known_info: 已知六亲信息字典
                {
                    "父亲生肖": "鼠",  # 父亲生肖
                    "母亲生肖": "猴"   # 母亲生肖
                }
            possible_kebies: 可能的刻别列表，默认["初刻", "正刻"]
        
        返回：
            (推荐刻别, 匹配度字典)
        """
        if possible_kebies is None:
            possible_kebies = ["初刻", "正刻"]
        
        match_scores = {}
        try:
            for kebie in possible_kebies:
                score = 0
                # 获取父母相关的条文
                parent_fortunes = self.get_six_qin_fortunes("父母", kebie)
                
                for key, zodiac in known_info.items():
                    if zodiac and "生肖" in key:
                        search_text = f"属{zodiac}"
                        for fort in parent_fortunes:
                            if search_text in fort["duanyu"] or zodiac in fort["duanyu"]:
                                score += 1
                                break
                
                match_scores[kebie] = score
        except Exception as e:
            print(f"  [警告] 六亲考刻验证出错: {e}")
            return None, {}
        
        # 找出匹配度最高的刻别
        if match_scores:
            best_kebie = max(match_scores.keys(), key=lambda k: match_scores[k])
            return best_kebie, match_scores
        return None, {}
    
    def get_six_qin_complete_analysis(self, main_num, ke_gan_num, kebie):
        """获取完整的六亲考刻分析（简化版，只针对父母）
        
        参数：
            main_num: 本命基数
            ke_gan_num: 刻干数
            kebie: 刻别
        
        返回：
            六亲分析结果
        """
        try:
            analysis = {}
            
            # 计算终局条文数（铁板核心公式）
            final_fortune = calculate_tieban_fortune(main_num, ke_gan_num)
            
            # 获取终局条文的断语
            final_duanyu, final_age = self.get_fortune_duanyu(final_fortune)
            
            # 只分析父母相关的条文
            parent_fortunes = self.get_six_qin_fortunes("父母", kebie)
            
            # 找到最接近终局条文数的条文
            closest_fortune = None
            min_diff = float('inf')
            for fort in parent_fortunes:
                diff = abs(fort["num"] - final_fortune)
                if diff < min_diff:
                    min_diff = diff
                    closest_fortune = fort
            
            analysis["父母"] = {
                "fortune": closest_fortune,
                "closest_diff": min_diff,
                "all_fortunes": parent_fortunes[:5]  # 返回前5条参考
            }
            
            return {
                "final_fortune": final_fortune,
                "final_duanyu": final_duanyu,
                "final_age": final_age,
                "qin_analysis": analysis
            }
        except Exception as e:
            print(f"  [警告] 六亲考刻分析出错: {e}")
            return {
                "final_fortune": 0,
                "final_duanyu": "",
                "final_age": "",
                "qin_analysis": {}
            }

# ==============================================================================
# 3. Calculator
# ==============================================================================
class TieBanCalculator:
    def __init__(self):
        self.loader = TieBanDataLoader()
        self.db = self.loader
        self.tiangan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
        self.dizhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

    def get_gan_group(self, gan):
        if gan not in self.tiangan: return "甲己"
        return ["甲己", "乙庚", "丙辛", "丁壬", "戊癸"][self.tiangan.index(gan) % 5]

    def get_liunian_groups(self, year_gan, year_zhi):
        b_group = "未知"
        if year_zhi in "寅午戌": b_group = "寅午戌"
        elif year_zhi in "申子辰": b_group = "申子辰"
        elif year_zhi in "巳酉丑": b_group = "巳酉丑"
        elif year_zhi in "亥卯未": b_group = "亥卯未"
        s_group = "未知"
        if year_gan in "甲乙丙丁": s_group = "甲乙丙丁"
        elif year_gan in "戊己": s_group = "戊己"
        elif year_gan in "庚辛": s_group = "庚辛"
        elif year_gan in "壬癸": s_group = "壬癸"
        return b_group, s_group

    def is_yang_year(self, year_gan):
        return year_gan in ["甲", "丙", "戊", "庚", "壬"]
    
    def calculate_correction(self, original_correction, age):
        """
        根据年龄计算校正后的条文校正数
        规则：
        1. 1-10岁/81-108岁：校正数+2（>6则-6）
        2. 其他年龄：校正数+3（>20则-20）
        """
        if original_correction == 0:
            return 0
            
        # 情况一：1-10岁 或 81-108岁
        if (1 <= age <= 10) or (81 <= age <= 108):
            new_correction = original_correction + 2
            if new_correction > 6:
                new_correction -= 6
        # 情况二：其他年龄
        else:
            new_correction = original_correction + 3
            if new_correction > 20:
                new_correction -= 20
                
        return new_correction
    
    def get_fortune_duanyu(self, fortune_num):
        """
        根据条文数字获取对应的断语和年龄
        返回：(断语, 对应年龄)
        """
        if not fortune_num or fortune_num == "" or not self._is_numeric(fortune_num):
            return ("", "")
        
        try:
            num = int(float(fortune_num))
            return self.db.FORTUNE_DUANYU_MAP.get(num, ("未找到断语", "未知"))
        except:
            return ("", "")
    
    def _is_numeric(self, value):
        """判断值是否可以转换为数字"""
        if not value:
            return False
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def calculate(self, payload):
        birth, query, gender = payload['birth_info'], payload['query_info'], payload['gender']
        y_gan, y_zhi = birth['bazi']['year'][0], birth['bazi']['year'][1]
        t_zhi = birth['bazi']['time'][1]
        d_day, t_gan, t_time = birth['bazi']['day'], query['bazi']['time'][0], query['bazi']['time']
        
        details = {}
        details['header_info'] = f"性别:{gender}, 农历:{birth['lunar_str']}，闰月{'是' if birth['is_leap'] else '否'}，出生八字：{birth['bazi']['year']} {birth['bazi']['month']} {birth['bazi']['day']} {birth['bazi']['time']}\n求测日期：阳历：{query['date_str']}     八字：{query['bazi']['year']} {query['bazi']['month']} {query['bazi']['day']} {query['bazi']['time']}"

        # Step 1: 计算先天命数
        calc_month = str(m_idx := birth['lunar_month'] + (1 if birth['is_leap'] else 0))
        if int(m_idx) > 12: calc_month = "1"
        month_val = self.db.tables['14-1'].get(calc_month, int(calc_month))
        time_val = self.db.tables['14-2'].get(t_zhi, 0)
        cong_num = month_val + 3 - time_val
        if cong_num <= 0: cong_num += 12
        details['cong_calc'] = f"先天命数 = {cong_num}"
        details['cong_num'] = cong_num

        # Step 2: 计算五音命数
        gan_group = self.get_gan_group(y_gan)
        tone = self.db.tables.get('14-3', {}).get(cong_num, {}).get(gan_group, "宫")
        tone_num = self.db.tables['14-4'].get(tone, 5)
        details['tone_num'] = tone_num

        # Step 3: 计算日命数和时运数
        day_n = NAYIN_WUXING.get(d_day, "金")
        day_life = self.db.tables.get('14-5', {}).get(day_n, {}).get(t_gan, 0)
        time_n = NAYIN_WUXING.get(t_time, "金")
        time_luck = self.db.tables['14-6'].get(time_n, 0)
        details['day_life_calc'] = f"日命:{day_life}, 时运:{time_luck}"

        # Step 4: 确定刻别（八刻细分：初刻/一刻/二刻/.../正刻）
        # 先从出生时间计算八刻细分
        birth_datetime = datetime.datetime.strptime(birth['date_str'], "%Y-%m-%d %H:%M")
        moment_cn = get_eight_ke_from_time(birth_datetime)
        ke_gan_num = get_ke_gan_number(moment_cn)
        
        # 保留原有的考刻逻辑（用于兼容旧数据结构）
        sum_val = day_life + time_luck
        is_yang = self.is_yang_year(y_gan)
        grp = "阳男阴女" if (gender == "男" and is_yang) or (gender == "女" and not is_yang) else "阴男阳女"
        cond = ">6" if sum_val > 6 else "<=6"
        
        moment = "Main"  # 默认为正刻
        for r in self.db.rule_tables:
            if r['组别'] == grp and r['和值条件'] == cond:
                moment = "Initial" if r['刻别'] == "初刻" else "Main"
                break
        
        details['moment_calc'] = f"考刻: {moment_cn} (刻干数:{ke_gan_num}, {grp})"
        details['moment_cn'] = moment_cn
        details['ke_gan_num'] = ke_gan_num

        # Step 5: 计算本命数与终局条文数
        base_val = tone_num * 5 + day_life + time_luck
        fact = (base_val - 1) if sum_val <= 6 else (base_val - 6)
        main_num = fact * 30 + birth['lunar_day']
        
        # 铁板神数核心公式：终局条文数 = 本命基数 + 刻干数 × 48
        # 将本命数作为基数，应用核心公式
        final_fortune_num = calculate_tieban_fortune(main_num, ke_gan_num)
        
        details['main_calc'] = f"本命数: {main_num}, 终局条文数: {final_fortune_num} (公式:{main_num}+{ke_gan_num}×48)"
        details['main_num'] = main_num
        details['final_fortune_num'] = final_fortune_num

        # Step 6: 查找卦名
        hex_name = self.db.HEXAGRAM_DETAIL_MAP.get((moment_cn, main_num), 
                                                  self.db.HEXAGRAM_MAP.get(main_num, 
                                                                          f"未知(刻别:{moment_cn},本命数:{main_num}未匹配)"))
        details['hex_name'] = hex_name
        
        # 查找详细数据
        tbl_data = self.db.DESTINY_DATA.get((hex_name, moment, cong_num))
        # 为每个条文获取断语
        if tbl_data and tbl_data.get('offsets'):
            tbl_data_with_duanyu = dict(tbl_data)  # 复制一份
            tbl_data_with_duanyu['duanyus'] = {}
            for category, offsets in tbl_data['offsets'].items():
                tbl_data_with_duanyu['duanyus'][category] = []
                for off in offsets:
                    fortune = tbl_data['base'] + tbl_data['seq'] + off
                    duanyu_text, duanyu_age = self.get_fortune_duanyu(fortune)
                    tbl_data_with_duanyu['duanyus'][category].append({
                        'fortune': fortune,
                        'duanyu': duanyu_text,
                        'age': duanyu_age
                    })
            details['tbl_data'] = tbl_data_with_duanyu
        else:
            details['tbl_data'] = tbl_data
        report_log("info", "tbl_data_lookup", {
            "lookup_key": {"hex_name": hex_name, "moment": moment, "cong_num": cong_num},
            "tbl_data": tbl_data
        })

        # Step 7: 计算后天命数
        pn_sum = cong_num + main_num
        pn_num = pn_sum % 8
        if pn_num == 0: pn_num = 8
        
        # ========== 应用五数寄宫规则 ==========
        # 获取出生年份用于判断三元九运
        birth_year = int(birth['date_str'].split('-')[0])
        san_yuan = get_san_yuan_period(birth_year)
        details['san_yuan'] = san_yuan
        
        # 检查是否为五数寄宫（后天命数为5）
        original_pn_num = pn_num
        wu_shu_gong_gua = ""
        if pn_num == 5:
            wu_shu_gong_gua = get_wu_shu_ji_gong_gua(san_yuan, gender, is_yang)
            pn_num = HOU_TIAN_GUA_NUM.get(wu_shu_gong_gua, 5)
            details['wu_shu_ji_gong'] = {
                'original': 5,
                '寄宫卦': wu_shu_gong_gua,
                '实际命数': pn_num,
                '依据': f"{san_yuan} {gender} {'阳' if is_yang else '阴'}"
            }
        else:
            details['wu_shu_ji_gong'] = None
        
        details['pn_log'] = f"先天命数＋本命数＝{cong_num}＋{main_num}＝{pn_sum}÷8→余数＝{original_pn_num}"
        details['pn_num'] = pn_num
        
        # ========== 计算八卦加则信息 ==========
        # 获取八卦加则起始数
        jiaze_start = get_bagua_jiaze_start(hex_name)
        details['bagua_jiaze'] = {
            '卦名': hex_name,
            '起始数': jiaze_start,
            '规则': BA_GUA_JIA_ZHE.get(hex_name, {}).get('desc', '其他卦从30起') if hex_name in BA_GUA_JIA_ZHE else '其他卦从30起'
        }

        # Step 8: 计算流年条文（核心修改）
        liunian = []
        try:
            bg, sg = self.get_liunian_groups(y_gan, y_zhi)
            start = 0
            for k in [(cong_num, bg, gender), ('generic', bg, gender)]:
                if k in self.db.LIUNIAN_START:
                    start = self.db.LIUNIAN_START[k]; break
            raw_seq = []
            final_seq = ["?"] * 12
            if start != 0:
                for k in [(cong_num, y_gan), (cong_num, sg)]:
                    if k in self.db.LIUNIAN_SEQ:
                        raw_seq = self.db.LIUNIAN_SEQ[k]; break
                if raw_seq and len(raw_seq) >= 12:
                    off = (13 - start) % 12
                    final_seq = [raw_seq[(i + off) % 12] for i in range(12)]

            tg_list = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
            dz_list = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
            st_tg = tg_list.index(y_gan)
            st_dz = dz_list.index(y_zhi)
            
            # 生成1-108岁的流年数据（覆盖81-108岁的校正需求）
            for age in range(1, 109):
                cur_tg = tg_list[(st_tg + age - 1) % 10]
                cur_dz = dz_list[(st_dz + age - 1) % 12]
                sound = final_seq[(age - 1) % 12] if final_seq[0] != "?" else "?"
                marker = self.db.MARKER_TABLE.get(cur_dz, {}).get(pn_num, "?")
                
                age_parity = "奇数" if age % 2 != 0 else "偶数"
                # 八刻细分到初刻/正刻的映射，用于兼容旧数据
                # 初刻、一刻、二刻、三刻 → 初刻
                # 四刻、五刻、六刻、正刻 → 正刻
                legacy_moment = "初刻" if ke_gan_num <= 4 else "正刻"
                letter = self.db.LETTER_TABLE.get((legacy_moment, age_parity, sound, marker), "?")

                # 初始化变量
                base = 0
                add = 0
                original_correction = 0  # 原始条文校正数
                corrected_correction = 0  # 校正后的条文校正数
                original_fortune = ""     # 原始条文数
                corrected_fortune = ""    # 校正后的条文数
                formula = ""
                corrected_letter = ""     # 校正后的字母
                
                # 查找原始数据
                if letter != "?" and (letter, age) in self.db.DATA_BY_LETTER:
                    base, add, original_correction = self.db.DATA_BY_LETTER[(letter, age)]
                    formula = f"{base}+{add}"
                    original_fortune = str(base + add)
                    
                    # 计算校正后的条文校正数
                    corrected_correction = self.calculate_correction(original_correction, age)
                    
                    # 根据新的校正数查找校正后的条文
                    if corrected_correction > 0 and (corrected_correction, age) in self.db.DATA_BY_CORRECTION:
                        corr_base, corr_add = self.db.DATA_BY_CORRECTION[(corrected_correction, age)]
                        corrected_fortune = str(corr_base + corr_add)
                        # 查找校正后的字母（可选）
                        corrected_letter = self.db.CORRECTION_TO_LETTER.get((corrected_correction, age), "?")
                
                # ========== 铁板神数核心公式应用 ==========
                # 终局条文数 = 本命基数 + 刻干数 × 48
                tieban_fortune = ""
                tieban_duanyu = ""
                tieban_duanyu_age = ""
                
                if original_fortune and original_fortune != "?":
                    try:
                        orig_num = int(original_fortune)
                        # 应用铁板神数核心公式
                        tieban_num = calculate_tieban_fortune(orig_num, ke_gan_num)
                        tieban_fortune = str(tieban_num)
                        # 获取应用公式后的断语
                        tieban_duanyu, tieban_duanyu_age = self.get_fortune_duanyu(tieban_fortune)
                    except:
                        tieban_fortune = ""
                
                # ========== 新增：获取断语信息 ==========
                # 原始条文断语
                original_duanyu, original_duanyu_age = self.get_fortune_duanyu(original_fortune)
                # 校正后条文断语
                corrected_duanyu, corrected_duanyu_age = self.get_fortune_duanyu(corrected_fortune)
                
                # ========== 八卦加则演变计算 ==========
                # 应用八卦加则规则：使用校正后的条文数作为输入
                jiaze_result = ""
                jiaze_stop = False
                if corrected_fortune and corrected_fortune != "?":
                    try:
                        # 使用校正后的条文数进行八卦加则演变
                        fortune_val = int(corrected_fortune)
                        final_num, jiaze_stop, iterations = apply_bagua_jiaze_rule(fortune_val, hex_name)
                        jiaze_result = str(final_num)
                    except:
                        jiaze_result = "?"
                else:
                    jiaze_result = "?"
                
                # 构建流年数据
                liunian.append({
                    "age": age, 
                    "year": f"{cur_tg}{cur_dz}", 
                    "sound": sound,
                    "marker": marker, 
                    "letter": letter,
                    "corrected_letter": corrected_letter,
                    "original_correction": str(original_correction),
                    "corrected_correction": str(corrected_correction),
                    "formula": formula, 
                    "original_fortune": original_fortune,
                    "corrected_fortune": corrected_fortune,
                    # 铁板神数核心公式字段
                    "tieban_fortune": tieban_fortune,          # 终局条文数
                    "tieban_duanyu": tieban_duanyu,            # 公式后的断语
                    "tieban_duanyu_age": tieban_duanyu_age,    # 公式后的年龄
                    # 新增断语字段
                    "original_duanyu": original_duanyu,          # 原始条文断语
                    "original_duanyu_age": original_duanyu_age,  # 原始条文对应年龄
                    "corrected_duanyu": corrected_duanyu,        # 校正后条文断语
                    "corrected_duanyu_age": corrected_duanyu_age, # 校正后条文对应年龄
                    # 八卦加则字段
                    "jiaze_result": jiaze_result,              # 八卦加则演变结果
                    "jiaze_stop": jiaze_stop                   # 是否停止
                })
        except Exception as e:
            print(f"计算流年数据时出错: {e}")
            traceback.print_exc()
            pass
            
        details['liunian'] = liunian
        
        # Step 9: 六亲考刻分析（临时禁用）
        # try:
        #     # 获取六亲完整分析
        #     legacy_moment = "初刻" if ke_gan_num <= 4 else "正刻"
        #     six_qin_analysis = self.db.get_six_qin_complete_analysis(main_num, ke_gan_num, legacy_moment)
        #     details['six_qin_analysis'] = six_qin_analysis
        #     
        #     # 检查是否有六亲验证信息
        #     if 'six_qin_info' in payload and payload['six_qin_info']:
        #         known_info = payload['six_qin_info']
        #         # 映射到初刻/正刻
        #         possible_kebies = ["初刻", "正刻"]
        #         
        #         verified_kebie, match_scores = self.db.verify_kebie_by_six_qin(known_info, possible_kebies)
        #         details['six_qin_verify'] = {
        #             'known_info': known_info,
        #             'verified_kebie': verified_kebie,
        #             'match_scores': match_scores
        #         }
        # except Exception as e:
        #     print(f"  [警告] 六亲考刻分析出错，已跳过: {e}")
        #     # 即使六亲考刻出错，也要保证有基本结构，防止前端报错
        #     details['six_qin_analysis'] = {
        #         "final_fortune": 0,
        #         "final_duanyu": "",
        #         "final_age": "",
        #         "qin_analysis": {}
        #     }
        
        return details

    def print_report(self, res):
        print("\n" + "="*220)
        print(res['header_info'])
        print("="*220 + "\n")
        
        print("【基础排盘信息】")
        print(f"{res['cong_calc']}")
        print(f"五音命数 = {res['tone_num']}")
        print(f"{res['day_life_calc']}")
        print(f"{res['moment_calc']}")
        print(f"{res['main_calc']}")
        print(f"十二辟卦: {res['hex_name']}")
        
        # 显示三元九运信息
        print(f"三元九运: {res.get('san_yuan', '未知')}")
        
        # 显示五数寄宫信息
        wu_shu_info = res.get('wu_shu_ji_gong')
        if wu_shu_info:
            print(f"五数寄宫: 原命数={wu_shu_info['original']} → 寄宫卦={wu_shu_info['寄宫卦']} → 实际命数={wu_shu_info['实际命数']} (依据: {wu_shu_info['依据']})")
        
        # 显示八卦加则信息
        jiaze_info = res.get('bagua_jiaze')
        if jiaze_info:
            print(f"八卦加则: 卦名={jiaze_info['卦名']}, 起始数={jiaze_info['起始数']}, 规则={jiaze_info['规则']}")
        
        print("\n【本命条文】")
        if res['tbl_data']:
            tbl = res['tbl_data']
            base, seq, offsets = tbl['base'], tbl['seq'], tbl['offsets']
            print(f"十二辟卦 —— {res['hex_name']}  +{base}")
            print(f"{res['moment_cn']}生人  先天命数 {res['cong_num']}")
            print("-" * 60)
            print(f"{'序数':<6}{'性格':<10}{'才能前程':<10}{'财运':<10}{'兄弟个数':<10}")
            s_char = ",".join(map(str, offsets['性格']))
            s_car = ",".join(map(str, offsets['才能前程']))
            s_wea = ",".join(map(str, offsets['财运']))
            s_bro = ",".join(map(str, offsets['兄弟个数']))
            print(f"{seq:<6}{s_char:<10}{s_car:<10}{s_wea:<10}{s_bro:<10}")
            print("-" * 60)
            print("\n本命条文详细计算：")
            def print_calc(title, offset_list):
                for off in offset_list:
                    result = base + seq + off
                    print(f"  {title}: {base} + {seq} + {off} = {result}")
                    report_log("info", "benming_calc", {
                        "category": title,
                        "formula": f"{base} + {seq} + {off}",
                        "result": result,
                        "base": base,
                        "seq": seq,
                        "offset": off
                    })
            print_calc("(1) 性格", offsets['性格'])
            print_calc("(2) 才能、前程", offsets['才能前程'])
            print_calc("(3) 财运", offsets['财运'])
            print_calc("(4) 兄弟个数", offsets['兄弟个数'])
        else:
            print(f"  [提示] 未在 14-10 表中找到匹配的条文数据 (卦名: {res['hex_name']}, 刻别: {res['moment_cn']}, 先天数: {res['cong_num']})")

        print("\n【流年条文 (1-100岁)】")
        print("=" * 220)
        # 打印表头（包含断语列和八卦加则列）
        header_parts = [
            f"{'岁数':<6}", f"{'干支':<6}", f"{'四声':<6}", f"{'标记':<6}", f"{'字母':<6}",
            f"{'校正数':<8}", f"{'校正后校正数':<12}", f"{'计算公式':<10}",
            f"{'原条文':<8}", f"{'原断语':<30}", f"{'原断语年龄':<10}",
            f"{'校正后条文':<10}", f"{'校正后断语':<30}", f"{'校正后断语年龄':<10}",
            f"{'加则结果':<8}", f"{'停止':<4}"
        ]
        print("".join(header_parts))
        print("=" * 220)
        
        # 打印1-100岁的流年数据
        for i in [item for item in res['liunian'] if 1 <= item['age'] <= 100]:
            # 截断过长的断语，保持表格整洁
            original_duanyu = i['original_duanyu'][:28] + ".." if len(i['original_duanyu']) > 30 else i['original_duanyu']
            corrected_duanyu = i['corrected_duanyu'][:28] + ".." if len(i['corrected_duanyu']) > 30 else i['corrected_duanyu']
            
            row_parts = [
                f"{i['age']:<6}", f"{i['year']:<6}", f"{i['sound']:<6}", f"{i['marker']:<6}", f"{i['letter']:<6}",
                f"{i['original_correction']:<8}", f"{i['corrected_correction']:<12}", f"{i['formula']:<10}",
                f"{i['original_fortune']:<8}", f"{original_duanyu:<30}", f"{i['original_duanyu_age']:<10}",
                f"{i['corrected_fortune']:<10}", f"{corrected_duanyu:<30}", f"{i['corrected_duanyu_age']:<10}",
                f"{i.get('jiaze_result', ''):<8}", f"{'√' if i.get('jiaze_stop') else '':<4}"
            ]
            print("".join(row_parts))
        print("=" * 220)

    def save_to_md(self, res, b_str, q_str):
        """保存排盘结果到Markdown文件"""
        if not os.path.exists("output"):
            os.makedirs("output")
        
        fname = f"output/铁板排盘_{b_str.split()[0]}_{q_str.split()[0]}.md"
        with open(fname, "w", encoding="utf-8") as f:
            # 写入基础信息
            f.write("# 铁板神数排盘结果\n\n")
            f.write(f"**排盘时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 基础信息\n")
            f.write(f"```\n{res['header_info']}\n```\n\n")
            
            # 写入基础排盘数据
            f.write("## 基础排盘\n")
            f.write(f"- 先天命数：{res['cong_calc']}\n")
            f.write(f"- 五音命数：{res['tone_num']}\n")
            f.write(f"- 日命数 & 时运数：{res['day_life_calc']}\n")
            f.write(f"- 考刻结果：{res['moment_calc']}\n")
            f.write(f"- 本命数：{res['main_calc']}\n")
            f.write(f"- 十二辟卦：{res['hex_name']}\n\n")
            
            # 写入本命条文
            f.write("## 本命条文\n")
            if res['tbl_data']:
                tbl = res['tbl_data']
                base, seq, offsets = tbl['base'], tbl['seq'], tbl['offsets']
                f.write(f"**{res['moment_cn']}生人 - 先天命数 {res['cong_num']} - {res['hex_name']}(+{base})**\n\n")
                f.write("| 项目 | 数值 | 计算公式 |\n")
                f.write("|------|------|----------|\n")
                f.write(f"| 序数 | {seq} | - |\n")
                for item, values in offsets.items():
                    for val in values:
                        total = base + seq + val
                        f.write(f"| {item} | {total} | {base} + {seq} + {val} = {total} |\n")
            else:
                f.write("未找到匹配的本命条文数据\n\n")
            
            # 写入流年条文表格（包含断语）
            f.write("## 流年条文 (1-100岁)\n")
            f.write("| 岁数 | 干支 | 四声 | 标记 | 字母 | 校正数 | 校正后校正数 | 计算公式 | 原条文 | 原断语 | 原断语年龄 | 校正后条文 | 校正后断语 | 校正后断语年龄 |\n")
            f.write("|------|------|------|------|------|--------|--------------|----------|--------|--------|------------|------------|------------|----------------|\n")
            
            for i in [item for item in res['liunian'] if 1 <= item['age'] <= 100]:
                # 处理Markdown中的特殊字符
                original_duanyu = i['original_duanyu'].replace('|', '｜').replace('\n', ' ')
                corrected_duanyu = i['corrected_duanyu'].replace('|', '｜').replace('\n', ' ')
                
                f.write(f"| {i['age']} | {i['year']} | {i['sound']} | {i['marker']} | {i['letter']} | "
                        f"{i['original_correction']} | {i['corrected_correction']} | {i['formula']} | "
                        f"{i['original_fortune']} | {original_duanyu} | {i['original_duanyu_age']} | "
                        f"{i['corrected_fortune']} | {corrected_duanyu} | {i['corrected_duanyu_age']} |\n")
        
        print(f"\n[完成] 排盘报告已保存至: {os.path.abspath(fname)}")

    def save_to_html(self, res, b_str, q_str):
        """保存排盘结果到HTML文件，可用于生成PDF"""
        if not os.path.exists("output"):
            os.makedirs("output")
        
        fname = f"output/铁板排盘_{b_str.split()[0]}_{q_str.split()[0]}.html"
        
        # 解析日命和时运
        dayLifeMatch = res['day_life_calc'].match(r'日命:(\d+)')
        timeLuckMatch = res['day_life_calc'].match(r'时运:(\d+)')
        dayLife = dayLifeMatch.group(1) if dayLifeMatch else '?'
        timeLuck = timeLuckMatch.group(1) if timeLuckMatch else '?'
        
        # 卦象数据
        guaMap = {
            "乾": {"lines": "☰", "element": "金"},
            "坤": {"lines": "☷", "element": "土"},
            "震": {"lines": "☳", "element": "木"},
            "巽": {"lines": "☴", "element": "木"},
            "坎": {"lines": "☵", "element": "水"},
            "离": {"lines": "☲", "element": "火"},
            "艮": {"lines": "☶", "element": "土"},
            "兑": {"lines": "☱", "element": "金"}
        }
        
        twelveHexMap = {
            "乾": {"shang": "乾", "xia": "乾"},
            "夬": {"shang": "兑", "xia": "乾"},
            "大壮": {"shang": "震", "xia": "乾"},
            "泰": {"shang": "坤", "xia": "乾"},
            "临": {"shang": "坤", "xia": "兑"},
            "复": {"shang": "坤", "xia": "震"},
            "坤": {"shang": "坤", "xia": "坤"},
            "剥": {"shang": "艮", "xia": "坤"},
            "观": {"shang": "巽", "xia": "坤"},
            "否": {"shang": "乾", "xia": "坤"},
            "遁": {"shang": "乾", "xia": "艮"},
            "姤": {"shang": "乾", "xia": "巽"}
        }
        
        hexName = res['hex_name']
        shangName = twelveHexMap.get(hexName, {"shang": "乾", "xia": "坤"})['shang']
        xiaName = twelveHexMap.get(hexName, {"shang": "乾", "xia": "坤"})['xia']
        shangGua = guaMap.get(shangName, guaMap["乾"])
        xiaGua = guaMap.get(xiaName, guaMap["坤"])
        
        # 生成本命条文表格HTML
        destinyTableHtml = ""
        if res['tbl_data'] and res['tbl_data'].get('offsets'):
            rows = []
            for cat, offsets in res['tbl_data']['offsets'].items():
                if offsets:
                    off = offsets[0]
                    fortune = res['tbl_data']['base'] + res['tbl_data']['seq'] + off
                    rows.append(f"<tr><td>{cat}</td><td>{off}</td><td>{fortune}</td><td>{res['tbl_data']['base']} + {res['tbl_data']['seq']} + {off} = {fortune}</td></tr>")
            
            if rows:
                destinyTableHtml = f"""
<table class="destiny-table">
    <thead>
        <tr><th>类别</th><th>加数</th><th>条文数</th><th>计算式</th></tr>
    </thead>
    <tbody>
        {''.join(rows)}
    </tbody>
</table>"""
            else:
                destinyTableHtml = '<div style="text-align:center;color:#666;padding:20px;">未找到匹配的本命条文数据</div>'
        else:
            destinyTableHtml = '<div style="text-align:center;color:#666;padding:20px;">未找到匹配的本命条文数据</div>'
        
        # 生成流年条文表格HTML
        liunianRows = []
        for item in res['liunian']:
            if 1 <= item['age'] <= 100:
                liunianRows.append(f"""
<tr>
    <td class="age-cell">{item['age']}</td>
    <td>{item['year']}</td>
    <td>{item['sound']}</td>
    <td>{item['marker']}</td>
    <td class="highlight-cell">{item['letter']}</td>
    <td>{item['corrected_letter'] or '—'}</td>
    <td>{item['original_fortune'] or '—'}</td>
    <td class="duanyu-cell">{item['original_duanyu'] or '—'}</td>
    <td>{item['original_duanyu_age'] or '—'}</td>
    <td class="highlight-cell">{item['corrected_fortune'] or '—'}</td>
    <td class="duanyu-cell">{item['corrected_duanyu'] or '—'}</td>
    <td>{item['corrected_duanyu_age'] or '—'}</td>
</tr>""")
        
        # 生成基础信息HTML
        headerLines = res['header_info'].split('\n')
        infoItems = []
        for line in headerLines:
            if ':' in line:
                parts = line.split(':', 1)
                infoItems.append(f'<div class="input-info-item"><span class="input-label">{parts[0].strip()}</span><span class="input-value">{parts[1].strip()}</span></div>')
        
        # 生成HTML内容
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>铁板神数 - 排盘结果</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "Microsoft YaHei", "Hiragino Sans GB", "SimSun", sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            padding-bottom: 30px;
            border-bottom: 2px solid #d4af37;
            margin-bottom: 30px;
        }}
        .title {{
            font-size: 28px;
            font-weight: bold;
            color: #8b4513;
            letter-spacing: 8px;
            margin-bottom: 10px;
        }}
        .subtitle {{
            font-size: 14px;
            color: #666;
        }}
        .section-title {{
            font-size: 18px;
            color: #8b4513;
            margin: 25px 0 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #d4af3730;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-title::before {{
            content: "☯";
            font-size: 20px;
        }}
        .input-info {{
            background: #fff8dc;
            border: 1px solid #d4af3730;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .input-info-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #d4af3720;
        }}
        .input-info-item:last-child {{ border-bottom: none; }}
        .input-label {{ color: #666; font-size: 13px; }}
        .input-value {{ color: #333; font-weight: 500; }}
        .basic-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .basic-item {{
            background: #fff8dc;
            border: 1px solid #d4af3730;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }}
        .basic-item-label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 6px;
        }}
        .basic-item-value {{
            font-size: 20px;
            font-weight: bold;
            color: #8b4513;
        }}
        .gua-display-container {{
            display: flex;
            justify-content: center;
            gap: 50px;
            align-items: center;
            padding: 25px;
            background: #faf8f0;
            border-radius: 8px;
            margin-top: 20px;
        }}
        .gua-section {{ text-align: center; }}
        .gua-label {{ color: #666; font-size: 12px; margin-bottom: 8px; }}
        .gua-symbol {{
            font-family: "STKaiti", "KaiTi", serif;
            font-size: 40px;
            color: #8b4513;
            margin-bottom: 6px;
        }}
        .gua-name {{ font-size: 16px; font-weight: bold; color: #333; }}
        .gua-element {{ font-size: 12px; color: #666; }}
        .gua-main-section {{
            text-align: center;
            padding: 0 25px;
            border-left: 1px solid #d4af3730;
            border-right: 1px solid #d4af3730;
        }}
        .gua-main-label {{ color: #666; font-size: 12px; margin-bottom: 8px; }}
        .gua-main-name {{
            font-size: 24px;
            font-weight: bold;
            color: #8b4513;
            margin-bottom: 4px;
        }}
        .gua-combination {{ font-size: 12px; color: #666; }}
        .destiny-tiaowen {{
            background: #faf8f0;
            border-radius: 8px;
            padding: 20px;
        }}
        .destiny-header {{
            margin-bottom: 15px;
            padding-bottom: 12px;
            border-bottom: 1px solid #d4af3730;
        }}
        .destiny-info {{
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .destiny-info-item {{ color: #333; }}
        .destiny-info-item span {{
            color: #8b4513;
            font-weight: bold;
        }}
        .destiny-table, .liunian-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }}
        .destiny-table th, .liunian-table th {{
            background: #d4af3720;
            color: #8b4513;
            padding: 10px;
            text-align: center;
            font-weight: 500;
            border: 1px solid #d4af3730;
        }}
        .destiny-table td, .liunian-table td {{
            padding: 8px;
            text-align: center;
            border: 1px solid #d4af3720;
        }}
        .liunian-table {{
            font-size: 10px;
            table-layout: auto;
        }}
        .liunian-table th.group-header {{
            background: #d4af3730;
            font-size: 11px;
        }}
        .liunian-table th.sub-header {{
            background: #d4af3715;
            font-size: 9px;
        }}
        .age-cell {{
            color: #8b4513;
            font-weight: bold;
        }}
        .highlight-cell {{
            background: #fff8dc;
            color: #8b4513;
        }}
        .duanyu-cell {{
            text-align: left;
            max-width: 120px;
            font-size: 9px;
            line-height: 1.3;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #d4af3730;
            color: #666;
            font-size: 12px;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">☯ 铁板神数 ☯</div>
            <div class="subtitle">先天考刻推演结果</div>
        </div>
        
        <div class="section-title">基础信息</div>
        <div class="input-info">
            {''.join(infoItems)}
        </div>
        
        <div class="section-title">基础排盘</div>
        <div class="basic-grid">
            <div class="basic-item"><div class="basic-item-label">先天命数</div><div class="basic-item-value">{res['cong_num']}</div></div>
            <div class="basic-item"><div class="basic-item-label">五音命数</div><div class="basic-item-value">{res['tone_num']}</div></div>
            <div class="basic-item"><div class="basic-item-label">日命数</div><div class="basic-item-value">{dayLife}</div></div>
            <div class="basic-item"><div class="basic-item-label">时运数</div><div class="basic-item-value">{timeLuck}</div></div>
            <div class="basic-item"><div class="basic-item-label">刻别</div><div class="basic-item-value">{res['moment_cn']}</div></div>
            <div class="basic-item"><div class="basic-item-label">本命数</div><div class="basic-item-value">{res['main_num']}</div></div>
            <div class="basic-item"><div class="basic-item-label">十二辟卦</div><div class="basic-item-value">{res['hex_name']}</div></div>
            <div class="basic-item"><div class="basic-item-label">后天命数</div><div class="basic-item-value">{res['pn_num']}</div></div>
        </div>
        
        <div class="gua-display-container">
            <div class="gua-section">
                <div class="gua-label">上卦</div>
                <div class="gua-symbol">{shangGua['lines']}</div>
                <div class="gua-name">{shangName}</div>
                <div class="gua-element">{shangGua['element']}</div>
            </div>
            <div class="gua-main-section">
                <div class="gua-main-label">本卦</div>
                <div class="gua-main-name">{hexName}</div>
                <div class="gua-combination">{shangName} + {xiaName}</div>
            </div>
            <div class="gua-section">
                <div class="gua-label">下卦</div>
                <div class="gua-symbol">{xiaGua['lines']}</div>
                <div class="gua-name">{xiaName}</div>
                <div class="gua-element">{xiaGua['element']}</div>
            </div>
        </div>
        
        <div class="section-title">本命条文</div>
        <div class="destiny-tiaowen">
            <div class="destiny-header">
                <div class="destiny-info">
                    <div class="destiny-info-item">十二辟卦：<span>{res['hex_name']}</span></div>
                    <div class="destiny-info-item">刻别：<span>{res['moment_cn']}</span></div>
                    <div class="destiny-info-item">先天命数：<span>{res['cong_num']}</span></div>
                </div>
            </div>
            {destinyTableHtml}
        </div>
        
        <div class="section-title">流年条文 (1-100岁)</div>
        <div class="destiny-tiaowen" style="overflow-x:auto;">
            <table class="liunian-table">
                <thead>
                    <tr>
                        <th rowspan="2" class="age-cell">岁数</th>
                        <th rowspan="2">干支</th>
                        <th rowspan="2">五音</th>
                        <th rowspan="2">标记</th>
                        <th colspan="2" class="group-header">字母</th>
                        <th colspan="3" class="group-header">原条文</th>
                        <th colspan="3" class="group-header">校正后条文</th>
                    </tr>
                    <tr>
                        <th class="sub-header">字母</th>
                        <th class="sub-header">校正字母</th>
                        <th class="sub-header">条文</th>
                        <th class="sub-header">断语</th>
                        <th class="sub-header">年龄</th>
                        <th class="sub-header">条文</th>
                        <th class="sub-header">断语</th>
                        <th class="sub-header">年龄</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(liunianRows)}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            ☯ 本站为传统文化展示与研习历程，仅供文化研习参考 | 排盘时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>'''
        
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"\n[完成] 排盘报告(HTML)已保存至: {os.path.abspath(fname)}")
        return fname

def main():
    print("="*60 + "\n  铁板神数排盘系统 (完整版)\n" + "="*60)
    try:
        # 获取性别
        while True:
            g = input("\n请输入性别 (1:男, 2:女): ").strip()
            if g in ['1', '男']:
                gender = "男"
                break
            elif g in ['2', '女']:
                gender = "女"
                break
            else:
                print("输入无效，请输入 1 或 2")
        
        # 获取时间
        print("\n【时间输入说明】格式为 YYYY-MM-DD HH:MM，例如：1990-01-01 12:00")
        dt_b = input_datetime("出生时间")
        dt_q = datetime.datetime.now()
        
        # 转换为八字信息
        print("\n>>> 正在转换八字信息...")
        info_b = convert_to_bazi_info(dt_b)
        info_q = convert_to_bazi_info(dt_q)
        
        if not info_b:
            print("【错误】出生时间转换失败！")
            return
        if not info_q:
            print("【错误】求测时间转换失败！")
            return
        
        # 开始排盘
        print("\n>>> 正在进行铁板神数排盘...")
        calculator = TieBanCalculator()
        result = calculator.calculate({
            "birth_info": info_b, 
            "query_info": info_q, 
            "gender": gender
        })
        
        # 打印报告
        calculator.print_report(result)
        
        # 保存文件
        calculator.save_to_md(result, info_b['date_str'], info_q['date_str'])
        calculator.save_to_html(result, info_b['date_str'], info_q['date_str'])
        
    except KeyboardInterrupt:
        print("\n\n程序已被用户中断")
    except Exception as e:
        print(f"\n\n程序运行出错: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()