# boot.py - 在CircuitPython启动时运行

import storage
import microcontroller

# 如果需要禁用USB存储（可选）
storage.disable_usb_drive()

# 设置下次复位时运行正常模式
microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)

# 确保HID设备已启用
# 默认情况下，CircuitPython会启用键盘和鼠标HID设备