"""
优化的随机数生成器模块
提供高性能的伪随机数生成，减少系统调用开销
"""

import time
from constants import *


class FastRandom:
    """快速伪随机数生成器"""
    
    def __init__(self, seed=None):
        """初始化随机数生成器"""
        if seed is None:
            seed = int(time.monotonic() * 1000000) & 0xFFFFFFFF
        self.state = seed
    
    def random(self):
        """生成 [0, 1) 范围内的随机浮点数"""
        # 使用Xorshift算法生成伪随机数
        self.state ^= (self.state << 13) & 0xFFFFFFFF
        self.state ^= (self.state >> 17) & 0xFFFFFFFF
        self.state ^= (self.state << 5) & 0xFFFFFFFF
        
        # 使用位移和整数运算，返回 [0, 1) 范围的浮点数
        # 取低16位，除以65536
        return (self.state & 0xFFFF) / 65536.0
    
    def random_int16(self):
        """生成 [0, 65535) 范围内的16位整数（定点数优化）"""
        self.state ^= (self.state << 13) & 0xFFFFFFFF
        self.state ^= (self.state >> 17) & 0xFFFFFFFF
        self.state ^= (self.state << 5) & 0xFFFFFFFF
        return (self.state & 0xFFFF)
    
    def randint(self, a, b):
        """生成 [a, b] 范围内的随机整数（优化版本）"""
        range_size = b - a + 1
        # 使用整数运算代替浮点运算
        rand_int = self.random_int16()
        return a + (rand_int * range_size) // 65536
    
    def uniform(self, a, b):
        """生成 [a, b) 范围内的随机浮点数（优化版本）"""
        # 使用整数运算减少浮点运算
        range_val = b - a
        # 使用16位整数随机数代替浮点随机数
        rand_int = self.random_int16()
        # rand_int / 65536 * range_val + a
        return a + (rand_int * range_val) / 65536
    
    def choice(self, seq):
        """从序列中随机选择一个元素"""
        return seq[self.randint(0, len(seq) - 1)]
    
    def randrange(self, start, stop=None, step=1):
        """生成 range(start, stop, step) 中的随机数"""
        if stop is None:
            stop = start
            start = 0
        
        if step == 0:
            return start
        return start + int(self.random() * ((stop - start + step - 1) // step)) * step


class RandomPool:
    """轻量级随机数池，使用时间换空间策略"""
    
    def __init__(self, pool_size=20):
        """初始化随机数池"""
        self.pool_size = pool_size
        self.float_pool = []
        self.int_pool = {}
        self.current_index = 0
        self.generator = FastRandom()
        self._generate_pool()
    
    def _generate_pool(self):
        """生成极简随机数池"""
        # 只生成最基本的池
        self.float_pool = [self.generator.random() for _ in range(self.pool_size)]
        self.int_pool = {
            'small': [self.generator.randint(-10, 10) for _ in range(self.pool_size)],
            'medium': [self.generator.randint(-100, 100) for _ in range(self.pool_size)],
            'large': [self.generator.randint(-1000, 1000) for _ in range(self.pool_size)]
        }
    
    def random(self):
        """获取随机浮点数 - 使用时间换空间策略"""
        self.current_index += 1
        return self.generator.random()
    
    def randint(self, a, b=None):
        """获取随机整数 - 使用时间换空间策略"""
        self.current_index += 1
        
        # 如果只有一个参数，使用生成器直接计算
        if b is None:
            # 假设是范围名称，直接使用生成器
            return self.generator.randint(-100, 100)
        else:
            # 直接使用生成器
            return self.generator.randint(a, b)
    
    def uniform(self, a, b):
        """获取随机浮点数 - 使用时间换空间策略（优化版本）"""
        self.current_index += 1
        return self.generator.uniform(a, b)
    
    def choice(self, seq):
        """从序列中随机选择一个元素"""
        return seq[self.randint(0, len(seq) - 1)]


class WeightedRandom:
    """加权随机选择器"""
    
    def __init__(self, items_with_weights):
        """
        初始化加权随机选择器
        items_with_weights: [(item, weight), ...] 格式的列表
        """
        self.items = []
        self.weights = []
        self.cumulative_weights = []
        self.total_weight = 0
        
        for item, weight in items_with_weights:
            self.items.append(item)
            self.weights.append(weight)
            self.total_weight += weight
            self.cumulative_weights.append(self.total_weight)
    
    def choice(self):
        """根据权重随机选择一个项目（优化版本）"""
        if not self.items:
            return None
        
        if self.total_weight == 0:
            return self.items[0] if self.items else None
        
        # 使用整数运算代替浮点运算
        # 生成 [0, total_weight) 范围内的整数
        rand_gen = FastRandom()
        rand_int = rand_gen.random_int16()
        r = (rand_int * self.total_weight) >> 16  # 除以65536
        
        for i, cumulative_weight in enumerate(self.cumulative_weights):
            if r <= cumulative_weight:
                return self.items[i]
        
        return self.items[-1]


class RandomRangeManager:
    """超轻量级随机数范围管理器"""
    
    def __init__(self):
        """初始化范围管理器"""
        # 使用硬编码范围以避免导入时序问题
        self.ranges = {
            'web_browse_x': (-400, 400),
            'web_browse_y': (-100, 100),
            'page_scan_start_x': (-150, -50),
            'page_scan_y': (-600, 600),
            'page_scan_end_x': (600, 800),
            'exploratory_move': (-200, 200),
            'random_move': (-150, 150),
            'circle_center': (-600, 600),
            'target_focus': (-400, 400)
        }
        self.generator = FastRandom()
    
    def get_range(self, name):
        """获取指定名称的范围"""
        return self.ranges.get(name, (-100, 100))
    
    def randint(self, range_name):
        """在指定范围内生成随机整数"""
        a, b = self.get_range(range_name)
        return self.generator.randint(a, b)
    
    def randuniform(self, range_name):
        """在指定范围内生成随机浮点数（优化版本）"""
        a, b = self.get_range(range_name)
        return self.generator.uniform(a, b)


# 全局随机数生成器实例
fast_random = FastRandom()
random_pool = RandomPool()
range_manager = RandomRangeManager()

# 模式权重配置
MODE_WEIGHTS = [
    ("web_browsing", 25),
    ("page_scanning", 20),
    ("exploratory_move", 20),
    ("random_movement", 15),
    ("circular_move", 10),
    ("target_focus", 10)
]

weighted_mode_selector = WeightedRandom(MODE_WEIGHTS)