#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正则表达式助手
提供正则表达式测试、调试和生成功能
"""

import re
import sys
import argparse
from typing import List, Tuple, Optional


# 常用正则表达式模式
PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "phone": r"1[3-9]\d{9}",
    "idcard": r"\d{17}[\dXx]",
    "ipv4": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
    "url": r"https?://[^\s]+",
    "date": r"\d{4}-\d{2}-\d{2}",
    "time": r"\d{2}:\d{2}:\d{2}",
    "chinese": r"[\u4e00-\u9fa5]+",
    "username": r"[a-zA-Z0-9_]{3,20}",
    "password": r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}",
}


def print_section(title: str, content: str = ""):
    """打印分节标题"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")
    if content:
        print(content)


def match_test(pattern: str, text: str, flags: int = 0):
    """测试基本匹配"""
    print_section("基本匹配测试")
    print(f"正则表达式: {pattern}")
    print(f"测试文本: {text}")
    print(f"\n{'='*50}")

    try:
        result = re.search(pattern, text, flags)
        if result:
            print(f"✅ 匹配成功!")
            print(f"匹配位置: {result.span()}")
            print(f"匹配内容: '{result.group()}'")
        else:
            print("❌ 无匹配")
    except re.error as e:
        print(f"❌ 正则表达式错误: {e}")


def find_all(pattern: str, text: str, flags: int = 0):
    """提取所有匹配"""
    print_section("提取所有匹配")
    print(f"正则表达式: {pattern}")
    print(f"测试文本: {text}")
    print(f"\n{'='*50}")

    try:
        matches = re.findall(pattern, text, flags)
        if matches:
            print(f"✅ 找到 {len(matches)} 个匹配:")
            for i, match in enumerate(matches, 1):
                if isinstance(match, tuple):
                    # 处理有分组的情况
                    print(f"  {i}. 分组结果: {match}")
                else:
                    print(f"  {i}. '{match}'")
        else:
            print("❌ 无匹配")
    except re.error as e:
        print(f"❌ 正则表达式错误: {e}")


def find_iter(pattern: str, text: str, flags: int = 0):
    """使用finditer查看所有匹配的详细信息"""
    print_section("匹配详情 (finditer)")
    print(f"正则表达式: {pattern}")
    print(f"测试文本: {text}")
    print(f"\n{'='*50}")

    try:
        for i, match in enumerate(re.finditer(pattern, text, flags), 1):
            print(f"\n匹配 {i}:")
            print(f"  位置: {match.span()}")
            print(f"  内容: '{match.group()}'")
            # 显示所有分组
            for g_idx, group in enumerate(match.groups(), 1):
                if group:
                    print(f"  分组{g_idx}: '{group}'")
    except re.error as e:
        print(f"❌ 正则表达式错误: {e}")


def groups(pattern: str, text: str, flags: int = 0):
    """查看分组捕获"""
    print_section("分组捕获")
    print(f"正则表达式: {pattern}")
    print(f"测试文本: {text}")
    print(f"\n{'='*50}")

    try:
        result = re.search(pattern, text, flags)
        if result:
            print(f"✅ 匹配成功!")
            print(f"完整匹配 (group 0): '{result.group()}'")
            print(f"\n捕获分组:")
            for i, group in enumerate(result.groups(), 1):
                if group is not None:
                    print(f"  group({i}): '{group}'")
                else:
                    print(f"  group({i}): (未匹配)")

            if result.groupdict():
                print(f"\n命名分组:")
                for name, value in result.groupdict().items():
                    print(f"  ?P<{name}>: '{value}'")
        else:
            print("❌ 无匹配")
    except re.error as e:
        print(f"❌ 正则表达式错误: {e}")


def substitute(pattern: str, replacement: str, text: str, count: int = 0, flags: int = 0):
    """执行替换操作"""
    print_section("文本替换")
    print(f"正则表达式: {pattern}")
    print(f"替换内容: {replacement}")
    print(f"原文: {text}")
    print(f"\n{'='*50}")

    try:
        result = re.sub(pattern, replacement, text, count=count, flags=flags)
        print(f"替换后: {result}")

        # 显示替换次数
        if count == 0:
            matches = re.findall(pattern, text, flags)
            print(f"\n共替换了 {len(matches)} 处")
        else:
            print(f"\n最多替换了 {count} 处")

    except re.error as e:
        print(f"❌ 正则表达式错误: {e}")


def get_pattern(name: str):
    """获取常用正则表达式模式"""
    print_section(f"常用模式: {name}")
    if name in PATTERNS:
        print(f"模式: {PATTERNS[name]}")
        print(f"\n说明:")
        descriptions = {
            "email": "匹配常见邮箱地址格式",
            "phone": "匹配中国大陆手机号 (11位，1开头)",
            "idcard": "匹配中国大陆身份证号 (18位)",
            "ipv4": "匹配IPv4地址格式",
            "url": "匹配HTTP/HTTPS URL",
            "date": "匹配日期格式 YYYY-MM-DD",
            "time": "匹配时间格式 HH:MM:SS",
            "chinese": "匹配中文字符",
            "username": "匹配用户名 (3-20位字母数字下划线)",
            "password": "匹配密码 (至少8位，包含字母和数字)",
        }
        print(descriptions.get(name, "无说明"))
        print(f"\n使用示例:")
        print(f"python3 script/main.py match '{PATTERNS[name]}' '<你的测试文本>'")
    else:
        print(f"❌ 未找到模式 '{name}'")
        print(f"\n可用模式: {', '.join(PATTERNS.keys())}")


def list_patterns():
    """列出所有可用模式"""
    print_section("所有可用模式")
    for name, pattern in PATTERNS.items():
        print(f"  {name:12s} → {pattern}")
    print(f"\n使用 'python3 script/main.py pattern <名称>' 查看详情")


def main():
    parser = argparse.ArgumentParser(description="正则表达式助手")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # match 命令
    match_parser = subparsers.add_parser("match", help="测试基本匹配")
    match_parser.add_argument("pattern", help="正则表达式")
    match_parser.add_argument("text", help="测试文本")
    match_parser.add_argument("-i", "--ignorecase", action="store_true", help="忽略大小写")
    match_parser.add_argument("-m", "--multiline", action="store_true", help="多行模式")

    # findall 命令
    find_parser = subparsers.add_parser("findall", help="提取所有匹配")
    find_parser.add_argument("pattern", help="正则表达式")
    find_parser.add_argument("text", help="测试文本")
    find_parser.add_argument("-i", "--ignorecase", action="store_true", help="忽略大小写")

    # finditer 命令
    iter_parser = subparsers.add_parser("finditer", help="查看所有匹配详情")
    iter_parser.add_argument("pattern", help="正则表达式")
    iter_parser.add_argument("text", help="测试文本")

    # groups 命令
    groups_parser = subparsers.add_parser("groups", help="查看分组捕获")
    groups_parser.add_argument("pattern", help="正则表达式")
    groups_parser.add_argument("text", help="测试文本")

    # sub 命令
    sub_parser = subparsers.add_parser("sub", help="执行替换操作")
    sub_parser.add_argument("pattern", help="正则表达式")
    sub_parser.add_argument("replacement", help="替换内容")
    sub_parser.add_argument("text", help="原始文本")
    sub_parser.add_argument("-c", "--count", type=int, default=0, help="最大替换次数")

    # pattern 命令
    pattern_parser = subparsers.add_parser("pattern", help="获取常用模式")
    pattern_parser.add_argument("name", help="模式名称", nargs="?")

    # list 命令
    subparsers.add_parser("list", help="列出所有可用模式")

    args = parser.parse_args()

    # 构建flags
    flags = 0
    if hasattr(args, "ignorecase") and args.ignorecase:
        flags |= re.IGNORECASE
    if hasattr(args, "multiline") and args.multiline:
        flags |= re.MULTILINE

    # 执行命令
    if args.command == "match":
        match_test(args.pattern, args.text, flags)
    elif args.command == "findall":
        find_all(args.pattern, args.text, flags)
    elif args.command == "finditer":
        find_iter(args.pattern, args.text, flags)
    elif args.command == "groups":
        groups(args.pattern, args.text, flags)
    elif args.command == "sub":
        substitute(args.pattern, args.replacement, args.text, args.count, flags)
    elif args.command == "pattern":
        if args.name:
            get_pattern(args.name)
        else:
            list_patterns()
    elif args.command == "list":
        list_patterns()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
