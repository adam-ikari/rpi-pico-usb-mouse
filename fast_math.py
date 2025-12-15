"""Doom 风格快速数学运算和定点数系统"""

# 定点数格式常量
FIXED_SHIFT_16 = 16
FIXED_ONE_16 = 1 << FIXED_SHIFT_16

# 百分比定点数 (×100)
PERCENT_SHIFT = 2
PERCENT_ONE = 100

# 万分比定点数 (×10000)
TRIG_SHIFT = 4
TRIG_ONE = 10000


def fast_distance(dx, dy):
    """快速距离计算 (Doom 近似算法)"""
    dx = abs(dx)
    dy = abs(dy)
    if dx < dy:
        dx, dy = dy, dx
    return dx + (dy >> 1)


def fixed_mul(a, b, shift=FIXED_SHIFT_16):
    """定点数乘法"""
    return (a * b) >> shift


def fixed_div(a, b, shift=FIXED_SHIFT_16):
    """定点数除法"""
    if b == 0:
        return 0
    return (a << shift) // b


def percent_to_float(p):
    """百分比定点数转浮点 (100 -> 1.0)"""
    return p / PERCENT_ONE


def percent_to_int(p):
    """百分比定点数转整数"""
    return p // PERCENT_ONE


def float_to_percent(f):
    """浮点转百分比定点数 (1.0 -> 100)"""
    return int(f * PERCENT_ONE)


def trig_to_float(t):
    """三角函数定点数转浮点 (10000 -> 1.0)"""
    return t / TRIG_ONE


def compare_percent(value, threshold):
    """比较百分比 (避免浮点比较)"""
    return value < threshold
