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
        
        # 呼吸灯状态
        self.current_brightness_int = 100
        self.brightness_direction = -1
        
        # 亮度过渡
        self.brightness_transition_active = False
        self.brightness_transition_start = 0
        self.brightness_transition_duration = 0.5  # 500ms亮度过渡
        self.brightness_start = 100
        self.brightness_target = 100
        
        # 颜色过渡
        self.current_color = (0, 0, 0)
        self.target_color = (0, 0, 0)
        self.color_transition_active = False
        self.color_transition_start = 0
        self.color_transition_duration = 2.0  # 2s过渡时间
        
        # LED模式：'active' 活动中（恒定亮度） / 'idle' 停顿中（呼吸灯）
        self.led_mode = 'idle'
    
    def _ease_in_out(self, t):
        """缓动函数：ease-in-out (平滑加速和减速)"""
        # 使用三次函数实现平滑过渡
        if t < 0.5:
            return 4 * t * t * t
        else:
            p = 2 * t - 2
            return 1 + p * p * p / 2
    
    def _lerp_color(self, color1, color2, t):
        """颜色插值（使用缓动函数）"""
        # 应用缓动函数使过渡更平滑
        eased_t = self._ease_in_out(t)
        r = int(color1[0] + (color2[0] - color1[0]) * eased_t)
        g = int(color1[1] + (color2[1] - color1[1]) * eased_t)
        b = int(color1[2] + (color2[2] - color1[2]) * eased_t)
        return (r, g, b)
    
    def set_color_with_brightness(self, color, brightness):
        """设置LED颜色和亮度"""
        self.pixels.brightness = brightness
        self.pixels.fill(color)
        self.pixels.show()
    
    def update(self):
        """更新LED状态（颜色过渡 + 亮度控制）"""
        current_time = time.monotonic()
        time_delta = min(current_time - self.last_time, TRANSITION_TIME_DELTA_LIMIT)
        self.last_time = current_time
        
        # 1. 更新颜色过渡
        display_color = self.current_color
        if self.color_transition_active:
            elapsed = current_time - self.color_transition_start
            if elapsed >= self.color_transition_duration:
                # 过渡完成
                self.color_transition_active = False
                self.current_color = self.target_color
                display_color = self.target_color
            else:
                # 计算过渡进度
                t = elapsed / self.color_transition_duration
                display_color = self._lerp_color(self.current_color, self.target_color, t)
        
        # 2. 根据模式更新亮度
        if self.brightness_transition_active:
            # 亮度过渡中
            elapsed = current_time - self.brightness_transition_start
            if elapsed >= self.brightness_transition_duration:
                # 过渡完成
                self.brightness_transition_active = False
                self.current_brightness_int = self.brightness_target
                brightness = self.brightness_target * 0.01
            else:
                # 计算过渡进度（线性插值）
                t = elapsed / self.brightness_transition_duration
                self.current_brightness_int = int(self.brightness_start + (self.brightness_target - self.brightness_start) * t)
                brightness = self.current_brightness_int * 0.01
        elif self.led_mode == 'active':
            # 活动模式：恒定最大亮度
            brightness = BREATHE_MAX_BRIGHTNESS
        else:
            # 停顿模式：呼吸灯效果
            delta_int = int(time_delta * 200)
            self.current_brightness_int += self.brightness_direction * delta_int
            
            if self.current_brightness_int >= 100:
                self.current_brightness_int = 100
                self.brightness_direction = -1
            elif self.current_brightness_int <= 10:
                self.current_brightness_int = 10
                self.brightness_direction = 1
            
            brightness = self.current_brightness_int * 0.01
        
        # 3. 应用到LED（仅在变化时更新）
        needs_update = False
        
        # 检查亮度变化
        if abs(self.pixels.brightness - brightness) > 0.01:
            self.pixels.brightness = brightness
            needs_update = True
        
        # 检查颜色变化
        if display_color != getattr(self, '_last_color', None):
            self.pixels.fill(display_color)
            self._last_color = display_color
            needs_update = True
        
        # 仅在有变化时更新硬件
        if needs_update:
            self.pixels.show()
    

    
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
    
    def set_mode(self, mode):
        """设置LED模式：'active' 活动中 / 'idle' 停顿中"""
        if mode == 'active' and self.led_mode == 'idle':
            # 从停顿切换到活动：启动亮度过渡到最大亮度
            self.brightness_start = self.current_brightness_int
            self.brightness_target = 100
            self.brightness_transition_active = True
            self.brightness_transition_start = time.monotonic()
        
        self.led_mode = mode
    
    def set_next_color(self, mode_name):
        """设置下一个模式的颜色（启动颜色过渡）"""
        # 记录模式切换
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_mode_switch(mode_name)
        
        color = self.get_mode_color(mode_name)
        
        # 启动颜色过渡
        if color != self.target_color:
            self.target_color = color
            self.color_transition_active = True
            self.color_transition_start = time.monotonic()
        
        return color
    