# 定点数系统说明

## 概述

为了在无 FPU 的 RP2040 上获得最佳性能，项目使用定点数代替浮点数运算。

## 定点数格式

### 1. 百分比格式 (×100)
用于表示 0.00-1.00 范围的值
- `100` = `1.0`
- `50` = `0.5`
- `1` = `0.01`

**使用场景：**
- 速度因子
- 概率值
- 偏移量

**转换函数：**
```python
from fast_math import percent_to_float, float_to_percent

# 定点数转浮点
value = percent_to_float(150)  # 150 -> 1.5

# 浮点转定点数
fixed = float_to_percent(0.75)  # 0.75 -> 75
```

### 2. 三角函数格式 (×10000)
用于存储三角函数查找表
- `10000` = `1.0`
- `5000` = `0.5`

**转换函数：**
```python
from fast_math import trig_to_float

value = trig_to_float(7071)  # 7071 -> 0.7071 (sin 45°)
```

### 3. 16.16 定点数
用于高精度计算
- 16位整数部分 + 16位小数部分
- `65536` = `1.0`

**运算函数：**
```python
from fast_math import fixed_mul, fixed_div, int_to_fixed

a = int_to_fixed(3)  # 3 -> 196608
b = int_to_fixed(2)  # 2 -> 131072
result = fixed_mul(a, b)  # 3 * 2 = 6
```

## 常量定义规则

### constants.py 中的定点数常量

所有浮点常量都以整数形式存储（×100）：

```python
# ❌ 旧方式（浮点）
ACCEL_START_FACTOR = 0.01
THINK_PAUSE_PROBABILITY = 0.15

# ✅ 新方式（定点数）
ACCEL_START_FACTOR = 1      # 表示 0.01
THINK_PAUSE_PROBABILITY = 15  # 表示 0.15
```

## 使用示例

### 速度曲线计算
```python
from fast_math import percent_to_float

# 计算加速因子
factor = 1 + (99 * t_sq_scaled) // 100  # 整数运算
profile.append(percent_to_float(factor))  # 转为浮点
```

### 概率比较
```python
from fast_math import percent_to_float

# 检查是否暂停
if random_pool.random() < percent_to_float(THINK_PAUSE_PROBABILITY):
    pause()
```

### 偏移量计算
```python
from fast_math import percent_to_float

offset = random_pool.uniform(SMALL_MOVE_OFFSET_MIN, SMALL_MOVE_OFFSET_MAX)
actual_offset = percent_to_float(offset) * velocity_factor
```

## 性能优势

1. **避免浮点运算**：整数运算比浮点快 3-10 倍
2. **节省内存**：整数常量占用更少空间
3. **更精确**：避免浮点精度问题
4. **可维护性**：统一的转换接口

### 实测性能数据

**定点数优化后实测**（RP2040 @ 133MHz）：

**5分钟稳定性测试**（35230个循环）：
- 平均帧率: **116.1 FPS**
- 帧时间: 最小 1.0ms / 平均 8.6ms / 最大 22.0ms
- 内存占用: 74KB 可用，峰值使用 72KB
- 数学运算: 贝塞尔 103次 / 三角函数 238次
- 模式分布: 页面扫描 33% / 随机移动 25% / 网页浏览 20%

**性能特点**：
- 平均帧时间仅 8.6ms，响应流畅
- 最坏情况 22ms，仍在可接受范围
- 内存使用稳定，无内存泄漏
- 长时间运行稳定（已测试5分钟+）

## 注意事项

1. 所有常量都以整数形式存储
2. 使用时通过 `percent_to_float()` 转换
3. 内部计算尽量使用整数
4. 只在最后需要时才转为浮点

## 迁移指南

将现有浮点常量转为定点数：

1. 将常量值乘以 100
2. 使用时调用 `percent_to_float()`
3. 更新注释说明

```python
# 迁移前
SPEED = 0.5
velocity = SPEED * factor

# 迁移后  
SPEED = 50  # 定点数，表示 0.5
velocity = percent_to_float(SPEED) * factor
```
