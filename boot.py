# boot.py - 在CircuitPython启动时运行

import microcontroller
import storage
import usb_cdc
import usb_hid
import usb_midi

# 启用USB CDC（串口）用于调试和统计
usb_cdc.enable(console=True, data=False)

# 禁用USB MIDI
usb_midi.disable()

# 禁用USB HID
usb_hid.disable()

# 如果需要禁用USB存储（可选）
storage.disable_usb_drive()

# 启用USB HID MOUSE
usb_hid.enable((usb_hid.Device.MOUSE,))  # 只启用鼠标

# 设置下次复位时运行正常模式
microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)