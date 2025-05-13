#!/usr/bin/env python3
"""测试剪映导出功能"""

import os
import sys
import logging
import argparse
from pathlib import Path
from pyJianYingDraft import Jianying_controller, Export_resolution, Export_framerate

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_draft_folder():
    """查找剪映草稿文件夹"""
    possible_paths = [
        os.path.expanduser("~/Library/Application Support/JianyingPro/User Data/Projects/com.lveditor.draft"),
        os.path.expanduser("~/Library/Application Support/JianyingPro/Projects/com.lveditor.draft"),
        os.path.expanduser("~/Documents/jianyan/JianyingPro Drafts"),
        os.path.expanduser("~/Documents/JianyingPro Drafts")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"找到剪映草稿文件夹: {path}")
            return path
            
    logger.error("未找到剪映草稿文件夹，请确认剪映已安装")
    return None

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='剪映视频导出测试')
    parser.add_argument('--draft-folder', type=str, help='剪映草稿文件夹路径')
    parser.add_argument('--draft-name', type=str, required=True, help='要导出的草稿名称')
    parser.add_argument('--output-dir', type=str, help='导出目录路径')
    parser.add_argument('--resolution', type=str, choices=['8K', '4K', '2K', '1080P', '720P', '480P'],
                      default='1080P', help='导出分辨率')
    parser.add_argument('--framerate', type=str, choices=['24', '25', '30', '50', '60'],
                      default='30', help='导出帧率')
    parser.add_argument('--debug', action='store_true', help='启用调试日志')
    
    return parser.parse_args()

def get_resolution(resolution_str: str) -> Export_resolution:
    """获取分辨率枚举值"""
    resolution_map = {
        '8K': Export_resolution.RES_8K,
        '4K': Export_resolution.RES_4K,
        '2K': Export_resolution.RES_2K,
        '1080P': Export_resolution.RES_1080P,
        '720P': Export_resolution.RES_720P,
        '480P': Export_resolution.RES_480P
    }
    return resolution_map[resolution_str]

def get_framerate(framerate_str: str) -> Export_framerate:
    """获取帧率枚举值"""
    framerate_map = {
        '24': Export_framerate.FR_24,
        '25': Export_framerate.FR_25,
        '30': Export_framerate.FR_30,
        '50': Export_framerate.FR_50,
        '60': Export_framerate.FR_60
    }
    return framerate_map[framerate_str]

def test_export(args):
    """测试导出功能"""
    try:
        # 设置日志级别
        log_level = logging.DEBUG if args.debug else logging.INFO
        logger.setLevel(log_level)
        
        # 获取草稿文件夹
        draft_folder = args.draft_folder or find_draft_folder()
        if not draft_folder:
            return False
            
        # 创建控制器实例
        controller = Jianying_controller(draft_path=draft_folder, log_level=log_level)
        
        # 设置输出路径
        if args.output_dir:
            test_output_dir = os.path.expanduser(args.output_dir)
        else:
            test_output_dir = os.path.expanduser("~/Desktop/剪映导出测试")
            
        test_output_path = os.path.join(test_output_dir, f"{args.draft_name}.mp4")
        
        # 确保输出目录存在
        os.makedirs(test_output_dir, exist_ok=True)
        
        logger.info("开始测试导出功能")
        logger.info(f"草稿文件夹: {draft_folder}")
        logger.info(f"项目名称: {args.draft_name}")
        logger.info(f"输出路径: {test_output_path}")
        logger.info(f"分辨率: {args.resolution}")
        logger.info(f"帧率: {args.framerate}")
        
        # 执行导出
        controller.export_draft(
            draft_name=args.draft_name,
            output_path=test_output_path,
            resolution=get_resolution(args.resolution),
            framerate=get_framerate(args.framerate)
        )
        
        # 验证导出结果
        if os.path.exists(test_output_path):
            file_size = os.path.getsize(test_output_path) / (1024 * 1024)  # 转换为MB
            logger.info(f"导出成功！文件大小: {file_size:.1f}MB")
            return True
        else:
            logger.error("导出失败：文件不存在")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        return False

def main():
    """主函数"""
    args = parse_args()
    logger.info("开始测试")
    
    # 运行测试
    success = test_export(args)
    
    # 输出测试结果
    if success:
        logger.info("测试通过！")
        sys.exit(0)
    else:
        logger.error("测试失败！")
        sys.exit(1)

if __name__ == "__main__":
    main() 