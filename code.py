import time
import usb_hid
from adafruit_hid.mouse import Mouse

# Initialize the Mouse object
mouse = Mouse(usb_hid.devices)

# Example: Move the mouse cursor
# mouse.move(x=delta_x, y=delta_y, wheel=delta_wheel)
# delta_x: horizontal movement (positive for right, negative for left)
# delta_y: vertical movement (positive for down, negative for up)
# delta_wheel: scroll wheel movement (positive for scroll up, negative for scroll down)

# Example: Click a mouse button
# mouse.click(Mouse.LEFT_BUTTON)
# mouse.click(Mouse.RIGHT_BUTTON)
# mouse.click(Mouse.MIDDLE_BUTTON)

while True:
    # Example: Move the mouse in a square pattern
    mouse.move(x=20, y=0)
    time.sleep(0.5)
    mouse.move(x=0, y=20)
    time.sleep(0.5)
    mouse.move(x=-20, y=0)
    time.sleep(0.5)
    mouse.move(x=0, y=-20)
    time.sleep(0.5)

    # Example: Click the left button every 5 seconds
    # mouse.click(Mouse.LEFT_BUTTON)
    # time.sleep(5)