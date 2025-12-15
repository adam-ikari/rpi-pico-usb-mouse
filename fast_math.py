"""
Doom 风格的快速数学运算
使用位运算和查找表优化性能
"""


def fast_inv_sqrt(x):
    """
    快速平方根倒数（Quake III 算法）
    适用于归一化向量等场景
    """
    if x <= 0:
        return 0
    
    threehalfs = 1.5
    x2 = x * 0.5
    i = int(x)
    i = 0x5f3759df - (i >> 1)
    y = float(i)
    y = y * (threehalfs - (x2 * y * y))
    return y


def fast_sqrt(x):
    """快速平方根（使用牛顿迭代）"""
    if x <= 0:
        return 0
    if x == 1:
        return 1
    
    guess = x >> 1
    if guess == 0:
        guess = 1
    
    for _ in range(4):
        guess = (guess + x // guess) >> 1
    
    return guess


def fast_distance(dx, dy):
    """
    快速距离计算（Doom 风格）
    使用整数运算和近似
    """
    dx = abs(dx)
    dy = abs(dy)
    
    if dx < dy:
        dx, dy = dy, dx
    
    return dx + (dy >> 1)


def fast_normalize(x, y):
    """
    快速向量归一化
    返回整数坐标
    """
    dist = fast_distance(x, y)
    if dist == 0:
        return 0, 0
    
    norm_x = (x << 8) // dist
    norm_y = (y << 8) // dist
    
    return norm_x, norm_y


def angle_to_dir_fast(angle_deg):
    """
    快速角度转方向（使用 Doom 的 8 方向查找表）
    angle_deg: 0-360 度
    返回: (dx, dy) 整数方向向量
    """
    DIR_TABLE = [
        (256, 0),      # 0° 东
        (181, 181),    # 45° 东北
        (0, 256),      # 90° 北
        (-181, 181),   # 135° 西北
        (-256, 0),     # 180° 西
        (-181, -181),  # 225° 西南
        (0, -256),     # 270° 南
        (181, -181),   # 315° 东南
    ]
    
    idx = ((angle_deg + 22) // 45) % 8
    return DIR_TABLE[idx]


def fixed_mul(a, b, shift=8):
    """
    定点数乘法（Doom 风格）
    shift: 小数位数
    """
    return (a * b) >> shift


def fixed_div(a, b, shift=8):
    """
    定点数除法（Doom 风格）
    shift: 小数位数
    """
    if b == 0:
        return 0
    return (a << shift) // b
