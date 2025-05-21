"""
剪映AI MCP (Master Control Program)

这个模块提供了一个AI驱动的主控程序，可以：
1. 接收自然语言指令
2. 解析指令并转换为API调用
3. 管理整个视频创建流程
4. 提供简单的聊天式界面
5. 支持从互联网下载视频
6. 支持自动视频剪辑
7. 支持自动搜索和下载视频

通过整合openai/langchain与template_config_manager.py，它允许用户通过自然语言来创建和修改视频草稿。
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
import re
import asyncio
import yt_dlp
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from config import API_KEYS, ARK_CONFIG, OPENAI_CONFIG, JIANYING_CONFIG, PEXELS_API_KEY
from youtubesearchpython import VideosSearch
import traceback

# 设置API客户端
def get_llm_client():
    """获取LLM客户端"""
    # 优先使用ARK API
    if API_KEYS["ARK_API_KEY"]:
        return OpenAI(
            base_url=ARK_CONFIG["base_url"],
            api_key=API_KEYS["ARK_API_KEY"]
        )
    # 如果没有ARK API Key，则使用OpenAI
    elif API_KEYS["OPENAI_API_KEY"]:
        return OpenAI(api_key=API_KEYS["OPENAI_API_KEY"])
    else:
        raise ValueError("未设置任何API密钥，请在config.py中配置ARK_API_KEY或OPENAI_API_KEY")

# API基础URL
BASE_URL = JIANYING_CONFIG["base_url"]

# 当前草稿追踪
current_drafts = {}

# 临时文件目录
TEMP_DIR = Path(tempfile.gettempdir()) / "jianying_mcp"
TEMP_DIR.mkdir(exist_ok=True)

class DraftInfo(BaseModel):
    """草稿信息模型"""
    draft_id: str
    draft_name: str
    creation_time: datetime
    last_modified: datetime
    description: str = ""

class VideoAnalyzer:
    """视频分析器"""
    
    def __init__(self):
        """初始化视频分析器"""
        self.client = get_llm_client()
    
    def analyze_video(self, video_path: str, theme: str = None) -> List[Dict[str, Any]]:
        """分析视频内容，返回精彩片段列表
        
        Args:
            video_path: 视频文件路径
            theme: 视频主题，用于指导剪辑方向
            
        Returns:
            精彩片段列表，每个片段包含开始时间、持续时间和描述
        """
        # 提取视频关键帧
        frames = self._extract_keyframes(video_path)
        
        # 使用LLM分析关键帧
        analysis = self._analyze_frames(frames, theme)
        
        # 生成精彩片段列表
        clips = self._generate_clips(analysis)
        
        return clips
    
    def _extract_keyframes(self, video_path: str) -> List[Tuple[float, np.ndarray]]:
        """提取视频关键帧
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            关键帧列表，每个元素为(时间戳, 帧图像)
        """
        frames = []
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # 每隔5秒提取一帧
        interval = int(fps * 5)
        frame_count = 0
        max_frames = 50  # 最多只提取50帧
        while cap.isOpened() and len(frames) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % interval == 0:
                timestamp = frame_count / fps
                frames.append((timestamp, frame))
            frame_count += 1
        cap.release()
        return frames
    
    def _analyze_frames(self, frames: List[Tuple[float, np.ndarray]], theme: str = None) -> List[Dict[str, Any]]:
        """使用LLM分析关键帧
        
        Args:
            frames: 关键帧列表
            theme: 视频主题
            
        Returns:
            分析结果列表
        """
        # 将帧转换为base64编码
        frame_descriptions = []
        for timestamp, frame in frames:
            # 将帧转换为较小的尺寸以节省空间
            small_frame = cv2.resize(frame, (320, 180))
            _, buffer = cv2.imencode('.jpg', small_frame)
            frame_base64 = buffer.tobytes().hex()
            
            frame_descriptions.append({
                "timestamp": timestamp,
                "frame": frame_base64
            })
        
        # 构建提示词
        theme_prompt = f"主题：{theme}\n" if theme else ""
        prompt = f"""
        请分析以下视频帧序列，找出最精彩的片段。{theme_prompt}
        每个片段应该：
        1. 包含有趣或重要的内容
        2. 有清晰的开始和结束
        3. 持续时间适中（5-15秒）
        4. 符合主题要求（如果指定了主题）
        
        帧序列：
        {json.dumps(frame_descriptions)}
        
        请返回JSON格式的分析结果，包含每个精彩片段的：
        1. 开始时间（秒）
        2. 持续时间（秒）
        3. 简短描述
        4. 与主题的相关性（如果指定了主题）
        """
        
        try:
            response = self.client.chat.completions.create(
                model=ARK_CONFIG["model"] if API_KEYS["ARK_API_KEY"] else OPENAI_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你是视频分析专家，负责找出视频中的精彩片段。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # 尝试提取JSON
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            try:
                result = json.loads(json_str)
                print("LLM分析结果：", result)
                return result
            except json.JSONDecodeError:
                print(f"无法解析JSON响应: {content}")
                return []
        
        except Exception as e:
            print(f"分析视频帧时发生错误: {str(e)}")
            traceback.print_exc()
            return []
    
    def _generate_clips(self, analysis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """根据分析结果生成剪辑片段
        
        Args:
            analysis: 分析结果列表
            
        Returns:
            剪辑片段列表
        """
        clips = []
        for item in analysis:
            clip = {
                "start": f"{int(item['start'])}s",
                "duration": f"{int(item['duration'])}s",
                "description": item['description']
            }
            if "relevance" in item:
                clip["relevance"] = item["relevance"]
            clips.append(clip)
        
        return clips

class VideoDownloader:
    """视频下载器"""
    
    def __init__(self):
        """初始化下载器"""
        self.ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': str(TEMP_DIR / '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True
        }
        self.analyzer = VideoAnalyzer()
    
    def download_video(self, url: str) -> Optional[str]:
        """下载视频（支持 TikTok、YouTube、B站等主流平台）
        
        Args:
            url: 视频URL（支持 TikTok、YouTube、B站等）
            
        Returns:
            下载后的视频文件路径，如果下载失败则返回None
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = str(TEMP_DIR / f"{info['id']}.mp4")
                return video_path if os.path.exists(video_path) else None
        except Exception as e:
            print(f"下载视频时发生错误: {str(e)}")
            print("提示：如为 YouTube 视频，需配置 cookies；如为 TikTok、B站等公开视频，通常无需额外配置。")
            traceback.print_exc()
            return None
    
    def download_and_analyze(self, url: str, theme: str = None) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """下载并分析视频
        
        Args:
            url: 视频URL（支持 TikTok、YouTube、B站等）
            theme: 视频主题
            
        Returns:
            (视频文件路径, 精彩片段列表)
        """
        video_path = self.download_video(url)
        if not video_path:
            return None, []
        
        clips = self.analyzer.analyze_video(video_path, theme)
        return video_path, clips

class NLPProcessor:
    """自然语言处理器"""
    
    def __init__(self):
        """初始化NLP处理器"""
        self.client = get_llm_client()
    
    def process_command(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入命令
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            解析后的命令和参数
        """
        prompt = f"""
你是一个视频编辑助手，需要将用户的自然语言指令转换为结构化的API调用信息。
根据以下用户输入，判断用户想要执行的操作，并返回JSON格式的结构化数据。

可能的操作类型包括：
1. create_draft - 创建新草稿
2. add_video - 添加视频
3. add_audio - 添加音频
4. add_text - 添加文本
5. get_draft_info - 获取草稿信息
6. save_draft - 保存草稿
7. list_drafts - 列出所有草稿
8. delete_draft - 删除草稿
9. download_and_edit - 下载并编辑视频
10. search_and_edit - 搜索并编辑视频
11. search_only - 只搜索视频并返回列表
12. unknown - 无法识别的命令

注意：
- 如果用户输入为"搜索xxx视频"或"查找xxx视频"，action 应为 search_only，query 字段为关键词。
- 如果用户输入中包含明确的视频URL（如以 http 开头），action 应为 download_and_edit。
- 如果用户输入只是描述视频内容（如"下载并剪辑美食探店视频"或"搜索并剪辑美食视频"），action 应为 search_and_edit，query 字段为用户描述的关键词。
- 如果用户输入中既有URL又有描述，优先以URL为准。

用户输入: {user_input}

请返回JSON格式的响应，例如：
对于只搜索视频：
{{
    "action": "search_only",
    "query": "美食探店"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=ARK_CONFIG["model"] if API_KEYS["ARK_API_KEY"] else OPENAI_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你是视频编辑助手，负责将自然语言转换为API调用。请始终返回有效的JSON格式响应。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # 尝试提取JSON
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            try:
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                print(f"无法解析JSON响应: {content}")
                return {"action": "unknown", "error": "无法解析响应"}
        
        except Exception as e:
            print(f"API调用错误: {str(e)}")
            traceback.print_exc()
            return {"action": "unknown", "error": str(e)}

class VideoSearcher:
    """视频搜索器"""
    
    def __init__(self):
        """初始化视频搜索器"""
        self.client = get_llm_client()
    
    def search_videos(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """搜索视频
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数量
            
        Returns:
            视频信息列表
        """
        try:
            # 使用YouTube搜索
            videos_search = VideosSearch(query, limit=max_results)
            yt_results = videos_search.result()["result"]
            
            print("YouTube搜索原始结果：", yt_results)
            
            # 处理搜索结果
            results = []
            for result in yt_results:
                results.append({
                    "title": result["title"],
                    "url": result["link"],
                    "duration": result.get("duration", "未知"),
                    "views": result.get("viewCount", {}).get("text", "未知"),
                    "channel": result.get("channel", {}).get("name", "未知"),
                    "description": result.get("description", "")
                })
            
            return results[:max_results]
        
        except Exception as e:
            print(f"搜索视频时发生错误: {str(e)}")
            traceback.print_exc()
            return []
    
    def search_and_analyze(self, query: str, theme: str = None, max_results: int = 5) -> Dict[str, Any]:
        """搜索并分析视频
        
        Args:
            query: 搜索关键词
            theme: 视频主题
            max_results: 最大结果数量
            
        Returns:
            视频分析结果
        """
        # 搜索视频
        videos = self.search_videos(query, max_results)
        if not videos:
            return {}
        
        # 使用LLM分析搜索结果
        prompt = f"""
        请分析以下视频搜索结果，找出最相关的视频。搜索关键词：{query}
        主题：{theme if theme else '无特定主题'}
        
        搜索结果：
        {json.dumps(videos, ensure_ascii=False, indent=2)}
        
        请返回JSON格式的分析结果，字段必须为：
        {{
          "url": "最相关视频的URL",
          "reason": "选择理由",
          "suggested_theme": "建议剪辑主题",
          "suggested_points": "建议剪辑要点"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=ARK_CONFIG["model"] if API_KEYS["ARK_API_KEY"] else OPENAI_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你是视频搜索专家，负责找出最相关的视频。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # 尝试提取JSON
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            try:
                result = json.loads(json_str)
                print("LLM分析结果：", result)
                print("search_results:", result)
                return result
            except json.JSONDecodeError:
                print(f"无法解析JSON响应: {content}")
                return {}
        
        except Exception as e:
            print(f"分析搜索结果时发生错误: {str(e)}")
            traceback.print_exc()
            return {}

class PexelsVideoSearcher:
    """Pexels免费视频搜索器"""
    def __init__(self, api_key):
        self.api_key = api_key

    def search_videos(self, query, max_results=5):
        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": self.api_key}
        params = {"query": query, "per_page": max_results}
        print(f"[Pexels] 请求: {url} params={params}")
        resp = requests.get(url, headers=headers, params=params)
        print(f"[Pexels] 状态码: {resp.status_code}")
        data = resp.json()
        print(f"[Pexels] 返回: {json.dumps(data, ensure_ascii=False, indent=2)}")
        videos = []
        for v in data.get("videos", []):
            if v.get("video_files"):
                videos.append({
                    "title": v.get("user", {}).get("name", "Pexels"),
                    "url": v["video_files"][0]["link"],
                    "duration": v.get("duration"),
                    "description": v.get("url")
                })
        print(f"[Pexels] 解析后视频列表: {videos}")
        return videos

class JianyingAIMCP:
    """剪映AI主控程序"""
    
    def __init__(self):
        """初始化主控程序"""
        self.nlp_processor = NLPProcessor()
        self.video_downloader = VideoDownloader()
        self.video_searcher = VideoSearcher()
        self.pexels_searcher = PexelsVideoSearcher(PEXELS_API_KEY)
        self.current_draft_id = None
    
    def process_user_command(self, user_input: str) -> str:
        """处理用户命令并执行相应操作
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            处理结果的描述
        """
        print("[调试] 进入 process_user_command，用户输入:", user_input)
        command = self.nlp_processor.process_command(user_input)
        action = command.get("action", "unknown")
        print("[调试] 解析到 action:", action)
        
        # 执行相应操作
        if action == "create_draft":
            return self._create_draft(command)
        elif action == "add_video":
            return self._add_video(command)
        elif action == "add_audio":
            return self._add_audio(command)
        elif action == "add_text":
            return self._add_text(command)
        elif action == "get_draft_info":
            return self._get_draft_info(command)
        elif action == "save_draft":
            return self._save_draft(command)
        elif action == "list_drafts":
            return self._list_drafts()
        elif action == "delete_draft":
            return self._delete_draft(command)
        elif action == "download_and_edit":
            return self._download_and_edit(command)
        elif action == "search_and_edit":
            return self._search_and_edit(command)
        elif action == "search_only":
            return self._search_only(command)
        else:
            return f"抱歉，我无法理解您的命令。错误信息: {command.get('error', '未知错误')}"
    
    def _create_draft(self, command: Dict[str, Any]) -> str:
        """创建新草稿"""
        draft_name = command.get("draft_name", f"草稿_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        width = command.get("width", 1080)
        height = command.get("height", 1920)
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts",
                json={
                    "draft_name": draft_name,
                    "width": width,
                    "height": height
                }
            )
            
            if response.status_code == 200:
                draft_id = response.json()["draft_id"]
                self.current_draft_id = draft_id
                current_drafts[draft_id] = DraftInfo(
                    draft_id=draft_id,
                    draft_name=draft_name,
                    creation_time=datetime.now(),
                    last_modified=datetime.now(),
                    description=command.get("description", "")
                )
                return f"成功创建草稿 '{draft_name}'，ID: {draft_id}"
            else:
                return f"创建草稿失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"创建草稿时发生错误: {str(e)}"
    
    def _add_video(self, command: Dict[str, Any]) -> str:
        """添加视频"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        file_path = command.get("file_path", "")
        if not file_path:
            return "错误: 未提供视频路径或URL。"
        
        # 构建请求数据，包含必要的默认值
        request_data = {
            "file_path": file_path,
            "start": command.get("start", "0s"),
            "duration": command.get("duration", "10s"),
            "target_start": command.get("target_start", "0s"),
            "transition": "左移",  # 使用"左移"作为默认转场效果
            "effects": []  # 空列表作为默认值
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts/{draft_id}/videos",
                json=request_data
            )
            
            if response.status_code == 200:
                return f"成功添加视频 '{file_path}'"
            else:
                return f"添加视频失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"添加视频时发生错误: {str(e)}"
    
    def _add_audio(self, command: Dict[str, Any]) -> str:
        """添加音频"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        url = command.get("url", "")
        if not url:
            return "错误: 未提供音频URL。"
        
        # 构建请求数据，只包含非空属性
        request_data = {
            "url": url
        }
        
        # 只添加非空的属性
        if command.get("enabled") is not None:
            request_data["enabled"] = command["enabled"]
        if command.get("volume") is not None:
            request_data["volume"] = command["volume"]
        if command.get("start"):
            request_data["start"] = command["start"]
        if command.get("target_start"):
            request_data["target_start"] = command["target_start"]
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts/{draft_id}/audio",
                json=request_data
            )
            
            if response.status_code == 200:
                return f"成功添加音频 '{url}'"
            else:
                return f"添加音频失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"添加音频时发生错误: {str(e)}"
    
    def _add_text(self, command: Dict[str, Any]) -> str:
        """添加文本"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        text = command.get("text", "")
        if not text:
            return "错误: 未提供文本内容。"
        
        track_name = command.get("track_name", "主字幕")
        
        # 构建请求数据，包含必要的默认值
        request_data = {
            "track_name": track_name,
            "text": text,
            "start": command.get("start", "0s"),
            "duration": command.get("duration", "5s"),
            "font": command.get("font", "后现代体"),
            "style": command.get("style", {
                "color": [0, 0, 0],
                "size": 36,
                "bold": True,
                "italic": False,
                "underline": False,
                "alpha": 1.0,
                "align": 0,
                "vertical": False,
                "letter_spacing": 0,
                "line_spacing": 0
            }),
            "position": command.get("position", {
                "x": 0.5,
                "y": 0.907
            }),
            "intro_animation": command.get("intro_animation", "随机打字机"),
            "outro_animation": command.get("outro_animation", "滑动下落"),
            "linebreak": command.get("linebreak", {
                "mode": "manual",
                "zh_length": 8,
                "en_words": 3
            })
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts/{draft_id}/text",
                json=request_data
            )
            
            if response.status_code == 200:
                return f"成功添加文本 '{text[:20]}...' 到轨道 '{track_name}'"
            else:
                return f"添加文本失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"添加文本时发生错误: {str(e)}"
    
    def _get_draft_info(self, command: Dict[str, Any]) -> str:
        """获取草稿信息"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        try:
            response = requests.get(f"{BASE_URL}/drafts/{draft_id}")
            
            if response.status_code == 200:
                draft_info = response.json()
                return f"""
草稿信息:
- 名称: {draft_info['draft_name']}
- 分辨率: {draft_info['resolution']['width']}x{draft_info['resolution']['height']}
- 视频数量: {len(draft_info['videos'])}
- 音频数量: {len(draft_info['audio'])}
- 文本轨道数量: {len(draft_info['text_tracks'])}
- 总时长: {draft_info['timeline']['total_duration']}
                """
            else:
                return f"获取草稿信息失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"获取草稿信息时发生错误: {str(e)}"
    
    def _save_draft(self, command: Dict[str, Any]) -> str:
        """保存草稿"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        try:
            response = requests.post(f"{BASE_URL}/drafts/{draft_id}/save")
            
            if response.status_code == 200:
                output_path = response.json()["output_path"]
                return f"草稿已成功保存到: {output_path}"
            else:
                return f"保存草稿失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"保存草稿时发生错误: {str(e)}"
    
    def _list_drafts(self) -> str:
        """列出所有草稿"""
        try:
            response = requests.get(f"{BASE_URL}/drafts")
            
            if response.status_code == 200:
                drafts = response.json()
                if not drafts:
                    return "目前没有可用的草稿。"
                
                result = "可用的草稿:\n"
                for i, draft in enumerate(drafts, 1):
                    result += f"{i}. {draft['draft_name']} (ID: {draft['draft_id']}, 时长: {draft['total_duration']})\n"
                
                return result
            else:
                return f"获取草稿列表失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"获取草稿列表时发生错误: {str(e)}"
    
    def _delete_draft(self, command: Dict[str, Any]) -> str:
        """删除草稿"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        try:
            response = requests.delete(f"{BASE_URL}/drafts/{draft_id}")
            
            if response.status_code == 200:
                if draft_id in current_drafts:
                    del current_drafts[draft_id]
                
                if self.current_draft_id == draft_id:
                    self.current_draft_id = None
                
                return f"草稿 (ID: {draft_id}) 已成功删除。"
            else:
                return f"删除草稿失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"删除草稿时发生错误: {str(e)}"
    
    def _download_and_edit(self, command: Dict[str, Any]) -> str:
        """下载并编辑视频"""
        url = command.get("url", "")
        if not url:
            return "错误: 未提供视频URL。"
        
        # 获取主题
        theme = command.get("theme")
        
        # 下载并分析视频
        video_path, auto_clips = self.video_downloader.download_and_analyze(url, theme)
        if not video_path:
            return "错误: 视频下载失败。"
        
        try:
            # 创建新草稿
            draft_name = command.get("draft_name", f"下载视频_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            if theme:
                draft_name = f"{theme}_{draft_name}"
            
            draft_response = requests.post(
                f"{BASE_URL}/drafts",
                json={
                    "draft_name": draft_name,
                    "width": 1080,
                    "height": 1920,
                    "description": command.get("description", f"从网络下载的视频{(' - ' + theme) if theme else ''}")
                }
            )
            
            if draft_response.status_code != 200:
                return f"创建草稿失败，状态码: {draft_response.status_code}, 错误: {draft_response.text}"
            
            draft_id = draft_response.json()["draft_id"]
            self.current_draft_id = draft_id
            
            # 添加视频片段
            clips = command.get("clips", [])
            if not clips:
                # 如果没有指定片段，使用自动分析的片段
                if auto_clips:
                    # 如果指定了主题，按相关性排序
                    if theme:
                        auto_clips.sort(key=lambda x: x.get("relevance", 0), reverse=True)
                    clips = auto_clips
                else:
                    # 如果自动分析失败，添加整个视频
                    self._add_video({
                        "file_path": video_path,
                        "draft_id": draft_id
                    })
            
            # 添加指定的片段
            for clip in clips:
                self._add_video({
                    "file_path": video_path,
                    "draft_id": draft_id,
                    "start": clip.get("start", "0s"),
                    "duration": clip.get("duration", "10s"),
                    "target_start": clip.get("target_start", "0s")
                })
                
                # 如果有描述，添加文本
                if clip.get("description"):
                    self._add_text({
                        "draft_id": draft_id,
                        "text": clip["description"],
                        "start": clip.get("start", "0s"),
                        "duration": clip.get("duration", "10s")
                    })
            
            return f"成功下载并编辑视频，创建草稿: {draft_name}"
        
        except Exception as e:
            return f"下载并编辑视频时发生错误: {str(e)}"
        finally:
            # 清理临时文件
            try:
                os.remove(video_path)
            except:
                pass
    
    def _search_and_edit(self, command: Dict[str, Any]) -> str:
        """搜索并编辑视频（优先用Pexels）"""
        print("[调试] 进入 _search_and_edit，参数:", command)
        query = command.get("query", "")
        if not query:
            return "错误: 未提供搜索关键词。"
        
        theme = command.get("theme")
        
        # 优先用Pexels搜索
        videos = self.pexels_searcher.search_videos(query, max_results=5)
        if not videos:
            print("[Pexels] 未找到任何视频！")
            return "错误: Pexels 未找到相关免费视频。"
        
        print("Pexels搜索到的视频：")
        for idx, v in enumerate(videos, 1):
            print(f"{idx}. {v['title']} - {v['url']}")
        
        video_url = videos[0].get("url")
        print(f"[Pexels] 选用视频URL: {video_url}")
        if not video_url:
            print("[Pexels] 视频结果无有效URL！")
            return "错误: Pexels 视频结果无有效URL。"
        return self._download_and_edit({
            "url": video_url,
            "theme": theme,
            "draft_name": command.get("draft_name", f"{query}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            "description": command.get("description", f"Pexels搜索结果: {query}")
        })

    def _search_only(self, command: Dict[str, Any]) -> str:
        print("[调试] 进入 _search_only，参数:", command)
        query = command.get("query", "")
        if not query:
            return "错误: 未提供搜索关键词。"
        videos = self.pexels_searcher.search_videos(query, max_results=10)
        if not videos:
            return "未找到相关视频。"
        result = ""
        # 最相关推荐
        top = videos[0]
        result += f"最相关推荐：\n1. {top['title']} - {top['url']}\n"
        # 其它相关
        if len(videos) > 1:
            result += "其它相关视频：\n"
            for idx, v in enumerate(videos[1:], 2):
                result += f"{idx}. {v['title']} - {v['url']}\n"
        return result

# 简单的CLI界面
def main():
    """主函数"""
    mcp = JianyingAIMCP()
    
    print("=" * 50)
    print("欢迎使用剪映AI MCP (Master Control Program)")
    print("您可以使用自然语言来创建和编辑视频草稿")
    print("示例命令:")
    print("- 创建一个1080p的新视频草稿，叫做'我的旅行视频'")
    print("- 添加一个视频，URL是https://example.com/video.mp4")
    print("- 在5秒处添加文本'精彩时刻'，持续3秒")
    print("- 保存当前草稿")
    print("- 下载并剪辑 https://www.tiktok.com/@xxx/video/xxxxxxxxx")
    print("- 下载并剪辑 https://www.youtube.com/watch?v=xxxxxxx")
    print("- 下载并剪辑 https://v.douyin.com/xxxxxxx")
    print("- 下载并剪辑 https://www.bilibili.com/video/BVxxxxxxx")
    print("- 下载并剪辑 https://www.pexels.com/video/xxxxxxx/")
    print("- 下载并剪辑美食探店视频（自动搜索并剪辑相关视频）")
    print("- 搜索美食探店视频（只展示相关视频列表，不下载）")
    print("- 搜索城市夜景视频")
    print("- 搜索美食短片")
    print("输入'退出'或'exit'结束程序")
    print("=" * 50)
    
    while True:
        user_input = input("\n> ")
        
        if user_input.lower() in ['退出', 'exit', 'quit']:
            print("谢谢使用，再见！")
            break
        
        response = mcp.process_user_command(user_input)
        print(response)

if __name__ == "__main__":
    main()
