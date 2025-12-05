import time
import usb_hid
import random
import math
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
RANDOM_MOVEMENT_COLOR = (255, 0, 255)  # 紫色 - 随机移动
CIRCULAR_MOVEMENT_COLOR = (255, 165, 0)  # 橙色 - 圆形移动
TARGET_FOCUS_COLOR = (255, 0, 0)    # 红色 - 目标聚焦

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
        self.velocity_profile = []  # 速度变化曲线

    def quick_move_to_target(self, end_x, end_y, duration_factor=0.02):
        """
        非阻塞快速移动鼠标到目标位置，更自然的人类移动模式
        实现加速-匀速-减速的人类移动模式
        """
        distance = ((end_x - 0) ** 2 + (end_y - 0) ** 2) ** 0.5
        if distance == 0:
            return  # 如果距离为0，直接返回

        # 基于距离计算步数，但增加一些随机性
        base_steps = max(int(distance / 10), 5)  # 增加步数以实现更平滑的加速/减速
        self.total_steps = int(base_steps * random.uniform(0.8, 1.2))  # 增加路径长度的变化
        
        # 创建速度变化曲线：加速-匀速-减速
        self.velocity_profile = self._create_velocity_profile(self.total_steps)
        
        # 计算每步的移动量
        self.step_x = end_x / self.total_steps
        self.step_y = end_y / self.total_steps
        self.current_step = 0
        self.active = True
        self.start_time = time.monotonic()
        self.move_duration = duration_factor  # 总移动时间

    def _create_velocity_profile(self, total_steps):
        """
        创建速度变化曲线，模拟人类移动的加速-匀速-减速模式
        """
        # 将移动分为三个阶段：加速、匀速、减速
        accel_steps = max(1, int(total_steps * 0.3))  # 加速阶段占30%
        decel_steps = max(1, int(total_steps * 0.3))  # 减速阶段占30%
        const_steps = total_steps - accel_steps - decel_steps  # 匀速阶段
        
        profile = []
        
        # 加速阶段
        for i in range(accel_steps):
            # 从0.3加速到1.0，使用平方函数使加速更自然
            factor = 0.3 + 0.7 * (i / accel_steps) ** 2
            profile.append(factor)
        
        # 匀速阶段
        for i in range(const_steps):
            profile.append(1.0 + random.uniform(-0.1, 0.1))  # 稍微变化以模拟手部微小抖动
        
        # 减速阶段
        for i in range(decel_steps):
            # 从1.0减速到0.2，使用平方函数使减速更自然
            factor = 1.0 - 0.8 * (i / decel_steps) ** 2
            profile.append(max(0.2, factor))  # 确保不低于0.2
        
        return profile

    def smooth_move_small(self, start_x, start_y, end_x, end_y, duration_factor=0.1):
        """
        非阻塞在小范围内平滑移动鼠标，更自然的人类移动模式
        包含加速-匀速-减速和随机速度变化
        """
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        if distance == 0:
            return  # 如果距离为0，直接返回

        # 增加更多步骤以实现更自然的曲线移动
        base_steps = max(int(distance / 2), 5)
        steps = int(base_steps * random.uniform(1.5, 2.5))  # 增加路径长度，模拟人类的不精确移动
        
        # 创建速度变化曲线
        velocity_profile = self._create_velocity_profile(steps)
        
        # 创建小移动步骤列表，模拟人类移动的不规则性
        self.small_move_steps = []
        cumulative_x, cumulative_y = 0, 0  # 累计偏移，确保最终到达目标点
        
        for i in range(steps):
            # 基础移动量
            base_x = (end_x - start_x) / steps
            base_y = (end_y - start_y) / steps
            
            # 应用速度变化
            velocity_factor = velocity_profile[i] if i < len(velocity_profile) else 1.0
            
            # 添加速度变化
            actual_x = base_x * velocity_factor
            actual_y = base_y * velocity_factor
            
            # 添加更多的随机偏移，模拟人类手部微小抖动
            offset_x = random.uniform(-0.8, 0.8) * velocity_factor
            offset_y = random.uniform(-0.8, 0.8) * velocity_factor
            actual_x += offset_x
            actual_y += offset_y
            
            # 每隔几步骤添加一个稍大的偏移，模拟人类调整方向
            if i % random.randint(5, 10) == 0:
                actual_x += random.uniform(-1.5, 1.5)
                actual_y += random.uniform(-1.5, 1.5)
            
            # 偶尔加入停顿，模拟人类思考
            if random.random() < 0.05:  # 5%概率停顿
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
        else:  # 快速移动 - 现在使用速度变化曲线
            if self.current_step < self.total_steps:
                # 根据速度曲线应用移动
                velocity_factor = self.velocity_profile[self.current_step] if self.current_step < len(self.velocity_profile) else 1.0
                x_move = int(self.step_x * velocity_factor)
                y_move = int(self.step_y * velocity_factor)
                mouse.move(x=x_move, y=y_move)
                self.current_step += 1
                # 不再使用time.sleep，而是返回表示未完成
                return False  # 未完成
            else:
                self.velocity_profile = []  # 清空速度曲线
                self.active = False
                return True  # 完成

# 创建鼠标移动器实例
mouse_mover = MouseMover()

def init_context():
    """
    初始化上下文并启动第一个模式
    """
    context = MouseContext()
    check_and_start_next_mode(context)
    return context

# 非阻塞模拟函数
def start_web_browsing():
    """
    启动网页浏览模拟，更自然的人类行为
    """
    # 生成更小范围的目标位置，模拟真实网页浏览
    target_x = random.randint(-150, 150)
    target_y = random.randint(-150, 150)
    mouse_mover.quick_move_to_target(target_x, target_y)
    # 增加小范围移动次数，模拟更真实的阅读行为
    return {"target_x": target_x, "target_y": target_y, "small_moves_left": random.randint(6, 12), "current_x": target_x, "current_y": target_y, "time_at_location": 0, "total_time_at_location": random.uniform(2.0, 5.0)}

def start_page_scanning():
    """
    启动页面扫描模拟，更自然的人类行为
    """
    # 从屏幕左侧开始，模拟真实页面扫描
    start_x = random.randint(-200, -100)
    start_y = random.randint(-150, 150)
    mouse_mover.quick_move_to_target(start_x, start_y)
    # 移动到屏幕右侧，但随机化终点
    end_x = random.randint(100, 200)
    distance = end_x - start_x
    # 增加更多步骤，模拟人类阅读时的不规则移动
    steps = max(int(distance / 8), 5)  # 增加步数，模拟更细致的扫描
    step_x = distance / steps
    return {"start_x": start_x, "start_y": start_y, "end_x": end_x, "distance": distance, "steps": steps, "step_x": step_x, "current_step": 0, "current_y_offset": start_y, "scan_time": 0, "total_scan_time": random.uniform(3.0, 6.0)}

def start_exploratory_movement():
    """
    启动探索性移动模拟，更自然的人类行为
    """
    target_x = random.randint(-180, 180)
    target_y = random.randint(-180, 180)
    mouse_mover.quick_move_to_target(target_x, target_y)
    # 增加探索性移动次数，让人行为更自然
    return {"target_x": target_x, "target_y": target_y, "exploratory_moves_left": random.randint(5, 10), "current_x": target_x, "current_y": target_y, "time_at_exploration": 0, "total_time_at_exploration": random.uniform(2.5, 5.0)}

def update_web_browsing(state):
    """
    更新网页浏览模拟，非阻塞，更自然的人类行为
    """
    current_time = time.monotonic()
    if mouse_mover.active:
        # 如果鼠标正在移动，更新移动状态
        mouse_mover.update()
        return False  # 未完成
    elif state["small_moves_left"] > 0:
        # 开始下一个小范围移动，更小的范围以模拟真实的鼠标操作
        small_move_x = random.randint(-15, 15)
        small_move_y = random.randint(-15, 15)
        mouse_mover.smooth_move_small(state["current_x"], state["current_y"], state["current_x"] + small_move_x, state["current_y"] + small_move_y)
        state["current_x"] += small_move_x
        state["current_y"] += small_move_y
        state["small_moves_left"] -= 1
        return False  # 未完成
    elif state["time_at_location"] < state["total_time_at_location"]:
        # 在当前位置停留一段时间，模拟阅读或思考
        if "start_time" not in state:
            state["start_time"] = current_time
        state["time_at_location"] = current_time - state["start_time"]
        return False  # 未完成
    else:
        return True  # 完成

def update_page_scanning(state):
    """
    更新页面扫描模拟，非阻塞，更自然的人类行为
    """
    current_time = time.monotonic()
    if mouse_mover.active:
        # 如果鼠标正在移动到起始点，更新移动状态
        mouse_mover.update()
        return False  # 未完成
    elif state["current_step"] < state["steps"]:
        # 水平扫描，但加入垂直方向的轻微随机移动，模拟人类阅读时的不规则性
        x_move = int(state["step_x"])
        # 添加轻微的垂直偏移，模拟人类阅读时视线的微小变化
        y_offset = random.randint(-3, 3)
        
        # 模拟人类阅读时的非匀速移动：有时快有时慢，偶尔停顿
        if state["current_step"] % random.randint(6, 12) == 0:
            # 随机决定是否停顿或放慢速度
            pause_or_slow = random.choice(["pause", "slow", "normal"])
            if pause_or_slow == "pause":
                # 添加停顿，模拟阅读文字
                return False  # 刻意不移动，模拟停顿
            elif pause_or_slow == "slow":
                # 减慢移动速度
                x_move = int(x_move * 0.5)
                y_offset = int(y_offset * 0.5)
        elif state["current_step"] % random.randint(3, 6) == 0:
            # 偶尔加速（移动稍大距离）
            x_move = int(x_move * 1.5)
            y_offset = int(y_offset * 1.5)
        
        mouse.move(x=x_move, y=y_offset)
        state["current_step"] += 1
        return False  # 未完成
    elif state["scan_time"] < state["total_scan_time"]:
        # 扫描完成后在结尾处停留一段时间
        if "scan_start_time" not in state:
            state["scan_start_time"] = current_time
        state["scan_time"] = current_time - state["scan_start_time"]
        return False  # 未完成
    else:
        return True  # 完成

def update_exploratory_movement(state):
    """
    更新探索性移动模拟，非阻塞，更自然的人类行为
    """
    current_time = time.monotonic()
    if mouse_mover.active:
        # 如果鼠标正在移动，更新移动状态
        mouse_mover.update()
        return False  # 未完成
    elif state["exploratory_moves_left"] > 0:
        # 开始下一个探索移动，使用更小的移动范围，更像人类操作
        direction_x = random.randint(-25, 25)
        direction_y = random.randint(-25, 25)
        mouse_mover.smooth_move_small(state["current_x"], state["current_y"], state["current_x"] + direction_x, state["current_y"] + direction_y)
        state["current_x"] += direction_x
        state["current_y"] += direction_y
        state["exploratory_moves_left"] -= 1
        return False  # 未完成
    elif state["time_at_exploration"] < state["total_time_at_exploration"]:
        # 在探索完成后停留一段时间，模拟人类的观察行为
        if "exploration_start_time" not in state:
            state["exploration_start_time"] = current_time
        state["time_at_exploration"] = current_time - state["exploration_start_time"]
        return False  # 未完成
    else:
        return True  # 完成

def start_random_movement():
    """
    启动随机移动模式，模拟人类随意移动鼠标的行为
    """
    target_x = random.randint(-200, 200)
    target_y = random.randint(-200, 200)
    mouse_mover.quick_move_to_target(target_x, target_y)
    return {
        "target_x": target_x, 
        "target_y": target_y, 
        "random_moves_left": random.randint(3, 8), 
        "current_x": target_x, 
        "current_y": target_y,
        "pause_time": 0,
        "total_pause_time": random.uniform(1.0, 4.0)
    }

def update_random_movement(state):
    """
    更新随机移动模式，非阻塞
    """
    current_time = time.monotonic()
    if mouse_mover.active:
        # 如果鼠标正在移动，更新移动状态
        mouse_mover.update()
        return False  # 未完成
    elif state["random_moves_left"] > 0:
        # 开始下一个随机移动
        direction_x = random.randint(-40, 40)
        direction_y = random.randint(-40, 40)
        mouse_mover.smooth_move_small(state["current_x"], state["current_y"], state["current_x"] + direction_x, state["current_y"] + direction_y)
        state["current_x"] += direction_x
        state["current_y"] += direction_y
        state["random_moves_left"] -= 1
        return False  # 未完成
    elif state["pause_time"] < state["total_pause_time"]:
        # 暂停一段时间，模拟人类行为
        if "pause_start_time" not in state:
            state["pause_start_time"] = current_time
        state["pause_time"] = current_time - state["pause_start_time"]
        return False  # 未完成
    else:
        return True  # 完成

def start_circular_movement():
    """
    启动圆形移动模式，模拟鼠标沿圆形轨迹移动
    """
    center_x = random.randint(-100, 100)
    center_y = random.randint(-100, 100)
    radius = random.randint(30, 80)
    start_angle = random.uniform(0, 2 * 3.14159)
    return {
        "center_x": center_x,
        "center_y": center_y,
        "radius": radius,
        "current_angle": start_angle,
        "angle_step": random.uniform(0.1, 0.3),
        "steps_completed": 0,
        "total_steps": random.randint(10, 20),
        "time_at_location": 0,
        "total_time_at_location": random.uniform(2.0, 5.0)
    }

def update_circular_movement(state):
    """
    更新圆形移动模式，非阻塞
    """
    current_time = time.monotonic()
    if state["steps_completed"] < state["total_steps"]:
        # 计算圆形轨迹上的下一个点
        new_x = int(state["center_x"] + state["radius"] * math.cos(state["current_angle"]))
        new_y = int(state["center_y"] + state["radius"] * math.sin(state["current_angle"]))
        
        # 初始化 prev_x 和 prev_y，如果是第一次移动
        if "prev_x" not in state or "prev_y" not in state:
            state["prev_x"] = new_x
            state["prev_y"] = new_y
        
        # 移动到新位置
        actual_x = new_x - state["prev_x"]
        actual_y = new_y - state["prev_y"]
        
        mouse.move(x=actual_x, y=actual_y)
        
        # 更新状态
        state["prev_x"] = new_x
        state["prev_y"] = new_y
        state["current_angle"] += state["angle_step"]
        state["steps_completed"] += 1
        
        # 随机改变移动速度，模拟人类行为
        if random.random() < 0.3:  # 30% 概率改变速度
            state["angle_step"] = random.uniform(0.05, 0.4)
        
        return False  # 未完成
    elif state["time_at_location"] < state["total_time_at_location"]:
        # 在圆形移动完成后停留一段时间
        if "location_start_time" not in state:
            state["location_start_time"] = current_time
        state["time_at_location"] = current_time - state["location_start_time"]
        return False  # 未完成
    else:
        return True  # 完成

def start_target_focus():
    """
    启动目标聚焦模式，模拟用户专注于某个区域的行为
    """
    center_x = random.randint(-50, 50)
    center_y = random.randint(-50, 50)
    mouse_mover.quick_move_to_target(center_x, center_y)
    return {
        "center_x": center_x,
        "center_y": center_y,
        "focus_duration": 0,
        "total_focus_duration": random.uniform(3.0, 8.0),
        "micro_movements_left": random.randint(5, 15)
    }

def update_target_focus(state):
    """
    更新目标聚焦模式，非阻塞
    """
    current_time = time.monotonic()
    if mouse_mover.active:
        # 如果鼠标正在移动，更新移动状态
        mouse_mover.update()
        return False  # 未完成
    elif state["micro_movements_left"] > 0:
        # 在焦点区域内进行微小移动
        micro_x = random.randint(-8, 8)
        micro_y = random.randint(-8, 8)
        mouse.move(x=micro_x, y=micro_y)
        state["micro_movements_left"] -= 1
        return False  # 未完成
    elif state["focus_duration"] < state["total_focus_duration"]:
        # 在目标区域停留，偶尔进行微小移动
        if "focus_start_time" not in state:
            state["focus_start_time"] = current_time
        state["focus_duration"] = current_time - state["focus_start_time"]
        
        # 10% 概率进行微小移动
        if random.random() < 0.1:
            micro_x = random.randint(-3, 3)
            micro_y = random.randint(-3, 3)
            mouse.move(x=micro_x, y=micro_y)
        
        return False  # 未完成
    else:
        return True  # 完成

# 上下文管理类
class MouseContext:
    def __init__(self):
        self.current_mode = None
        self.led_mode_color = (0, 0, 0)  # 初始为关闭状态
        self.current_state = None
        self.mode_start_time = 0
        self.mode_duration = 0
        self.post_mode_wait_time = 0
        self.post_mode_wait_duration = 0
        self.breathing_active = False
        self.breathing_start_time = 0
        self.breathing_duration = 0

def update_led_for_mode(context, mode, is_active=True):
    """
    根据当前模式更新LED状态
    """
    context.current_mode = mode
    
    if is_active:
        if mode == "web_browsing":
            context.led_mode_color = WEB_BROWSING_COLOR
        elif mode == "page_scanning":
            context.led_mode_color = PAGE_SCANNING_COLOR
        elif mode == "exploratory_move":
            context.led_mode_color = EXPLORATORY_COLOR
        elif mode == "random_movement":
            context.led_mode_color = RANDOM_MOVEMENT_COLOR
        elif mode == "circular_move":
            context.led_mode_color = CIRCULAR_MOVEMENT_COLOR
        elif mode == "target_focus":
            context.led_mode_color = TARGET_FOCUS_COLOR
        # 设置为正常亮度
        set_led_color_with_brightness(context.led_mode_color, BREATHE_MAX_BRIGHTNESS)
    else:
        # 设置为低亮度
        set_led_color_with_brightness(context.led_mode_color, BREATHE_MIN_BRIGHTNESS)

def start_breathing_led(context, duration=1.0):
    """
    启动呼吸灯效果
    """
    context.breathing_active = True
    context.breathing_start_time = time.monotonic()
    context.breathing_duration = duration

def update_breathing_led_task(context):
    """
    更新呼吸灯任务
    """
    if context.breathing_active:
        update_breathing_led(context.led_mode_color)
        if time.monotonic() - context.breathing_start_time >= context.breathing_duration:
            context.breathing_active = False

def check_and_start_next_mode(context):
    """
    检查并启动下一个模式
    """
    # 随机选择一种浏览行为，降低模式切换的概率，让每个模式持续更长时间
    action = random.choice([
        "web_browsing",      # 网页浏览漫游
        "page_scanning",     # 页面扫描
        "exploratory_move",  # 探索性移动
        "random_movement",   # 随机移动
        "circular_move",     # 圆形移动
        "target_focus"       # 目标聚焦
    ])
    
    # 更新LED以反映当前模式
    update_led_for_mode(context, action, True)
    context.current_mode = action
    
    # 根据模式启动相应的模拟
    if action == "web_browsing":
        context.current_state = start_web_browsing()
    elif action == "page_scanning":
        context.current_state = start_page_scanning()
    elif action == "exploratory_move":
        context.current_state = start_exploratory_movement()
    elif action == "random_movement":
        context.current_state = start_random_movement()
    elif action == "circular_move":
        context.current_state = start_circular_movement()
    elif action == "target_focus":
        context.current_state = start_target_focus()
    
    context.mode_start_time = time.monotonic()
    # 设置一个更长的模式持续时间，降低切换频率
    context.mode_duration = random.uniform(5, 10)

# 初始化上下文
def main():
    # 初始化上下文
    context = init_context()

    # 主事件循环
    last_update_time = time.monotonic()

    while True:
        current_time = time.monotonic()
        
        # 限制更新频率，避免过度占用CPU
        if current_time - last_update_time >= 0.01:  # 每10ms更新一次
            last_update_time = current_time
            
            # 更新呼吸灯效果
            if not context.breathing_active and context.current_mode:
                update_breathing_led(context.led_mode_color)
            
            # 根据当前模式更新模拟状态
            if context.current_mode == "web_browsing" and context.current_state:
                if update_web_browsing(context.current_state):
                    # 模式完成，设置等待时间
                    update_led_for_mode(context, context.current_mode, False)
                    context.post_mode_wait_time = current_time
                    context.post_mode_wait_duration = random.uniform(3, 6)
                    context.current_mode = None
            elif context.current_mode == "page_scanning" and context.current_state:
                if update_page_scanning(context.current_state):
                    # 模式完成，设置等待时间
                    update_led_for_mode(context, context.current_mode, False)
                    context.post_mode_wait_time = current_time
                    context.post_mode_wait_duration = random.uniform(3, 6)
                    context.current_mode = None
            elif context.current_mode == "exploratory_move" and context.current_state:
                if update_exploratory_movement(context.current_state):
                    # 模式完成，设置等待时间
                    update_led_for_mode(context, context.current_mode, False)
                    context.post_mode_wait_time = current_time
                    context.post_mode_wait_duration = random.uniform(3, 6)
                    context.current_mode = None
            elif context.current_mode == "random_movement" and context.current_state:
                if update_random_movement(context.current_state):
                    # 模式完成，设置等待时间
                    update_led_for_mode(context, context.current_mode, False)
                    context.post_mode_wait_time = current_time
                    context.post_mode_wait_duration = random.uniform(2, 5)
                    context.current_mode = None
            elif context.current_mode == "circular_move" and context.current_state:
                if update_circular_movement(context.current_state):
                    # 模式完成，设置等待时间
                    update_led_for_mode(context, context.current_mode, False)
                    context.post_mode_wait_time = current_time
                    context.post_mode_wait_duration = random.uniform(2, 5)
                    context.current_mode = None
            elif context.current_mode == "target_focus" and context.current_state:
                if update_target_focus(context.current_state):
                    # 模式完成，设置等待时间
                    update_led_for_mode(context, context.current_mode, False)
                    context.post_mode_wait_time = current_time
                    context.post_mode_wait_duration = random.uniform(3, 6)
                    context.current_mode = None
            
            # 检查是否需要启动新模式
            if context.current_mode is None and current_time - context.post_mode_wait_time >= context.post_mode_wait_duration:
                check_and_start_next_mode(context)
                # 启动短暂的呼吸灯效果以示活跃
                start_breathing_led(context, 0.5)
            
            # 更新呼吸灯任务（如果活动）
            update_breathing_led_task(context)

# 启动主程序
if __name__ == "__main__":
    main()