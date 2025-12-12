import sys
import supervisor

class SerialControl:
    def __init__(self, perf_stats=None):
        self.perf_stats = perf_stats
        self.buffer = ""
        self.serial_available = hasattr(supervisor, 'runtime') and supervisor.runtime.serial_connected
    
    def check_commands(self):
        if not self.serial_available:
            return
        
        if not supervisor.runtime.serial_connected:
            return
        
        if supervisor.runtime.serial_bytes_available:
            data = sys.stdin.read(supervisor.runtime.serial_bytes_available)
            self.buffer += data
            
            if '\n' in self.buffer or '\r' in self.buffer:
                lines = self.buffer.replace('\r', '\n').split('\n')
                for line in lines[:-1]:
                    self._process_command(line.strip())
                self.buffer = lines[-1]
    
    def _process_command(self, cmd):
        if not cmd:
            return
        
        cmd_lower = cmd.lower()
        
        if cmd_lower == "help":
            self._print_help()
        
        elif cmd_lower == "stats on":
            if self.perf_stats:
                self.perf_stats.enable_stats = True
                print("Performance stats enabled")
            else:
                print("Performance stats not available")
        
        elif cmd_lower == "stats off":
            if self.perf_stats:
                self.perf_stats.enable_stats = False
                print("Performance stats disabled")
            else:
                print("Performance stats not available")
        
        elif cmd_lower == "report":
            if self.perf_stats:
                self.perf_stats.print_report()
            else:
                print("Performance stats not available")
        
        elif cmd_lower == "reset":
            if self.perf_stats:
                self.perf_stats.reset()
                print("Performance stats reset")
            else:
                print("Performance stats not available")
        
        elif cmd_lower == "status":
            self._print_status()
        
        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")
    
    def _print_help(self):
        print("=== Serial Control Commands ===")
        print("help       - Show this help message")
        print("stats on   - Enable performance statistics")
        print("stats off  - Disable performance statistics")
        print("report     - Print current performance report")
        print("reset      - Reset performance statistics")
        print("status     - Show current status")
        print("===============================")
    
    def _print_status(self):
        print("=== System Status ===")
        if self.perf_stats:
            enabled = "enabled" if self.perf_stats.enable_stats else "disabled"
            print(f"Performance stats: {enabled}")
            if self.perf_stats.enable_stats:
                print(f"Uptime: {self.perf_stats.get_uptime():.1f}s")
                print(f"Loop count: {self.perf_stats.loop_count}")
                print(f"Avg FPS: {self.perf_stats.get_fps():.1f}")
        else:
            print("Performance stats: not available")
        print("====================")
