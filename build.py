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
    
    def build(self):
        """构建项目"""
        print("🔨 构建项目...")
        
        self.build_dir.mkdir(exist_ok=True)
        self.dist_dir.mkdir(exist_ok=True)
        
        for file in self.source_files:
            src = self.project_root / file
            if not src.exists():
                print(f"  ⚠️  跳过不存在的文件: {file}")
                continue
            
            dst = self.dist_dir / file
            shutil.copy2(src, dst)
            print(f"  ✓ 复制 {file}")
        
        lib_src = self.project_root / self.lib_dir
        lib_dst = self.dist_dir / self.lib_dir
        if lib_src.exists():
            shutil.copytree(lib_src, lib_dst, dirs_exist_ok=True)
            print(f"  ✓ 复制 {self.lib_dir}/")
        
        print(f"✅ 构建完成: {self.dist_dir}\n")
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
        print("用法: python3 build.py [命令]")
        print("\n可用命令:")
        print("  clean    - 清理构建目录")
        print("  check    - 检查语法和依赖")
        print("  build    - 构建项目")
        print("  package  - 打包为 ZIP")
        print("  all      - 执行完整构建流程")
        print("  info     - 显示项目信息")
        sys.exit(1)
    
    command = sys.argv[1]
    
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
        if not tool.build():
            sys.exit(1)
    
    elif command == "package":
        tool.info()
        if not tool.check_syntax():
            sys.exit(1)
        if not tool.check_dependencies():
            sys.exit(1)
        if not tool.build():
            sys.exit(1)
        tool.package()
    
    elif command == "all":
        tool.clean()
        tool.info()
        if not tool.check_syntax():
            sys.exit(1)
        if not tool.check_dependencies():
            sys.exit(1)
        if not tool.build():
            sys.exit(1)
        tool.package()
        print("🎉 完整构建流程执行成功!")
    
    elif command == "info":
        tool.info()
    
    else:
        print(f"❌ 未知命令: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
