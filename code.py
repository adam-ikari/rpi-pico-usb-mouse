import time
import usb_hid
import random
from adafruit_hid.mouse import Mouse

# Initialize the Mouse object
mouse = Mouse(usb_hid.devices)

def quick_move_to_target(end_x, end_y):
    """
    快速移动鼠标到目标位置
    """
    # 计算当前位置到目标位置的距离
    distance = ((end_x - 0) ** 2 + (end_y - 0) ** 2) ** 0.5
    
    # 计算需要的移动步数（较少的步数实现快速移动）
    steps = max(int(distance / 20), 1)  # 每步移动约20像素，快速移动
    
    step_x = end_x / steps
    step_y = end_y / steps
    
    for i in range(steps):
        mouse.move(x=int(step_x), y=int(step_y))
        # 快速移动时延迟较短
        time.sleep(random.uniform(0.005, 0.02))

def smooth_mouse_move_small(start_x, start_y, end_x, end_y):
    """
    在小范围内平滑移动鼠标，模拟到达目标后的精确移动
    """
    # 计算距离，使用较小的步长以实现平滑移动
    distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
    steps = max(int(distance / 2), 5)  # 较小的步长，更平滑
    
    step_x = (end_x - start_x) / steps
    step_y = (end_y - start_y) / steps
    
    for i in range(steps):
        # 添加轻微的随机偏移，模拟人为移动的不精确性
        offset_x = random.uniform(-0.5, 0.5)
        offset_y = random.uniform(-0.5, 0.5)
        
        # 计算实际移动的增量
        actual_x = step_x + offset_x
        actual_y = step_y + offset_y
        
        mouse.move(x=int(actual_x), y=int(actual_y))
        
        # 较慢的速度以实现平滑移动
        time.sleep(random.uniform(0.02, 0.06))

def simulate_web_browsing():
    """
    模拟浏览网页时的鼠标漫游效果：快速移动到目标位置，然后小范围移动
    """
    # 生成大范围的随机移动目标位置
    target_x = random.randint(-200, 200)
    target_y = random.randint(-200, 200)
    
    # 快速移动到目标位置
    quick_move_to_target(target_x, target_y)
    
    # 在目标位置附近做一些小的平滑移动，模拟阅读或寻找内容
    current_x, current_y = target_x, target_y
    for _ in range(random.randint(4, 8)):
        small_move_x = random.randint(-25, 25)
        small_move_y = random.randint(-25, 25)
        smooth_mouse_move_small(current_x, current_y, current_x + small_move_x, current_y + small_move_y)
        
        # 更新当前位置
        current_x += small_move_x
        current_y += small_move_y
        time.sleep(random.uniform(0.3, 1.0))

def simulate_page_scanning():
    """
    模拟扫描页面内容的鼠标移动：快速移动到起始点，然后水平扫描
    """
    # 随机选择起始点
    start_x = random.randint(-180, -120)
    start_y = random.randint(-180, 180)
    
    # 快速移动到起始点
    quick_move_to_target(start_x, start_y)
    
    # 从起始点向右水平移动，模拟阅读行为
    end_x = random.randint(120, 180)
    distance = end_x - start_x
    steps = max(int(distance / 15), 1)  # 每步移动约15像素
    step_x = distance / steps
    
    for i in range(steps):
        mouse.move(x=int(step_x), y=0)
        time.sleep(random.uniform(0.01, 0.03))
    
    time.sleep(random.uniform(0.5, 1.5))

def simulate_exploratory_movement():
    """
    模拟探索性的鼠标移动：快速跳转到不同区域
    """
    # 生成一个随机位置
    target_x = random.randint(-180, 180)
    target_y = random.randint(-180, 180)
    
    # 快速移动到该位置
    quick_move_to_target(target_x, target_y)
    
    # 在该区域进行探索性的小范围移动
    current_x, current_y = target_x, target_y
    for _ in range(random.randint(3, 6)):
        direction_x = random.randint(-40, 40)
        direction_y = random.randint(-40, 40)
        smooth_mouse_move_small(current_x, current_y, current_x + direction_x, current_y + direction_y)
        
        # 更新当前位置
        current_x += direction_x
        current_y += direction_y
        
        time.sleep(random.uniform(0.4, 1.0))

while True:
    # 随机选择一种浏览行为
    action = random.choice([
        "web_browsing",     # 网页浏览漫游
        "page_scanning",    # 页面扫描
        "exploratory_move"  # 探索性移动
    ])
    
    if action == "web_browsing":
        # 执行网页浏览时的鼠标漫游
        simulate_web_browsing()
        time.sleep(random.uniform(1, 3))
    
    elif action == "page_scanning":
        # 模拟扫描页面内容
        simulate_page_scanning()
        time.sleep(random.uniform(1, 2))
    
    elif action == "exploratory_move":
        # 模拟探索性移动
        simulate_exploratory_movement()
        time.sleep(random.uniform(1, 2))
    
    # 随机等待时间，模拟人类浏览网页的节奏
    time.sleep(random.uniform(2, 6))