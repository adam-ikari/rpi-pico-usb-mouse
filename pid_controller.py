"""
PID 控制器模块
模拟人手的调整延迟和随机扰动
"""

import time
from constants import *
from random_generator import random_pool


class PIDController:
    """
    PID 控制器，模拟人手对鼠标移动的微调
    特点：
    1. 数百毫秒的反应延迟
    2. 随机扰动
    3. 不完美的控制（模拟人手抖动）
    """
    
    def __init__(self, kp=PID_KP, ki=PID_KI, kd=PID_KD):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        # 向量 PID 控制（基于距离）
        self.error_distance_sum = 0  # 距离误差积分
        self.last_error_distance = 0  # 上次距离误差
        
        # 过冲检测
        self.has_overshot = False  # 是否已过冲
        self.overshoot_damping = 10  # 过冲后的阻尼系数（×100）
        
        self.last_update_time = time.monotonic()
        self.reaction_delay = random_pool.randint(HUMAN_REACTION_DELAY_MIN, HUMAN_REACTION_DELAY_MAX) / 1000.0
        self.next_reaction_time = self.last_update_time + self.reaction_delay
        
        # 向量噪声（方向和幅度）
        self.noise_time = 0
        self.noise_angle = 0      # 噪声方向（弧度）
        self.noise_magnitude = 0  # 噪声幅度
        
        self.pending_correction_x = 0
        self.pending_correction_y = 0
    
    def update(self, target_x, target_y, current_x, current_y):
        """
        向量 PID 控制器
        
        模拟人手特性：
        - 朝向目标的向量运动
        - 延迟反应（100-400ms）
        - 向量随机扰动
        - 距离积分饱和限制
        """
        current_time = time.monotonic()
        
        # 计算误差向量
        error_x = target_x - current_x
        error_y = target_y - current_y
        
        if current_time < self.next_reaction_time:
            return 0, 0
        
        dt = current_time - self.last_update_time
        if dt <= 0:
            dt = 0.01
        
        # 1. 计算误差距离和方向（向量）
        error_distance = self._fast_distance(error_x, error_y)
        
        if error_distance == 0:
            return 0, 0
        
        # 误差方向（归一化向量）
        direction_x = (error_x * 100) // error_distance  # ×100 保持精度
        direction_y = (error_y * 100) // error_distance
        
        # 2. 过冲检测
        if self.last_error_distance > 0 and error_distance > self.last_error_distance:
            # 误差距离增大 → 已过冲
            if not self.has_overshot:
                self.has_overshot = True
                self.error_distance_sum = 0  # 清除积分项，避免震荡
        
        # 3. 基于距离的 PID 控制
        if not self.has_overshot:
            # 正常 PID 控制
            self.error_distance_sum += error_distance
            self.error_distance_sum = max(-1000, min(1000, self.error_distance_sum))
            
            error_diff = error_distance - self.last_error_distance
            
            p_term = (error_distance * self.kp) // 100
            i_term = (self.error_distance_sum * self.ki) // 100
            d_term = (error_diff * self.kd) // 100
            
            correction_distance = p_term + i_term + d_term
        else:
            # 已过冲：大幅降低修正力度，仅保留 10% P 项
            p_term = (error_distance * self.kp * self.overshoot_damping) // 10000
            correction_distance = p_term
        
        # 4. 添加向量噪声
        if current_time - self.noise_time > (PID_NOISE_FREQUENCY / 1000.0):
            # 随机噪声方向和幅度
            self.noise_angle = random_pool.uniform(-314, 314) / 100  # -π 到 π
            self.noise_magnitude = random_pool.randint(-PID_NOISE_AMPLITUDE, PID_NOISE_AMPLITUDE)
            self.noise_time = current_time
        
        # 噪声向量分量
        noise_x = int(self._fast_cos(self.noise_angle) * self.noise_magnitude)
        noise_y = int(self._fast_sin(self.noise_angle) * self.noise_magnitude)
        
        # 5. 沿误差方向分解修正量
        correction_x = (correction_distance * direction_x) // 100 + noise_x
        correction_y = (correction_distance * direction_y) // 100 + noise_y
        
        # 更新历史
        self.last_error_distance = error_distance
        self.last_update_time = current_time
        
        self.reaction_delay = random_pool.randint(HUMAN_REACTION_DELAY_MIN, HUMAN_REACTION_DELAY_MAX) / 1000.0
        self.next_reaction_time = current_time + self.reaction_delay
        
        return int(correction_x), int(correction_y)
    
    def _fast_distance(self, x, y):
        """快速距离计算（整数平方根）"""
        # 使用牛顿法近似
        if x == 0 and y == 0:
            return 0
        
        val = abs(x) + abs(y)
        if abs(x) > abs(y):
            val = abs(x) + (abs(y) >> 1)
        else:
            val = abs(y) + (abs(x) >> 1)
        
        return val
    
    def _fast_sin(self, angle):
        """快速 sin 近似（泰勒级数）"""
        import math
        return math.sin(angle)
    
    def _fast_cos(self, angle):
        """快速 cos 近似（泰勒级数）"""
        import math
        return math.cos(angle)
    
    def reset(self):
        """重置 PID 状态"""
        self.error_distance_sum = 0
        self.last_error_distance = 0
        self.has_overshot = False  # 重置过冲标志
        self.last_update_time = time.monotonic()
        self.reaction_delay = random_pool.randint(HUMAN_REACTION_DELAY_MIN, HUMAN_REACTION_DELAY_MAX) / 1000.0
        self.next_reaction_time = self.last_update_time + self.reaction_delay
        self.pending_correction_x = 0
        self.pending_correction_y = 0
