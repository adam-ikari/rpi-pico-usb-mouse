# boot.py - 在CircuitPython启动时运行

import storage
import microcontroller
import sys
import usb_cdc

# 如果需要禁用USB存储（可选）
storage.disable_usb_drive()

# 完全禁用串口功能
try:
    usb_cdc.disable()
except:
    pass

# 禁用串口输出
sys.stdout = None
sys.stderr = None

# 设置下次复位时运行正常模式
microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)

# 确保HID设备已启用
# 默认情况下，CircuitPython会启用键盘和鼠标HID设备