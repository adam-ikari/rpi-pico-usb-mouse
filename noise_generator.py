"""
优化的噪声生成器模块
提供高性能的Perlin噪声实现，使用查找表优化性能
"""

import math
from constants import *


class NoiseGenerator:
    """超轻量级噪声生成器类 - 使用时间换空间策略"""
    
    # 类变量
    _INITIALIZED = False
    _GRADIENTS = []
    _PERMUTATION = []
    
    @classmethod
    def _initialize(cls):
        """初始化梯度表和排列表"""
        if cls._INITIALIZED:
            return
        
        # 生成梯度向量（8个方向）
        cls._GRADIENTS = [
            (1, 1), (-1, 1), (1, -1), (-1, -1),
            (1, 0), (-1, 0), (0, 1), (0, -1)
        ]
        
        # 生成排列表（0-63的随机排列）
        permutation = list(range(64))
        # 使用简单的伪随机数生成器打乱
        for i in range(63, 0, -1):
            j = int((math.sin(i * 12.9898 + 78.233) * 43758.5453) % 64)
            permutation[i], permutation[j] = permutation[j], permutation[i]
        
        # 复制一份以避免索引溢出
        cls._PERMUTATION = permutation + permutation
        
        cls._INITIALIZED = True
    
    @classmethod
    def _fade(cls, t):
        """淡化函数：6t⁵ - 15t⁴ + 10t³"""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    @classmethod
    def _lerp(cls, a, b, t):
        """线性插值"""
        return a + t * (b - a)
    
    @classmethod
    def _contribution(cls, xi, yi, x0, y0):
        """计算Simplex噪声顶点贡献度"""
        cls._initialize()
        
        # 计算距离
        t0 = 0.5 - x0 * x0 - y0 * y0
        if t0 < 0:
            return 0
        
        t0 *= t0
        # 获取梯度
        gi = cls._PERMUTATION[(xi + cls._PERMUTATION[yi & 63]) & 63] % 8
        gradient = cls._GRADIENTS[gi]
        
        # 计算点积
        n0 = t0 * t0 * t0 * (gradient[0] * x0 + gradient[1] * y0)
        return n0
    

    
    @classmethod
    def perlin_noise_2d(cls, x, y, frequency=1.0, octaves=1, persistence=0.5, lacunarity=2.0):
        """
        超轻量级Perlin噪声实现
        完全避免预计算，使用时间换空间
        """
        total = 0
        amplitude = 1
        max_value = 0
        
        # 简单的梯度方向（4个方向）
        gradients = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        
        for _ in range(octaves):
            # 缩放坐标
            scaled_x = x * frequency
            scaled_y = y * frequency
            
            # 获取整数部分和小数部分
            xi = int(scaled_x)
            yi = int(scaled_y)
            xf = scaled_x - xi
            yf = scaled_y - yi
            
            # 简单的哈希函数
            def hash_gradient(ix, iy):
                n = ix * 73856093 ^ iy * 19349663
                return gradients[n % 4]
            
            # 计算四个角的梯度点积
            def dot_gradient(gx, gy, dx, dy):
                return gx * dx + gy * dy
            
            g00 = hash_gradient(xi, yi)
            g10 = hash_gradient(xi + 1, yi)
            g01 = hash_gradient(xi, yi + 1)
            g11 = hash_gradient(xi + 1, yi + 1)
            
            n00 = dot_gradient(g00[0], g00[1], xf, yf)
            n10 = dot_gradient(g10[0], g10[1], xf - 1, yf)
            n01 = dot_gradient(g01[0], g01[1], xf, yf - 1)
            n11 = dot_gradient(g11[0], g11[1], xf - 1, yf - 1)
            
            # 简单的线性插值
            def lerp(a, b, t):
                return a + t * (b - a)
            
            def fade(t):
                # 使用整数运算优化
                # t * t * (3 - 2*t) = 3t^2 - 2t^3
                t_int = int(t * 256)  # 转为整数 0-256
                t_sq = (t_int * t_int) >> 8  # t^2
                t_cu = (t_sq * t_int) >> 8   # t^3
                result = (3 * t_sq - 2 * t_cu) >> 8
                return result / 256
            
            u = fade(xf)
            v = fade(yf)
            
            x1 = lerp(n00, n10, u)
            x2 = lerp(n01, n11, u)
            
            total += lerp(x1, x2, v) * amplitude
            
            # 更新参数
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
        
        # 归一化到 [-1, 1]
        return total / max_value if max_value > 0 else 0
    
    @classmethod
    def fast_simplex_noise(cls, x, y, frequency=1.0):
        """
        简化的Simplex噪声实现（比Perlin噪声更快且视觉效果更好）
        使用预计算的查找表优化性能
        """
        cls._initialize()
        
        # 缩放坐标
        scaled_x = x * frequency
        scaled_y = y * frequency
        
        # Simplex噪声的F2和F3常数
        F2 = 0.5 * (math.sqrt(3.0) - 1.0)
        G2 = (3.0 - math.sqrt(3.0)) / 6.0
        
        # 计算Simplex网格坐标
        s = (scaled_x + scaled_y) * F2
        i = int(scaled_x + s)
        j = int(scaled_y + s)
        
        t = (i + j) * G2
        X0 = i - t
        Y0 = j - t
        x0 = scaled_x - X0
        y0 = scaled_y - Y0
        
        # 确定Simplex方向
        if x0 > y0:
            i1, j1 = 1, 0
        else:
            i1, j1 = 0, 1
        
        # 计算其他顶点
        x1 = x0 - i1 + G2
        y1 = y0 - j1 + G2
        x2 = x0 - 1.0 + 2.0 * G2
        y2 = y0 - 1.0 + 2.0 * G2
        
        # 计算贡献度
        n0 = cls._contribution(X0, Y0, x0, y0)
        n1 = cls._contribution(X0 + i1, Y0 + j1, x1, y1)
        n2 = cls._contribution(X0 + 1, Y0 + 1, x2, y2)
        
        # 缩放结果
        return 70.0 * (n0 + n1 + n2)
    

    @classmethod
    def value_noise_2d(cls, x, y, frequency=1.0):
        """
        超轻量级值噪声实现
        完全避免预计算，使用时间换空间
        """
        # 缩放坐标
        scaled_x = x * frequency
        scaled_y = y * frequency
        
        # 获取整数部分和小数部分
        xi = int(scaled_x)
        yi = int(scaled_y)
        xf = scaled_x - xi
        yf = scaled_y - yi
        
        # 直接计算四个角的伪随机值，避免预计算
        def pseudo_random(ix, iy):
            # 使用简单的哈希函数
            n = ix * 73856093 ^ iy * 19349663
            return (math.sin(n) * 43758.5453) % 1.0
        
        # 获取四个角的伪随机值
        v00 = pseudo_random(xi, yi)
        v10 = pseudo_random(xi + 1, yi)
        v01 = pseudo_random(xi, yi + 1)
        v11 = pseudo_random(xi + 1, yi + 1)
        
        # 简单的线性插值
        def lerp(a, b, t):
            return a + t * (b - a)
        
        def fade(t):
            return t * t * (3.0 - 2.0 * t)
        
        u = fade(xf)
        v = fade(yf)
        
        x1 = lerp(v00, v10, u)
        x2 = lerp(v01, v11, u)
        
        return lerp(x1, x2, v)
    
    
    
    @classmethod
    def turbulence(cls, x, y, frequency=1.0, octaves=4):
        """
        湍流噪声（绝对值累加的噪声）
        适合用于模拟火焰、云彩等效果
        """
        value = 0
        amplitude = 1
        freq = frequency
        
        for _ in range(octaves):
            value += abs(cls.perlin_noise_2d(x * freq, y * freq)) * amplitude
            freq *= 2
            amplitude *= 0.5
        
        return value
    
    @classmethod
    def ridged_noise(cls, x, y, frequency=1.0, octaves=4):
        """
        脊状噪声（1-abs(noise)的噪声）
        适合用于模拟山脉、闪电等效果
        """
        value = 0
        amplitude = 1
        freq = frequency
        
        for _ in range(octaves):
            noise = abs(cls.perlin_noise_2d(x * freq, y * freq))
            value += (1 - noise) * amplitude
            freq *= 2
            amplitude *= 0.5
        
        return value


# 全局噪声生成器实例
noise_generator = NoiseGenerator()