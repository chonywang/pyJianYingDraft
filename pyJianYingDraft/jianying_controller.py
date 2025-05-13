"""剪映自动化控制，主要与自动导出有关"""

import time
import shutil
import json
import os
from pathlib import Path
from enum import Enum
from typing import Optional, Literal, Dict, Any, Tuple, List
import logging

from . import exceptions
from .exceptions import AutomationError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Export_resolution(Enum):
    """导出分辨率"""
    RES_8K = "8K"
    RES_4K = "4K"
    RES_2K = "2K"
    RES_1080P = "1080P"
    RES_720P = "720P"
    RES_480P = "480P"

class Export_framerate(Enum):
    """导出帧率"""
    FR_24 = "24fps"
    FR_25 = "25fps"
    FR_30 = "30fps"
    FR_50 = "50fps"
    FR_60 = "60fps"

class Jianying_controller:
    """剪映控制器 - 文件操作版本"""

    def __init__(self, draft_path: Optional[str] = None, log_level: int = logging.INFO):
        """初始化剪映控制器
        
        Args:
            draft_path (str, optional): 剪映草稿文件夹路径，如果不指定则使用默认路径
            log_level (int, optional): 日志级别，默认为 INFO
        """
        logger.setLevel(log_level)
        self.draft_path = draft_path or self._get_default_draft_path()
        if not os.path.exists(self.draft_path):
            raise AutomationError(f"剪映草稿文件夹不存在: {self.draft_path}")
        
        # 获取默认导出路径
        self.default_export_path = self._get_default_export_path()
        logger.info(f"草稿路径: {self.draft_path}")
        logger.info(f"默认导出路径: {self.default_export_path}")

    def _get_default_draft_path(self) -> str:
        """获取剪映默认草稿文件夹路径"""
        if os.name == 'nt':  # Windows
            return os.path.expanduser("~/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft")
        elif os.name == 'posix':  # macOS/Linux
            # 尝试多个可能的路径
            possible_paths = [
                os.path.expanduser("~/Library/Application Support/JianyingPro/User Data/Projects/com.lveditor.draft"),
                os.path.expanduser("~/Library/Application Support/JianyingPro/Projects/com.lveditor.draft"),
                os.path.expanduser("~/Documents/jianyan/JianyingPro Drafts"),
                os.path.expanduser("~/Documents/JianyingPro Drafts")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
                    
            # 如果都找不到，返回最可能的路径
            return possible_paths[2]  # 返回 ~/Documents/jianyan/JianyingPro Drafts
        else:
            raise AutomationError("不支持的操作系统")

    def _get_default_export_path(self) -> str:
        """获取剪映默认导出路径"""
        if os.name == 'nt':  # Windows
            return os.path.expanduser("~/Videos/剪映导出")
        elif os.name == 'posix':  # macOS/Linux
            return os.path.expanduser("~/Movies/剪映导出")
        else:
            raise AutomationError("不支持的操作系统")

    def _find_draft_folder(self, draft_name: str) -> str:
        """查找指定名称的草稿文件夹
        
        Args:
            draft_name (str): 草稿名称
            
        Returns:
            str: 草稿文件夹路径
            
        Raises:
            DraftNotFound: 未找到指定名称的草稿
        """
        logger.info(f"查找草稿: {draft_name}")
        for folder in os.listdir(self.draft_path):
            folder_path = os.path.join(self.draft_path, folder)
            if not os.path.isdir(folder_path):
                continue
                
            # 支持 draft_meta.json 和 draft_meta_info.json
            meta_file = os.path.join(folder_path, "draft_meta.json")
            if not os.path.exists(meta_file):
                meta_file = os.path.join(folder_path, "draft_meta_info.json")
                if not os.path.exists(meta_file):
                    continue
                
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    if meta.get('draft_name') == draft_name:
                        logger.info(f"找到草稿: {folder_path}")
                        return folder_path
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"读取草稿元数据失败: {folder_path}, 错误: {str(e)}")
                continue
                
        raise exceptions.DraftNotFound(f"未找到名为{draft_name}的剪映草稿")

    def _get_export_filename(self, draft_name: str) -> str:
        """根据草稿名称生成导出文件名
        
        Args:
            draft_name (str): 草稿名称
            
        Returns:
            str: 导出文件名
        """
        # 移除非法字符
        safe_name = "".join(c for c in draft_name if c.isalnum() or c in " -_")
        return f"{safe_name}.mp4"

    def _prepare_output_path(self, output_path: Optional[str], draft_name: str) -> Tuple[str, str]:
        """准备输出路径
        
        Args:
            output_path (str, optional): 用户指定的输出路径
            draft_name (str): 草稿名称
            
        Returns:
            Tuple[str, str]: (临时导出路径, 最终输出路径)
        """
        if output_path is None:
            # 使用默认导出路径
            output_path = os.path.join(self.default_export_path, self._get_export_filename(draft_name))
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # 临时导出路径（在默认导出目录）
        temp_export_path = os.path.join(self.default_export_path, self._get_export_filename(draft_name))
        
        logger.info(f"临时导出路径: {temp_export_path}")
        logger.info(f"最终输出路径: {output_path}")
        
        return temp_export_path, output_path

    def _monitor_export_progress(self, temp_export_path: str, timeout: float) -> bool:
        """监控导出进度
        
        Args:
            temp_export_path (str): 临时导出文件路径
            timeout (float): 超时时间
            
        Returns:
            bool: 是否成功导出
        """
        st = time.time()
        last_size = 0
        no_change_count = 0
        
        while True:
            if os.path.exists(temp_export_path):
                try:
                    current_size = os.path.getsize(temp_export_path)
                    if current_size > last_size:
                        logger.info(f"导出进度: {current_size / 1024 / 1024:.1f}MB")
                        last_size = current_size
                        no_change_count = 0
                    else:
                        no_change_count += 1
                        if no_change_count >= 5:  # 5秒没有变化，认为导出完成
                            return True
                except OSError:
                    pass
                    
            if time.time() - st > timeout:
                logger.error(f"导出超时，时限为{timeout}秒")
                return False
                
            time.sleep(1)
            
        return False

    def _move_exported_file(self, temp_export_path: str, final_output_path: str, max_retries: int = 3) -> bool:
        """移动导出的文件
        
        Args:
            temp_export_path (str): 临时导出文件路径
            final_output_path (str): 最终输出路径
            max_retries (int): 最大重试次数
            
        Returns:
            bool: 是否成功移动
        """
        for i in range(max_retries):
            try:
                # 等待文件写入完成
                time.sleep(2)
                # 移动文件到最终位置
                shutil.move(temp_export_path, final_output_path)
                logger.info(f"文件已移动到: {final_output_path}")
                return True
            except (shutil.Error, OSError) as e:
                logger.warning(f"移动文件失败 (尝试 {i+1}/{max_retries}): {str(e)}")
                time.sleep(1)
                
        return False

    def export_draft(self, draft_name: str, output_path: Optional[str] = None, *,
                     resolution: Optional[Export_resolution] = None,
                     framerate: Optional[Export_framerate] = None,
                     timeout: float = 1200) -> None:
        """导出指定的剪映草稿
        
        Args:
            draft_name (str): 要导出的剪映草稿名称
            output_path (str, optional): 导出路径，支持指向文件夹或直接指向文件
            resolution (Export_resolution, optional): 导出分辨率
            framerate (Export_framerate, optional): 导出帧率
            timeout (float, optional): 导出超时时间(秒)，默认为20分钟
            
        Raises:
            DraftNotFound: 未找到指定名称的剪映草稿
            AutomationError: 导出操作失败
        """
        logger.info(f"开始导出草稿: {draft_name}")
        
        # 查找草稿文件夹
        draft_folder = self._find_draft_folder(draft_name)
        
        # 更新导出设置
        if resolution is not None or framerate is not None:
            self._update_export_settings(draft_folder, resolution, framerate)
        
        # 准备输出路径
        temp_export_path, final_output_path = self._prepare_output_path(output_path, draft_name)
            
        # 导出视频
        logger.info("\n请在剪映中执行以下步骤：")
        logger.info("1. 打开剪映并找到项目")
        logger.info("2. 点击导出按钮")
        logger.info("3. 确认导出设置")
        logger.info("4. 点击导出")
        logger.info("\n导出完成后，文件将被移动到指定位置")
        
        # 监控导出进度
        if not self._monitor_export_progress(temp_export_path, timeout):
            raise AutomationError(f"导出超时，时限为{timeout}秒")
            
        # 移动导出的文件
        if not self._move_exported_file(temp_export_path, final_output_path):
            raise AutomationError("移动导出文件失败")
            
        logger.info(f"导出完成: {final_output_path}")

    def _update_export_settings(self, draft_folder: str, 
                              resolution: Optional[Export_resolution] = None,
                              framerate: Optional[Export_framerate] = None) -> None:
        """更新导出设置
        
        Args:
            draft_folder (str): 草稿文件夹路径
            resolution (Export_resolution, optional): 导出分辨率
            framerate (Export_framerate, optional): 导出帧率
        """
        # 支持多种设置文件名
        settings_candidates = [
            os.path.join(draft_folder, "draft_settings.json"),
            os.path.join(draft_folder, "draft_settings"),
            os.path.join(draft_folder, "draft_setting.json"),
            os.path.join(draft_folder, "draft_setting"),
        ]
        settings_file = None
        for candidate in settings_candidates:
            if os.path.exists(candidate):
                settings_file = candidate
                break
        
        if not settings_file:
            logger.warning(f"未找到导出设置文件，跳过分辨率/帧率设置")
            return
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if first_line.strip().startswith('['):  # INI格式
                    logger.warning(f"导出设置文件为INI格式，无法自动设置分辨率/帧率: {settings_file}")
                    return
                f.seek(0)
                try:
                    settings = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"导出设置文件不是合法JSON，跳过分辨率/帧率设置: {settings_file}")
                    return
                
            if resolution is not None:
                settings['export_resolution'] = resolution.value
                logger.info(f"设置导出分辨率: {resolution.value}")
            if framerate is not None:
                settings['export_framerate'] = framerate.value
                logger.info(f"设置导出帧率: {framerate.value}")
                
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
        except (KeyError, IOError) as e:
            raise AutomationError(f"更新导出设置失败: {str(e)}")
