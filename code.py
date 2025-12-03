import time
import usb_hid
import random
from adafruit_hid.mouse import Mouse
import board
import neopixel

# Initialize the Mouse object
mouse = Mouse(usb_hid.devices)

# Initialize the WS2812 LED on GP16
pixel_pin = board.GP16
num_pixels = 1
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=True)

# 定义不同模式的颜色
WEB_BROWSING_COLOR = (0, 255, 0)    # 绿色 - 网页浏览
PAGE_SCANNING_COLOR = (0, 0, 255)   # 蓝色 - 页面扫描
EXPLORATORY_COLOR = (255, 255, 0)   # 青色 - 探索性移动

# 呼吸灯相关参数
BREATHE_MIN_BRIGHTNESS = 0.05  # 最小亮度，确保LED不会完全熄灭
BREATHE_MAX_BRIGHTNESS = 0.3   # 最大亮度

# 事件循环相关变量
last_time = time.monotonic()
current_brightness = BREATHE_MAX_BRIGHTNESS
brightness_direction = -0.01  # 亮度变化方向
transition_start_time = None
transition_duration = 0

def set_led_color_with_brightness(color, brightness):
    """
    设置LED颜色和亮度
    """
    pixels.brightness = brightness
    pixels.fill(color)
    pixels.show()

def update_breathing_led(color):
    """
    非阻塞更新呼吸灯效果
    """
    global current_brightness, brightness_direction, last_time
    
    current_time = time.monotonic()
    # 使用较小的时间增量以获得更平滑的效果
    time_delta = min(current_time - last_time, 0.1)  # 限制时间增量以避免大的跳跃
    last_time = current_time
    
    # 更新亮度
    current_brightness += brightness_direction * (time_delta / 0.05)  # 调整变化速度
    
    # 反转方向如果达到边界
    if current_brightness >= BREATHE_MAX_BRIGHTNESS:
        current_brightness = BREATHE_MAX_BRIGHTNESS
        brightness_direction = -abs(brightness_direction)
    elif current_brightness <= BREATHE_MIN_BRIGHTNESS:
        current_brightness = BREATHE_MIN_BRIGHTNESS
        brightness_direction = abs(brightness_direction)
    
    set_led_color_with_brightness(color, current_brightness)

def start_transition_timer(duration):
    """
    启动过渡计时器
    """
    global transition_start_time, transition_duration
    transition_start_time = time.monotonic()
    transition_duration = duration

def is_transition_complete():
    """
    检查过渡是否完成
    """
    global transition_start_time, transition_duration
    if transition_start_time is None:
        return True
    return time.monotonic() - transition_start_time >= transition_duration

# 鼠标移动状态类，用于非阻塞操作
class MouseMover:
    def __init__(self):
        self.active = False
        self.current_step = 0
        self.total_steps = 0
        self.step_x = 0
        self.step_y = 0
        self.start_time = 0
        self.move_duration = 0
        self.small_move_steps = []
        self.small_move_index = 0

    def quick_move_to_target(self, end_x, end_y, duration_factor=0.02):
        """
        非阻塞快速移动鼠标到目标位置
        """
        distance = ((end_x - 0) ** 2 + (end_y - 0) ** 2) ** 0.5
        self.total_steps = max(int(distance / 20), 1)
        self.step_x = end_x / self.total_steps
        self.step_y = end_y / self.total_steps
        self.current_step = 0
        self.active = True
        self.start_time = time.monotonic()
        self.move_duration = duration_factor  # 总移动时间

    def smooth_move_small(self, start_x, start_y, end_x, end_y, duration_factor=0.1):
        """
        非阻塞在小范围内平滑移动鼠标
        """
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        steps = max(int(distance / 2), 5)
        step_x = (end_x - start_x) / steps
        step_y = (end_y - start_y) / steps

        # 创建小移动步骤列表
        self.small_move_steps = []
        for i in range(steps):
            offset_x = random.uniform(-0.5, 0.5)
            offset_y = random.uniform(-0.5, 0.5)
            actual_x = step_x + offset_x
            actual_y = step_y + offset_y
            self.small_move_steps.append((int(actual_x), int(actual_y)))
        self.small_move_index = 0
        self.active = True

    def update(self):
        """
        更新鼠标移动状态，非阻塞
        """
        if not self.active:
            return True  # 如果未激活，返回True表示已完成

        # 根据移动类型决定如何更新
        if self.small_move_steps:  # 平滑小移动
            if self.small_move_index < len(self.small_move_steps):
                x, y = self.small_move_steps[self.small_move_index]
                mouse.move(x=x, y=y)
                self.small_move_index += 1
                # 不再使用time.sleep，而是返回表示未完成
                return False  # 未完成
            else:
                self.small_move_steps = []
                self.active = False
                return True  # 完成
        else:  # 快速移动
            if self.current_step < self.total_steps:
                mouse.move(x=int(self.step_x), y=int(self.step_y))
                self.current_step += 1
                # 不再使用time.sleep，而是返回表示未完成
                return False  # 未完成
            else:
                self.active = False
                return True  # 完成

# 创建鼠标移动器实例
mouse_mover = MouseMover()

# 非阻塞模拟函数
def start_web_browsing():
    """
    启动网页浏览模拟
    """
    target_x = random.randint(-200, 200)
    target_y = random.randint(-200, 200)
    mouse_mover.quick_move_to_target(target_x, target_y)
    return {"target_x": target_x, "target_y": target_y, "small_moves_left": random.randint(4, 8), "current_x": target_x, "current_y": target_y}

def start_page_scanning():
    """
    启动页面扫描模拟
    """
    start_x = random.randint(-180, -120)
    start_y = random.randint(-180, 180)
    mouse_mover.quick_move_to_target(start_x, start_y)
    end_x = random.randint(120, 180)
    distance = end_x - start_x
    steps = max(int(distance / 15), 1)
    step_x = distance / steps
    return {"start_x": start_x, "start_y": start_y, "end_x": end_x, "distance": distance, "steps": steps, "step_x": step_x, "current_step": 0}

def start_exploratory_movement():
    """
    启动探索性移动模拟
    """
    target_x = random.randint(-180, 180)
    target_y = random.randint(-180, 180)
    mouse_mover.quick_move_to_target(target_x, target_y)
    return {"target_x": target_x, "target_y": target_y, "exploratory_moves_left": random.randint(3, 6), "current_x": target_x, "current_y": target_y}

def update_web_browsing(state):
    """
    更新网页浏览模拟，非阻塞
    """
    if mouse_mover.active:
        # 如果鼠标正在移动，更新移动状态
        mouse_mover.update()
        # 不管是否完成，都返回False，等待下一次调用
        return False  # 未完成
    elif state["small_moves_left"] > 0:
        # 开始下一个小范围移动
        small_move_x = random.randint(-25, 25)
        small_move_y = random.randint(-25, 25)
        mouse_mover.smooth_move_small(state["current_x"], state["current_y"], state["current_x"] + small_move_x, state["current_y"] + small_move_y)
        state["current_x"] += small_move_x
        state["current_y"] += small_move_y
        state["small_moves_left"] -= 1
        return False  # 未完成
    else:
        return True  # 完成

def update_page_scanning(state):
    """
    更新页面扫描模拟，非阻塞
    """
    if mouse_mover.active:
        # 如果鼠标正在移动到起始点，更新移动状态
        mouse_mover.update()
        return False  # 未完成
    elif state["current_step"] < state["steps"]:
        # 继续水平扫描
        mouse.move(x=int(state["step_x"]), y=0)
        state["current_step"] += 1
        return False  # 未完成
    else:
        return True  # 完成

def update_exploratory_movement(state):
    """
    更新探索性移动模拟，非阻塞
    """
    if mouse_mover.active:
        # 如果鼠标正在移动，更新移动状态
        mouse_mover.update()
        # 不管是否完成，都返回False，等待下一次调用
        return False  # 未完成
    elif state["exploratory_moves_left"] > 0:
        # 开始下一个探索移动
        direction_x = random.randint(-40, 40)
        direction_y = random.randint(-40, 40)
        mouse_mover.smooth_move_small(state["current_x"], state["current_y"], state["current_x"] + direction_x, state["current_y"] + direction_y)
        state["current_x"] += direction_x
        state["current_y"] += direction_y
        state["exploratory_moves_left"] -= 1
        return False  # 未完成
    else:
        return True  # 完成

# 全局变量来跟踪当前模式和LED状态
current_mode = None
led_mode_color = (0, 0, 0)  # 初始为关闭状态
current_state = None
mode_start_time = 0
mode_duration = 0
post_mode_wait_time = 0
post_mode_wait_duration = 0
breathing_active = False
breathing_start_time = 0
breathing_duration = 0

def update_led_for_mode(mode, is_active=True):
    """
    根据当前模式更新LED状态
    """
    global current_mode, led_mode_color
    current_mode = mode
    
    if is_active:
        if mode == "web_browsing":
            led_mode_color = WEB_BROWSING_COLOR
        elif mode == "page_scanning":
            led_mode_color = PAGE_SCANNING_COLOR
        elif mode == "exploratory_move":
            led_mode_color = EXPLORATORY_COLOR
        # 设置为正常亮度
        set_led_color_with_brightness(led_mode_color, BREATHE_MAX_BRIGHTNESS)
    else:
        # 设置为低亮度
        set_led_color_with_brightness(led_mode_color, BREATHE_MIN_BRIGHTNESS)

def start_breathing_led(duration=1.0):
    """
    启动呼吸灯效果
    """
    global breathing_active, breathing_start_time, breathing_duration
    breathing_active = True
    breathing_start_time = time.monotonic()
    breathing_duration = duration

def update_breathing_led_task():
    """
    更新呼吸灯任务
    """
    global breathing_active
    if breathing_active:
        update_breathing_led(led_mode_color)
        if time.monotonic() - breathing_start_time >= breathing_duration:
            breathing_active = False

def check_and_start_next_mode():
    """
    检查并启动下一个模式
    """
    global current_mode, current_state, mode_start_time, mode_duration, post_mode_wait_time, post_mode_wait_duration, led_mode_color
    
    # 随机选择一种浏览行为
    action = random.choice([
        "web_browsing",     # 网页浏览漫游
        "page_scanning",    # 页面扫描
        "exploratory_move"  # 探索性移动
    ])
    
    # 更新LED以反映当前模式
    update_led_for_mode(action, True)
    current_mode = action
    
    # 根据模式启动相应的模拟
    if action == "web_browsing":
        current_state = start_web_browsing()
    elif action == "page_scanning":
        current_state = start_page_scanning()
    elif action == "exploratory_move":
        current_state = start_exploratory_movement()
    
    mode_start_time = time.monotonic()
    # 设置一个合理的模式持续时间
    mode_duration = random.uniform(2, 5)

# 初始化第一个模式
check_and_start_next_mode()

# 主事件循环
last_update_time = time.monotonic()

while True:
    current_time = time.monotonic()
    
    # 限制更新频率，避免过度占用CPU
    if current_time - last_update_time >= 0.01:  # 每10ms更新一次
        last_update_time = current_time
        
        # 更新呼吸灯效果
        if not breathing_active and current_mode:
            update_breathing_led(led_mode_color)
        
        # 根据当前模式更新模拟状态
        if current_mode == "web_browsing" and current_state:
            if update_web_browsing(current_state):
                # 模式完成，设置等待时间
                update_led_for_mode(current_mode, False)
                post_mode_wait_time = current_time
                post_mode_wait_duration = random.uniform(1, 3)
                current_mode = None
        elif current_mode == "page_scanning" and current_state:
            if update_page_scanning(current_state):
                # 模式完成，设置等待时间
                update_led_for_mode(current_mode, False)
                post_mode_wait_time = current_time
                post_mode_wait_duration = random.uniform(1, 3)
                current_mode = None
        elif current_mode == "exploratory_move" and current_state:
            if update_exploratory_movement(current_state):
                # 模式完成，设置等待时间
                update_led_for_mode(current_mode, False)
                post_mode_wait_time = current_time
                post_mode_wait_duration = random.uniform(1, 3)
                current_mode = None
        
        # 检查是否需要启动新模式
        if current_mode is None and current_time - post_mode_wait_time >= post_mode_wait_duration:
            check_and_start_next_mode()
            # 启动短暂的呼吸灯效果以示活跃
            start_breathing_led(0.5)
        
        # 更新呼吸灯任务（如果活动）
        update_breathing_led_task()