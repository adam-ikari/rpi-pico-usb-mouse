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
        
        current_time = time.monotonic()
        frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        if frame_time > self.max_frame_time:
            self.max_frame_time = frame_time
        if frame_time < self.min_frame_time:
            self.min_frame_time = frame_time
        
        if len(self.frame_times) < 100:
            self.frame_times.append(frame_time)
        else:
            self.frame_times[self.loop_count % 100] = frame_time
    
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
        
        if hasattr(gc, 'mem_free'):
            mem_free = gc.mem_free()
            if mem_free < self.mem_free_min:
                self.mem_free_min = mem_free
    
    def get_avg_frame_time(self):
        if not self.frame_times:
            return 0
        return sum(self.frame_times) / len(self.frame_times)
    
    def get_fps(self):
        avg_frame_time = self.get_avg_frame_time()
        if avg_frame_time > 0:
            return 1.0 / avg_frame_time
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
            return "Performance stats disabled"
        
        uptime = self.get_uptime()
        avg_fps = self.get_fps()
        
        report = []
        report.append("=== Performance Report ===")
        report.append(f"Uptime: {uptime:.1f}s")
        report.append(f"Loop count: {self.loop_count}")
        report.append(f"Avg FPS: {avg_fps:.1f}")
        report.append(f"Frame time: avg={self.get_avg_frame_time()*1000:.2f}ms min={self.min_frame_time*1000:.2f}ms max={self.max_frame_time*1000:.2f}ms")
        
        if hasattr(gc, 'mem_free'):
            mem_free = gc.mem_free()
            mem_used = self.mem_free_start - mem_free
            mem_peak = self.mem_free_start - self.mem_free_min
            report.append(f"Memory: free={mem_free}B used={mem_used}B peak={mem_peak}B")
        
        report.append("Mode switches:")
        for mode, count in self.mode_counts.items():
            report.append(f"  {mode}: {count}")
        
        report.append(f"Bezier calcs: {self.bezier_calc_count}")
        report.append(f"Trig calls: {self.trig_call_count}")
        
        return "\n".join(report)
    
    def print_report(self):
        print(self.get_report())
    
    def reset(self):
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
