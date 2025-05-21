"""
剪映模板配置管理器

这个模块提供了一个面向对象的方式来管理剪映模板配置。
支持通过唯一ID串联不同的操作，可以通过HTTP请求逐步构建草稿。

主要组件：
- VideoManager: 视频轨道管理器
- AudioManager: 音频轨道管理器
- TextManager: 文本轨道管理器
- TimelineManager: 时间轴管理器
- DraftGenerator: 草稿生成器
- DraftManager: 草稿管理器（管理多个草稿）
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Union
import json
import os
from datetime import datetime
from enum import Enum
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# 创建 FastAPI 应用
app = FastAPI(title="剪映草稿管理器")

class TrackType(Enum):
    """轨道类型枚举"""
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"

@dataclass
class Resolution:
    """视频分辨率配置类"""
    width: int
    height: int

@dataclass
class VideoEffect:
    """视频特效配置类"""
    effect_id: str
    start: str
    duration: str

@dataclass
class TimelineItem:
    """时间轴项目基类"""
    track_type: TrackType
    start: str  # 格式如 "0s", "1.5s"
    duration: str
    target_start: str
    track_index: int  # 在各自轨道中的索引

@dataclass
class VideoTimelineItem(TimelineItem):
    """视频时间轴项目"""
    transition: str
    effects: List[Dict[str, Any]]

@dataclass
class AudioTimelineItem(TimelineItem):
    """音频时间轴项目"""
    volume: float
    enabled: bool

@dataclass
class TextTimelineItem(TimelineItem):
    """文本时间轴项目"""
    track_name: str
    text_index: int

class VideoManager:
    """视频轨道管理器"""
    
    def __init__(self):
        self.videos: List[Dict[str, Any]] = []
    
    def add_video(self, video_data: Dict[str, Any]) -> None:
        self.videos.append(video_data)
    
    def update_video(self, index: int, video_data: Dict[str, Any]) -> None:
        if 0 <= index < len(self.videos):
            self.videos[index] = video_data
        else:
            raise IndexError("Video index out of range")
    
    def remove_video(self, index: int) -> None:
        if 0 <= index < len(self.videos):
            self.videos.pop(index)
        else:
            raise IndexError("Video index out of range")
    
    def get_videos(self) -> List[Dict[str, Any]]:
        return self.videos

class AudioManager:
    """音频轨道管理器"""
    
    def __init__(self):
        self.audio_tracks: List[Dict[str, Any]] = []
    
    def add_audio(self, audio_data: Dict[str, Any]) -> None:
        self.audio_tracks.append(audio_data)
    
    def update_audio(self, index: int, audio_data: Dict[str, Any]) -> None:
        if 0 <= index < len(self.audio_tracks):
            self.audio_tracks[index] = audio_data
        else:
            raise IndexError("Audio index out of range")
    
    def remove_audio(self, index: int) -> None:
        if 0 <= index < len(self.audio_tracks):
            self.audio_tracks.pop(index)
        else:
            raise IndexError("Audio index out of range")
    
    def get_audio_tracks(self) -> List[Dict[str, Any]]:
        return self.audio_tracks

class TextManager:
    """文本轨道管理器"""
    
    def __init__(self):
        self.text_tracks: List[Dict[str, Any]] = []
    
    def add_text_track(self, track_name: str, relative_index: int) -> None:
        self.text_tracks.append({
            "name": track_name,
            "relative_index": relative_index,
            "texts": []
        })
    
    def add_text(self, track_name: str, text_data: Dict[str, Any]) -> None:
        for track in self.text_tracks:
            if track["name"] == track_name:
                track["texts"].append(text_data)
                return
        raise ValueError(f"Text track '{track_name}' not found")
    
    def update_text(self, track_name: str, text_index: int, text_data: Dict[str, Any]) -> None:
        for track in self.text_tracks:
            if track["name"] == track_name:
                if 0 <= text_index < len(track["texts"]):
                    track["texts"][text_index] = text_data
                    return
                else:
                    raise IndexError("Text index out of range")
        raise ValueError(f"Text track '{track_name}' not found")
    
    def remove_text(self, track_name: str, text_index: int) -> None:
        for track in self.text_tracks:
            if track["name"] == track_name:
                if 0 <= text_index < len(track["texts"]):
                    track["texts"].pop(text_index)
                    return
                else:
                    raise IndexError("Text index out of range")
        raise ValueError(f"Text track '{track_name}' not found")
    
    def get_text_tracks(self) -> List[Dict[str, Any]]:
        return self.text_tracks

class TimelineManager:
    """时间轴管理器"""
    
    def __init__(self):
        self.timeline_items: List[TimelineItem] = []
        self.total_duration: str = "0s"
    
    def _parse_time(self, time_str: str) -> float:
        return float(time_str.rstrip('s'))
    
    def _format_time(self, seconds: float) -> str:
        return f"{seconds}s"
    
    def add_item(self, item: TimelineItem) -> None:
        self.timeline_items.append(item)
        self._update_total_duration()
    
    def remove_item(self, track_type: TrackType, track_index: int) -> None:
        self.timeline_items = [
            item for item in self.timeline_items
            if not (item.track_type == track_type and item.track_index == track_index)
        ]
        self._update_total_duration()
    
    def update_item(self, track_type: TrackType, track_index: int, 
                   new_start: str, new_duration: str, new_target_start: str) -> None:
        for item in self.timeline_items:
            if item.track_type == track_type and item.track_index == track_index:
                item.start = new_start
                item.duration = new_duration
                item.target_start = new_target_start
                break
        self._update_total_duration()
    
    def _update_total_duration(self) -> None:
        if not self.timeline_items:
            self.total_duration = "0s"
            return
        
        max_end = max(
            self._parse_time(item.target_start) + self._parse_time(item.duration)
            for item in self.timeline_items
        )
        self.total_duration = self._format_time(max_end)
    
    def get_items_by_time(self, time: str) -> List[TimelineItem]:
        time_seconds = self._parse_time(time)
        return [
            item for item in self.timeline_items
            if (self._parse_time(item.target_start) <= time_seconds < 
                self._parse_time(item.target_start) + self._parse_time(item.duration))
        ]
    
    def get_items_by_track(self, track_type: TrackType) -> List[TimelineItem]:
        return [item for item in self.timeline_items if item.track_type == track_type]
    
    def get_timeline_data(self) -> Dict[str, Any]:
        return {
            'total_duration': self.total_duration,
            'items': [
                {
                    'track_type': item.track_type.value,
                    'start': item.start,
                    'duration': item.duration,
                    'target_start': item.target_start,
                    'track_index': item.track_index,
                    **(
                        {'transition': item.transition, 'effects': item.effects}
                        if isinstance(item, VideoTimelineItem)
                        else {}
                    ),
                    **(
                        {'volume': item.volume, 'enabled': item.enabled}
                        if isinstance(item, AudioTimelineItem)
                        else {}
                    ),
                    **(
                        {'track_name': item.track_name, 'text_index': item.text_index}
                        if isinstance(item, TextTimelineItem)
                        else {}
                    )
                }
                for item in self.timeline_items
            ]
        }

class DraftGenerator:
    """草稿生成器"""
    
    def __init__(self, draft_name: str, drafts_root: str, template_folder: str, resolution: Resolution):
        self.draft_name = draft_name
        self.drafts_root = drafts_root
        self.template_folder = template_folder
        self.resolution = resolution
        self.jianying_version = "3.1.0-beta7"
        self.video_manager = VideoManager()
        self.audio_manager = AudioManager()
        self.text_manager = TextManager()
        self.timeline_manager = TimelineManager()
    
    def add_video(self, video_data: Dict[str, Any]) -> None:
        self.video_manager.add_video(video_data)
        timeline_item = VideoTimelineItem(
            track_type=TrackType.VIDEO,
            start=video_data['start'],
            duration=video_data['duration'],
            target_start=video_data['target_start'],
            track_index=len(self.video_manager.videos) - 1,
            transition=video_data['transition'],
            effects=video_data['effects']
        )
        self.timeline_manager.add_item(timeline_item)
    
    def add_audio(self, audio_data: Dict[str, Any]) -> None:
        self.audio_manager.add_audio(audio_data)
        timeline_item = AudioTimelineItem(
            track_type=TrackType.AUDIO,
            start=audio_data['start'],
            duration=audio_data.get('duration', '0s'),
            target_start=audio_data['target_start'],
            track_index=len(self.audio_manager.audio_tracks) - 1,
            volume=audio_data['volume'],
            enabled=audio_data['enabled']
        )
        self.timeline_manager.add_item(timeline_item)
    
    def add_text(self, track_name: str, text_data: Dict[str, Any]) -> None:
        # 如果轨道不存在，自动创建
        track_exists = False
        for track in self.text_manager.text_tracks:
            if track["name"] == track_name:
                track_exists = True
                break
        
        if not track_exists:
            self.text_manager.add_text_track(track_name, len(self.text_manager.text_tracks) + 1)
        
        self.text_manager.add_text(track_name, text_data)
        
        # 找到轨道和文本索引
        track_index = 0
        text_index = 0
        for i, track in enumerate(self.text_manager.text_tracks):
            if track["name"] == track_name:
                track_index = i
                text_index = len(track["texts"]) - 1
                break
        
        timeline_item = TextTimelineItem(
            track_type=TrackType.TEXT,
            start=text_data['start'],
            duration=text_data['duration'],
            target_start=text_data.get('target_start', text_data['start']),
            track_index=track_index,
            track_name=track_name,
            text_index=text_index
        )
        self.timeline_manager.add_item(timeline_item)
    
    def generate_draft(self) -> Dict[str, Any]:
        return {
            'draft_name': self.draft_name,
            'drafts_root': self.drafts_root,
            'template_folder': self.template_folder,
            'resolution': {
                'width': self.resolution.width,
                'height': self.resolution.height
            },
            'jianying_version': self.jianying_version,
            'videos': self.video_manager.get_videos(),
            'audio': self.audio_manager.get_audio_tracks(),
            'text_tracks': self.text_manager.get_text_tracks(),
            'timeline': self.timeline_manager.get_timeline_data()
        }
    
    def save_draft(self, output_path: str) -> None:
        config = self.generate_draft()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

class DraftManager:
    """草稿管理器"""
    
    def __init__(self, drafts_root: str, template_folder: str):
        self.drafts_root = drafts_root
        self.template_folder = template_folder
        self.drafts: Dict[str, DraftGenerator] = {}
    
    def create_draft(self, draft_name: str, resolution: Resolution) -> str:
        draft_id = str(uuid.uuid4())
        self.drafts[draft_id] = DraftGenerator(
            draft_name=draft_name,
            drafts_root=self.drafts_root,
            template_folder=self.template_folder,
            resolution=resolution
        )
        return draft_id
    
    def get_draft(self, draft_id: str) -> DraftGenerator:
        if draft_id not in self.drafts:
            raise KeyError(f"Draft {draft_id} not found")
        return self.drafts[draft_id]
    
    def delete_draft(self, draft_id: str) -> None:
        if draft_id not in self.drafts:
            raise KeyError(f"Draft {draft_id} not found")
        del self.drafts[draft_id]
    
    def list_drafts(self) -> List[Dict[str, Any]]:
        return [
            {
                'draft_id': draft_id,
                'draft_name': draft.draft_name,
                'total_duration': draft.timeline_manager.total_duration
            }
            for draft_id, draft in self.drafts.items()
        ]

# FastAPI 模型定义
class CreateDraftRequest(BaseModel):
    draft_name: str
    width: int
    height: int

class AddVideoRequest(BaseModel):
    file_path: str
    start: str
    duration: str
    target_start: str
    transition: str
    effects: List[Dict[str, Any]]

class AddAudioRequest(BaseModel):
    url: str
    enabled: bool
    volume: float
    start: str
    target_start: str

class AddTextRequest(BaseModel):
    track_name: str
    text: str
    start: str
    duration: str
    font: str
    style: Dict[str, Any]
    position: Dict[str, float]
    intro_animation: str
    outro_animation: str
    linebreak: Dict[str, Any]

# 全局草稿管理器实例
draft_manager = None

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化草稿管理器"""
    global draft_manager
    draft_manager = DraftManager(
        drafts_root="/Users/danielwang/Documents/jianyan/JianyingPro Drafts",
        template_folder="/Users/danielwang/Documents/jianyan/JianyingPro Drafts/Draft Template Old"
    )

@app.post("/drafts")
async def create_draft(request: CreateDraftRequest):
    """创建新草稿"""
    try:
        draft_id = draft_manager.create_draft(
            draft_name=request.draft_name,
            resolution=Resolution(width=request.width, height=request.height)
        )
        return {"draft_id": draft_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/drafts")
async def list_drafts():
    """列出所有草稿"""
    return draft_manager.list_drafts()

@app.get("/drafts/{draft_id}")
async def get_draft(draft_id: str):
    """获取草稿信息"""
    try:
        draft = draft_manager.get_draft(draft_id)
        return draft.generate_draft()
    except KeyError:
        raise HTTPException(status_code=404, detail="Draft not found")

@app.post("/drafts/{draft_id}/videos")
async def add_video(draft_id: str, request: AddVideoRequest):
    """添加视频轨道"""
    try:
        draft = draft_manager.get_draft(draft_id)
        draft.add_video(request.dict())
        return {"status": "success"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Draft not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/drafts/{draft_id}/audio")
async def add_audio(draft_id: str, request: AddAudioRequest):
    """添加音频轨道"""
    try:
        draft = draft_manager.get_draft(draft_id)
        draft.add_audio(request.dict())
        return {"status": "success"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Draft not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/drafts/{draft_id}/text")
async def add_text(draft_id: str, request: AddTextRequest):
    """添加文本轨道"""
    try:
        draft = draft_manager.get_draft(draft_id)
        draft.add_text(request.track_name, request.dict())
        return {"status": "success"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Draft not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/drafts/{draft_id}")
async def delete_draft(draft_id: str):
    """删除草稿"""
    try:
        draft_manager.delete_draft(draft_id)
        return {"status": "success"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Draft not found")

@app.post("/drafts/{draft_id}/save")
async def save_draft(draft_id: str):
    """保存草稿"""
    try:
        draft = draft_manager.get_draft(draft_id)
        output_path = os.path.join(
            draft.drafts_root,
            f"{draft.draft_name}.json"
        )
        draft.save_draft(output_path)
        return {"status": "success", "output_path": output_path}
    except KeyError:
        raise HTTPException(status_code=404, detail="Draft not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 