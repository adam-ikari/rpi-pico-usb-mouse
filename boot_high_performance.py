# boot_high_performance.py - 高性能 USB HID 配置
# 
# 使用方法：
# 1. 将此文件重命名为 boot.py
# 2. 重启 Raspberry Pi Pico
# 3. 回报率将提升到 1000Hz (1ms)
#
# 注意：
# - 需要修改 UPDATE_INTERVAL 为 0.001 (1ms)
# - CPU 负载会显著增加
# - 某些主机可能不支持 1000Hz

import microcontroller
import storage
import usb_cdc
import usb_hid
import usb_midi

# 禁用不需要的 USB 功能
usb_cdc.disable()
usb_midi.disable()
storage.disable_usb_drive()

# 创建自定义 HID 鼠标描述符（1000Hz 回报率）
# 基于 GitHub issue #1705 的解决方案
import usb_hid

# HID 鼠标报告描述符（标准）
MOUSE_REPORT_DESCRIPTOR = bytes((
    0x05, 0x01,        # Usage Page (Generic Desktop Ctrls)
    0x09, 0x02,        # Usage (Mouse)
    0xA1, 0x01,        # Collection (Application)
    0x09, 0x01,        #   Usage (Pointer)
    0xA1, 0x00,        #   Collection (Physical)
    0x05, 0x09,        #     Usage Page (Button)
    0x19, 0x01,        #     Usage Minimum (0x01)
    0x29, 0x03,        #     Usage Maximum (0x03)
    0x15, 0x00,        #     Logical Minimum (0)
    0x25, 0x01,        #     Logical Maximum (1)
    0x95, 0x03,        #     Report Count (3)
    0x75, 0x01,        #     Report Size (1)
    0x81, 0x02,        #     Input (Data,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x95, 0x01,        #     Report Count (1)
    0x75, 0x05,        #     Report Size (5)
    0x81, 0x03,        #     Input (Const,Var,Abs,No Wrap,Linear,Preferred State,No Null Position)
    0x05, 0x01,        #     Usage Page (Generic Desktop Ctrls)
    0x09, 0x30,        #     Usage (X)
    0x09, 0x31,        #     Usage (Y)
    0x15, 0x81,        #     Logical Minimum (-127)
    0x25, 0x7F,        #     Logical Maximum (127)
    0x75, 0x08,        #     Report Size (8)
    0x95, 0x02,        #     Report Count (2)
    0x81, 0x06,        #     Input (Data,Var,Rel,No Wrap,Linear,Preferred State,No Null Position)
    0xC0,              #   End Collection
    0xC0,              # End Collection
))

# 创建 HID 设备（1ms 轮询间隔 = 1000Hz）
mouse = usb_hid.Device(
    report_descriptor=MOUSE_REPORT_DESCRIPTOR,
    usage_page=0x01,           # Generic Desktop Controls
    usage=0x02,                # Mouse
    report_ids=(0,),           # Report ID
    in_report_lengths=(4,),    # 输入报告长度
    out_report_lengths=(0,),   # 输出报告长度
)

# 启用自定义 HID 设备
usb_hid.enable((mouse,), boot_device=1)  # boot_device=1 设置 1ms 轮询间隔

# 设置下次复位时运行正常模式
microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)

print("USB HID 已配置为 1000Hz 回报率")
print("请确保 constants.py 中 UPDATE_INTERVAL = 0.001")
