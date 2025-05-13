#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用pyJianYingDraft创建剪映项目
包含远程视频、远程语音和指定字幕
"""

import os
import tempfile
import urllib.request
from pathlib import Path

from pyJianYingDraft.script_file import Script_file
from pyJianYingDraft.local_materials import Video_material, Audio_material
from pyJianYingDraft.video_segment import Video_segment
from pyJianYingDraft.audio_segment import Audio_segment
from pyJianYingDraft.text_segment import Text_segment, Text_style
from pyJianYingDraft.track import Track_type
from pyJianYingDraft.time_util import trange, SEC
from pyJianYingDraft.jianying_controller import Jianying_controller, Export_resolution, Export_framerate


def download_file(url, local_filename=None):
    """从URL下载文件到本地临时目录"""
    if local_filename is None:
        # 创建临时文件
        suffix = os.path.splitext(url.split('?')[0])[1]  # 获取扩展名
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            local_filename = tmp.name
    
    print(f"正在下载 {url} 到 {local_filename}")
    try:
        with urllib.request.urlopen(url) as response:
            with open(local_filename, 'wb') as out_file:
                out_file.write(response.read())
        return local_filename
    except Exception as e:
        print(f"下载文件失败: {e}")
        if os.path.exists(local_filename):
            os.remove(local_filename)
        return None


def create_project():
    """创建剪映项目"""
    # 远程资源URL
    video_url = "https://video-snot-12220.oss-cn-shanghai.aliyuncs.com/2025-05-09/video/2222a427-37a2-4974-ae13-cdcafc1c543a.mp4"
    audio_url = "https://lf26-appstore-sign.oceancloudapi.com/ocean-cloud-tos/VolcanoUserVoice/speech_7426725529589661723_91619aff-42aa-42f9-88cd-becd704fe614.mp3?lk3s=da27ec82&x-expires=1746975312&x-signature=tqDS%2F%2FPN8QT229fhIQ%2FMIz4kG5w%3D"
    
    # 字幕文本
    subtitle_text = "你有没有过这种情况？和人聊天时，对方笑着说'没事'，但眉毛却皱成小括号？"
    
    # 下载远程文件
    video_file = download_file(video_url)
    audio_file = download_file(audio_url)
    
    if not video_file or not audio_file:
        print("下载文件失败，无法继续")
        return
    
    try:
        # 创建剪映草稿文件 (1080p)
        script = Script_file(width=1920, height=1080, fps=30)
        
        # 创建各种轨道
        script.add_track(Track_type.video, "主视频轨道")
        script.add_track(Track_type.audio, "音频轨道")
        script.add_track(Track_type.text, "字幕轨道")
        
        # 添加视频素材
        video_material = Video_material(video_file)
        script.add_material(video_material)
        
        # 添加音频素材
        audio_material = Audio_material(audio_file)
        script.add_material(audio_material)
        
        # 获取音频的实际持续时间
        print(f"音频文件持续时间: {audio_material.duration / SEC:.2f}秒")
        print(f"视频文件持续时间: {video_material.duration / SEC:.2f}秒")
        
        # 使用音频的实际持续时间，或者如果视频较短则使用视频的持续时间
        audio_duration = min(audio_material.duration, video_material.duration)
        print(f"使用持续时间: {audio_duration / SEC:.2f}秒")
        
        # 创建视频片段（与音频等长）
        video_segment = Video_segment(
            video_material,
            trange("0s", str(audio_duration / SEC) + "s")
        )
        script.add_segment(video_segment, "主视频轨道")
        
        # 创建音频片段
        audio_segment = Audio_segment(
            audio_material,
            trange("0s", str(audio_duration / SEC) + "s")
        )
        script.add_segment(audio_segment, "音频轨道")
        
        # 创建字幕片段
        text_segment = Text_segment(
            subtitle_text,
            trange("0s", str(audio_duration / SEC) + "s"),
            style=Text_style(size=10, align=1, color=(1, 1, 1), alpha=1.0)  # 居中对齐，白色字体
        )
        script.add_segment(text_segment, "字幕轨道")
        
        # 保存项目
        project_name = "语音视频字幕项目"
        draft_folder = os.path.expanduser("~/Documents/jianyan/JianyingPro Drafts")
        output_path = os.path.join(draft_folder, f"{project_name}.json")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        script.dump(output_path)
        
        print(f"\n项目已保存到 {output_path}")
        print("请在剪映中打开此项目并进行进一步编辑/导出")
        
        # 提示用户如何导出
        print("\n要导出项目，可以使用以下代码：")
        print("controller = Jianying_controller()")
        print(f"controller.export_draft(\"{project_name}\", resolution=Export_resolution.RES_1080P)")
    
    finally:
        # 清理临时文件
        if video_file and os.path.exists(video_file):
            os.remove(video_file)
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)


if __name__ == "__main__":
    create_project() 