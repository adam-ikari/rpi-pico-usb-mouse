"""
主应用类
管理所有组件和全局状态，替代使用全局变量的方式
"""

import time
from constants import *
from performance_stats import PerformanceStats
from mouse_mover import MouseMover
from led_controller import LEDController
from movement_modes import ModeFactory
from random_generator import weighted_mode_selector, random_pool


class MouseContext:
    """鼠标上下文管理类"""
    
    def __init__(self):
        self.current_mode = None
        self.led_mode_color = (0, 0, 0)
        self.current_state = None
        self.mode_start_time = 0
        self.mode_duration = 0
        self.post_mode_wait_time = 0
        self.post_mode_wait_duration = 0
        self.breathing_active = False
        self.breathing_start_time = 0
        self.breathing_duration = 0
        self.last_movement_time = time.monotonic()
        self.movement_interval = random_pool.uniform(0.5, 3.0)


class MouseSimulatorApp:
    """鼠标模拟器主应用类"""
    
    def __init__(self, mouse_device, pixels, enable_performance_stats=False):
        """初始化应用"""
        # 初始化核心组件
        self.mouse = mouse_device
        self.pixels = pixels
        
        # 初始化性能统计
        self.perf_stats = PerformanceStats(enable_stats=enable_performance_stats)
        
        # 初始化鼠标移动器
        self.mouse_mover = MouseMover(mouse_device, self.perf_stats)
        
        # 初始化LED控制器
        self.led_controller = LEDController(pixels, self.perf_stats)
        
        # 初始化上下文
        self.context = MouseContext()
        self.context.perf_stats = self.perf_stats
        
        # 可用模式列表
        self.available_modes = [
            "web_browsing",
            "page_scanning", 
            "exploratory_move",
            "random_movement",
            "circular_move",
            "target_focus"
        ]
        
        # 当前模式实例
        self.current_mode_instance = None
        
        # 打印启动信息
        print("=== Mouse Movement Simulator ===")
        print("Starting mouse movement simulation...")
        print("================================")
    
    def start_next_mode(self, mode_name=None):
        """启动下一个模式"""
        # 如果没有指定模式，则随机选择
        if mode_name is None:
            mode_name = weighted_mode_selector.choice()
        
        # 输出模式切换日志
        print(f"[Mode] Starting: {mode_name}")
        
        # 设置LED为活动模式（恒定亮度）
        self.led_controller.set_mode('active')
        self.context.led_mode_color = self.led_controller.set_next_color(mode_name)
        self.context.current_mode = mode_name
        
        # 创建模式实例
        self.current_mode_instance = ModeFactory.create_mode(
            mode_name, 
            self.mouse_mover, 
            self.perf_stats
        )
        
        # 启动模式
        self.context.current_state = self.current_mode_instance.start()
        
        self.context.mode_start_time = time.monotonic()
        self.context.mode_duration = random_pool.uniform(MODE_DURATION_MIN, MODE_DURATION_MAX)
        
        # 重置等待时间
        self.context.post_mode_wait_time = 0
    
    def update(self):
        """更新应用状态"""
        current_time = time.monotonic()
        
        # 更新性能统计
        self.perf_stats.record_loop()
        self.perf_stats.update_memory_stats()
        
        # 定期打印性能报告
        if self.perf_stats.should_report(PERFORMANCE_REPORT_INTERVAL):
            self.perf_stats.print_report()
        
        # 更新LED效果（活动时恒定亮度，停顿时呼吸灯）
        if not self.context.breathing_active:
            self.led_controller.update()
        
        # 更新当前模式
        if self.context.current_mode and self.context.current_state and self.current_mode_instance:
            if self.current_mode_instance.update(self.context.current_state):
                # 模式完成，设置等待时间并预告下一个模式
                self.context.post_mode_wait_time = current_time
                
                wait_min, wait_max = self.current_mode_instance.get_wait_time_range()
                self.context.post_mode_wait_duration = random_pool.uniform(wait_min, wait_max)
                
                # 立即选择下一个模式（但不启动颜色过渡）
                next_mode_name = weighted_mode_selector.choice()
                self.context.next_mode = next_mode_name
                self.context.color_transition_started = False  # 标记颜色过渡未开始
                print(f"[Mode] Next: {next_mode_name} (waiting {self.context.post_mode_wait_duration:.1f}s)")
                
                # 设置LED为停顿模式（呼吸灯）
                self.led_controller.set_mode('idle')
                
                self.context.current_mode = None
                self.current_mode_instance = None
        
        # 在停顿时间过半时启动颜色过渡
        if (self.context.current_mode is None and 
            hasattr(self.context, 'next_mode') and
            not self.context.color_transition_started and
            self.context.post_mode_wait_time > 0):
            elapsed = current_time - self.context.post_mode_wait_time
            if elapsed >= self.context.post_mode_wait_duration / 2:
                # 启动颜色过渡
                self.led_controller.set_next_color(self.context.next_mode)
                self.context.color_transition_started = True
                print(f"[LED] Color transition started -> {self.context.next_mode}")
        
        # 检查是否需要启动新模式
        if (self.context.current_mode is None and 
            hasattr(self.context, 'next_mode') and
            self.context.post_mode_wait_time > 0 and
            current_time - self.context.post_mode_wait_time >= self.context.post_mode_wait_duration):
            # 启动之前预告的模式
            self.start_next_mode(self.context.next_mode)
            delattr(self.context, 'next_mode')
            # 启动短暂的呼吸灯效果以示活跃
            self.start_breathing_led(0.5)
        
        # 更新呼吸灯任务（如果活动）
        self.update_breathing_led()
    
    def start_breathing_led(self, duration=1.0):
        """启动呼吸灯效果"""
        self.context.breathing_active = True
        self.context.breathing_start_time = time.monotonic()
        self.context.breathing_duration = duration
    
    def update_breathing_led(self):
        """更新呼吸灯任务"""
        if self.context.breathing_active:
            self.led_controller.update()
            if time.monotonic() - self.context.breathing_start_time >= self.context.breathing_duration:
                self.context.breathing_active = False
    
    def run(self):
        """运行主循环"""
        try:
            # 启动第一个模式
            self.start_next_mode()
            
            # 主事件循环
            last_update_time = time.monotonic()
            
            while True:
                current_time = time.monotonic()
                
                # 限制更新频率，避免过度占用CPU
                if current_time - last_update_time >= UPDATE_INTERVAL:
                    last_update_time = current_time
                    self.update()
        
        except KeyboardInterrupt:
            # 用户中断（Ctrl+C），正常退出
            print("Program interrupted by user")
            self.pixels.fill((0, 0, 0))
            self.pixels.show()
        except OSError as e:
            # USB 设备错误或其他 I/O 错误
            print(f"USB/IO error: {e}")
            # 闪烁红色 LED 指示错误
            for _ in range(10):
                self.pixels.fill((255, 0, 0))
                self.pixels.show()
                time.sleep(0.2)
                self.pixels.fill((0, 0, 0))
                self.pixels.show()
                time.sleep(0.2)
        except Exception as e:
            # 打印错误信息
            print(f"Unknown error: {e}")
            print("Error type:", type(e).__name__)
            print("Error args:", e.args)
            
            # 输出调用栈
            import sys
            print("Call stack:")
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if exc_traceback:
                    tb = exc_traceback
                    while tb:
                        print(f"  File \"{tb.tb_frame.f_code.co_filename}\", line {tb.tb_lineno}, in {tb.tb_frame.f_code.co_name}")
                        tb = tb.tb_next
            except:
                print("  Unable to get traceback")
            
            # 快速闪烁红色 LED 指示严重错误
            for _ in range(20):
                self.pixels.fill((255, 0, 0))
                self.pixels.show()
                time.sleep(0.1)
                self.pixels.fill((0, 0, 0))
                self.pixels.show()
                time.sleep(0.1)