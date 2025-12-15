"""
打包工具：将所有 Python 模块打包成单个 code.py 文件
"""

import os
import re
from pathlib import Path


def extract_imports(file_path):
    """提取文件中的本地模块导入"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    imports = set()
    # 匹配 from xxx import ...
    for match in re.finditer(r'from\s+(\w+)\s+import', content):
        module = match.group(1)
        if not module.startswith('adafruit') and module not in ['time', 'usb_hid', 'random', 'math', 'board', 'neopixel', 'gc', 'sys']:
            imports.add(module)
    
    # 匹配 import xxx
    for match in re.finditer(r'^import\s+(\w+)', content, re.MULTILINE):
        module = match.group(1)
        if not module.startswith('adafruit') and module not in ['time', 'usb_hid', 'random', 'math', 'board', 'neopixel', 'gc', 'sys']:
            imports.add(module)
    
    return imports


def collect_all_modules(entry_file, src_dir):
    """递归收集所有依赖的模块"""
    visited = set()
    to_visit = {Path(entry_file).stem}
    module_order = []
    
    while to_visit:
        module = to_visit.pop()
        if module in visited:
            continue
        
        visited.add(module)
        module_file = src_dir / f"{module}.py"
        
        if not module_file.exists():
            continue
        
        # 提取这个模块的导入
        imports = extract_imports(module_file)
        
        # 添加新的依赖到待访问列表
        for imp in imports:
            if imp not in visited:
                to_visit.add(imp)
        
        # 记录模块顺序（被依赖的模块要放在前面）
        if module not in module_order:
            module_order.insert(0, module)
    
    # 移除 main，它应该最后处理
    if 'main' in module_order:
        module_order.remove('main')
    
    return module_order


def remove_imports(content, local_modules):
    """移除本地模块的导入语句"""
    lines = content.split('\n')
    result_lines = []
    
    for line in lines:
        # 跳过本地模块的导入
        is_local_import = False
        for module in local_modules:
            if f'from {module} import' in line or f'import {module}' in line:
                is_local_import = True
                break
        
        if not is_local_import:
            result_lines.append(line)
    
    return '\n'.join(result_lines)


def build_single_file(src_dir, entry_file, output_file):
    """构建单文件版本"""
    src_dir = Path(src_dir)
    output_file = Path(output_file)
    
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 收集所有模块
    print("收集依赖模块...")
    modules = collect_all_modules(entry_file, src_dir)
    print(f"找到 {len(modules)} 个模块: {', '.join(modules)}")
    
    # 读取 main.py
    main_file = src_dir / "main.py"
    with open(main_file, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # 构建输出内容
    output_lines = []
    output_lines.append('"""')
    output_lines.append('鼠标移动模拟器 - 单文件打包版本')
    output_lines.append('自动生成，请勿手动编辑')
    output_lines.append('"""')
    output_lines.append('')
    
    # 添加 main.py 的标准库导入
    output_lines.append('# 标准库和外部库导入')
    for line in main_content.split('\n'):
        if line.startswith('import ') or line.startswith('from '):
            # 只保留非本地模块的导入
            is_local = False
            for module in modules:
                if f'from {module}' in line or f'import {module}' == line.strip():
                    is_local = True
                    break
            if not is_local:
                output_lines.append(line)
    output_lines.append('')
    output_lines.append('')
    
    # 按依赖顺序添加各模块内容
    all_modules = set(modules)
    for module in modules:
        module_file = src_dir / f"{module}.py"
        if not module_file.exists():
            continue
        
        print(f"打包模块: {module}")
        
        with open(module_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 移除导入和文档字符串开头
        content = remove_imports(content, all_modules)
        
        # 移除开头的文档字符串
        content = re.sub(r'^"""[\s\S]*?"""', '', content).lstrip()
        
        output_lines.append(f'# ===== {module}.py =====')
        output_lines.append(content)
        output_lines.append('')
        output_lines.append('')
    
    # 添加 main.py 的主要逻辑（移除导入部分）
    output_lines.append('# ===== main.py =====')
    main_code_lines = []
    in_import_section = True
    for line in main_content.split('\n'):
        # 跳过文档字符串和导入部分
        if line.startswith('"""'):
            continue
        if line.startswith('import ') or line.startswith('from '):
            continue
        if line.strip() == '':
            if in_import_section:
                continue
        else:
            in_import_section = False
        
        main_code_lines.append(line)
    
    output_lines.extend(main_code_lines)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"\n✅ 打包完成: {output_file}")
    print(f"文件大小: {output_file.stat().st_size} 字节")


if __name__ == "__main__":
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    entry_file = src_dir / "main.py"
    output_file = project_root / "dist" / "code.py"
    
    build_single_file(src_dir, entry_file, output_file)
