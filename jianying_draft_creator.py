#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JianYing Draft Creator - 模块化、可配置的剪映草稿创建工具

功能特点:
- 支持从配置文件或命令行参数创建草稿
- 支持添加多段视频、转场效果
- 支持添加音频(网络或本地)
- 支持添加文本
- 完整的日志记录
- 错误处理和恢复
"""

import os
import sys
import json
import uuid
import time
import logging
import requests
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# 对于当前目录的项目，已经在正确路径上
# 无需额外添加路径

# 导入JianYing相关库
try:
    from pyJianYingDraft import Transition_type, Track_type, trange, tim
    from pyJianYingDraft.script_file import Script_file
    from pyJianYingDraft.audio_segment import Audio_segment
    from pyJianYingDraft.local_materials import Audio_material
    from jianying_utils import batch_generate_drafts
except ImportError as e:
    print(f"错误: 找不到pyJianYingDraft库或相关模块。详情: {e}")
    sys.exit(1)

# 如果tim未导入，提供一个备用实现
if 'tim' not in locals():
    def tim(time_str):
        """将时间字符串转换为微秒整数"""
        if isinstance(time_str, int):
            return time_str
        if isinstance(time_str, str) and 's' in time_str:
            return int(float(time_str.rstrip('s')) * 1000000)
        return 0

# 确保日志目录存在
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, "jianying_draft_creator.log"))
    ]
)
logger = logging.getLogger("JianYingDraftCreator")

# 默认配置
DEFAULT_CONFIG = {
    "draft_name": "auto_generated_draft",
    "drafts_root": os.path.expanduser("~/Documents/jianyan/JianyingPro Drafts"),
    "resolution": {
        "width": 1920,
        "height": 1080
    },
    "jianying_version": "3.1.0-beta7",
    "videos": [],
    "audio": [
        {
        "url": None,
        "local_path": None,
        "enabled": False,
        "volume": 1.0,
        "fade_in": None,   # 淡入时间，如 "0.5s"
        "fade_out": None,  # 淡出时间，如 "0.5s"
            "effects": [],      # 音频特效列表
            "start": "0s"      # 音频开始时间
        }
    ],
    "texts": []
}

class JianYingDraftCreator:
    """JianYing草稿创建器"""
    
    def __init__(self, config: Dict):
        """初始化创建器
        
        Args:
            config: 包含所有配置选项的字典
        """
        self.config = self._validate_and_fill_config(config)
        
        # 创建草稿文件夹
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.draft_name = f"{self.config['draft_name']}_{self.timestamp}"
        self.draft_path = os.path.join(self.config['drafts_root'], self.draft_name)
        os.makedirs(self.draft_path, exist_ok=True)
        
        # 初始化资源列表
        self.downloaded_files = []
        logger.info(f"草稿将保存到: {self.draft_path}")
    
    def _validate_and_fill_config(self, config: Dict) -> Dict:
        """验证配置并填充默认值
        
        Args:
            config: 用户提供的配置
            
        Returns:
            合并后的完整配置
        """
        # 深度合并默认配置和用户配置
        result = DEFAULT_CONFIG.copy()
        
        # 合并顶层键
        for key, value in config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 如果两者都是字典，递归合并
                result[key].update(value)
            else:
                # 否则直接替换
                result[key] = value
        
        # 验证必要的配置
        if not result["videos"]:
            logger.warning("未提供视频配置，草稿将为空")
        
        # 检查并创建drafts_root目录
        os.makedirs(result["drafts_root"], exist_ok=True)
        
        return result
    
    def download_file(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """从URL下载文件到草稿目录
        
        Args:
            url: 文件URL
            filename: 文件保存名称，如果未提供则从URL提取
            
        Returns:
            下载的文件路径，失败则返回None
        """
        if not filename:
            filename = os.path.basename(url.split("?")[0])
        
        output_path = os.path.join(self.draft_path, filename)
        
        # 如果已经存在就不重复下载
        if os.path.exists(output_path):
            logger.info(f"文件已存在: {output_path}")
            self.downloaded_files.append(output_path)
            return output_path
        
        try:
            logger.info(f"下载文件: {url}")
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024
                
                with open(output_path, 'wb') as f:
                    for data in response.iter_content(block_size):
                        f.write(data)
                
                logger.info(f"文件下载完成: {output_path}")
                self.downloaded_files.append(output_path)
                return output_path
            else:
                logger.error(f"下载失败，HTTP状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"下载文件时发生错误: {str(e)}")
            return None
    
    def create_draft(self) -> Optional[str]:
        """创建草稿
        
        Returns:
            创建成功的草稿路径，失败返回None
        """
        try:
            # 第1步: 创建基础草稿
            logger.info("开始创建基础草稿...")
            
            # 下载所有视频
            video_files = []
            for video_config in self.config["videos"]:
                if video_config.get("file_path"):
                    video_path = video_config["file_path"]
                    # 检查是否是URL
                    if video_path.startswith(("http://", "https://")):
                        downloaded_path = self.download_file(video_path)
                        if downloaded_path:
                            video_config["local_file_path"] = downloaded_path
                        else:
                            logger.error(f"无法下载视频: {video_path}")
                            continue
                    else:
                        # 本地文件 - 确保存在
                        if os.path.exists(video_path):
                            video_config["local_file_path"] = video_path
                        else:
                            logger.error(f"找不到本地视频文件: {video_path}")
                            continue
                    
                    video_files.append(video_config)
            
            # 创建初始草稿
            res = self.config["resolution"]
            draft_params = [{
                "draft_name": self.draft_name,
                "videos": video_files,
                "texts": self.config.get("texts", [])
            }]
            
            # 尝试找到模板目录
            template_folder = self._find_template_folder()
            if not template_folder:
                logger.warning("未找到模板目录，尝试使用默认模板")
                # 使用默认模板路径
                template_folder = os.path.join(self.config["drafts_root"], "Draft Template Old")
            
            # 使用demo.batch_generate_drafts创建基础草稿
            batch_generate_drafts(draft_params, 
                                  template_folder=template_folder,
                                  drafts_root=self.config["drafts_root"])
            
            # 查找实际的草稿目录
            self._find_actual_draft_path()
            
            # 处理完整的草稿参数
            draft_data = {
                "videos": video_files,
                "texts": self.config.get("texts", []),
                "audio": self.config.get("audio", [])
            }
            
            # 将音频直接添加到初始草稿中 - 使用更简单的方法
            if any(audio.get("enabled", False) for audio in self.config.get("audio", [])):
                if self._process_audio_with_demo_method(draft_data, self.actual_draft_path):
                    logger.info("音频处理成功")
                else:
                    logger.warning("音频处理失败")
            
            # 使用找到的实际草稿路径
            if hasattr(self, 'actual_draft_path') and self.actual_draft_path:
                logger.info(f"草稿创建成功: {self.actual_draft_path}")
                return self.actual_draft_path
            else:
                logger.info(f"草稿创建成功: {self.draft_path}")
                return self.draft_path
            
        except Exception as e:
            logger.error(f"创建草稿时发生错误: {str(e)}", exc_info=True)
            return None
    
    def _find_actual_draft_path(self) -> None:
        """查找实际生成的草稿路径"""
        # 首先检查原始路径是否包含draft_content.json
        draft_content_path = os.path.join(self.draft_path, "draft_content.json")
        if os.path.exists(draft_content_path):
            self.actual_draft_path = self.draft_path
            return
        
        # 查找以草稿名称开头的子目录
        potential_dirs = [d for d in os.listdir(self.config['drafts_root']) 
                         if os.path.isdir(os.path.join(self.config['drafts_root'], d)) and 
                         d.startswith(self.draft_name)]
        
        if potential_dirs:
            # 按创建时间排序，使用最新的目录
            latest_dir = max(potential_dirs, 
                            key=lambda d: os.path.getmtime(os.path.join(self.config['drafts_root'], d)))
            
            self.actual_draft_path = os.path.join(self.config['drafts_root'], latest_dir)
            logger.info(f"找到实际草稿目录: {self.actual_draft_path}")
            return
        
        # 如果都找不到，尝试递归查找
        for root, dirs, files in os.walk(self.config['drafts_root']):
            if "draft_content.json" in files and self.draft_name in root:
                self.actual_draft_path = root
                logger.info(f"通过递归找到实际草稿目录: {self.actual_draft_path}")
                return
        
        logger.warning(f"无法找到实际草稿目录，将使用原始路径: {self.draft_path}")
    
    def _find_template_folder(self) -> Optional[str]:
        """查找可用的模板目录
        
        Returns:
            模板目录路径，如果找不到则返回None
        """
        # 按优先级搜索模板目录
        template_candidates = [
            # 1. 配置文件中指定的模板目录
            self.config.get("template_folder"),
            # 2. 相对于当前目录的template目录
            os.path.join(PROJECT_ROOT, "template"),
            # 3. 相对于drafts_root的Draft Template Old目录
            os.path.join(self.config["drafts_root"], "Draft Template Old"),
            # 4. 按名称搜索drafts_root下的疑似模板目录
            *[os.path.join(self.config["drafts_root"], d) for d in os.listdir(self.config["drafts_root"])
              if os.path.isdir(os.path.join(self.config["drafts_root"], d)) and "template" in d.lower()]
        ]
        
        # 筛选存在的目录
        valid_templates = [t for t in template_candidates if t and os.path.isdir(t)]
        
        if valid_templates:
            template_path = valid_templates[0]
            logger.info(f"使用模板目录: {template_path}")
            return template_path
        
        return None
    
    def _process_audio_with_demo_method(self, draft_data: Dict, draft_folder: str) -> bool:
        """使用类似demo.py的方式处理音频
        
        Args:
            draft_data: 草稿数据
            draft_folder: 草稿文件夹路径
        
        Returns:
            成功返回True，否则False
        """
        try:
            # 读取现有的草稿内容
            draft_content_path = os.path.join(draft_folder, "draft_content.json")
            if not os.path.exists(draft_content_path):
                logger.error(f"找不到草稿内容文件: {draft_content_path}")
                return False
            
            with open(draft_content_path, "r", encoding="utf-8") as f:
                content = json.load(f)
            
            # 创建音频轨道（如果不存在）
            if "tracks" not in content:
                content["tracks"] = []
            
            # 查找现有的音频轨道
            audio_track = None
            for track in content["tracks"]:
                if track.get("type") == "audio":
                    audio_track = track
                    break
            
            # 如果没有音频轨道，创建一个
            if not audio_track:
                audio_track = {
                    "id": str(uuid.uuid4()).replace("-", ""),
                    "type": "audio",
                    "name": "音轨",
                    "segments": []
                }
                content["tracks"].append(audio_track)
                logger.info("已创建新的音频轨道")
            elif "segments" not in audio_track:
                audio_track["segments"] = []
            
            # 确保materials部分存在
            if "materials" not in content:
                content["materials"] = {}
            
            if "audios" not in content["materials"]:
                content["materials"]["audios"] = []
            
            # 处理音频
            processed_count = 0
            for audio_index, audio in enumerate(draft_data.get("audio", [])):
                if not audio.get("enabled", False):
                    continue
                
                # 下载音频文件
                audio_path = None
                if audio.get("local_path"):
                    if os.path.exists(audio.get("local_path")):
                        audio_path = audio.get("local_path")
                    else:
                        logger.error(f"找不到本地音频文件: {audio.get('local_path')}")
                        continue
                elif audio.get("url"):
                    audio_filename = f"audio_{audio_index}_{time.strftime('%Y%m%d_%H%M%S')}.mp3"
                    downloaded_path = self.download_file(audio.get("url"), audio_filename)
                    if downloaded_path:
                        audio_path = downloaded_path
                    else:
                        logger.error(f"无法下载音频: {audio.get('url')}")
                        continue
                else:
                    logger.warning(f"音频 #{audio_index+1} 没有提供路径或URL，跳过处理")
                    continue
                
                # 创建音频素材
                # 1. 创建唯一ID
                audio_id = str(uuid.uuid4()).replace("-", "")
                
                # 2. 获取音频文件的时长
                # 使用 Script_file 和 Audio_material 获取时长
                script = Script_file(1920, 1080)
                audio_material = Audio_material(audio_path)
                
                # 毫秒为单位的时长
                audio_duration_ms = audio_material.duration
                audio_duration_s = audio_duration_ms / 1000000
                logger.info(f"音频 #{audio_index+1} 时长: {audio_duration_s:.3f}秒")
                
                # 设置各属性
                volume = audio.get("volume", 1.0)
                start_time_str = audio.get("start", "0s")
                start_time_ms = 0
                
                if isinstance(start_time_str, str) and start_time_str.endswith("s"):
                    start_time_s = float(start_time_str.rstrip("s"))
                    start_time_ms = int(start_time_s * 1000000)
                
                # 3. 创建音频素材对象
                audio_material_obj = {
                    "app_id": 0,
                    "category_id": "",
                    "category_name": "local",
                    "check_flag": 1,
                    "copyright_limit_type": "none",
                    "duration": audio_duration_ms,
                    "effect_id": "",
                    "formula_id": "",
                    "id": audio_id,
                    "intensifies_path": "",
                    "is_ai_clone_tone": False,
                    "is_text_edit_overdub": False,
                    "is_ugc": False,
                    "local_material_id": audio_id,
                    "music_id": audio_id,
                    "name": os.path.basename(audio_path),
                    "path": audio_path,
                    "query": "",
                    "request_id": "",
                    "resource_id": "",
                    "search_id": "",
                    "source_from": "",
                    "source_platform": 0,
                    "team_id": "",
                    "text_id": "",
                    "type": "extract_music",
                    "video_id": "",
                    "wave_points": []
                }
                
                # 添加到素材列表
                content["materials"]["audios"].append(audio_material_obj)
                
                # 4. 创建音频片段
                segment_id = str(uuid.uuid4()).replace("-", "")
                
                # 音频可能有淡入淡出效果
                has_fade = audio.get("fade_in") or audio.get("fade_out")
                fade_material_id = None
                
                # 如果有淡入淡出，需要创建fade素材
                if has_fade:
                    # 创建fade ID
                    fade_material_id = str(uuid.uuid4()).replace("-", "")
                    
                    # 确保audio_fades部分存在
                    if "audio_fades" not in content["materials"]:
                        content["materials"]["audio_fades"] = []
                    
                    # 淡入/淡出参数
                    fade_in_ms = 0
                    fade_out_ms = 0
                    
                    if audio.get("fade_in"):
                        fade_in_str = audio.get("fade_in")
                        if isinstance(fade_in_str, str) and fade_in_str.endswith("s"):
                            fade_in_s = float(fade_in_str.rstrip("s"))
                            fade_in_ms = int(fade_in_s * 1000000)
                    
                    if audio.get("fade_out"):
                        fade_out_str = audio.get("fade_out")
                        if isinstance(fade_out_str, str) and fade_out_str.endswith("s"):
                            fade_out_s = float(fade_out_str.rstrip("s"))
                            fade_out_ms = int(fade_out_s * 1000000)
                    
                    # 创建淡入淡出素材
                    fade_material = {
                        "id": fade_material_id,
                        "type": "audio_fade",
                        "fade_in": fade_in_ms,
                        "fade_out": fade_out_ms,
                        "fade_in_type": 0 if fade_in_ms > 0 else None,
                        "fade_out_type": 0 if fade_out_ms > 0 else None
                    }
                    
                    content["materials"]["audio_fades"].append(fade_material)
                    logger.info(f"已添加淡入淡出效果: 淡入={fade_in_ms/1000000:.1f}s, 淡出={fade_out_ms/1000000:.1f}s")
                
                # 创建音频片段对象
                segment = {
                    "enable_adjust": True,
                    "enable_color_correct_adjust": False,
                    "enable_color_curves": True,
                    "enable_color_match_adjust": False,
                    "enable_color_wheels": True,
                    "enable_lut": True,
                    "enable_smart_color_adjust": False,
                    "last_nonzero_volume": volume,
                    "reverse": False,
                    "track_attribute": 0,
                    "track_render_index": 0,
                    "visible": True,
                    "id": segment_id,
                    "material_id": audio_id,
                    "target_timerange": {
                        "start": start_time_ms,
                        "duration": audio_duration_ms
                    },
                    "common_keyframes": [],
                    "keyframe_refs": [],
                    "source_timerange": {
                        "start": 0,
                        "duration": audio_duration_ms
                    },
                    "speed": 1.0,
                    "volume": volume,
                    "extra_material_refs": []
                }
                
                # 如果有淡入淡出，添加引用
                if fade_material_id:
                    segment["extra_material_refs"].append(fade_material_id)
                
                # 添加片段到轨道
                audio_track["segments"].append(segment)
                
                logger.info(f"已添加音频片段 #{audio_index+1} 到轨道, 开始时间: {start_time_ms/1000000}秒, 时长: {audio_duration_ms/1000000}秒")
                processed_count += 1
            
            # 更新草稿持续时间
            # 找出所有片段的最大结束时间
            end_time_ms = 0
            for track in content["tracks"]:
                for segment in track.get("segments", []):
                    timerange = segment.get("target_timerange", {})
                    if timerange:
                        segment_end = timerange.get("start", 0) + timerange.get("duration", 0)
                        end_time_ms = max(end_time_ms, segment_end)
            
            # 如果现有时长小于计算出的时长，则更新
            if end_time_ms > content.get("duration", 0):
                content["duration"] = end_time_ms
                logger.info(f"更新草稿持续时间为: {end_time_ms/1000000:.3f}秒")
            
            # 保存回文件
            with open(draft_content_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已处理 {processed_count} 个音频文件")
            return processed_count > 0
            
        except Exception as e:
            logger.error(f"处理音频时发生错误: {str(e)}", exc_info=True)
            return False
    
    def cleanup(self) -> None:
        """清理临时资源（如果需要）"""
        pass

def load_config(config_path: str) -> Dict:
    """从文件加载配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {str(e)}")
        return {}

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="JianYing草稿创建工具")
    
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--name", help="草稿名称")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--template", help="模板目录路径")
    parser.add_argument("--video", action="append", help="添加视频（可多次使用）")
    parser.add_argument("--audio", action="append", help="添加音频（URL或本地路径，可多次使用）")
    parser.add_argument("--audio-volume", type=float, default=1.0, help="音频音量（0.0-2.0）")
    parser.add_argument("--audio-start", default="0s", help="音频开始时间（如 1.5s）")
    parser.add_argument("--audio-fade-in", help="音频淡入时间（如 0.5s）")
    parser.add_argument("--audio-fade-out", help="音频淡出时间（如 0.5s）")
    parser.add_argument("--version", "-v", action="store_true", help="显示版本信息")
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 显示版本信息
    if args.version:
        print("JianYing草稿创建工具 v1.0.0")
        return
    
    # 初始化配置
    config = DEFAULT_CONFIG.copy()
    
    # 从配置文件加载（如果提供）
    if args.config:
        file_config = load_config(args.config)
        config.update(file_config)
    
    # 从命令行参数更新配置
    if args.name:
        config["draft_name"] = args.name
    
    if args.output_dir:
        config["drafts_root"] = args.output_dir
    
    if args.template:
        config["template_folder"] = args.template
    
    if args.video:
        videos = []
        for video_path in args.video:
            videos.append({
                "file_path": video_path,
                "start": "0s",
                "duration": "5s",
                "target_start": f"{len(videos) * 5}s",
                "transition": ["上移", "闪白", "叠化"][len(videos) % 3],
                "effects": []
            })
        config["videos"] = videos
    
    # 处理音频相关参数
    if args.audio:
        audio_tracks = []
        for audio_path in args.audio:
            audio_config = {
                "enabled": True,
                "volume": args.audio_volume,
                "start": args.audio_start
            }
            
            # 设置音频路径或URL
            if audio_path.startswith(("http://", "https://")):
                audio_config["url"] = audio_path
            else:
                audio_config["local_path"] = audio_path
            
            # 设置淡入淡出
            if args.audio_fade_in:
                audio_config["fade_in"] = args.audio_fade_in
            
            if args.audio_fade_out:
                audio_config["fade_out"] = args.audio_fade_out
            
            audio_tracks.append(audio_config)
        
        if audio_tracks:
            config["audio"] = audio_tracks
    
    # 确保视频配置存在
    if not config.get("videos"):
        print("错误: 未提供视频配置")
        print("请通过--video参数或配置文件提供至少一个视频源")
        return
    
    # 创建并运行生成器
    creator = JianYingDraftCreator(config)
    draft_path = creator.create_draft()
    
    if draft_path:
        print(f"\n✅ 成功创建草稿")
        print(f"📁 草稿路径: {draft_path}")
        print(f"🎬 请在剪映中打开并查看")
    else:
        print("\n❌ 创建草稿失败，请查看日志了解详情")

if __name__ == "__main__":
    main() 