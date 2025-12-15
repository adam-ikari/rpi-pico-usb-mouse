import time
import gc

class PerformanceStats:
    def __init__(self, enable_stats=True):
        self.enable_stats = enable_stats
        
        self.loop_count = 0
        self.start_time = time.monotonic()
        self.last_report_time = self.start_time
        
        self.mode_counts = {
            "web_browsing": 0,
            "page_scanning": 0,
            "exploratory_move": 0,
            "random_movement": 0,
            "circular_move": 0,
            "target_focus": 0
        }
        
        self.bezier_calc_count = 0
        self.trig_call_count = 0
        
        self.frame_times = []
        self.max_frame_time = 0
        self.min_frame_time = float('inf')
        
        self.last_frame_time = time.monotonic()
        
        self.mem_free_start = gc.mem_free() if hasattr(gc, 'mem_free') else 0
        self.mem_free_min = self.mem_free_start
    
    def record_loop(self):
        if not self.enable_stats:
            return
        
        self.loop_count += 1
        
        # 防止长时间运行计数器溢出（约1天@116FPS）
        if self.loop_count > 10000000:
            self.reset(print_notice=True)
            return
        
        current_time = time.monotonic()
        
        if self.loop_count > 1:
            frame_time = current_time - self.last_frame_time
            
            if frame_time > 0:
                if frame_time > self.max_frame_time:
                    self.max_frame_time = frame_time
                if frame_time < self.min_frame_time:
                    self.min_frame_time = frame_time
                
                if len(self.frame_times) < 100:
                    self.frame_times.append(frame_time)
                else:
                    self.frame_times[(self.loop_count - 1) % 100] = frame_time
        
        self.last_frame_time = current_time
    
    def record_mode_switch(self, mode_name):
        if not self.enable_stats:
            return
        
        if mode_name in self.mode_counts:
            self.mode_counts[mode_name] += 1
    
    def record_bezier_calc(self):
        if not self.enable_stats:
            return
        
        self.bezier_calc_count += 1
    
    def record_trig_call(self):
        if not self.enable_stats:
            return
        
        self.trig_call_count += 1
    
    def update_memory_stats(self):
        if not self.enable_stats:
            return
        
        if self.loop_count % 100 == 0 and hasattr(gc, 'mem_free'):
            mem_free = gc.mem_free()
            if mem_free < self.mem_free_min:
                self.mem_free_min = mem_free
    
    def get_avg_frame_time(self):
        if not self.frame_times:
            return 0
        return sum(self.frame_times) / len(self.frame_times)
    
    def get_fps(self):
        avg_frame_time = self.get_avg_frame_time()
        if avg_frame_time > 0.001:  # 设置合理阈值（>1ms）
            fps = 1.0 / avg_frame_time
            return min(fps, 1000)   # 限制最大 FPS 为 1000
        return 0
    
    def get_uptime(self):
        return time.monotonic() - self.start_time
    
    def should_report(self, interval=60):
        current_time = time.monotonic()
        if current_time - self.last_report_time >= interval:
            self.last_report_time = current_time
            return True
        return False
    
    def get_report(self):
        if not self.enable_stats:
            return "Stats disabled"
        
        uptime = self.get_uptime()
        avg_fps = self.get_fps()
        avg_frame = self.get_avg_frame_time() * 1000
        
        report = []
        report.append("=== Perf ===")
        report.append(f"Up: {uptime:.0f}s | Loops: {self.loop_count}")
        report.append(f"FPS: {avg_fps:.1f}")
        report.append(f"Frame: {avg_frame:.1f}/{self.min_frame_time*1000:.1f}/{self.max_frame_time*1000:.1f}ms")
        
        if hasattr(gc, 'mem_free'):
            mem_free = gc.mem_free()
            mem_kb = mem_free // 1024
            peak_kb = (self.mem_free_start - self.mem_free_min) // 1024
            report.append(f"Mem: {mem_kb}KB free, {peak_kb}KB peak")
        
        total_modes = sum(self.mode_counts.values())
        if total_modes > 0:
            report.append("Modes:")
            for mode, count in self.mode_counts.items():
                pct = (count * 100) // total_modes
                if count > 0:
                    report.append(f"  {mode[:12]}: {count} ({pct}%)")
        
        if self.bezier_calc_count > 0 or self.trig_call_count > 0:
            report.append(f"Math: B={self.bezier_calc_count} T={self.trig_call_count}")
        
        return "\n".join(report)
    
    def print_report(self):
        print(self.get_report())
    
    def reset(self, print_notice=False):
        if print_notice and self.enable_stats:
            print("=== Stats Reset (overflow protection) ===")
        
        self.loop_count = 0
        self.start_time = time.monotonic()
        self.last_report_time = self.start_time
        
        for mode in self.mode_counts:
            self.mode_counts[mode] = 0
        
        self.bezier_calc_count = 0
        self.trig_call_count = 0
        
        self.frame_times = []
        self.max_frame_time = 0
        self.min_frame_time = float('inf')
        
        self.last_frame_time = time.monotonic()
        
        self.mem_free_start = gc.mem_free() if hasattr(gc, 'mem_free') else 0
        self.mem_free_min = self.mem_free_start
    
    def track_bezier(self, func):
        """装饰器：统计贝塞尔计算调用"""
        def wrapper(*args, **kwargs):
            if self.enable_stats:
                self.record_bezier_calc()
            return func(*args, **kwargs)
        return wrapper
    
    def track_trig(self, func):
        """装饰器：统计三角函数调用"""
        def wrapper(*args, **kwargs):
            if self.enable_stats:
                self.record_trig_call()
            return func(*args, **kwargs)
        return wrapper
