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
        
        self.error_sum = 0
        self.last_error = 0
        
        self.last_update_time = time.monotonic()
        self.reaction_delay = random_pool.randint(HUMAN_REACTION_DELAY_MIN, HUMAN_REACTION_DELAY_MAX) / 1000.0
        self.next_reaction_time = self.last_update_time + self.reaction_delay
        
        self.noise_time = 0
        self.noise_value = 0
        
        self.pending_correction_x = 0
        self.pending_correction_y = 0
    
    def update(self, target_x, target_y, current_x, current_y):
        """
        更新 PID 控制器，计算修正值
        返回 (correction_x, correction_y)
        
        模拟人手特性：
        - 延迟反应（100-400ms）
        - 随机扰动
        - 积分饱和限制
        """
        current_time = time.monotonic()
        
        error_x = target_x - current_x
        error_y = target_y - current_y
        
        if current_time < self.next_reaction_time:
            return 0, 0
        
        dt = current_time - self.last_update_time
        if dt <= 0:
            dt = 0.01
        
        self.error_sum += error_x + error_y
        self.error_sum = max(-1000, min(1000, self.error_sum))
        
        error_diff_x = (error_x - self.last_error) if self.last_error != 0 else 0
        error_diff_y = (error_y - self.last_error) if self.last_error != 0 else 0
        
        p_term_x = (error_x * self.kp) // 100
        p_term_y = (error_y * self.kp) // 100
        
        i_term = (self.error_sum * self.ki) // 100
        
        d_term_x = (error_diff_x * self.kd) // 100
        d_term_y = (error_diff_y * self.kd) // 100
        
        correction_x = p_term_x + i_term + d_term_x
        correction_y = p_term_y + i_term + d_term_y
        
        if current_time - self.noise_time > (PID_NOISE_FREQUENCY / 1000.0):
            self.noise_value = random_pool.randint(-PID_NOISE_AMPLITUDE, PID_NOISE_AMPLITUDE)
            self.noise_time = current_time
        
        correction_x += self.noise_value
        correction_y += self.noise_value
        
        self.last_error = (error_x + error_y) // 2
        self.last_update_time = current_time
        
        self.reaction_delay = random_pool.randint(HUMAN_REACTION_DELAY_MIN, HUMAN_REACTION_DELAY_MAX) / 1000.0
        self.next_reaction_time = current_time + self.reaction_delay
        
        return int(correction_x), int(correction_y)
    
    def reset(self):
        """重置 PID 状态"""
        self.error_sum = 0
        self.last_error = 0
        self.last_update_time = time.monotonic()
        self.reaction_delay = random_pool.randint(HUMAN_REACTION_DELAY_MIN, HUMAN_REACTION_DELAY_MAX) / 1000.0
        self.next_reaction_time = self.last_update_time + self.reaction_delay
        self.pending_correction_x = 0
        self.pending_correction_y = 0
