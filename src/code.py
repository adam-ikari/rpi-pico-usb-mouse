"""
主程序入口
使用模块化架构的鼠标移动模拟器
"""

import time
import usb_hid
import random
import math
from adafruit_hid.mouse import Mouse
import board
import neopixel
from pin_config import LED_PIN
from constants import *
from application import MouseSimulatorApp

# Error indicator patterns
ERROR_PATTERNS = {
    'division_error': [(255, 0, 0), (0, 0, 0), (255, 0, 0)],  # Red flash
    'memory_error': [(255, 255, 0), (0, 0, 0), (255, 255, 0)],  # Yellow flash
    'import_error': [(0, 0, 255), (0, 0, 0), (0, 0, 255)],  # Blue flash
    'other_error': [(255, 0, 255), (0, 0, 0), (255, 0, 255)]  # Purple flash
}

def show_error_pattern(error_type, pixels):
    """Show error pattern using LED"""
    pattern = ERROR_PATTERNS.get(error_type, ERROR_PATTERNS['other_error'])
    for _ in range(3):
        for color in pattern:
            pixels.fill(color)
            pixels.show()
            time.sleep(0.2)


def main():
    """Main function with exception handling"""
    print("init...")
    pixels = None
    mouse = None
    try:
        # Initialize USB HID mouse device
        mouse = Mouse(usb_hid.devices)
        
        # Initialize WS2812 LED
        pixels = neopixel.NeoPixel(
            LED_PIN, 
            NUM_PIXELS, 
            brightness=DEFAULT_BRIGHTNESS, 
            auto_write=True
        )
        
        # Create and run application
        app = MouseSimulatorApp(
            mouse_device=mouse,
            pixels=pixels,
            enable_performance_stats=ENABLE_PERFORMANCE_STATS
        )
        
        app.run()
    
    except ZeroDivisionError as e:
        if pixels is not None:
            show_error_pattern('division_error', pixels)
        
    except MemoryError as e:
        if pixels is not None:
            show_error_pattern('memory_error', pixels)
        
    except ImportError as e:
        if pixels is not None:
            show_error_pattern('import_error', pixels)
        
    except Exception as e:
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
        
        if pixels is not None:
            show_error_pattern('other_error', pixels)


# 启动主程序
if __name__ == "__main__":
    main()