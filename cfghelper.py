#!/usr/bin/env python3
"""
cfghelper.py - immortalwrt 配置辅助工具（Python 版）
功能：提取、同步、比较、检查配置，重置为默认配置，按分类提取配置
所有命令默认输出到 stdout
"""

import os
import sys
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Optional, Tuple

# ============ 全局配置 ============
SCRIPT_DIR = Path(__file__).resolve().parent
PARENT_DIR = SCRIPT_DIR.parent
DEFAULT_REF = Path(os.environ.get("REF_FILE", SCRIPT_DIR / "cfg-default.txt"))

# ============ 分类函数 ============
def get_category(name: str) -> str:
    """根据配置名前缀返回分类"""
    if name.startswith("CONFIG_PACKAGE_"):
        return "PACKAGE"
    if name.startswith("CONFIG_TARGET_"):
        return "TARGET"
    if name.startswith("CONFIG_KERNEL_"):
        return "KERNEL"
    if name.startswith("CONFIG_BUSYBOX_"):
        return "BUSYBOX"
    if re.match(r"CONFIG_(LIBC_|GCC_|BINUTILS_)", name):
        return "TOOLCHAIN"
    if name.startswith("CONFIG_FEED_"):
        return "FEED"
    if name.startswith("CONFIG_PKG_"):
        return "PKG"
    if name.startswith("CONFIG_"):
        return "OTHER"
    return "UNKNOWN"

# ============ 工具函数 ============
def read_enabled_configs(file_path: Path) -> Dict[str, str]:
    """读取配置文件，提取所有启用的配置项（非注释且非"is not set"）"""
    configs = {}
    if not file_path.exists():
        return configs
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.endswith(' is not set'):
                continue
            match = re.match(r'^(CONFIG_[A-Za-z0-9_\-]+)=(.*)$', line)
            if match:
                configs[match.group(1)] = match.group(2)
    return configs

def parse_reference_configs(ref_file: Path) -> Dict[str, str]:
    """解析参考文件，支持 CONFIG_XXX 或 CONFIG_XXX=值，默认 =y"""
    configs = {}
    if not ref_file.exists():
        return configs
    with open(ref_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.endswith(' is not set'):
                continue
            match = re.match(r'^(CONFIG_[A-Za-z0-9_\-]+)(?:=(.*))?$', line)
            if match:
                name = match.group(1)
                value = match.group(2) if match.group(2) is not None else 'y'
                configs[name] = value
    return configs

def categorize_configs(configs: Dict[str, str]) -> Dict[str, List[str]]:
    """将配置字典按分类分组"""
    cats = defaultdict(list)
    for name in configs.keys():
        cat = get_category(name)
        cats[cat].append(name)
    for cat in cats:
        cats[cat].sort()
    return dict(cats)

def format_categorized_output(configs: Dict[str, str], source_file: str = "", title: str = "已启用的配置项分类列表") -> str:
    """生成分类输出的文本"""
    cats = categorize_configs(configs)
    lines = []
    lines.append(title)
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if source_file:
        lines.append(f"源文件: {source_file}")
    lines.append("=======================")
    lines.append("")
    for cat in sorted(cats.keys()):
        lines.append(f"[{cat}]")
        for name in cats[cat]:
            lines.append(f"  {name}")
        lines.append("")
    return "\n".join(lines)

# ============ 命令实现 ============
def cmd_extract(args):
    """extract 命令：输出到 stdout，-o 额外保存到文件"""
    config_file = Path(args.config_file)
    if not config_file.exists():
        print(f"错误: 配置文件 '{config_file}' 不存在", file=sys.stderr)
        return 1

    configs = read_enabled_configs(config_file)
    if not configs:
        print("错误: 未找到任何启用的配置项", file=sys.stderr)
        return 1

    output_text = format_categorized_output(configs, source_file=str(config_file))
    print(output_text)  # 默认输出到 stdout

    if args.output:
        Path(args.output).write_text(output_text)

    return 0

def cmd_sync(args):
    """sync 命令：输出缺失项到 stdout，-o 额外保存到文件"""
    target_file = Path(args.target_file)
    ref_file = Path(args.ref_file) if args.ref_file else DEFAULT_REF

    if not ref_file.exists():
        print(f"错误: 参考文件 '{ref_file}' 不存在", file=sys.stderr)
        return 1
    if not target_file.exists():
        print(f"错误: 目标文件 '{target_file}' 不存在", file=sys.stderr)
        return 1

    ref_configs = parse_reference_configs(ref_file)
    if not ref_configs:
        print("错误: 参考文件中未找到任何有效配置项", file=sys.stderr)
        return 1

    temp_file = target_file.with_suffix(target_file.suffix + ".tmp")
    processed = set()

    with open(target_file, 'r') as fin, open(temp_file, 'w') as fout:
        for line in fin:
            line_stripped = line.strip()
            match_commented = re.match(r'^#\s*(CONFIG_[A-Za-z0-9_\-]+)\s+is not set$', line_stripped)
            if match_commented:
                name = match_commented.group(1)
                if name in ref_configs:
                    fout.write(f"{name}={ref_configs[name]}\n")
                    processed.add(name)
                else:
                    fout.write(line)
                continue

            match_normal = re.match(r'^(CONFIG_[A-Za-z0-9_\-]+)=(.*)$', line_stripped)
            if match_normal:
                name = match_normal.group(1)
                if name in ref_configs:
                    fout.write(f"{name}={ref_configs[name]}\n")
                    processed.add(name)
                else:
                    fout.write(line)
                continue

            fout.write(line)

        missing = {}
        for name, value in ref_configs.items():
            if name not in processed:
                missing[name] = value

    temp_file.replace(target_file)

    # 生成缺失项文本
    missing_lines = [f"{name}={value}" for name, value in missing.items()]
    output_text = "\n".join(missing_lines)
    if output_text:
        print(output_text)  # 输出到 stdout

    if args.output:
        Path(args.output).write_text(output_text)

    return 0

def cmd_diff(args):
    """diff 命令：输出差异报告到 stdout，-o 额外保存到文件"""
    file1 = Path(args.file1)
    file2 = Path(args.file2)
    if not file1.exists():
        print(f"错误: 文件 '{file1}' 不存在", file=sys.stderr)
        return 1
    if not file2.exists():
        print(f"错误: 文件 '{file2}' 不存在", file=sys.stderr)
        return 1

    configs1 = read_enabled_configs(file1)
    configs2 = read_enabled_configs(file2)

    set1 = set(configs1.keys())
    set2 = set(configs2.keys())

    only1 = set1 - set2
    only2 = set2 - set1

    # 构建报告文本
    lines = []
    lines.append("配置差异比较")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"文件1: {file1}")
    lines.append(f"文件2: {file2}")
    lines.append("=======================")
    lines.append("")

    if not only1 and not only2:
        lines.append("两个文件的启用配置项完全相同，无差异。")
    else:
        if only1:
            lines.append("========================")
            lines.append("仅在文件1中启用的配置项")
            lines.append("========================")
            cats1 = categorize_configs({name: '' for name in only1})
            for cat in sorted(cats1.keys()):
                lines.append(f"\n[{cat}]")
                for name in cats1[cat]:
                    lines.append(f"  {name}")
        if only2:
            lines.append("\n")
            lines.append("========================")
            lines.append("仅在文件2中启用的配置项")
            lines.append("========================")
            cats2 = categorize_configs({name: '' for name in only2})
            for cat in sorted(cats2.keys()):
                lines.append(f"\n[{cat}]")
                for name in cats2[cat]:
                    lines.append(f"  {name}")

    # 总结信息放在最后
    lines.append("")
    lines.append(f"总结: 仅在文件1中的项数: {len(only1)}, 仅在文件2中的项数: {len(only2)}")

    output_text = "\n".join(lines)
    print(output_text)  # 输出到 stdout

    if args.output:
        Path(args.output).write_text(output_text)

    return 0

def cmd_check(args):
    """check 命令：输出检查报告到 stdout，-o 额外保存到文件"""
    target_file = Path(args.target_file)
    ref_file = Path(args.ref_file) if args.ref_file else DEFAULT_REF

    if not ref_file.exists():
        print(f"错误: 参考文件 '{ref_file}' 不存在", file=sys.stderr)
        return 1
    if not target_file.exists():
        print(f"错误: 目标文件 '{target_file}' 不存在", file=sys.stderr)
        return 1

    ref_configs = parse_reference_configs(ref_file)
    if not ref_configs:
        print("错误: 参考文件中未找到任何有效配置项", file=sys.stderr)
        return 1

    enabled = {}
    disabled = set()
    with open(target_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^#\s*(CONFIG_[A-Za-z0-9_\-]+)\s+is not set$', line)
            if m:
                disabled.add(m.group(1))
                continue
            m = re.match(r'^(CONFIG_[A-Za-z0-9_\-]+)=(.*)$', line)
            if m:
                enabled[m.group(1)] = m.group(2)

    issues = defaultdict(lambda: defaultdict(list))
    for name, expected_value in ref_configs.items():
        if name in enabled:
            if enabled[name] != expected_value:
                issues["值不匹配"][get_category(name)].append(f"{name} (当前={enabled[name]}, 期望={expected_value})")
        elif name in disabled:
            issues["已禁用"][get_category(name)].append(name)
        else:
            issues["未设置"][get_category(name)].append(name)

    # 构建报告文本
    lines = []
    lines.append("配置检查报告")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"参考文件: {ref_file}")
    lines.append(f"目标文件: {target_file}")
    lines.append(f"检查项总数: {len(ref_configs)}")
    total_issues = sum(len(cats) for cats in issues.values())
    lines.append(f"问题项总数: {total_issues}")
    lines.append("=======================")
    lines.append("")

    if total_issues == 0:
        lines.append("所有参考配置项在目标文件中均已正确设置。")
    else:
        for status, cats in sorted(issues.items()):
            lines.append(f"[{status}]")
            for cat in sorted(cats.keys()):
                lines.append(f"  {cat}:")
                for name in sorted(cats[cat]):
                    lines.append(f"    {name}")
            lines.append("")

    # 总结信息放在最后
    lines.append("")
    lines.append(f"总结: 未设置: {len(issues.get('未设置', {}))} 项, 已禁用: {len(issues.get('已禁用', {}))} 项, 值不匹配: {len(issues.get('值不匹配', {}))} 项")

    output_text = "\n".join(lines)
    print(output_text)  # 输出到 stdout

    if args.output:
        Path(args.output).write_text(output_text)

    return 0

def cmd_reset(args):
    """reset 命令：将配置文件重置为指定的默认配置"""
    # 检查 defconfig 目录可能的位置
    defconfig_candidates = [
        SCRIPT_DIR / "defconfig",           # 脚本同级目录
        Path.cwd() / "defconfig",           # 当前工作目录
        PARENT_DIR / "defconfig",           # 上级目录（项目根目录）
        SCRIPT_DIR.parent.parent / "defconfig",  # 上上级目录
    ]

    defconfig_dir = None
    for candidate in defconfig_candidates:
        if candidate.exists():
            defconfig_dir = candidate
            break

    if not defconfig_dir:
        print(f"错误: 未找到 defconfig 目录，搜索路径:", file=sys.stderr)
        for candidate in defconfig_candidates:
            print(f"  - {candidate}", file=sys.stderr)
        return 1

    # 扫描 defconfig 目录，收集所有配置文件信息
    config_files = []
    config_info = {}  # 存储每个文件的详细信息
    device_groups = {}  # 按设备名分组
    chip_groups = {}  # 按芯片分组

    if defconfig_dir.exists():
        for file_path in sorted(defconfig_dir.glob("*.config")):
            filename = file_path.name
            name_without_ext = filename[:-7] if filename.endswith('.config') else filename
            config_files.append(name_without_ext)

            # 解析文件名: 芯片型号-设备名-版本
            parts = name_without_ext.split('-')
            chip = parts[0] if parts else ""
            device = parts[1] if len(parts) > 1 else ""
            version = parts[2] if len(parts) > 2 else ""

            config_info[name_without_ext] = {
                'filename': filename,
                'chip': chip,
                'device': device,
                'version': version,
                'parts': parts,
                'has_version': len(parts) > 2  # 是否有版本号
            }

            # 按设备名分组
            if device:
                if device not in device_groups:
                    device_groups[device] = []
                device_groups[device].append(name_without_ext)

            # 按芯片分组
            if chip:
                if chip not in chip_groups:
                    chip_groups[chip] = []
                chip_groups[chip].append(name_without_ext)

    if not config_files:
        print(f"错误: 在 '{defconfig_dir}' 中未找到任何 .config 文件", file=sys.stderr)
        return 1

    # 获取目标平台并转换为小写（不区分大小写）
    keyword = args.platform.lower()
    if not keyword:
        print("错误: 请指定目标平台或设备名", file=sys.stderr)
        return 1

    # 目标文件
    target_file = Path(args.target_file) if args.target_file else Path(".config")

    # 特殊处理：芯片数字简写
    chip_aliases = {
        '7981': 'mt7981',
        '7986': 'mt7986',
        'mt7981': 'mt7981',
        'mt7986': 'mt7986',
    }

    # 如果是数字简写，转换为完整芯片名
    if keyword in chip_aliases:
        keyword = chip_aliases[keyword]

    # 匹配逻辑
    exact_matches = []  # 精确匹配完整文件名
    chip_matches = []   # 芯片型号匹配
    device_matches = [] # 设备名匹配
    version_matches = [] # 版本匹配
    partial_matches = [] # 部分匹配

    for name, info in config_info.items():
        # 1. 精确匹配完整文件名
        if name.lower() == keyword:
            exact_matches.append((name, info, '精确匹配'))

        # 2. 匹配芯片型号
        if info['chip'].lower() == keyword:
            chip_matches.append((name, info, '芯片型号匹配'))

        # 3. 匹配设备名
        if info['device'].lower() == keyword:
            device_matches.append((name, info, '设备名匹配'))

        # 4. 匹配版本
        if info['version'].lower() == keyword:
            version_matches.append((name, info, '版本匹配'))

        # 5. 部分匹配 (包含关键词)
        if keyword in name.lower() and keyword not in [info['chip'].lower(), info['device'].lower(), info['version'].lower()]:
            partial_matches.append((name, info, '部分匹配'))

    # 处理匹配结果
    # 1. 精确匹配优先
    if exact_matches:
        name, info, match_type = exact_matches[0]
        src_file = defconfig_dir / info['filename']

        # 检查是否还有其他相关版本
        device = info['device']
        other_versions = []
        if device in device_groups:
            for config_name in device_groups[device]:
                if config_name != name:
                    other_versions.append(config_name)

        if other_versions:
            print(f"提示: 找到精确匹配 '{name}.config'，已自动选择")
            print(f"该设备还有其他版本:")
            for version in other_versions:
                print(f"  - {version}.config")
            print(f"如需使用其他版本，请指定完整文件名:")
            for version in other_versions:
                print(f"  ./cfghelper reset {version}")
            print()

        # 复制文件
        try:
            shutil.copy2(src_file, target_file)
            print(f"已将 {info['filename']} 复制到 {target_file}")
        except Exception as e:
            print(f"错误: 复制文件失败 - {e}", file=sys.stderr)
            return 1
        return 0

    # 2. 芯片型号匹配：优先选择通用配置（没有版本号的）
    if chip_matches:
        # 分离通用配置（没有版本）和带版本的配置
        general_configs = []
        versioned_configs = []

        for name, info, match_type in chip_matches:
            if not info['has_version']:
                general_configs.append((name, info, match_type))
            else:
                versioned_configs.append((name, info, match_type))

        # 如果有通用配置，优先选择
        if general_configs:
            # 如果有多个通用配置，选择第一个（通常是 ax3000 或 ax6000）
            name, info, match_type = general_configs[0]
            src_file = defconfig_dir / info['filename']

            # 检查是否还有其他配置
            if len(chip_matches) > 1:
                print(f"提示: 芯片 {keyword} 有多个配置文件，已自动选择通用版本 '{name}.config'")
                print(f"该芯片的其他配置版本:")
                for nm, inf, _ in chip_matches:
                    if nm != name:
                        print(f"  - {nm}.config")
                print(f"如需使用其他版本，请指定完整文件名:")
                for nm, inf, _ in chip_matches[:3]:
                    if nm != name:
                        print(f"  ./cfghelper reset {nm}")
                print()

            # 复制文件
            try:
                shutil.copy2(src_file, target_file)
                print(f"已将 {info['filename']} 复制到 {target_file}")
            except Exception as e:
                print(f"错误: 复制文件失败 - {e}", file=sys.stderr)
                return 1
            return 0

        # 没有通用配置，列出所有选项让用户选择
        print(f"找到 {keyword} 芯片的多个配置文件 (无通用版本)，请选择:")
        for i, (name, info, _) in enumerate(chip_matches, 1):
            version_info = f" (版本: {info['version']})" if info['version'] else ""
            print(f"  {i}. {name} (设备: {info['device']}{version_info})")

        print("\n请使用更精确的关键词重新运行，例如:")
        for name, _, _ in chip_matches[:3]:
            print(f"  ./cfghelper reset {name}")
        return 1

    # 3. 设备名匹配：如果有多个版本，提示选择
    if device_matches:
        # 检查是否有通用版本（没有版本号的）
        general_configs = []
        versioned_configs = []

        for name, info, match_type in device_matches:
            if not info['has_version']:
                general_configs.append((name, info, match_type))
            else:
                versioned_configs.append((name, info, match_type))

        # 如果有通用配置，优先选择
        if general_configs:
            name, info, match_type = general_configs[0]
            src_file = defconfig_dir / info['filename']

            if versioned_configs:
                print(f"提示: 设备 {keyword} 有多个版本，已自动选择通用版本 '{name}.config'")
                print(f"该设备的其他版本:")
                for nm, inf, _ in versioned_configs:
                    print(f"  - {nm}.config")
                print(f"如需使用其他版本，请指定完整文件名:")
                for nm, inf, _ in versioned_configs[:3]:
                    print(f"  ./cfghelper reset {nm}")
                print()

            # 复制文件
            try:
                shutil.copy2(src_file, target_file)
                print(f"已将 {info['filename']} 复制到 {target_file}")
            except Exception as e:
                print(f"错误: 复制文件失败 - {e}", file=sys.stderr)
                return 1
            return 0

        # 没有通用版本，列出所有版本让用户选择
        print(f"找到设备 '{keyword}' 的多个配置文件 (无通用版本)，请选择:")
        for i, (name, info, _) in enumerate(device_matches, 1):
            version_info = f" (版本: {info['version']})" if info['version'] else ""
            print(f"  {i}. {name} (芯片: {info['chip']}{version_info})")

        print("\n请使用更精确的关键词重新运行，例如:")
        for name, _, _ in device_matches[:3]:
            print(f"  ./cfghelper reset {name}")
        return 1

    # 4. 版本匹配或部分匹配
    if version_matches or partial_matches:
        all_matches = version_matches + partial_matches
        print(f"找到匹配 '{keyword}' 的配置文件:")
        for i, (name, info, match_type) in enumerate(all_matches, 1):
            print(f"  {i}. {name} (芯片: {info['chip']}, 设备: {info['device']})")

        print("\n请使用更精确的关键词重新运行，例如:")
        for name, _, _ in all_matches[:3]:
            print(f"  ./cfghelper reset {name}")
        return 1

    # 没有匹配
    print(f"错误: 未找到匹配 '{args.platform}' 的配置文件", file=sys.stderr)
    print("\n可用的配置文件:")
    for i, name in enumerate(sorted(config_files), 1):
        print(f"  {i}. {name}")
    print("\n提示: 可以使用芯片型号 (mt7981/mt7986) 或设备名 (如 rax3000m)")
    return 1

def cmd_get(args):
    """get 命令：按分类输出启用的配置项"""
    config_file = Path(args.config_file)
    if not config_file.exists():
        print(f"错误: 配置文件 '{config_file}' 不存在", file=sys.stderr)
        return 1

    configs = read_enabled_configs(config_file)
    if not configs:
        print("错误: 未找到任何启用的配置项", file=sys.stderr)
        return 1

    category = args.category.lower()
    items = []

    if category == "app":
        # 特殊分类：输出所有 CONFIG_PACKAGE_luci-app-* 项
        for name in sorted(configs.keys()):
            if name.startswith("CONFIG_PACKAGE_luci-app-"):
                items.append(name)
    else:
        # 普通分类
        for name, value in configs.items():
            if get_category(name) == category.upper():
                items.append(name)

    if not items:
        print(f"错误: 未找到分类 '{category}' 的配置项", file=sys.stderr)
        return 1

    output_text = "\n".join(items)
    print(output_text)  # 输出到 stdout

    if args.output:
        Path(args.output).write_text(output_text)

    return 0

# ============ 主程序 ============
def main():
    parser = argparse.ArgumentParser(
        description="OpenWrt 配置辅助工具",
        usage="%(prog)s <命令> [参数...]",
        add_help=False
    )
    parser.add_argument('command', nargs='?', help='子命令')
    parser.add_argument('args', nargs=argparse.REMAINDER, help='子命令参数')

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    command = sys.argv[1]
    if command in ('help', '-h', '--help'):
        print_help()
        sys.exit(0)

    if command == 'extract':
        subparser = argparse.ArgumentParser(prog='extract', description='提取启用的配置项并输出到 stdout')
        subparser.add_argument('config_file', help='配置文件路径')
        subparser.add_argument('-o', '--output', help='额外保存到文件（可选）')
        args = subparser.parse_args(sys.argv[2:])
        sys.exit(cmd_extract(args))

    elif command == 'sync':
        subparser = argparse.ArgumentParser(prog='sync', description='同步配置项，缺失项输出到 stdout')
        subparser.add_argument('target_file', help='目标文件路径')
        subparser.add_argument('-r', '--ref-file', help='参考文件路径（默认 cfg-default.txt）')
        subparser.add_argument('-o', '--output', help='额外保存缺失项到文件（可选）')
        args = subparser.parse_args(sys.argv[2:])
        sys.exit(cmd_sync(args))

    elif command == 'diff':
        subparser = argparse.ArgumentParser(prog='diff', description='比较两个配置文件，输出到 stdout')
        subparser.add_argument('file1', help='第一个配置文件')
        subparser.add_argument('file2', help='第二个配置文件')
        subparser.add_argument('-o', '--output', help='额外保存报告到文件（可选）')
        args = subparser.parse_args(sys.argv[2:])
        sys.exit(cmd_diff(args))

    elif command == 'check':
        subparser = argparse.ArgumentParser(prog='check', description='检查配置状态，输出到 stdout')
        subparser.add_argument('target_file', help='目标文件路径')
        subparser.add_argument('-r', '--ref-file', help='参考文件路径（默认 cfg-default.txt）')
        subparser.add_argument('-o', '--output', help='额外保存报告到文件（可选）')
        args = subparser.parse_args(sys.argv[2:])
        sys.exit(cmd_check(args))

    elif command == 'reset':
        subparser = argparse.ArgumentParser(prog='reset', description='重置配置文件为指定的默认配置')
        subparser.add_argument('platform', help='目标平台或设备名 (如 mt7981, 7981, rax3000m)')
        subparser.add_argument('target_file', nargs='?', default='.config', help='目标文件路径（默认 .config）')
        args = subparser.parse_args(sys.argv[2:])
        sys.exit(cmd_reset(args))

    elif command == 'get':
        subparser = argparse.ArgumentParser(prog='get', description='按分类输出启用的配置项')
        subparser.add_argument('category', help='分类名 (如 PACKAGE, TARGET, KERNEL, BUSYBOX, TOOLCHAIN, FEED, PKG, OTHER, UNKNOWN, 或 app 表示 Luci 应用)')
        subparser.add_argument('config_file', help='配置文件路径')
        subparser.add_argument('-o', '--output', help='额外保存到文件（可选）')
        args = subparser.parse_args(sys.argv[2:])
        sys.exit(cmd_get(args))

    else:
        print(f"错误: 未知命令 '{command}'", file=sys.stderr)
        print_help()
        sys.exit(1)

def print_help():
    help_text = """
用法: cfghelper.py <命令> [参数...]

命令:
  extract [-o <输出文件>] <config文件>
      提取所有启用的配置项，按分类输出到 stdout（可管道）
      若指定 -o，则额外保存到文件
      示例: cfghelper.py extract .config | grep app
      示例: cfghelper.py extract .config -o my.txt

  sync [-r <参考文件>] [-o <输出文件>] <目标文件>
      根据参考文件同步配置项到目标文件
      修改目标文件中存在的项为参考值
      不追加不存在的项，缺失项输出到 stdout
      -o 选项额外保存缺失项到文件
      示例: cfghelper.py sync .config
      示例: cfghelper.py sync -r my_cfg.txt .config -o missing.txt

  diff <文件1> <文件2> [-o <输出文件>]
      比较两个配置文件的启用配置项差异，输出到 stdout
      -o 选项额外保存报告到文件
      示例: cfghelper.py diff .config old.config

  check <目标文件> [-r <参考文件>] [-o <输出文件>]
      检查目标文件中参考配置项的状态（未设置、已禁用、值不匹配）
      生成报告输出到 stdout，-o 额外保存报告到文件
      示例: cfghelper.py check .config

  reset <平台/设备名> [目标文件]
      将配置文件重置为指定的默认配置
      支持芯片型号: mt7981, mt7986 (或简写 7981, 7986)
      支持设备名: 如 rax3000m, ax3000, ax6000
      自动选择通用版本（无版本后缀），若有多个版本会提示
      目标文件默认为 .config
      示例: cfghelper.py reset 7981
      示例: cfghelper.py reset mt7986
      示例: cfghelper.py reset rax3000m
      示例: cfghelper.py reset mt7981-rax3000m-emmc my.config

  get <分类> <config文件> [-o <输出文件>]
      按分类输出启用的配置项（每行一个配置名）
      支持分类: PACKAGE, TARGET, KERNEL, BUSYBOX, TOOLCHAIN, FEED, PKG, OTHER, UNKNOWN
      特殊分类: app (输出所有 CONFIG_PACKAGE_luci-app-* 项)
      示例: cfghelper.py get PACKAGE .config
      示例: cfghelper.py get app .config | grep luci-app-xxx

环境变量:
  REF_FILE    默认参考文件（默认: {DEFAULT_REF}）
""".format(DEFAULT_REF=DEFAULT_REF)
    print(help_text)

if __name__ == '__main__':
    main()
