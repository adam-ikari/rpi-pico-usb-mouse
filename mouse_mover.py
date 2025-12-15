import time
import random
from constants import *
from random_generator import fast_random, random_pool
from fast_math import fast_distance, percent_to_float


class MouseMover:
    """鼠标移动控制器，使用非阻塞方式实现"""
    
    def __init__(self, mouse_device, perf_stats=None):
        self.mouse = mouse_device
        self.perf_stats = perf_stats
        self.active = False
        self.current_step = 0
        self.total_steps = 0
        self.step_x = 0
        self.step_y = 0
        self.start_time = 0
        self.move_duration = 0
        self.small_move_steps = []
        self.small_move_index = 0
        self.velocity_profile = []
        
        # 贝塞尔曲线相关
        self.bezier_points = []
        self.bezier_index = 0
        self.current_x = 0
        self.current_y = 0

    def quick_move_to_target(self, end_x, end_y, duration_factor=0.02):
        """
        非阻塞快速移动鼠标到目标位置，使用贝塞尔曲线实现自然移动
        """
        try:
            distance = fast_distance(int(end_x), int(end_y))
            if distance == 0:
                return

            base_steps = max(int(distance / BASE_STEP_DISTANCE), MIN_BASE_STEPS)
            total_steps = int(base_steps * random_pool.uniform(DISTANCE_RANDOM_FACTOR_MIN, DISTANCE_RANDOM_FACTOR_MAX))
            
            control_x, control_y = self._generate_bezier_control_point(0, 0, end_x, end_y)
            
            self.bezier_points = []
            prev_x, prev_y = 0, 0
            
            for i in range(total_steps):
                bx, by = self._calculate_bezier_point(i, total_steps, 0, 0, end_x, end_y, control_x, control_y)
                dx = int(bx - prev_x)
                dy = int(by - prev_y)
                self.bezier_points.append((dx, dy))
                prev_x, prev_y = bx, by
            
            self.bezier_index = 0
            self.active = True
            self.start_time = time.monotonic()
            self.move_duration = duration_factor
            
        except Exception as e:
            raise

    def _generate_bezier_control_point(self, start_x, start_y, end_x, end_y):
        """生成二次贝塞尔曲线的控制点（使用整数运算）"""
        dx = int(end_x - start_x)
        dy = int(end_y - start_y)
        
        mid_x = start_x + (dx >> 1)
        mid_y = start_y + (dy >> 1)
        
        offset_range = (abs(dx + dy) * random_pool.randint(BEZIER_CONTROL_OFFSET_MIN, BEZIER_CONTROL_OFFSET_MAX)) // 100
        offset_x = random_pool.randint(-offset_range, offset_range)
        offset_y = random_pool.randint(-offset_range, offset_range)
        
        control_x = mid_x + offset_x
        control_y = mid_y + offset_y
        
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
        """二次贝塞尔曲线计算（使用整数优化）"""
        t_int = int(t * 100)
        u_int = 100 - t_int
        
        uu = (u_int * u_int) // 100
        tt = (t_int * t_int) // 100
        ut2 = (2 * u_int * t_int) // 100
        
        p = (uu * p0) // 100
        p += (ut2 * p1) // 100
        p += (tt * p2) // 100
        
        return p
    
    def bezier_transition_move(self, end_x, end_y):
        """
        模式间的贝塞尔曲线过渡移动
        从当前位置平滑移动到下一个模式的起始位置
        """
        try:
            from constants import MODE_TRANSITION_MIN_STEPS, MODE_TRANSITION_MAX_STEPS, MODE_TRANSITION_CONTROL_OFFSET
            
            start_x, start_y = 0, 0
            distance = fast_distance(int(end_x), int(end_y))
            
            if distance == 0:
                return
            
            steps = random_pool.randint(MODE_TRANSITION_MIN_STEPS, MODE_TRANSITION_MAX_STEPS)
            
            dx = int(end_x - start_x)
            dy = int(end_y - start_y)
            mid_x = start_x + (dx >> 1)
            mid_y = start_y + (dy >> 1)
            
            offset_range = (abs(dx + dy) * MODE_TRANSITION_CONTROL_OFFSET) // 100
            offset_x = random_pool.randint(-offset_range, offset_range)
            offset_y = random_pool.randint(-offset_range, offset_range)
            
            control_x = mid_x + offset_x
            control_y = mid_y + offset_y
            
            self.bezier_points = []
            prev_x, prev_y = start_x, start_y
            
            for i in range(steps):
                bx, by = self._calculate_bezier_point(i, steps, start_x, start_y, end_x, end_y, control_x, control_y)
                dx_step = int(bx - prev_x)
                dy_step = int(by - prev_y)
                self.bezier_points.append((dx_step, dy_step))
                prev_x, prev_y = bx, by
            
            self.bezier_index = 0
            self.active = True
            
        except Exception as e:
            raise

    def smooth_move_small(self, start_x, start_y, end_x, end_y, duration_factor=0.1):
        """
        非阻塞在小范围内平滑移动鼠标，使用贝塞尔曲线实现自然移动
        """
        try:
            dx = end_x - start_x
            dy = end_y - start_y
            distance = fast_distance(int(dx), int(dy))
            if distance == 0:
                return

            base_steps = max(int(distance / SMALL_MOVE_BASE_DISTANCE), 5)
            steps = int(base_steps * random_pool.uniform(SMALL_MOVE_DISTANCE_FACTOR_MIN, SMALL_MOVE_DISTANCE_FACTOR_MAX))
            
            control_x, control_y = self._generate_bezier_control_point(start_x, start_y, end_x, end_y)
            
            self.small_move_steps = []
            prev_x, prev_y = start_x, start_y
            
            for i in range(steps):
                bx, by = self._calculate_bezier_point(i, steps, start_x, start_y, end_x, end_y, control_x, control_y)
                
                noise_x = int(random_pool.uniform(SMALL_MOVE_OFFSET_MIN, SMALL_MOVE_OFFSET_MAX))
                noise_y = int(random_pool.uniform(SMALL_MOVE_OFFSET_MIN, SMALL_MOVE_OFFSET_MAX))
                bx += noise_x
                by += noise_y
                
                dx = int(bx - prev_x)
                dy = int(by - prev_y)
                
                rand_val = int(random_pool.random() * 100)
                if rand_val < THINK_PAUSE_PROBABILITY:
                    self.small_move_steps.append((0, 0))
                
                self.small_move_steps.append((dx, dy))
                prev_x, prev_y = bx, by
            
            remaining_x = (end_x - start_x) - (prev_x - start_x)
            remaining_y = (end_y - start_y) - (prev_y - start_y)
            if abs(remaining_x) > 0 or abs(remaining_y) > 0:
                self.small_move_steps.append((remaining_x, remaining_y))

            self.small_move_index = 0
            self.active = True
            
        except Exception as e:
            raise

    def update(self):
        """
        更新鼠标移动状态，非阻塞
        """
        if not self.active:
            return True

        if self.perf_stats and self.perf_stats.enable_stats:
            self.perf_stats.record_loop()

        if self.small_move_steps:
            if self.small_move_index < len(self.small_move_steps):
                x, y = self.small_move_steps[self.small_move_index]
                self.mouse.move(x=x, y=y)
                self.small_move_index += 1
                return False
            else:
                self.small_move_steps = []
                self.active = False
                return True
        elif self.bezier_points:
            if self.bezier_index < len(self.bezier_points):
                x, y = self.bezier_points[self.bezier_index]
                self.mouse.move(x=x, y=y)
                self.bezier_index += 1
                return False
            else:
                self.bezier_points = []
                self.active = False
                return True
        else:
            self.active = False
            return True