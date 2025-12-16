"""
打包工具：将所有 Python 模块打包成单个 code.py 文件，并按 5KB 拆分
"""

import os
import re
import shutil
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


def remove_comments_and_docstrings(content):
    """删除代码中的注释和文档字符串"""
    lines = content.split('\n')
    result_lines = []
    in_multiline_string = False
    multiline_quote = None
    skip_docstring = False
    last_non_empty_was_def_or_class = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 检测多行字符串的开始/结束
        if not in_multiline_string:
            # 检查是否是文档字符串（在 def/class 后的第一个字符串）
            if (stripped.startswith('"""') or stripped.startswith("'''")) and last_non_empty_was_def_or_class:
                quote = '"""' if stripped.startswith('"""') else "'''"
                # 检查是否是单行文档字符串
                if stripped.count(quote) >= 2:
                    # 单行文档字符串，跳过
                    last_non_empty_was_def_or_class = False
                    continue
                else:
                    # 多行文档字符串开始
                    in_multiline_string = True
                    multiline_quote = quote
                    skip_docstring = True
                    continue
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                quote = '"""' if stripped.startswith('"""') else "'''"
                # 普通多行字符串（不是文档字符串）
                if stripped.count(quote) >= 2:
                    # 单行字符串，保留
                    result_lines.append(line)
                else:
                    in_multiline_string = True
                    multiline_quote = quote
                    skip_docstring = False
                    result_lines.append(line)
                last_non_empty_was_def_or_class = False
                continue
        else:
            # 在多行字符串中
            if multiline_quote in stripped:
                in_multiline_string = False
                multiline_quote = None
                if skip_docstring:
                    skip_docstring = False
                    last_non_empty_was_def_or_class = False
                    continue
                else:
                    result_lines.append(line)
                continue
            else:
                if skip_docstring:
                    continue
                else:
                    result_lines.append(line)
                continue
        
        # 删除单行注释
        if '#' in line:
            # 检查 # 是否在字符串中
            in_string = False
            quote_char = None
            for j, char in enumerate(line):
                if char in ['"', "'"] and (j == 0 or line[j-1] != '\\'):
                    if not in_string:
                        in_string = True
                        quote_char = char
                    elif char == quote_char:
                        in_string = False
                        quote_char = None
                elif char == '#' and not in_string:
                    # 找到注释，截断行
                    line = line[:j].rstrip()
                    break
        
        # 跳过空行（可选：保留一些空行以提高可读性）
        if stripped == '':
            # 保留空行
            result_lines.append(line)
        else:
            result_lines.append(line)
            # 检查是否是 def 或 class 定义
            if stripped.startswith('def ') or stripped.startswith('class '):
                last_non_empty_was_def_or_class = True
            else:
                last_non_empty_was_def_or_class = False
    
    return '\n'.join(result_lines)


def compress_code(content):
    """压缩代码：将代码尽可能放到一行，仅保留必要的换行"""
    lines = content.split('\n')
    compressed_code = []
    current_line = ""
    indent_level = 0
    
    for line in lines:
        stripped = line.strip()
        
        # 跳过空行
        if stripped == '':
            continue
            
        # 计算当前行的缩进级别
        line_indent = len(line) - len(line.lstrip())
        
        # 检查是否需要换行（控制结构）
        needs_newline = False
        if stripped.startswith(('def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ')):
            needs_newline = True
        
        # 检查是否是缩进减少的情况
        if line_indent < indent_level and current_line:
            needs_newline = True
        
        # 如果需要换行且当前行不为空，先添加当前行
        if needs_newline and current_line:
            compressed_code.append(current_line)
            current_line = ""
        
        # 添加当前行内容
        if current_line:
            current_line += " " + stripped
        else:
            current_line = stripped
        
        # 更新缩进级别
        if ':' in stripped and not stripped.startswith('#'):
            # 有冒号的行通常表示新块开始
            indent_level = line_indent + 4
        else:
            indent_level = line_indent
    
    # 添加最后一行
    if current_line:
        compressed_code.append(current_line)
    
    return '\n'.join(compressed_code)


def split_file_by_size(input_file, chunk_size_kb=5):
    """按指定大小(KB)拆分文件"""
    chunk_size = chunk_size_kb * 1024  # 转换为字节
    input_file = Path(input_file)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 计算需要拆分的文件数量
    total_size = len(content.encode('utf-8'))
    num_chunks = (total_size + chunk_size - 1) // chunk_size
    
    print(f"文件总大小: {total_size} 字节 ({total_size/1024:.2f} KB)")
    print(f"拆分成 {num_chunks} 个文件，每个约 {chunk_size_kb} KB")
    
    # 拆分文件
    for i in range(num_chunks):
        start_pos = i * chunk_size
        end_pos = min((i + 1) * chunk_size, total_size)
        
        # 确保不在多字节字符中间拆分
        chunk_content = content.encode('utf-8')[start_pos:end_pos].decode('utf-8', errors='ignore')
        
        # 生成文件名
        base_name = input_file.stem
        ext = input_file.suffix
        chunk_file = input_file.parent / f"{base_name}_part{i+1}{ext}"
        
        # 写入拆分文件
        with open(chunk_file, 'w', encoding='utf-8') as f:
            f.write(chunk_content)
        
        print(f"✅ 已创建: {chunk_file.name} ({len(chunk_content)} 字节)")
    
    # 删除原始文件
    input_file.unlink()
    print(f"✅ 已删除原始文件: {input_file.name}")


def build_single_file(src_dir, entry_file, output_file, production_mode=True):
    """构建单文件版本"""
    src_dir = Path(src_dir)
    entry_file = Path(entry_file)
    output_file = Path(output_file)
    
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 收集所有模块
    print("收集依赖模块...")
    modules = collect_all_modules(entry_file, src_dir)
    print(f"找到 {len(modules)} 个模块: {', '.join(modules)}")
    
    # 读取入口文件 (main.py)
    with open(entry_file, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # 构建输出内容
    output_lines = []
    
    if production_mode:
        # 生产模式：不添加文档字符串和注释
        # 添加 main.py 的标准库导入
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
    else:
        # 开发模式：保留文档字符串和注释
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
        
        # 移除导入
        content = remove_imports(content, all_modules)
        
        if production_mode:
            # 生产模式：移除开头的文档字符串、注释和压缩
            content = re.sub(r'^"""[\s\S]*?"""', '', content).lstrip()
            content = remove_comments_and_docstrings(content)
            content = compress_code(content)
            output_lines.append(content)
        else:
            # 开发模式：保留原始格式
            output_lines.append(f'# ===== {module}.py =====')
            output_lines.append(content)
            output_lines.append('')
            output_lines.append('')
    
    # 添加 main.py 的主要逻辑（移除导入部分）
    if production_mode:
        # 生产模式：直接添加处理后的代码
        main_code_lines = []
        for line in main_content.split('\n'):
            # 跳过文档字符串和导入部分
            if line.startswith('"""'):
                continue
            if line.startswith('import ') or line.startswith('from '):
                continue
            main_code_lines.append(line)
        
        # 删除 main.py 中的注释和文档字符串
        main_code = '\n'.join(main_code_lines)
        main_code = remove_comments_and_docstrings(main_code)
        main_code = compress_code(main_code)
        
        output_lines.append(main_code)
    else:
        # 开发模式：保留模块分隔符
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
    import sys
    
    project_root = Path(__file__).parent
    src_dir = project_root / "src"  # 使用 src 目录作为源目录
    entry_file = src_dir / "main.py"  # 入口文件为 main.py
    dist_dir = project_root / "dist"
    
    # 默认为开发模式
    mode = "dev"
    split_files = False
    
    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--prod":
            mode = "prod"
        elif sys.argv[1] == "--dev":
            mode = "dev"
        else:
            print("用法: python build.py [--dev|--prod] [--split]")
            print("  --dev   开发模式（默认）：不合并代码，保留原始格式")
            print("  --prod  生产模式：合并代码，删除空行、注释和文档")
            print("  --split 拆分文件为5KB大小（仅生产模式有效）")
            sys.exit(1)
    
    if len(sys.argv) > 2 and sys.argv[2] == "--split":
        split_files = True
    
    if mode == "dev":
        print("🔧 开发模式：复制原始文件到 dist/ 目录")
        
        # 确保输出目录存在
        dist_dir.mkdir(parents=True, exist_ok=True)
        
        # 复制所有源文件到 dist 目录
        for py_file in src_dir.glob("*.py"):
            dst_file = dist_dir / py_file.name
            shutil.copy2(py_file, dst_file)
            print(f"✅ 已复制: {py_file.name}")
        
        # 复制 boot.py
        boot_src = project_root / "boot.py"
        boot_dst = dist_dir / "boot.py"
        if boot_src.exists():
            shutil.copy2(boot_src, boot_dst)
            print(f"✅ 已复制: boot.py")
        
        # 复制 lib 文件夹
        lib_src = project_root / "lib"
        lib_dst = dist_dir / "lib"
        if lib_src.exists():
            if lib_dst.exists():
                shutil.rmtree(lib_dst)
            shutil.copytree(lib_src, lib_dst)
            print(f"✅ 已复制: lib/ 文件夹")
            
    else:  # prod mode
        print("🏭 生产模式：合并并压缩代码")
        output_file = dist_dir / "code.py"  # 输出文件名为 code.py
        
        # 打包 Python 代码
        build_single_file(src_dir, entry_file, output_file, production_mode=True)
        
        # 检查是否需要拆分文件
        if split_files:
            # 按大小拆分文件
            split_file_by_size(output_file, chunk_size_kb=5)
        
        # 复制 boot.py
        boot_src = project_root / "boot.py"
        boot_dst = dist_dir / "boot.py"
        if boot_src.exists():
            shutil.copy2(boot_src, boot_dst)
            print(f"✅ 已复制: boot.py")
        
        # 复制 lib 文件夹
        lib_src = project_root / "lib"
        lib_dst = dist_dir / "lib"
        if lib_src.exists():
            if lib_dst.exists():
                shutil.rmtree(lib_dst)
            shutil.copytree(lib_src, lib_dst)
            print(f"✅ 已复制: lib/ 文件夹")
    
    print(f"\n📦 {mode}模式打包完成! 所有文件已输出到 dist/ 目录")
    
    # 复制 boot.py
    boot_src = project_root / "boot.py"
    boot_dst = dist_dir / "boot.py"
    if boot_src.exists():
        shutil.copy2(boot_src, boot_dst)
        print(f"✅ 已复制: boot.py")
    
    # 复制 lib 文件夹
    lib_src = project_root / "lib"
    lib_dst = dist_dir / "lib"
    if lib_src.exists():
        if lib_dst.exists():
            shutil.rmtree(lib_dst)
        shutil.copytree(lib_src, lib_dst)
        print(f"✅ 已复制: lib/ 文件夹")
    
    print(f"\n📦 打包完成! 所有文件已输出到 dist/ 目录")