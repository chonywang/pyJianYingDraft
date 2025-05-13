#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
剪映项目创建主程序
提供从零创建或从模板创建两种方式
"""

import os
import sys
import argparse

from create_project import create_project
from create_from_template import create_project_from_template

def main():
    """主函数，解析命令行参数并执行相应的功能"""
    parser = argparse.ArgumentParser(description='创建剪映项目，添加视频、语音和字幕')
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='选择创建方式')
    
    # 从零创建的子命令
    create_parser = subparsers.add_parser('create', help='从零创建新项目')
    
    # 从模板创建的子命令
    template_parser = subparsers.add_parser('template', help='从模板创建项目')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 如果没有提供子命令，显示帮助信息并提示用户选择
    if not args.command:
        print("请选择创建方式：")
        print("1. 从零创建新项目")
        print("2. 从模板创建项目")
        choice = input("请输入选项(1-2): ")
        
        if choice == '1':
            args.command = 'create'
        elif choice == '2':
            args.command = 'template'
        else:
            print("无效的选项")
            parser.print_help()
            return
    
    # 执行选择的功能
    if args.command == 'create':
        print("\n从零创建剪映项目...\n")
        create_project()
    elif args.command == 'template':
        print("\n从模板创建剪映项目...\n")
        create_project_from_template()
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 