"""
LED控制模块
包含LED呼吸灯和颜色控制器
"""

import time
from constants import *


class LEDController:
    """LED 呼吸灯和颜色控制器"""
    
    def __init__(self, pixels, perf_stats=None):
        self.pixels = pixels
        self.perf_stats = perf_stats
        self.last_time = time.monotonic()
        self.current_brightness = BREATHE_MAX_BRIGHTNESS
        self.brightness_direction = -0.01
        self.transition_start_time = None
        self.transition_duration = 0
    
    def set_color_with_brightness(self, color, brightness):
        """设置LED颜色和亮度"""
        self.pixels.brightness = brightness
        self.pixels.fill(color)
        self.pixels.show()
    
    def update_breathing(self, color):
        """非阻塞更新呼吸灯效果"""
        current_time = time.monotonic()
        time_delta = min(current_time - self.last_time, TRANSITION_TIME_DELTA_LIMIT)
        self.last_time = current_time
        
        self.current_brightness += self.brightness_direction * (time_delta / max(BRIGHTNESS_CHANGE_SPEED_FACTOR, 0.001))
        
        if self.current_brightness >= BREATHE_MAX_BRIGHTNESS:
            self.current_brightness = BREATHE_MAX_BRIGHTNESS
            self.brightness_direction = -abs(self.brightness_direction)
        elif self.current_brightness <= BREATHE_MIN_BRIGHTNESS:
            self.current_brightness = BREATHE_MIN_BRIGHTNESS
            self.brightness_direction = abs(self.brightness_direction)
        
        self.set_color_with_brightness(color, self.current_brightness)
    
    def start_transition(self, duration):
        """启动过渡计时器"""
        self.transition_start_time = time.monotonic()
        self.transition_duration = duration
    
    def is_transition_complete(self):
        """检查过渡是否完成"""
        if self.transition_start_time is None:
            return True
        return time.monotonic() - self.transition_start_time >= self.transition_duration
    
    def get_mode_color(self, mode):
        """根据模式获取对应的LED颜色"""
        color_map = {
            "web_browsing": WEB_BROWSING_COLOR,
            "page_scanning": PAGE_SCANNING_COLOR,
            "exploratory_move": EXPLORATORY_COLOR,
            "random_movement": RANDOM_MOVEMENT_COLOR,
            "circular_move": CIRCULAR_MOVEMENT_COLOR,
            "target_focus": TARGET_FOCUS_COLOR
        }
        return color_map.get(mode, (0, 0, 0))
    
    def update_led_for_mode(self, mode, is_active=True):
        """
        根据当前模式更新LED状态
        """
        # 记录模式切换
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_mode_switch(mode)
        
        color = self.get_mode_color(mode)
        
        if is_active:
            # 设置为正常亮度
            self.set_color_with_brightness(color, BREATHE_MAX_BRIGHTNESS)
        else:
            # 设置为低亮度
            self.set_color_with_brightness(color, BREATHE_MIN_BRIGHTNESS)
        
        return color