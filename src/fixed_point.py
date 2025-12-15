"""
定点数运算模块
使用 16.16 定点数格式（16位整数部分，16位小数部分）
专为 RP2040 优化（无 FPU）
"""

# 定点数精度：16位小数部分
FIXED_SHIFT = 16
FIXED_ONE = 1 << FIXED_SHIFT  # 65536 = 1.0
FIXED_HALF = FIXED_ONE >> 1   # 32768 = 0.5

# 常用定点数常量
FIXED_PI = 205887  # 3.14159 * 65536
FIXED_TWO_PI = 411775  # 6.28318 * 65536
FIXED_HALF_PI = 102944  # 1.5708 * 65536


def float_to_fixed(f):
    """将浮点数转换为定点数"""
    return int(f * FIXED_ONE)


def fixed_to_float(x):
    """将定点数转换为浮点数（仅用于调试）"""
    return x / FIXED_ONE


def fixed_to_int(x):
    """将定点数转换为整数"""
    return x >> FIXED_SHIFT


def int_to_fixed(i):
    """将整数转换为定点数"""
    return i << FIXED_SHIFT


def fixed_mul(a, b):
    """定点数乘法"""
    return (a * b) >> FIXED_SHIFT


def fixed_div(a, b):
    """定点数除法"""
    if b == 0:
        return 0
    return (a << FIXED_SHIFT) // b


def fixed_sqrt(x):
    """定点数平方根（牛顿迭代法）"""
    if x <= 0:
        return 0
    
    # 初始估计
    result = x
    
    # 4次迭代足够精确
    for _ in range(4):
        result = (result + fixed_div(x, result)) >> 1
    
    return result


def fixed_sin_fast(angle):
    """
    快速定点数正弦函数（查表法）
    angle: 定点数角度（弧度）
    返回: 定点数 sin(angle)
    """
    # 正弦查找表（0-90度，每5度一个值）
    sin_table = [
        0,      # 0°
        5701,   # 5°
        11363,  # 10°
        16846,  # 15°
        22111,  # 20°
        27117,  # 25°
        31827,  # 30°
        36206,  # 35°
        40222,  # 40°
        43852,  # 45°
        47077,  # 50°
        49881,  # 55°
        52250,  # 60°
        54175,  # 65°
        55651,  # 70°
        56678,  # 75°
        57262,  # 80°
        57415,  # 85°
        57344   # 90°
    ]
    
    # 将角度规范化到 [0, 2π)
    angle = angle % FIXED_TWO_PI
    if angle < 0:
        angle += FIXED_TWO_PI
    
    # 确定象限
    if angle < FIXED_HALF_PI:
        # 第一象限
        idx = fixed_to_int(fixed_mul(angle, int_to_fixed(18)) // FIXED_HALF_PI)
        idx = min(idx, 18)
        return sin_table[idx]
    elif angle < FIXED_PI:
        # 第二象限
        angle = FIXED_PI - angle
        idx = fixed_to_int(fixed_mul(angle, int_to_fixed(18)) // FIXED_HALF_PI)
        idx = min(idx, 18)
        return sin_table[idx]
    elif angle < FIXED_PI + FIXED_HALF_PI:
        # 第三象限
        angle = angle - FIXED_PI
        idx = fixed_to_int(fixed_mul(angle, int_to_fixed(18)) // FIXED_HALF_PI)
        idx = min(idx, 18)
        return -sin_table[idx]
    else:
        # 第四象限
        angle = FIXED_TWO_PI - angle
        idx = fixed_to_int(fixed_mul(angle, int_to_fixed(18)) // FIXED_HALF_PI)
        idx = min(idx, 18)
        return -sin_table[idx]


def fixed_cos_fast(angle):
    """
    快速定点数余弦函数
    cos(x) = sin(x + π/2)
    """
    return fixed_sin_fast(angle + FIXED_HALF_PI)


class FixedRandom:
    """定点数随机数生成器"""
    
    def __init__(self, seed=None):
        """初始化随机数生成器"""
        if seed is None:
            import time
            seed = int(time.monotonic() * 1000000) & 0xFFFFFFFF
        self.state = seed
    
    def random_fixed(self):
        """生成 [0, 1) 范围内的定点数随机数"""
        # Xorshift算法
        self.state ^= (self.state << 13) & 0xFFFFFFFF
        self.state ^= (self.state >> 17) & 0xFFFFFFFF
        self.state ^= (self.state << 5) & 0xFFFFFFFF
        
        # 转换为定点数 [0, 1)
        return (self.state & 0xFFFF)  # 取低16位作为小数部分
    
    def randint_fixed(self, a, b):
        """生成 [a, b] 范围内的整数"""
        range_size = b - a + 1
        return a + ((self.random_fixed() * range_size) >> FIXED_SHIFT)
    
    def uniform_fixed(self, a_fixed, b_fixed):
        """生成 [a, b) 范围内的定点数"""
        range_fixed = b_fixed - a_fixed
        return a_fixed + fixed_mul(self.random_fixed(), range_fixed)


# 全局定点数随机数生成器
fixed_random = FixedRandom()
