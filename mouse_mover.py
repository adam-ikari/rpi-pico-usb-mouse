import time
import math
import random
from constants import *
from random_generator import fast_random, random_pool


class MouseMover:
    """鼠标移动控制器，使用非阻塞方式实现"""
    
    def __init__(self, mouse_device, perf_stats=None):
        self.mouse = mouse_device
        self.perf_stats = perf_stats
        self.active = False
        self.current_step = 0
        self.total_steps = 0
        self.step_x = 0
        self.step_y = 0
        self.start_time = 0
        self.move_duration = 0
        self.small_move_steps = []
        self.small_move_index = 0
        self.velocity_profile = []  # 速度变化曲线

    def quick_move_to_target(self, end_x, end_y, duration_factor=0.02):
        """
        非阻塞快速移动鼠标到目标位置，更自然的人类移动模式
        实现加速-匀速-减速的人类移动模式
        """
        try:
            distance = math.sqrt(end_x * end_x + end_y * end_y)
            if distance == 0:
                return  # 如果距离为0，直接返回

            # 基于距离计算步数，但增加一些随机性
            base_steps = max(int(distance / BASE_STEP_DISTANCE), MIN_BASE_STEPS)
            self.total_steps = int(base_steps * random_pool.uniform(DISTANCE_RANDOM_FACTOR_MIN, DISTANCE_RANDOM_FACTOR_MAX))
            
            # 创建速度变化曲线：加速-匀速-减速
            self.velocity_profile = self._create_velocity_profile(self.total_steps)
            
            # 计算每步的移动量
            if self.total_steps > 0:
                self.step_x = end_x / self.total_steps
                self.step_y = end_y / self.total_steps
            else:
                self.step_x = 0
                self.step_y = 0
            
            self.current_step = 0
            self.active = True
            self.start_time = time.monotonic()
            self.move_duration = duration_factor
            
        except Exception as e:
            raise

    def _create_velocity_profile(self, total_steps):
        """
        创建速度变化曲线，模拟人类移动的加速-匀速-减速模式
        """
        # 将移动分为三个阶段：加速、匀速、减速
        accel_steps = max(1, int(total_steps * ACCEL_DECEL_PHASE_RATIO))
        decel_steps = max(1, int(total_steps * ACCEL_DECEL_PHASE_RATIO))
        const_steps = total_steps - accel_steps - decel_steps
        
        profile = []
        
        # 加速阶段 - 更缓慢的加速
        for i in range(accel_steps):
            t = i / max(accel_steps, 1)
            factor = ACCEL_START_FACTOR + (ACCEL_END_FACTOR - ACCEL_START_FACTOR) * t * t
            profile.append(factor)
        
        # 匀速阶段
        for i in range(const_steps):
            profile.append(1.0 + random_pool.uniform(CONSTANT_PHASE_MIN_VARIATION, CONSTANT_PHASE_MAX_VARIATION))
        
        # 减速阶段 - 更缓慢的减速
        for i in range(decel_steps):
            t = i / max(decel_steps, 1)
            factor = DECEL_START_FACTOR - (DECEL_START_FACTOR - DECEL_END_FACTOR) * t * t
            profile.append(max(DECEL_MIN_FACTOR, factor))
        
        return profile

    def smooth_move_small(self, start_x, start_y, end_x, end_y, duration_factor=0.1):
        """
        非阻塞在小范围内平滑移动鼠标，更自然的人类移动模式
        包含加速-匀速-减速和随机速度变化
        """
        try:
            dx = end_x - start_x
            dy = end_y - start_y
            distance = math.sqrt(dx * dx + dy * dy)
            if distance == 0:
                return  # 如果距离为0，直接返回

            # 增加更多步骤以实现更自然的曲线移动
            base_steps = max(int(distance / SMALL_MOVE_BASE_DISTANCE), 5)
            steps = int(base_steps * random_pool.uniform(SMALL_MOVE_DISTANCE_FACTOR_MIN, SMALL_MOVE_DISTANCE_FACTOR_MAX))
            
            # 创建速度变化曲线
            velocity_profile = self._create_velocity_profile(steps)
            
            # 创建小移动步骤列表，模拟人类移动的不规则性
            self.small_move_steps = []
            cumulative_x, cumulative_y = 0, 0  # 累计偏移，确保最终到达目标点
            
            for i in range(steps):
                # 基础移动量
                if steps > 0:
                    base_x = (end_x - start_x) / steps
                    base_y = (end_y - start_y) / steps
                else:
                    base_x = 0
                    base_y = 0
                
                # 应用速度变化
                velocity_factor = velocity_profile[i] if i < len(velocity_profile) else 1.0
                
                # 添加速度变化
                actual_x = base_x * velocity_factor
                actual_y = base_y * velocity_factor
                
                # 添加更小的随机偏移，模拟人类手部微小抖动
                offset_x = random_pool.uniform(SMALL_MOVE_OFFSET_MIN, SMALL_MOVE_OFFSET_MAX) * velocity_factor
                offset_y = random_pool.uniform(SMALL_MOVE_OFFSET_MIN, SMALL_MOVE_OFFSET_MAX) * velocity_factor
                actual_x += offset_x
                actual_y += offset_y
                
                # 减少方向调整频率
                if i % random_pool.randint(DIRECTION_ADJUST_INTERVAL_MIN, DIRECTION_ADJUST_INTERVAL_MAX) == 0 and i > 0:
                    actual_x += random_pool.uniform(LARGE_MOVE_OFFSET_MIN, LARGE_MOVE_OFFSET_MAX)
                    actual_y += random_pool.uniform(LARGE_MOVE_OFFSET_MIN, LARGE_MOVE_OFFSET_MAX)
                
                # 增加停顿概率，模拟人类思考
                if random_pool.random() < THINK_PAUSE_PROBABILITY:
                    self.small_move_steps.append((0, 0))  # 停顿一步
                    self.small_move_steps.append((int(actual_x), int(actual_y)))
                else:
                    self.small_move_steps.append((int(actual_x), int(actual_y)))
                
                cumulative_x += actual_x
                cumulative_y += actual_y

            # 确保最终接近目标点
            if steps > 0:
                # 添加最后一步来修正累积误差
                remaining_x = (end_x - start_x) - cumulative_x
                remaining_y = (end_y - start_y) - cumulative_y
                if abs(remaining_x) > 0.5 or abs(remaining_y) > 0.5:
                    self.small_move_steps.append((int(remaining_x), int(remaining_y)))

            self.small_move_index = 0
            self.active = True
            
        except Exception as e:
            raise

    def update(self):
        """
        更新鼠标移动状态，非阻塞
        """
        if not self.active:
            return True  # 如果未激活，返回True表示已完成

        # 记录性能统计
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_loop()

        # 根据移动类型决定如何更新
        if self.small_move_steps:  # 平滑小移动
            if self.small_move_index < len(self.small_move_steps):
                x, y = self.small_move_steps[self.small_move_index]
                self.mouse.move(x=x, y=y)
                self.small_move_index += 1
                return False  # 未完成
            else:
                self.small_move_steps = []
                self.active = False
                return True  # 完成
        else:  # 快速移动 - 现在使用速度变化曲线
            if self.current_step < self.total_steps:
                # 根据速度曲线应用移动
                velocity_factor = self.velocity_profile[self.current_step] if self.current_step < len(self.velocity_profile) else 1.0
                x_move = int(self.step_x * velocity_factor)
                y_move = int(self.step_y * velocity_factor)
                self.mouse.move(x=x_move, y=y_move)
                self.current_step += 1
                return False  # 未完成
            else:
                self.velocity_profile = []  # 清空速度曲线
                self.active = False
                return True  # 完成