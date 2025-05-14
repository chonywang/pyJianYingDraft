#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置文件更新工具
用于更新API凭据等配置信息
"""

import os
import json
import argparse
from pathlib import Path

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")

def load_config():
    """加载现有配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "translate_api": {
            "baidu": {
                "app_id": "",
                "secret_key": ""
            }
        }
    }

def save_config(config):
    """保存配置到文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    print(f"配置已保存到: {CONFIG_FILE}")

def update_baidu_translate_credentials(app_id: str, secret_key: str):
    """更新百度翻译API凭据
    
    Args:
        app_id: 百度翻译API的APP ID
        secret_key: 百度翻译API的密钥
    """
    config = load_config()
    
    # 确保配置结构存在
    if "translate_api" not in config:
        config["translate_api"] = {}
    if "baidu" not in config["translate_api"]:
        config["translate_api"]["baidu"] = {}
    
    # 更新凭据
    config["translate_api"]["baidu"]["app_id"] = app_id
    config["translate_api"]["baidu"]["secret_key"] = secret_key
    
    # 保存配置
    save_config(config)
    print("百度翻译API凭据已更新")

def main():
    parser = argparse.ArgumentParser(description="更新配置文件")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 添加百度翻译API凭据更新命令
    baidu_parser = subparsers.add_parser("baidu", help="更新百度翻译API凭据")
    baidu_parser.add_argument("--app-id", required=True, help="百度翻译API的APP ID")
    baidu_parser.add_argument("--secret-key", required=True, help="百度翻译API的密钥")
    
    args = parser.parse_args()
    
    if args.command == "baidu":
        update_baidu_translate_credentials(args.app_id, args.secret_key)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 