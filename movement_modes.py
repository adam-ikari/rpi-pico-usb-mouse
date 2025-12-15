"""
移动模式模块
包含所有鼠标移动模式的实现
"""

import time
import math
from constants import *
from noise_generator import noise_generator
from random_generator import fast_random, random_pool, range_manager, weighted_mode_selector
from fast_math import fast_distance


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
    
    def get_duration_range(self):
        """返回模式持续时间范围（最小，最大）秒"""
        # 默认值：15-60秒
        return (15, 60)


class WebBrowsingMode(MovementMode):
    """网页浏览模式 - 使用贝塞尔曲线"""
    
    def start(self):
        target_x = range_manager.randint('web_browse_x')
        target_y = range_manager.randint('web_browse_y')
        self.mouse_mover.quick_move_to_target(target_x, target_y)
        
        return {
            "target_x": target_x,
            "target_y": target_y,
            "small_moves_left": random_pool.randint(10, 50),
            "current_x": target_x,
            "current_y": target_y,
            "time_at_location": 0,
            "total_time_at_location": random_pool.uniform(WEB_BROWSE_STAY_TIME_MIN, WEB_BROWSE_STAY_TIME_MAX),
            "time_offset": time.monotonic()
        }
    
    def update(self, state):
        current_time = time.monotonic()
        
        if self.mouse_mover.active:
            self.mouse_mover.update()
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
            small_move_x += int(noise_x * 2)
            small_move_y += int(noise_y * 2)
            
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
    
    def get_duration_range(self):
        """网页浏览：30-120秒"""
        return (30, 120)
    



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
            "scan_direction": 1,  # 1: 向右扫描, -1: 向左扫描
            "scan_count": 0,  # 已完成的扫描次数
            "total_scans": random_pool.randint(3, 8),  # 总共来回扫描3-8次
            "time_offset": time.monotonic()
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if self.mouse_mover.active:
            self.mouse_mover.update()
            return False
        elif state["current_step"] < state["steps"]:
            if not hasattr(state, "scan_bezier_points"):
                # 生成贝塞尔扫描轨迹
                start_x = state["start_x"] if state["scan_direction"] == 1 else state["end_x"]
                end_x = state["end_x"] if state["scan_direction"] == 1 else state["start_x"]
                
                dx = end_x - start_x
                mid_x = start_x + (dx >> 1)
                
                offset_range = abs(dx) // 10
                offset_y = random_pool.randint(-offset_range, offset_range)
                
                control_x = mid_x
                control_y = state["start_y"] + offset_y
                
                state["scan_bezier_points"] = []
                prev_x, prev_y = start_x, state["start_y"]
                
                for i in range(state["steps"]):
                    t = i / max(state["steps"] - 1, 1)
                    bx = self.mouse_mover._quadratic_bezier(t, start_x, control_x, end_x)
                    by = self.mouse_mover._quadratic_bezier(t, state["start_y"], control_y, state["start_y"])
                    
                    wind_x = noise_generator.value_noise_2d(i / 10, 0, frequency=1.0) * 3
                    wind_y = noise_generator.value_noise_2d(i / 10, 50, frequency=1.0) * 3
                    
                    bx += int(wind_x)
                    by += int(wind_y) >> 1
                    
                    dx_step = int(bx - prev_x)
                    dy_step = int(by - prev_y)
                    state["scan_bezier_points"].append((dx_step, dy_step))
                    prev_x, prev_y = bx, by
            
            if state["current_step"] < len(state["scan_bezier_points"]):
                x_move, y_move = state["scan_bezier_points"][state["current_step"]]
                
                # 仅对 X 轴应用速度缩放（水平扫描）
                if state["scan_direction"] == 1:
                    x_move = (x_move * SCAN_SPEED_RIGHT) // 100
                else:
                    x_move = (x_move * SCAN_SPEED_LEFT) // 100
                
                # 最后一步：强制校正到终点
                if state["current_step"] == len(state["scan_bezier_points"]) - 1:
                    expected_x = state["end_x"] if state["scan_direction"] == 1 else state["start_x"]
                    x_move = expected_x - state["current_x"]
                
                if state["current_step"] % random_pool.randint(10, 50) == 0:
                    pause_or_slow = random_pool.choice(["pause", "slow", "normal"])
                    if pause_or_slow == "pause":
                        return False
                    elif pause_or_slow == "slow":
                        x_move = (x_move * SLOW_SPEED_FACTOR) // 100
                
                self.mouse_mover.mouse.move(x=int(x_move), y=int(y_move))
                state["current_x"] += x_move
                state["current_y"] += y_move
                state["current_step"] += 1
                return False
            else:
                state["current_step"] += 1
                return False
        else:
            state["scan_count"] += 1
            if state["scan_count"] >= state["total_scans"]:
                return True
            else:
                state["scan_direction"] *= -1
                state["current_step"] = 0
                if hasattr(state, "scan_bezier_points"):
                    delattr(state, "scan_bezier_points")
                
                y_offset = random_pool.randint(20, 50)
                self.mouse_mover.mouse.move(x=0, y=y_offset)
                state["current_y"] += y_offset
                return False
    
    def get_wait_time_range(self):
        return POST_MODE_WAIT_TIME_PAGE_SCANNING_MIN, POST_MODE_WAIT_TIME_PAGE_SCANNING_MAX
    
    def get_duration_range(self):
        """页面扫描：20-60秒"""
        return (20, 60)
    
    def _apply_wind_effect(self, x, y, time_offset, wind_strength=2.0):
        """应用风力效果，添加横向偏移"""
        half_time = time_offset / 2
        wind_x = noise_generator.value_noise_2d(half_time, 0, frequency=1.0) * wind_strength
        wind_y = noise_generator.value_noise_2d(half_time, 50, frequency=1.0) * wind_strength
        wind_y = int(wind_y) >> 1
        return x + int(wind_x), y + wind_y


class ExploratoryMovementMode(MovementMode):
    """探索性移动模式"""
    
    def get_duration_range(self):
        """探索移动：10-30秒"""
        return (10, 30)
    
    def start(self):
        target_x = range_manager.randint('exploratory_move')
        target_y = range_manager.randint('exploratory_move')
        self.mouse_mover.quick_move_to_target(target_x, target_y)
        return {
            "target_x": target_x, 
            "target_y": target_y, 
            "exploratory_moves_left": random_pool.randint(2, 4),  # 减少移动次数
            "current_x": target_x, 
            "current_y": target_y, 
            "time_at_exploration": 0, 
            "total_time_at_exploration": random_pool.uniform(EXPLORATORY_STAY_TIME_MIN, EXPLORATORY_STAY_TIME_MAX),
            "last_move_time": 0  # 记录上次移动时间
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if self.mouse_mover.active:
            self.mouse_mover.update()
            return False
        elif state["exploratory_moves_left"] > 0:
            # 增加移动间隔，避免频繁移动
            if state["last_move_time"] == 0 or current_time - state["last_move_time"] >= 1.5:
                # 更大的移动距离，更自然的探索
                direction_x = random_pool.randint(-150, 150)
                direction_y = random_pool.randint(-150, 150)
                self.mouse_mover.quick_move_to_target(direction_x, direction_y)
                state["current_x"] += direction_x
                state["current_y"] += direction_y
                state["exploratory_moves_left"] -= 1
                state["last_move_time"] = current_time
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
            "random_moves_left": random_pool.randint(2, 5),  # 减少移动次数
            "current_x": target_x, 
            "current_y": target_y,
            "pause_time": 0,
            "total_pause_time": random_pool.uniform(RANDOM_MOVE_PAUSE_TIME_MIN, RANDOM_MOVE_PAUSE_TIME_MAX),
            "last_move_time": 0  # 记录上次移动时间
        }
    
    def update(self, state):
        current_time = time.monotonic()
        if self.mouse_mover.active:
            self.mouse_mover.update()
            return False
        elif state["random_moves_left"] > 0:
            # 添加移动间隔，避免频繁震颤
            if state["last_move_time"] == 0 or current_time - state["last_move_time"] >= 0.5:
                # 更大的随机移动距离
                direction_x = random_pool.randint(-80, 80)
                direction_y = random_pool.randint(-80, 80)
                self.mouse_mover.quick_move_to_target(direction_x, direction_y)
                state["current_x"] += direction_x
                state["current_y"] += direction_y
                state["random_moves_left"] -= 1
                state["last_move_time"] = current_time
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
    
    # 类级别共享查找表（所有实例共享）
    _SIN_LUT = None
    
    @classmethod
    def _init_trig_lut(cls):
        """初始化三角函数查找表（仅初始化一次）"""
        if cls._SIN_LUT is not None:
            return
        
        import math
        # 360个采样点，精度1度
        cls._SIN_LUT = [int(math.sin(i * 0.017453292519943295) * 10000) for i in range(361)]
    
    def start(self):
        center_x = range_manager.randint('circle_center')
        center_y = range_manager.randint('circle_center')
        
        base_radius = random_pool.randint(30, 100)
        radius_x = int(base_radius * random_pool.uniform(0.7, 1.3))
        radius_y = int(base_radius * random_pool.uniform(0.7, 1.3))
        
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
            "angle_step": random_pool.uniform(CIRCLE_ANGLE_STEP_MIN, CIRCLE_ANGLE_STEP_MAX) / 100,
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
            new_x += int(noise_x * 2)
            new_y += int(noise_y * 2)
            
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
            
            if random_pool.random() < (CIRCLE_SPEED_CHANGE_PROBABILITY / 100) and state["steps_completed"] > 5:
                change_factor = random_pool.uniform(90, 110) / 100
                state["angle_step"] *= change_factor
                state["angle_step"] = max(CIRCLE_NEW_ANGLE_STEP_MIN / 100, min(CIRCLE_NEW_ANGLE_STEP_MAX / 100, state["angle_step"]))
            
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
        """快速sin计算（使用类级别查找表）"""
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_trig_call()
        
        # 确保查找表已初始化
        if self._SIN_LUT is None:
            self._init_trig_lut()
        
        # 转换为角度 (0-360)
        angle_deg = int((angle_rad * 57.2957795) % 360)
        
        # 查表
        return self._SIN_LUT[angle_deg] / 10000
    
    def _fast_cos(self, angle_rad):
        """快速cos计算（sin(x + 90°)）"""
        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_trig_call()
        
        # cos(x) = sin(x + π/2)
        return self._fast_sin(angle_rad + 1.5708)
    
    


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
            
            micro_x = pull_x + int(noise_x * 3)
            micro_y = pull_y + int(noise_y * 3)
            
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
        distance = fast_distance(int(dx), int(dy))
        
        if distance > 0:
            strength_int = int(strength * 100)
            pull_x = (dx * strength_int * distance) // (distance * 100)
            pull_y = (dy * strength_int * distance) // (distance * 100)
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