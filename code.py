import time
import usb_hid
import random
import math
from adafruit_hid.mouse import Mouse
import board
import neopixel
from pin_config import LED_PIN
from constants import *
from performance_stats import PerformanceStats
from serial_control import SerialControl

ENABLE_PERFORMANCE_STATS = False

# 数学常量
PI = 3.141592653589793
DEG_TO_RAD = PI / 180.0  # 角度转弧度
RAD_TO_DEG = 180.0 / PI  # 弧度转角度

# Initialize the Mouse object
mouse = Mouse(usb_hid.devices)

# Initialize the WS2812 LED
pixel_pin = LED_PIN
num_pixels = NUM_PIXELS
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=DEFAULT_BRIGHTNESS, auto_write=True)

# 颜色和亮度常量已从 constants.py 导入，无需重复定义

# LED 控制器类（封装全局变量）
class LEDController:
    """LED 呼吸灯和颜色控制器"""
    def __init__(self, pixels):
        self.pixels = pixels
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
        
        self.current_brightness += self.brightness_direction * (time_delta / BRIGHTNESS_CHANGE_SPEED_FACTOR)
        
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

# ==================== 三角函数加速（查表法）====================

# 预计算 sin/cos 查找表（360度，每度一个值）
_SIN_LUT = []
_COS_LUT = []

def _init_trig_lut():
    """初始化三角函数查找表"""
    global _SIN_LUT, _COS_LUT
    if not _SIN_LUT:
        for i in range(360):
            angle_rad = i * DEG_TO_RAD
            _SIN_LUT.append(math.sin(angle_rad))
            _COS_LUT.append(math.cos(angle_rad))

_perf_stats_global = None

def _fast_sin_impl(angle_rad):
    """
    快速sin计算实现（查表法）
    angle_rad: 弧度值
    返回: sin值
    """
    if not _SIN_LUT:
        _init_trig_lut()
    
    # 将弧度转换为度数索引
    angle_deg = int((angle_rad * RAD_TO_DEG) % 360)
    return _SIN_LUT[angle_deg]

def fast_sin(angle_rad):
    """快速sin计算（带性能统计）"""
    if _perf_stats_global and _perf_stats_global.enable_stats:
        _perf_stats_global.record_trig_call()
    return _fast_sin_impl(angle_rad)

def _fast_cos_impl(angle_rad):
    """
    快速cos计算实现（查表法）
    angle_rad: 弧度值
    返回: cos值
    """
    if not _COS_LUT:
        _init_trig_lut()
    
    # 将弧度转换为度数索引
    angle_deg = int((angle_rad * RAD_TO_DEG) % 360)
    return _COS_LUT[angle_deg]

def fast_cos(angle_rad):
    """快速cos计算（带性能统计）"""
    if _perf_stats_global and _perf_stats_global.enable_stats:
        _perf_stats_global.record_trig_call()
    return _fast_cos_impl(angle_rad)

# ==================== 算法辅助函数 ====================

def smooth_noise_1d(x):
    """
    简化的一维Perlin噪声函数
    生成平滑的伪随机值，范围 [-1, 1]
    """
    integer_x = int(x)
    fractional_x = x - integer_x
    
    v1 = math.sin(integer_x * 12.9898 + 78.233) * 43758.5453
    v1 = v1 - int(v1)
    
    v2 = math.sin((integer_x + 1) * 12.9898 + 78.233) * 43758.5453
    v2 = v2 - int(v2)
    
    smooth = fractional_x * fractional_x * (3 - 2 * fractional_x)
    
    return (v1 * (1 - smooth) + v2 * smooth) * 2 - 1

def perlin_noise_2d(x, y, frequency=1.0):
    """
    二维Perlin噪声
    返回平滑的二维随机值
    """
    x_noise = smooth_noise_1d(x * frequency)
    y_noise = smooth_noise_1d(y * frequency + 100)
    return x_noise, y_noise

def quadratic_bezier(t, p0, p1, p2):
    """
    二次贝塞尔曲线计算（性能优化版）
    t: 参数 [0, 1]
    p0: 起点
    p1: 控制点
    p2: 终点
    
    公式: B(t) = (1-t)²*p0 + 2*(1-t)*t*p1 + t²*p2
    """
    u = 1 - t
    uu = u * u
    tt = t * t
    
    # 二次贝塞尔曲线公式
    p = uu * p0
    p += 2 * u * t * p1
    p += tt * p2
    
    return p

def calculate_bezier_point(step, total_steps, start_x, start_y, end_x, end_y, control_x, control_y):
    """
    函数式计算二次贝塞尔曲线上的单个点（零内存消耗，性能优化）
    根据当前步数实时计算，无需存储完整路径
    """
    if _perf_stats_global and _perf_stats_global.enable_stats:
        _perf_stats_global.record_bezier_calc()
    
    t = step / max(total_steps - 1, 1)
    x = quadratic_bezier(t, start_x, control_x, end_x)
    y = quadratic_bezier(t, start_y, control_y, end_y)
    return x, y

def generate_bezier_control_point(start_x, start_y, end_x, end_y):
    """
    生成二次贝塞尔曲线的控制点（仅需1个控制点）
    
    控制点位于起点和终点连线的中点附近，
    添加随机偏移以产生自然的曲线
    """
    dx = end_x - start_x
    dy = end_y - start_y
    
    # 控制点在中点位置，添加垂直方向的偏移
    mid_x = start_x + dx * 0.5
    mid_y = start_y + dy * 0.5
    
    # 添加随机偏移（垂直于连线方向）
    offset = random.uniform(-abs(dx + dy) * 0.2, abs(dx + dy) * 0.2)
    control_x = mid_x + offset
    control_y = mid_y + offset
    
    return control_x, control_y

def apply_wind_effect(x, y, time_offset, wind_strength=2.0):
    """
    应用风力效果，添加横向偏移
    """
    wind_x = smooth_noise_1d(time_offset * 0.5) * wind_strength
    wind_y = smooth_noise_1d(time_offset * 0.5 + 50) * wind_strength * 0.5
    return x + wind_x, y + wind_y

def apply_gravity_pull(current_x, current_y, target_x, target_y, strength=0.1):
    """
    应用重力效果，向目标点拉近
    """
    dx = target_x - current_x
    dy = target_y - current_y
    distance = math.sqrt(dx * dx + dy * dy)
    
    if distance > 0:
        pull_x = (dx / distance) * strength * distance
        pull_y = (dy / distance) * strength * distance
        return pull_x, pull_y
    return 0, 0

# ==================== LED 控制函数 ====================

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
        distance = math.sqrt(end_x * end_x + end_y * end_y)
        if distance == 0:
            return  # 如果距离为0，直接返回

        # 基于距离计算步数，但增加一些随机性
        base_steps = max(int(distance / BASE_STEP_DISTANCE), MIN_BASE_STEPS)  # 增加步数以实现更平滑的加速/减速
        self.total_steps = int(base_steps * random.uniform(DISTANCE_RANDOM_FACTOR_MIN, DISTANCE_RANDOM_FACTOR_MAX))  # 增加路径长度的变化
        
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
        accel_steps = max(1, int(total_steps * ACCEL_DECEL_PHASE_RATIO))  # 加速阶段占一定比例
        decel_steps = max(1, int(total_steps * ACCEL_DECEL_PHASE_RATIO))  # 减速阶段占一定比例
        const_steps = total_steps - accel_steps - decel_steps  # 匀速阶段
        
        profile = []
        
        # 加速阶段 - 更缓慢的加速
        for i in range(accel_steps):
            # 从ACCEL_START_FACTOR加速到ACCEL_END_FACTOR，使用更平缓的曲线
            t = i / accel_steps
            factor = ACCEL_START_FACTOR + (ACCEL_END_FACTOR - ACCEL_START_FACTOR) * t * t  # 使用平方函数使加速更平缓
            profile.append(factor)
        
        # 匀速阶段
        for i in range(const_steps):
            # 减少匀速阶段的速度波动
            profile.append(1.0 + random.uniform(CONSTANT_PHASE_MIN_VARIATION, CONSTANT_PHASE_MAX_VARIATION))
        
        # 减速阶段 - 更缓慢的减速
        for i in range(decel_steps):
            # 从DECEL_START_FACTOR减速到DECEL_END_FACTOR，使用更平缓的曲线
            t = i / decel_steps
            factor = DECEL_START_FACTOR - (DECEL_START_FACTOR - DECEL_END_FACTOR) * t * t  # 使用平方函数使减速更平缓
            profile.append(max(DECEL_MIN_FACTOR, factor))
        
        return profile

    def smooth_move_small(self, start_x, start_y, end_x, end_y, duration_factor=0.1):
        """
        非阻塞在小范围内平滑移动鼠标，更自然的人类移动模式
        包含加速-匀速-减速和随机速度变化
        """
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance == 0:
            return  # 如果距离为0，直接返回

        # 增加更多步骤以实现更自然的曲线移动
        base_steps = max(int(distance / SMALL_MOVE_BASE_DISTANCE), 5)
        steps = int(base_steps * random.uniform(SMALL_MOVE_DISTANCE_FACTOR_MIN, SMALL_MOVE_DISTANCE_FACTOR_MAX))
        
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
            
            # 添加更小的随机偏移，模拟人类手部微小抖动
            offset_x = random.uniform(SMALL_MOVE_OFFSET_MIN, SMALL_MOVE_OFFSET_MAX) * velocity_factor
            offset_y = random.uniform(SMALL_MOVE_OFFSET_MIN, SMALL_MOVE_OFFSET_MAX) * velocity_factor
            actual_x += offset_x
            actual_y += offset_y
            
            # 减少方向调整频率
            if i % random.randint(DIRECTION_ADJUST_INTERVAL_MIN, DIRECTION_ADJUST_INTERVAL_MAX) == 0 and i > 0:
                actual_x += random.uniform(LARGE_MOVE_OFFSET_MIN, LARGE_MOVE_OFFSET_MAX)
                actual_y += random.uniform(LARGE_MOVE_OFFSET_MIN, LARGE_MOVE_OFFSET_MAX)
            
            # 增加停顿概率，模拟人类思考
            if random.random() < THINK_PAUSE_PROBABILITY:
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

# 创建鼠标移动器和 LED 控制器实例
mouse_mover = MouseMover()
led_controller = LEDController(pixels)

def init_context():
    """
    初始化上下文并启动第一个模式
    """
    global _perf_stats_global
    perf_stats = PerformanceStats(enable_stats=ENABLE_PERFORMANCE_STATS)
    _perf_stats_global = perf_stats
    serial_control = SerialControl(perf_stats=perf_stats)
    context = MouseContext()
    context.perf_stats = perf_stats
    context.serial_control = serial_control
    check_and_start_next_mode(context)
    
    if serial_control.serial_available:
        print("=== Mouse Movement Simulator ===")
        print("Serial control enabled. Type 'help' for commands.")
        print("================================")
    
    return context

# 非阻塞模拟函数
def start_web_browsing():
    """
    启动网页浏览模拟，使用贝塞尔曲线（函数式计算，零路径存储）
    """
    target_x = random.randint(-WEB_BROWSE_X_RANGE_MAX, WEB_BROWSE_X_RANGE_MAX)
    target_y = random.randint(-WEB_BROWSE_Y_RANGE_MAX, WEB_BROWSE_Y_RANGE_MAX)
    
    distance = math.sqrt(target_x * target_x + target_y * target_y)
    total_steps = min(max(int(distance / 15), 15), 40)
    
    control_x, control_y = generate_bezier_control_point(0, 0, target_x, target_y)
    
    return {
        "start_x": 0,
        "start_y": 0,
        "target_x": target_x,
        "target_y": target_y,
        "control_x": control_x,
        "control_y": control_y,
        "current_step": 0,
        "total_steps": total_steps,
        "small_moves_left": random.randint(WEB_BROWSE_SMALL_MOVES_MIN, WEB_BROWSE_SMALL_MOVES_MAX),
        "current_x": 0,
        "current_y": 0,
        "time_at_location": 0,
        "total_time_at_location": random.uniform(WEB_BROWSE_STAY_TIME_MIN, WEB_BROWSE_STAY_TIME_MAX),
        "time_offset": time.monotonic()
    }

def start_page_scanning():
    """
    启动页面扫描模拟，使用风力算法模拟眼球跳动
    """
    start_x = random.randint(-PAGE_SCAN_START_X_MAX, -PAGE_SCAN_START_X_MIN)
    start_y = random.randint(-PAGE_SCAN_Y_RANGE_MAX, PAGE_SCAN_Y_RANGE_MAX)
    mouse_mover.quick_move_to_target(start_x, start_y)
    
    end_x = random.randint(PAGE_SCAN_END_X_MIN, PAGE_SCAN_END_X_MAX)
    distance = end_x - start_x
    steps = max(int(distance / SCAN_STEP_BASE_DISTANCE), PAGE_SCAN_STEPS_MIN)
    step_x = distance / steps
    
    return {
        "start_x": start_x,
        "start_y": start_y,
        "end_x": end_x,
        "distance": distance,
        "steps": steps,
        "step_x": step_x,
        "current_step": 0,
        "current_x": start_x,
        "current_y": start_y,
        "scan_time": 0,
        "total_scan_time": random.uniform(PAGE_SCAN_STAY_TIME_MIN, PAGE_SCAN_STAY_TIME_MAX),
        "time_offset": time.monotonic()
    }

def start_exploratory_movement():
    """
    启动探索性移动模拟，更自然的人类行为
    """
    target_x = random.randint(-EXPLORATORY_MOVE_RANGE_MAX, EXPLORATORY_MOVE_RANGE_MAX)
    target_y = random.randint(-EXPLORATORY_MOVE_RANGE_MAX, EXPLORATORY_MOVE_RANGE_MAX)
    mouse_mover.quick_move_to_target(target_x, target_y)
    # 增加探索性移动次数，让人行为更自然
    return {"target_x": target_x, "target_y": target_y, "exploratory_moves_left": random.randint(EXPLORATORY_MOVES_LEFT_MIN, EXPLORATORY_MOVES_LEFT_MAX), "current_x": target_x, "current_y": target_y, "time_at_exploration": 0, "total_time_at_exploration": random.uniform(EXPLORATORY_STAY_TIME_MIN, EXPLORATORY_STAY_TIME_MAX)}

def update_web_browsing(state):
    """
    更新网页浏览模拟，使用贝塞尔曲线（函数式实时计算）
    """
    current_time = time.monotonic()
    
    if state["current_step"] < state["total_steps"]:
        target_x, target_y = calculate_bezier_point(
            state["current_step"],
            state["total_steps"],
            state["start_x"],
            state["start_y"],
            state["target_x"],
            state["target_y"],
            state["control_x"],
            state["control_y"]
        )
        
        noise_x, noise_y = perlin_noise_2d(current_time - state["time_offset"], 0, 2.0)
        target_x += noise_x * 0.5
        target_y += noise_y * 0.5
        
        move_x = int(target_x - state["current_x"])
        move_y = int(target_y - state["current_y"])
        
        if abs(move_x) > 0 or abs(move_y) > 0:
            mouse.move(x=move_x, y=move_y)
            state["current_x"] = target_x
            state["current_y"] = target_y
        
        state["current_step"] += 1
        return False
    elif state["small_moves_left"] > 0:
        small_move_x = random.randint(-WEB_BROWSE_SMALL_MOVE_X_MAX, WEB_BROWSE_SMALL_MOVE_X_MAX)
        small_move_y = random.randint(-WEB_BROWSE_SMALL_MOVE_Y_MAX, WEB_BROWSE_SMALL_MOVE_Y_MAX)
        
        noise_x, noise_y = perlin_noise_2d(current_time - state["time_offset"], 1, 3.0)
        small_move_x += noise_x * 2
        small_move_y += noise_y * 2
        
        mouse.move(x=int(small_move_x), y=int(small_move_y))
        state["current_x"] += small_move_x
        state["current_y"] += small_move_y
        state["small_moves_left"] -= 1
        return False
    elif state["time_at_location"] < state["total_time_at_location"]:
        if "start_time" not in state:
            state["start_time"] = current_time
        state["time_at_location"] = current_time - state["start_time"]
        return False
    else:
        return True

def update_page_scanning(state):
    """
    更新页面扫描模拟，使用风力算法模拟眼球跳动
    """
    current_time = time.monotonic()
    if mouse_mover.active:
        mouse_mover.update()
        return False
    elif state["current_step"] < state["steps"]:
        x_move = state["step_x"]
        y_move = 0
        
        wind_offset_x, wind_offset_y = apply_wind_effect(
            x_move, y_move,
            current_time - state["time_offset"] + state["current_step"] * 0.1,
            wind_strength=3.0
        )
        
        x_move = wind_offset_x
        y_move = wind_offset_y
        
        if state["current_step"] % random.randint(SCAN_PAUSE_INTERVAL_MIN, SCAN_PAUSE_INTERVAL_MAX) == 0:
            pause_or_slow = random.choice(["pause", "slow", "normal"])
            if pause_or_slow == "pause":
                return False
            elif pause_or_slow == "slow":
                x_move *= SLOW_SPEED_FACTOR
                y_move *= SLOW_SPEED_FACTOR
        elif state["current_step"] % random.randint(SCAN_SLOWDOWN_INTERVAL_MIN, SCAN_SLOWDOWN_INTERVAL_MAX) == 0:
            x_move *= FAST_SPEED_FACTOR
            y_move *= FAST_SPEED_FACTOR
        
        mouse.move(x=int(x_move), y=int(y_move))
        state["current_x"] += x_move
        state["current_y"] += y_move
        state["current_step"] += 1
        return False
    elif state["scan_time"] < state["total_scan_time"]:
        if "scan_start_time" not in state:
            state["scan_start_time"] = current_time
        state["scan_time"] = current_time - state["scan_start_time"]
        return False
    else:
        return True

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
        direction_x = random.randint(EXPLORATORY_MOVE_XY_MIN, EXPLORATORY_MOVE_XY_MAX)
        direction_y = random.randint(EXPLORATORY_MOVE_XY_MIN, EXPLORATORY_MOVE_XY_MAX)
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
    target_x = random.randint(-RANDOM_MOVE_RANGE_MAX, RANDOM_MOVE_RANGE_MAX)
    target_y = random.randint(-RANDOM_MOVE_RANGE_MAX, RANDOM_MOVE_RANGE_MAX)
    mouse_mover.quick_move_to_target(target_x, target_y)
    return {
        "target_x": target_x, 
        "target_y": target_y, 
        "random_moves_left": random.randint(RANDOM_MOVES_LEFT_MIN, RANDOM_MOVES_LEFT_MAX), 
        "current_x": target_x, 
        "current_y": target_y,
        "pause_time": 0,
        "total_pause_time": random.uniform(RANDOM_MOVE_PAUSE_TIME_MIN, RANDOM_MOVE_PAUSE_TIME_MAX)
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
        direction_x = random.randint(RANDOM_MOVE_DIRECTION_MIN, RANDOM_MOVE_DIRECTION_MAX)
        direction_y = random.randint(RANDOM_MOVE_DIRECTION_MIN, RANDOM_MOVE_DIRECTION_MAX)
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
    启动圆形移动模式，使用椭圆轨迹 + Perlin噪声
    """
    center_x = random.randint(-CIRCLE_CENTER_RANGE_MAX, CIRCLE_CENTER_RANGE_MAX)
    center_y = random.randint(-CIRCLE_CENTER_RANGE_MAX, CIRCLE_CENTER_RANGE_MAX)
    
    base_radius = random.randint(CIRCLE_RADIUS_MIN, CIRCLE_RADIUS_MAX)
    radius_x = base_radius * random.uniform(0.7, 1.3)
    radius_y = base_radius * random.uniform(0.7, 1.3)
    
    start_angle = random.uniform(0, 2 * 3.14159)
    
    return {
        "center_x": center_x,
        "center_y": center_y,
        "radius_x": radius_x,
        "radius_y": radius_y,
        "current_angle": start_angle,
        "angle_step": random.uniform(CIRCLE_ANGLE_STEP_MIN, CIRCLE_ANGLE_STEP_MAX),
        "steps_completed": 0,
        "total_steps": random.randint(CIRCLE_TOTAL_STEPS_MIN, CIRCLE_TOTAL_STEPS_MAX),
        "time_at_location": 0,
        "total_time_at_location": random.uniform(CIRCLE_STAY_TIME_MIN, CIRCLE_STAY_TIME_MAX),
        "time_offset": time.monotonic()
    }

def update_circular_movement(state):
    """
    更新圆形移动模式，使用椭圆轨迹 + Perlin噪声（加速版）
    """
    current_time = time.monotonic()
    if state["steps_completed"] < state["total_steps"]:
        new_x = state["center_x"] + state["radius_x"] * fast_cos(state["current_angle"])
        new_y = state["center_y"] + state["radius_y"] * fast_sin(state["current_angle"])
        
        noise_x, noise_y = perlin_noise_2d(
            current_time - state["time_offset"],
            state["current_angle"],
            1.5
        )
        new_x += noise_x * 2
        new_y += noise_y * 2
        
        if "prev_x" not in state or "prev_y" not in state:
            state["prev_x"] = new_x
            state["prev_y"] = new_y
        
        actual_x = int(new_x - state["prev_x"])
        actual_y = int(new_y - state["prev_y"])
        
        mouse.move(x=actual_x, y=actual_y)
        
        state["prev_x"] = new_x
        state["prev_y"] = new_y
        state["current_angle"] += state["angle_step"]
        state["steps_completed"] += 1
        
        if random.random() < CIRCLE_SPEED_CHANGE_PROBABILITY and state["steps_completed"] > 5:
            change_factor = random.uniform(0.9, 1.1)
            state["angle_step"] *= change_factor
            state["angle_step"] = max(CIRCLE_NEW_ANGLE_STEP_MIN, min(CIRCLE_NEW_ANGLE_STEP_MAX, state["angle_step"]))
        
        return False
    elif state["time_at_location"] < state["total_time_at_location"]:
        if "location_start_time" not in state:
            state["location_start_time"] = current_time
        state["time_at_location"] = current_time - state["location_start_time"]
        return False
    else:
        return True

def start_target_focus():
    """
    启动目标聚焦模式，使用重力算法 + Perlin噪声
    """
    center_x = random.randint(-TARGET_FOCUS_RANGE_MAX, TARGET_FOCUS_RANGE_MAX)
    center_y = random.randint(-TARGET_FOCUS_RANGE_MAX, TARGET_FOCUS_RANGE_MAX)
    mouse_mover.quick_move_to_target(center_x, center_y)
    return {
        "center_x": center_x,
        "center_y": center_y,
        "current_x": 0,
        "current_y": 0,
        "focus_duration": 0,
        "total_focus_duration": random.uniform(TARGET_FOCUS_STAY_TIME_MIN, TARGET_FOCUS_STAY_TIME_MAX),
        "micro_movements_left": random.randint(TARGET_FOCUS_MICRO_MOVES_MIN, TARGET_FOCUS_MICRO_MOVES_MAX),
        "time_offset": time.monotonic()
    }

def update_target_focus(state):
    """
    更新目标聚焦模式，使用重力算法向中心拉近
    """
    current_time = time.monotonic()
    if mouse_mover.active:
        mouse_mover.update()
        return False
    elif state["micro_movements_left"] > 0:
        pull_x, pull_y = apply_gravity_pull(
            state["current_x"],
            state["current_y"],
            state["center_x"],
            state["center_y"],
            strength=0.15
        )
        
        noise_x, noise_y = perlin_noise_2d(
            current_time - state["time_offset"],
            state["micro_movements_left"],
            3.0
        )
        
        micro_x = int(pull_x + noise_x * 3)
        micro_y = int(pull_y + noise_y * 3)
        
        mouse.move(x=micro_x, y=micro_y)
        state["current_x"] += micro_x
        state["current_y"] += micro_y
        state["micro_movements_left"] -= 1
        return False
    elif state["focus_duration"] < state["total_focus_duration"]:
        if "focus_start_time" not in state:
            state["focus_start_time"] = current_time
        state["focus_duration"] = current_time - state["focus_start_time"]
        
        if random.random() < TARGET_FOCUS_ADDITIONAL_MOVE_PROBABILITY:
            noise_x, noise_y = perlin_noise_2d(
                current_time - state["time_offset"] + 100,
                state["focus_duration"],
                2.0
            )
            micro_x = int(noise_x * 5)
            micro_y = int(noise_y * 5)
            mouse.move(x=micro_x, y=micro_y)
            state["current_x"] += micro_x
            state["current_y"] += micro_y
        
        return False
    else:
        return True

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
        # 新增：记录上次移动时间，用于实现不规律的移动间隔
        self.last_movement_time = time.monotonic()
        # 新增：动态调整移动频率
        self.movement_interval = random.uniform(0.5, 3.0)

def update_led_for_mode(context, mode, is_active=True):
    """
    根据当前模式更新LED状态
    """
    context.current_mode = mode
    
    if hasattr(context, 'perf_stats'):
        context.perf_stats.record_mode_switch(mode)
    
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
        led_controller.set_color_with_brightness(context.led_mode_color, BREATHE_MAX_BRIGHTNESS)
    else:
        # 设置为低亮度
        led_controller.set_color_with_brightness(context.led_mode_color, BREATHE_MIN_BRIGHTNESS)

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
        led_controller.update_breathing(context.led_mode_color)
        if time.monotonic() - context.breathing_start_time >= context.breathing_duration:
            context.breathing_active = False

# 模式处理器映射表（优化重复代码）
MODE_HANDLERS = {
    "web_browsing": {
        "update": update_web_browsing,
        "start": start_web_browsing,
        "wait_min": lambda: POST_MODE_WAIT_TIME_WEB_BROWSING_MIN,
        "wait_max": lambda: POST_MODE_WAIT_TIME_WEB_BROWSING_MAX
    },
    "page_scanning": {
        "update": update_page_scanning,
        "start": start_page_scanning,
        "wait_min": lambda: POST_MODE_WAIT_TIME_PAGE_SCANNING_MIN,
        "wait_max": lambda: POST_MODE_WAIT_TIME_PAGE_SCANNING_MAX
    },
    "exploratory_move": {
        "update": update_exploratory_movement,
        "start": start_exploratory_movement,
        "wait_min": lambda: POST_MODE_WAIT_TIME_EXPLORATORY_MIN,
        "wait_max": lambda: POST_MODE_WAIT_TIME_EXPLORATORY_MAX
    },
    "random_movement": {
        "update": update_random_movement,
        "start": start_random_movement,
        "wait_min": lambda: POST_MODE_WAIT_TIME_RANDOM_MIN,
        "wait_max": lambda: POST_MODE_WAIT_TIME_RANDOM_MAX
    },
    "circular_move": {
        "update": update_circular_movement,
        "start": start_circular_movement,
        "wait_min": lambda: POST_MODE_WAIT_TIME_CIRCULAR_MIN,
        "wait_max": lambda: POST_MODE_WAIT_TIME_CIRCULAR_MAX
    },
    "target_focus": {
        "update": update_target_focus,
        "start": start_target_focus,
        "wait_min": lambda: POST_MODE_WAIT_TIME_TARGET_FOCUS_MIN,
        "wait_max": lambda: POST_MODE_WAIT_TIME_TARGET_FOCUS_MAX
    }
}

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
    
    # 使用映射表启动相应的模拟（优化后的代码）
    handler = MODE_HANDLERS.get(action)
    if handler:
        context.current_state = handler["start"]()
    
    context.mode_start_time = time.monotonic()
    # 设置一个更长的模式持续时间，降低切换频率
    context.mode_duration = random.uniform(MODE_DURATION_MIN, MODE_DURATION_MAX)

# 初始化上下文
def main():
    """主函数，包含异常处理"""
    try:
        # 初始化上下文
        context = init_context()

        # 主事件循环
        last_update_time = time.monotonic()

        while True:
            current_time = time.monotonic()
            
            if hasattr(context, 'serial_control'):
                context.serial_control.check_commands()
            
            # 限制更新频率，避免过度占用CPU
            if current_time - last_update_time >= UPDATE_INTERVAL:  # 每8ms更新一次（125Hz，匹配USB HID回报率）
                last_update_time = current_time
                
                if hasattr(context, 'perf_stats'):
                    context.perf_stats.record_loop()
                    context.perf_stats.update_memory_stats()
                    
                    if context.perf_stats.should_report(PERFORMANCE_REPORT_INTERVAL):
                        context.perf_stats.print_report()
                
                # 更新呼吸灯效果
                if not context.breathing_active and context.current_mode:
                    led_controller.update_breathing(context.led_mode_color)
                
                # 根据当前模式更新模拟状态（优化后的统一处理）
                if context.current_mode and context.current_state:
                    handler = MODE_HANDLERS.get(context.current_mode)
                    if handler:
                        update_func = handler["update"]
                        if update_func(context.current_state):
                            # 模式完成，设置等待时间
                            update_led_for_mode(context, context.current_mode, False)
                            context.post_mode_wait_time = current_time
                            context.post_mode_wait_duration = random.uniform(
                                handler["wait_min"](),
                                handler["wait_max"]()
                            )
                            context.current_mode = None
                
                # 检查是否需要启动新模式
                if context.current_mode is None and current_time - context.post_mode_wait_time >= context.post_mode_wait_duration:
                    check_and_start_next_mode(context)
                    # 启动短暂的呼吸灯效果以示活跃
                    start_breathing_led(context, 0.5)
                
                # 更新呼吸灯任务（如果活动）
                update_breathing_led_task(context)
    
    except KeyboardInterrupt:
        # 用户中断（Ctrl+C），正常退出
        print("程序被用户中断")
        pixels.fill((0, 0, 0))
        pixels.show()
    
    except OSError as e:
        # USB 设备错误或其他 I/O 错误
        print(f"USB/IO 错误: {e}")
        # 闪烁红色 LED 指示错误
        for _ in range(10):
            pixels.fill((255, 0, 0))
            pixels.show()
            time.sleep(0.2)
            pixels.fill((0, 0, 0))
            pixels.show()
            time.sleep(0.2)
    
    except Exception as e:
        # 捕获所有其他异常
        print(f"未知错误: {e}")
        # 快速闪烁红色 LED 指示严重错误
        for _ in range(20):
            pixels.fill((255, 0, 0))
            pixels.show()
            time.sleep(0.1)
            pixels.fill((0, 0, 0))
            pixels.show()
            time.sleep(0.1)

# 启动主程序
if __name__ == "__main__":
    main()