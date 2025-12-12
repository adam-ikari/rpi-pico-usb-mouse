#!/usr/bin/env python3
"""
构建工具 - Raspberry Pi Pico USB 鼠标模拟器
用于语法检查、打包和部署
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

class BuildTool:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build"
        self.dist_dir = self.project_root / "dist"
        
        self.source_files = [
            "boot.py",
            "code.py",
            "constants.py",
            "pin_config.py",
            "performance_stats.py",
            "serial_control.py"
        ]
        
        self.lib_dir = "lib"
    
    def clean(self):
        """清理构建目录"""
        print("🧹 清理构建目录...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print(f"  ✓ 删除 {self.build_dir}")
        
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
            print(f"  ✓ 删除 {self.dist_dir}")
        
        pycache_dirs = list(self.project_root.rglob("__pycache__"))
        for pycache in pycache_dirs:
            shutil.rmtree(pycache)
            print(f"  ✓ 删除 {pycache}")
        
        print("✅ 清理完成\n")
    
    def check_syntax(self):
        """检查 Python 语法"""
        print("🔍 检查 Python 语法...")
        
        errors = []
        for file in self.source_files:
            file_path = self.project_root / file
            if not file_path.exists():
                print(f"  ⚠️  文件不存在: {file}")
                continue
            
            try:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", str(file_path)],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root
                )
                
                if result.returncode == 0:
                    print(f"  ✓ {file}")
                else:
                    print(f"  ✗ {file}")
                    errors.append((file, result.stderr))
            except Exception as e:
                print(f"  ✗ {file}: {e}")
                errors.append((file, str(e)))
        
        if errors:
            print("\n❌ 语法检查失败:")
            for file, error in errors:
                print(f"\n{file}:")
                print(error)
            return False
        
        print("✅ 语法检查通过\n")
        return True
    
    def check_dependencies(self):
        """检查依赖库"""
        print("📚 检查依赖库...")
        
        lib_path = self.project_root / self.lib_dir
        if not lib_path.exists():
            print(f"  ❌ 依赖目录不存在: {self.lib_dir}")
            return False
        
        required_libs = [
            "adafruit_hid/__init__.mpy",
            "adafruit_hid/mouse.mpy",
            "neopixel.mpy"
        ]
        
        missing = []
        for lib in required_libs:
            lib_file = lib_path / lib
            if lib_file.exists():
                print(f"  ✓ {lib}")
            else:
                print(f"  ✗ {lib}")
                missing.append(lib)
        
        if missing:
            print(f"\n❌ 缺少依赖库: {', '.join(missing)}")
            return False
        
        print("✅ 依赖检查通过\n")
        return True
    
    def compress_code(self, src_path, dst_path):
        """压缩 Python 代码：移除注释和多余空行"""
        with open(src_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        compressed_lines = []
        in_docstring = False
        docstring_char = None
        
        for line in lines:
            stripped = line.strip()
            
            # 检测文档字符串
            if '"""' in stripped or "'''" in stripped:
                if not in_docstring:
                    docstring_char = '"""' if '"""' in stripped else "'''"
                    in_docstring = True
                    compressed_lines.append(line)
                    if stripped.count(docstring_char) >= 2:
                        in_docstring = False
                    continue
                else:
                    compressed_lines.append(line)
                    if docstring_char in stripped:
                        in_docstring = False
                    continue
            
            # 在文档字符串内，保留原样
            if in_docstring:
                compressed_lines.append(line)
                continue
            
            # 跳过空行和纯注释行
            if not stripped or stripped.startswith('#'):
                continue
            
            # 移除行尾注释（保留字符串中的 #）
            in_string = False
            string_char = None
            clean_line = []
            i = 0
            while i < len(line):
                char = line[i]
                
                # 处理字符串
                if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                
                # 移除注释（不在字符串内）
                if char == '#' and not in_string:
                    break
                
                clean_line.append(char)
                i += 1
            
            result = ''.join(clean_line).rstrip()
            if result:
                compressed_lines.append(result + '\n')
        
        with open(dst_path, 'w', encoding='utf-8') as f:
            f.writelines(compressed_lines)
    
    def compile_to_mpy(self, src_path, dst_path):
        """使用 mpy-cross 编译为 .mpy 文件"""
        try:
            result = subprocess.run(
                ["mpy-cross", str(src_path), "-o", str(dst_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True
            else:
                print(f"    ⚠️  mpy-cross 错误: {result.stderr}")
                return False
        except FileNotFoundError:
            print(f"    ⚠️  未找到 mpy-cross，请安装: pip install mpy-cross")
            return False
        except Exception as e:
            print(f"    ⚠️  编译失败: {e}")
            return False
    
    def build(self, compress=False, mpy=False):
        """构建项目"""
        print("🔨 构建项目...")
        if compress:
            print("  📦 启用代码压缩")
        if mpy:
            print("  ⚙️  启用 .mpy 编译")
        
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        
        total_original_size = 0
        total_compressed_size = 0
        
        for file in self.source_files:
            src = self.project_root / file
            if not src.exists():
                print(f"  ⚠️  跳过不存在的文件: {file}")
                continue
            
            if mpy:
                # 编译为 .mpy
                mpy_file = file.replace('.py', '.mpy')
                dst = self.dist_dir / mpy_file
                
                # 如果启用压缩，先压缩再编译
                if compress:
                    temp_py = self.build_dir / file
                    original_size = src.stat().st_size
                    self.compress_code(src, temp_py)
                    compressed_size = temp_py.stat().st_size
                    
                    if self.compile_to_mpy(temp_py, dst):
                        mpy_size = dst.stat().st_size
                        total_original_size += original_size
                        total_compressed_size += mpy_size
                        reduction = (1 - mpy_size / original_size) * 100
                        print(f"  ✓ 编译 {file} → {mpy_file} ({original_size}B → {mpy_size}B, -{reduction:.1f}%)")
                    else:
                        # 编译失败，回退到复制 .py
                        shutil.copy2(src, self.dist_dir / file)
                        print(f"  ✓ 回退复制 {file}")
                else:
                    original_size = src.stat().st_size
                    if self.compile_to_mpy(src, dst):
                        mpy_size = dst.stat().st_size
                        total_original_size += original_size
                        total_compressed_size += mpy_size
                        reduction = (1 - mpy_size / original_size) * 100
                        print(f"  ✓ 编译 {file} → {mpy_file} ({original_size}B → {mpy_size}B, -{reduction:.1f}%)")
                    else:
                        # 编译失败，回退到复制 .py
                        shutil.copy2(src, self.dist_dir / file)
                        print(f"  ✓ 回退复制 {file}")
            else:
                # 普通构建
                dst = self.dist_dir / file
                
                if compress:
                    original_size = src.stat().st_size
                    self.compress_code(src, dst)
                    compressed_size = dst.stat().st_size
                    total_original_size += original_size
                    total_compressed_size += compressed_size
                    reduction = (1 - compressed_size / original_size) * 100
                    print(f"  ✓ 压缩 {file} ({original_size}B → {compressed_size}B, -{reduction:.1f}%)")
                else:
                    shutil.copy2(src, dst)
                    print(f"  ✓ 复制 {file}")
        
        lib_src = self.project_root / self.lib_dir
        lib_dst = self.dist_dir / self.lib_dir
        if lib_src.exists():
            shutil.copytree(lib_src, lib_dst, dirs_exist_ok=True)
            print(f"  ✓ 复制 {self.lib_dir}/")
        
        if (compress or mpy) and total_original_size > 0:
            total_reduction = (1 - total_compressed_size / total_original_size) * 100
            print(f"\n  📊 总计: {total_original_size}B → {total_compressed_size}B (-{total_reduction:.1f}%)")
        
        print(f"✅ 构建完成: {self.dist_dir}\n")
        return True
    
    def merge_files(self):
        """合并所有源文件为单个 code.py"""
        print("🔗 合并源文件...")
        
        merged_file = self.dist_dir / "code.py"
        
        # 合并顺序：constants -> pin_config -> performance_stats -> serial_control -> code
        merge_order = [
            "constants.py",
            "pin_config.py", 
            "performance_stats.py",
            "serial_control.py",
            "code.py"
        ]
        
        with open(merged_file, 'w', encoding='utf-8') as outfile:
            outfile.write('# Merged file - Auto-generated by build.py\n')
            outfile.write('# DO NOT EDIT MANUALLY\n\n')
            
            for file in merge_order:
                src = self.project_root / file
                if not src.exists():
                    print(f"  ⚠️  跳过不存在的文件: {file}")
                    continue
                
                outfile.write(f'\n# ==================== {file} ====================\n\n')
                
                with open(src, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    
                    # 移除重复的 import 语句
                    lines = content.split('\n')
                    filtered_lines = []
                    
                    for line in lines:
                        # 跳过从其他模块导入的语句
                        if line.strip().startswith('from constants import'):
                            continue
                        if line.strip().startswith('from pin_config import'):
                            continue
                        if line.strip().startswith('from performance_stats import'):
                            continue
                        if line.strip().startswith('from serial_control import'):
                            continue
                        
                        filtered_lines.append(line)
                    
                    outfile.write('\n'.join(filtered_lines))
                    outfile.write('\n')
                
                print(f"  ✓ 合并 {file}")
        
        # 复制 boot.py
        boot_src = self.project_root / "boot.py"
        boot_dst = self.dist_dir / "boot.py"
        if boot_src.exists():
            shutil.copy2(boot_src, boot_dst)
            print(f"  ✓ 复制 boot.py")
        
        merged_size = merged_file.stat().st_size
        print(f"\n  📊 合并文件大小: {merged_size}B ({merged_size/1024:.1f}KB)")
        print(f"✅ 合并完成: {merged_file}\n")
        return True
    
    def package(self):
        """打包为压缩文件"""
        print("📦 打包项目...")
        
        archive_name = "rpi-pico-usb-mouse"
        archive_path = self.build_dir / archive_name
        
        shutil.make_archive(
            str(archive_path),
            'zip',
            self.dist_dir
        )
        
        zip_file = archive_path.with_suffix('.zip')
        print(f"✅ 打包完成: {zip_file}\n")
        return zip_file
    
    def get_version(self):
        """获取版本信息"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return "unknown"
    
    def info(self):
        """显示项目信息"""
        print("ℹ️  项目信息:")
        print(f"  项目根目录: {self.project_root}")
        print(f"  版本: {self.get_version()}")
        print(f"  源文件数: {len(self.source_files)}")
        print()

def main():
    tool = BuildTool()
    
    if len(sys.argv) < 2:
        print("用法: python3 build.py [命令] [选项]")
        print("\n可用命令:")
        print("  clean    - 清理构建目录")
        print("  check    - 检查语法和依赖")
        print("  build    - 构建项目")
        print("  merge    - 合并所有文件为单个 code.py")
        print("  package  - 打包为 ZIP")
        print("  all      - 执行完整构建流程")
        print("  info     - 显示项目信息")
        print("\n选项:")
        print("  --compress  - 压缩代码（移除注释和空行）")
        print("  --mpy       - 编译为 .mpy 字节码文件")
        print("\n示例:")
        print("  python3 build.py build --compress --mpy")
        print("  python3 build.py merge --compress")
        sys.exit(1)
    
    command = sys.argv[1]
    compress = "--compress" in sys.argv
    mpy = "--mpy" in sys.argv
    
    if command == "clean":
        tool.clean()
    
    elif command == "check":
        tool.info()
        if not tool.check_syntax():
            sys.exit(1)
        if not tool.check_dependencies():
            sys.exit(1)
    
    elif command == "build":
        tool.info()
        if not tool.check_syntax():
            sys.exit(1)
        if not tool.check_dependencies():
            sys.exit(1)
        if not tool.build(compress=compress, mpy=mpy):
            sys.exit(1)
    
    elif command == "package":
        tool.info()
        if not tool.check_syntax():
            sys.exit(1)
        if not tool.check_dependencies():
            sys.exit(1)
        if not tool.build(compress=compress, mpy=mpy):
            sys.exit(1)
        tool.package()
    
    elif command == "all":
        tool.clean()
        tool.info()
        if not tool.check_syntax():
            sys.exit(1)
        if not tool.check_dependencies():
            sys.exit(1)
        if not tool.build(compress=compress, mpy=mpy):
            sys.exit(1)
        tool.package()
        print("🎉 完整构建流程执行成功!")
    
    elif command == "merge":
        tool.clean()
        tool.info()
        if not tool.check_syntax():
            sys.exit(1)
        if not tool.check_dependencies():
            sys.exit(1)
        
        # 先构建临时文件
        tool.build_dir.mkdir(exist_ok=True)
        tool.dist_dir.mkdir(exist_ok=True)
        
        if compress:
            print("  📦 启用代码压缩")
            for file in tool.source_files:
                if file == "boot.py":
                    continue
                src = tool.project_root / file
                if src.exists():
                    dst = tool.build_dir / file
                    tool.compress_code(src, dst)
        
        if not tool.merge_files():
            sys.exit(1)
        
        # 复制 lib 目录
        lib_src = tool.project_root / tool.lib_dir
        lib_dst = tool.dist_dir / tool.lib_dir
        if lib_src.exists():
            shutil.copytree(lib_src, lib_dst, dirs_exist_ok=True)
            print(f"  ✓ 复制 {tool.lib_dir}/")
    
    elif command == "info":
        tool.info()
    
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
