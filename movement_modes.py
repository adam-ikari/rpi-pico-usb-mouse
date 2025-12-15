"""
移动模式模块
包含所有鼠标移动模式的实现
"""

import time
import math
from constants import *
from noise_generator import noise_generator
from random_generator import fast_random, random_pool, range_manager, weighted_mode_selector


class MovementMode:
    """移动模式基类"""
    
    def __init__(self, mouse_mover, perf_stats=None):
        self.mouse_mover = mouse_mover
        self.perf_stats = perf_stats
    
    def start(self):
        """启动模式，返回状态字典"""
        raise NotImplementedError
    
    def update(self, state):
        """更新模式状态，返回是否完成"""
        raise NotImplementedError
    
    def get_wait_time_range(self):
        """返回模式完成后等待时间范围（最小，最大）"""
        raise NotImplementedError


class WebBrowsingMode(MovementMode):
    """网页浏览模式 - 使用贝塞尔曲线"""
    
    def start(self):
        target_x = range_manager.randint('web_browse_x')
        target_y = range_manager.randint('web_browse_y')
        
        distance = math.sqrt(target_x * target_x + target_y * target_y)
        total_steps = min(max(int(distance / 15), 15), 40)
        
        control_x, control_y = self._generate_bezier_control_point(0, 0, target_x, target_y)
        
        return {
            "start_x": 0,
            "start_y": 0,
            "target_x": target_x,
            "target_y": target_y,
            "control_x": control_x,
            "control_y": control_y,
            "current_step": 0,
            "total_steps": total_steps,
            "small_moves_left": random_pool.randint(10, 50),
            "current_x": 0,
            "current_y": 0,
            "time_at_location": 0,
            "total_time_at_location": random_pool.uniform(WEB_BROWSE_STAY_TIME_MIN, WEB_BROWSE_STAY_TIME_MAX),
            "time_offset": time.monotonic()
        }
    
    def update(self, state):
        current_time = time.monotonic()
        
        if state["current_step"] < state["total_steps"]:
            target_x, target_y = self._calculate_bezier_point(
                state["current_step"],
                state["total_steps"],
                state["start_x"],
                state["start_y"],
                state["target_x"],
                state["target_y"],
                state["control_x"],
                state["control_y"]
            )
            
            noise_x = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"], 0, 
                frequency=2.0, octaves=1
            )
            noise_y = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"], 100, 
                frequency=2.0, octaves=1
            )
            target_x += noise_x * 0.5
            target_y += noise_y * 0.5
            
            move_x = int(target_x - state["current_x"])
            move_y = int(target_y - state["current_y"])
            
            if abs(move_x) > 0 or abs(move_y) > 0:
                self.mouse_mover.mouse.move(x=move_x, y=move_y)
                state["current_x"] = target_x
                state["current_y"] = target_y
            
            state["current_step"] += 1
            return False
        elif state["small_moves_left"] > 0:
            small_move_x = random_pool.randint(-10, 10)
            small_move_y = random_pool.randint(-10, 10)
            
            noise_x = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"], 1, 
                frequency=3.0, octaves=1
            )
            noise_y = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"], 101, 
                frequency=3.0, octaves=1
            )
            small_move_x += noise_x * 2
            small_move_y += noise_y * 2
            
            self.mouse_mover.mouse.move(x=int(small_move_x), y=int(small_move_y))
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
    
    def get_wait_time_range(self):
        return POST_MODE_WAIT_TIME_WEB_BROWSING_MIN, POST_MODE_WAIT_TIME_WEB_BROWSING_MAX
    
    def _generate_bezier_control_point(self, start_x, start_y, end_x, end_y):
        """生成二次贝塞尔曲线的控制点"""
        dx = end_x - start_x
        dy = end_y - start_y
        
        mid_x = start_x + dx * 0.5
        mid_y = start_y + dy * 0.5
        
        offset = random_pool.uniform(-abs(dx + dy) * 0.2, abs(dx + dy) * 0.2)
        control_x = mid_x + offset
        control_y = mid_y + offset
        
        return control_x, control_y
    
    def _calculate_bezier_point(self, step, total_steps, start_x, start_y, end_x, end_y, control_x, control_y):
        """计算二次贝塞尔曲线上的点"""
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_bezier_calc()
        
        t = step / max(total_steps - 1, 1)
        x = self._quadratic_bezier(t, start_x, control_x, end_x)
        y = self._quadratic_bezier(t, start_y, control_y, end_y)
        return x, y
    
    def _quadratic_bezier(self, t, p0, p1, p2):
        """二次贝塞尔曲线计算"""
        u = 1 - t
        uu = u * u
        tt = t * t
        
        p = uu * p0
        p += 2 * u * t * p1
        p += tt * p2
        
        return p
    



class PageScanningMode(MovementMode):
    """页面扫描模式 - 使用风力算法"""
    
    def start(self):
        start_x = range_manager.randint('page_scan_start_x')
        start_y = range_manager.randint('page_scan_y')
        self.mouse_mover.quick_move_to_target(start_x, start_y)
        
        end_x = random_pool.randint(600, 800)
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
            "total_scan_time": random_pool.uniform(PAGE_SCAN_STAY_TIME_MIN, PAGE_SCAN_STAY_TIME_MAX),
            "time_offset": time.monotonic()
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if self.mouse_mover.active:
            self.mouse_mover.update()
            return False
        elif state["current_step"] < state["steps"]:
            x_move = state["step_x"]
            y_move = 0
            
            wind_offset_x, wind_offset_y = self._apply_wind_effect(
                x_move, y_move,
                current_time - state["time_offset"] + state["current_step"] * 0.1,
                wind_strength=3.0
            )
            
            x_move = wind_offset_x
            y_move = wind_offset_y
            
            if state["current_step"] % random_pool.randint(10, 50) == 0:
                pause_or_slow = random_pool.choice(["pause", "slow", "normal"])
                if pause_or_slow == "pause":
                    return False
                elif pause_or_slow == "slow":
                    x_move *= SLOW_SPEED_FACTOR
                    y_move *= SLOW_SPEED_FACTOR
            elif state["current_step"] % random_pool.randint(10, 50) == 0:
                x_move *= FAST_SPEED_FACTOR
                y_move *= FAST_SPEED_FACTOR
            
            self.mouse_mover.mouse.move(x=int(x_move), y=int(y_move))
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
    
    def get_wait_time_range(self):
        return POST_MODE_WAIT_TIME_PAGE_SCANNING_MIN, POST_MODE_WAIT_TIME_PAGE_SCANNING_MAX
    
    def _apply_wind_effect(self, x, y, time_offset, wind_strength=2.0):
        """应用风力效果，添加横向偏移"""
        wind_x = noise_generator.value_noise_2d(time_offset * 0.5, 0, frequency=1.0) * wind_strength
        wind_y = noise_generator.value_noise_2d(time_offset * 0.5, 50, frequency=1.0) * wind_strength * 0.5
        return x + wind_x, y + wind_y


class ExploratoryMovementMode(MovementMode):
    """探索性移动模式"""
    
    def start(self):
        target_x = range_manager.randint('exploratory_move')
        target_y = range_manager.randint('exploratory_move')
        self.mouse_mover.quick_move_to_target(target_x, target_y)
        return {
            "target_x": target_x, 
            "target_y": target_y, 
            "exploratory_moves_left": random_pool.randint(3, 7), 
            "current_x": target_x, 
            "current_y": target_y, 
            "time_at_exploration": 0, 
            "total_time_at_exploration": random_pool.uniform(EXPLORATORY_STAY_TIME_MIN, EXPLORATORY_STAY_TIME_MAX)
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if self.mouse_mover.active:
            self.mouse_mover.update()
            return False
        elif state["exploratory_moves_left"] > 0:
            direction_x = random_pool.randint(-20, 20)
            direction_y = random_pool.randint(-20, 20)
            self.mouse_mover.smooth_move_small(state["current_x"], state["current_y"], state["current_x"] + direction_x, state["current_y"] + direction_y)
            state["current_x"] += direction_x
            state["current_y"] += direction_y
            state["exploratory_moves_left"] -= 1
            return False
        elif state["time_at_exploration"] < state["total_time_at_exploration"]:
            if "exploration_start_time" not in state:
                state["exploration_start_time"] = current_time
            state["time_at_exploration"] = current_time - state["exploration_start_time"]
            return False
        else:
            return True
    
    def get_wait_time_range(self):
        return POST_MODE_WAIT_TIME_EXPLORATORY_MIN, POST_MODE_WAIT_TIME_EXPLORATORY_MAX


class RandomMovementMode(MovementMode):
    """随机移动模式"""
    
    def start(self):
        target_x = range_manager.randint('random_move')
        target_y = range_manager.randint('random_move')
        self.mouse_mover.quick_move_to_target(target_x, target_y)
        return {
            "target_x": target_x, 
            "target_y": target_y, 
            "random_moves_left": random_pool.randint(3, 10), 
            "current_x": target_x, 
            "current_y": target_y,
            "pause_time": 0,
            "total_pause_time": random_pool.uniform(RANDOM_MOVE_PAUSE_TIME_MIN, RANDOM_MOVE_PAUSE_TIME_MAX)
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if self.mouse_mover.active:
            self.mouse_mover.update()
            return False
        elif state["random_moves_left"] > 0:
            direction_x = random_pool.randint(-3, 3)
            direction_y = random_pool.randint(-3, 3)
            self.mouse_mover.smooth_move_small(state["current_x"], state["current_y"], state["current_x"] + direction_x, state["current_y"] + direction_y)
            state["current_x"] += direction_x
            state["current_y"] += direction_y
            state["random_moves_left"] -= 1
            return False
        elif state["pause_time"] < state["total_pause_time"]:
            if "pause_start_time" not in state:
                state["pause_start_time"] = current_time
            state["pause_time"] = current_time - state["pause_start_time"]
            return False
        else:
            return True
    
    def get_wait_time_range(self):
        return POST_MODE_WAIT_TIME_RANDOM_MIN, POST_MODE_WAIT_TIME_RANDOM_MAX


class CircularMovementMode(MovementMode):
    """圆形移动模式 - 使用椭圆轨迹 + Perlin噪声"""
    
    def start(self):
        center_x = range_manager.randint('circle_center')
        center_y = range_manager.randint('circle_center')
        
        base_radius = random_pool.randint(30, 100)
        radius_x = base_radius * random_pool.uniform(0.7, 1.3)
        radius_y = base_radius * random_pool.uniform(0.7, 1.3)
        
        start_angle = random_pool.uniform(0, 2 * 3.14159)
        
        # 初始位置
        initial_x = center_x + radius_x
        initial_y = center_y
        
        return {
            "center_x": center_x,
            "center_y": center_y,
            "radius_x": radius_x,
            "radius_y": radius_y,
            "current_angle": start_angle,
            "angle_step": random_pool.uniform(CIRCLE_ANGLE_STEP_MIN, CIRCLE_ANGLE_STEP_MAX),
            "steps_completed": 0,
            "total_steps": random_pool.randint(30, 70),
            "time_at_location": 0,
            "total_time_at_location": random_pool.uniform(CIRCLE_STAY_TIME_MIN, CIRCLE_STAY_TIME_MAX),
            "time_offset": time.monotonic(),
            "prev_x": initial_x,
            "prev_y": initial_y
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if state["steps_completed"] < state["total_steps"]:
            new_x = state["center_x"] + state["radius_x"] * self._fast_cos(state["current_angle"])
            new_y = state["center_y"] + state["radius_y"] * self._fast_sin(state["current_angle"])
            
            noise_x = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"],
                state["current_angle"],
                frequency=1.5, octaves=1
            )
            noise_y = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"],
                state["current_angle"] + 100,
                frequency=1.5, octaves=1
            )
            new_x += noise_x * 2
            new_y += noise_y * 2
            
            if "prev_x" not in state or "prev_y" not in state:
                state["prev_x"] = new_x
                state["prev_y"] = new_y
            
            actual_x = int(new_x - state["prev_x"])
            actual_y = int(new_y - state["prev_y"])
            
            self.mouse_mover.mouse.move(x=actual_x, y=actual_y)
            
            state["prev_x"] = new_x
            state["prev_y"] = new_y
            state["current_angle"] += state["angle_step"]
            state["steps_completed"] += 1
            
            if random_pool.random() < CIRCLE_SPEED_CHANGE_PROBABILITY and state["steps_completed"] > 5:
                change_factor = random_pool.uniform(0.9, 1.1)
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
    
    def get_wait_time_range(self):
        return POST_MODE_WAIT_TIME_CIRCULAR_MIN, POST_MODE_WAIT_TIME_CIRCULAR_MAX
    
    def _fast_sin(self, angle_rad):
        """快速sin计算（查表法）"""
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_trig_call()
        return self._fast_sin_impl(angle_rad)
    
    def _fast_cos(self, angle_rad):
        """快速cos计算（查表法）"""
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_trig_call()
        return self._fast_cos_impl(angle_rad)
    
    def _fast_sin_impl(self, angle_rad):
        """快速sin计算实现（查表法）"""
        if not hasattr(self, '_sin_lut'):
            self._init_trig_lut()
        
        angle_deg = int((angle_rad * 57.29577951308232) % 360)
        return self._sin_lut[angle_deg]
    
    def _fast_cos_impl(self, angle_rad):
        """快速cos计算实现（查表法）"""
        if not hasattr(self, '_cos_lut'):
            self._init_trig_lut()
        
        angle_deg = int((angle_rad * 57.29577951308232) % 360)
        return self._cos_lut[angle_deg]
    
    def _init_trig_lut(self):
        """初始化三角函数查找表"""
        self._sin_lut = []
        self._cos_lut = []
        for i in range(360):
            angle_rad = i * 0.017453292519943295
            self._sin_lut.append(math.sin(angle_rad))
            self._cos_lut.append(math.cos(angle_rad))
    
    


class TargetFocusMode(MovementMode):
    """目标聚焦模式 - 使用重力算法 + Perlin噪声"""
    
    def start(self):
        center_x = range_manager.randint('target_focus')
        center_y = range_manager.randint('target_focus')
        self.mouse_mover.quick_move_to_target(center_x, center_y)
        return {
            "center_x": center_x,
            "center_y": center_y,
            "current_x": 0,
            "current_y": 0,
            "focus_duration": 0,
            "total_focus_duration": random_pool.uniform(TARGET_FOCUS_STAY_TIME_MIN, TARGET_FOCUS_STAY_TIME_MAX),
            "micro_movements_left": random_pool.randint(2, 7),
            "time_offset": time.monotonic()
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if self.mouse_mover.active:
            self.mouse_mover.update()
            return False
        elif state["micro_movements_left"] > 0:
            pull_x, pull_y = self._apply_gravity_pull(
                state["current_x"],
                state["current_y"],
                state["center_x"],
                state["center_y"],
                strength=0.15
            )
            
            noise_x = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"],
                state["micro_movements_left"],
                frequency=3.0, octaves=1
            )
            noise_y = noise_generator.perlin_noise_2d(
                current_time - state["time_offset"],
                state["micro_movements_left"] + 100,
                frequency=3.0, octaves=1
            )
            
            micro_x = int(pull_x + noise_x * 3)
            micro_y = int(pull_y + noise_y * 3)
            
            self.mouse_mover.mouse.move(x=micro_x, y=micro_y)
            state["current_x"] += micro_x
            state["current_y"] += micro_y
            state["micro_movements_left"] -= 1
            return False
        elif state["focus_duration"] < state["total_focus_duration"]:
            if "focus_start_time" not in state:
                state["focus_start_time"] = current_time
            state["focus_duration"] = current_time - state["focus_start_time"]
            
            if random_pool.random() < TARGET_FOCUS_ADDITIONAL_MOVE_PROBABILITY:
                noise_x = noise_generator.perlin_noise_2d(
                    current_time - state["time_offset"] + 100,
                    state["focus_duration"],
                    frequency=2.0, octaves=1
                )
                noise_y = noise_generator.perlin_noise_2d(
                    current_time - state["time_offset"] + 100,
                    state["focus_duration"] + 100,
                    frequency=2.0, octaves=1
                )
                micro_x = int(noise_x * 5)
                micro_y = int(noise_y * 5)
                self.mouse_mover.mouse.move(x=micro_x, y=micro_y)
                state["current_x"] += micro_x
                state["current_y"] += micro_y
            
            return False
        else:
            return True
    
    def get_wait_time_range(self):
        return POST_MODE_WAIT_TIME_TARGET_FOCUS_MIN, POST_MODE_WAIT_TIME_TARGET_FOCUS_MAX
    
    def _apply_gravity_pull(self, current_x, current_y, target_x, target_y, strength=0.1):
        """应用重力效果，向目标点拉近"""
        dx = target_x - current_x
        dy = target_y - current_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            pull_x = (dx / distance) * strength * distance
            pull_y = (dy / distance) * strength * distance
            return pull_x, pull_y
        return 0, 0
    
    # 模式工厂
class ModeFactory:
    """移动模式工厂"""
    
    @staticmethod
    def create_mode(mode_name, mouse_mover, perf_stats=None):
        """根据模式名称创建对应的模式实例"""
        modes = {
            "web_browsing": WebBrowsingMode,
            "page_scanning": PageScanningMode,
            "exploratory_move": ExploratoryMovementMode,
            "random_movement": RandomMovementMode,
            "circular_move": CircularMovementMode,
            "target_focus": TargetFocusMode
        }
        
        mode_class = modes.get(mode_name)
        if mode_class:
            return mode_class(mouse_mover, perf_stats)
        else:
            raise ValueError(f"Unknown mode: {mode_name}")