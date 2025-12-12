# boot.py - 在CircuitPython启动时运行

import microcontroller
import storage
import usb_cdc
import usb_hid
import usb_midi

# 串口控制（默认禁用，需要修改此行以启用调试功能）
# 如需启用串口进行调试和性能统计，请取消下一行注释并注释掉 usb_cdc.disable()
# usb_cdc.enable(console=True, data=False)
usb_cdc.disable()

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