# jianying_utils.py
# 工具函数：批量生成剪映草稿
# 从 demo.py 抽取
import os
import shutil
import json
import datetime
import uuid
import requests
from urllib.parse import urlparse
import pyJianYingDraft as draft
from pyJianYingDraft import Intro_type, Transition_type, trange, tim
from pyJianYingDraft.metadata.video_effect_meta import Video_scene_effect_type
from pyJianYingDraft.metadata.filter_meta import Filter_type
from pyJianYingDraft.metadata import Text_intro, Text_outro, Text_loop_anim

# 动画查找表自动导入
try:
    from animation_table import animation_table
except ImportError:
    animation_table = {}

def download_file_if_needed(file_path, save_dir):
    if file_path.startswith('http://') or file_path.startswith('https://'):
        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.basename(urlparse(file_path).path)
        local_path = os.path.join(save_dir, filename)
        if not os.path.exists(local_path):
            resp = requests.get(file_path, stream=True)
            resp.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"已下载: {local_path}")
        else:
            print(f"已存在: {local_path}")
        return local_path
    return file_path

def create_draft_from_params(params, new_draft_folder):
    # Create script with 1920x1080 resolution and old version compatible settings
    script = draft.Script_file(1920, 1080)
    # For old version template, ensure the script has old version compatible settings
    if "Template Old" in new_draft_folder:
        script.version = 360000
        script.new_version = "3.1.0"
        script.platform = {
            "app_id": 3704,
            "app_version": "3.1.0-beta7",
            "os": "mac",
            "os_version": "15.4.1"
        }
        script.last_modified_platform = script.platform.copy()
        script.canvas_config = {
            "height": 1080,
            "ratio": "original",
            "width": 1920
        }
        script.color_space = 0
        script.config = {
            "adjust_max_index": 1,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "material_save_mode": 0,
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "video_mute": False
        }
        script.fps = 30.0
        script.materials = {
            "audio_balances": [],
            "audio_effects": [],
            "audio_fades": [],
            "audios": [],
            "beats": [],
            "canvases": [
                {
                    "album_image": "",
                    "blur": 0.0,
                    "color": "",
                    "id": str(uuid.uuid4()).upper().replace("-", "-"),
                    "image": "",
                    "image_id": "",
                    "image_name": "",
                    "type": "canvas_color"
                }
            ],
            "chromas": [],
            "effects": [],
            "filters": [],
            "hsl": [],
            "images": [],
            "masks": [],
            "material_animations": [],
            "placeholders": [],
            "realtime_denoises": [],
            "speeds": [],
            "stickers": [],
            "tail_leaders": [],
            "text_templates": [],
            "texts": [],
            "transitions": [],
            "video_effects": [],
            "video_trackings": [],
            "videos": []
        }
        script.keyframes = {
            "adjusts": [],
            "audios": [],
            "filters": [],
            "stickers": [],
            "texts": [],
            "videos": []
        }
    # Add tracks only if corresponding segments exist
    if params.get("audios"):
        print("[DEBUG] 创建音频轨道")
        script.add_track(draft.Track_type.audio)
    if params.get("videos") or params.get("gifs"):
        print("[DEBUG] 创建视频轨道")
        script.add_track(draft.Track_type.video)
    
    # 添加字幕轨道
    print(f"\n[DEBUG] ===== 检查字幕轨道创建条件 =====")
    print(f"[DEBUG] texts 存在: {bool(params.get('texts'))}")
    print(f"[DEBUG] translated_texts 存在: {bool(params.get('translated_texts'))}")
    print(f"[DEBUG] translated_texts 内容: {params.get('translated_texts')}")
    
    if params.get("texts"):
        print("[DEBUG] 创建主字幕轨道")
        # 添加主字幕轨道
        script.add_track(draft.Track_type.text, track_name="主字幕", relative_index=1)
    
    if params.get("translated_texts"):
        print("[DEBUG] 创建翻译字幕轨道")
        # 添加翻译字幕轨道，位于主字幕轨道上方
        script.add_track(draft.Track_type.text, track_name="翻译字幕", relative_index=2)
    
    print(f"[DEBUG] ===== 字幕轨道创建完成 =====\n")
    
    if params.get("filters"):
        print("[DEBUG] 创建滤镜轨道")
        script.add_track(draft.Track_type.filter)
    video_segments = []
    video_effects_data = []
    for audio in params.get("audios", []):
        audio_path = download_file_if_needed(audio["file_path"], new_draft_folder)
        audio_material = draft.Audio_material(audio_path)
        audio_segment = draft.Audio_segment(
            audio_material,
            trange(audio.get("start", "0s"), audio.get("duration", "5s")),
            volume=audio.get("volume", 1.0)
        )
        if "fade_in" in audio:
            audio_segment.add_fade(tim(audio["fade_in"]), tim("0s"))
        elif "fade_out" in audio:
            audio_segment.add_fade(tim("0s"), tim(audio["fade_out"]))
        script.add_segment(audio_segment)
    for video in params.get("videos", []):
        video_path = download_file_if_needed(video["file_path"], new_draft_folder)
        video_material = draft.Video_material(video_path)
        if "target_start" in video:
            source_timerange = trange(video.get("start", "0s"), video.get("duration", "5s"))
            target_timerange = draft.Timerange(
                tim(video.get("target_start", "0s")),
                tim(video.get("duration", "5s"))
            )
            video_segment = draft.Video_segment(
                video_material,
                target_timerange,
                source_timerange=source_timerange
            )
        else:
            video_segment = draft.Video_segment(
                video_material,
                trange(video.get("start", "0s"), video.get("duration", "5s"))
            )
        if "transition" in video:
            video_segment.add_transition(getattr(Transition_type, video["transition"]))
        if "animation" in video and "Template Old" in new_draft_folder:
            animation_type = getattr(Intro_type, video["animation"])
            animation_id = str(uuid.uuid4()).replace("-", "")
            animation_material = {
                "id": animation_id,
                "type": "sticker_animation",
                "multi_language_current": "none",
                "animations": [
                    {
                        "anim_adjust_params": None,
                        "platform": "all",
                        "panel": "video",
                        "material_type": "video",
                        "name": video["animation"],
                        "id": str(animation_type.value.resource_id),
                        "type": "in",
                        "resource_id": str(animation_type.value.resource_id),
                        "start": 0,
                        "duration": animation_type.value.duration
                    }
                ]
            }
            if "material_animations" not in script.materials:
                script.materials.material_animations = []
            script.materials.material_animations.append(animation_material)
            video_segment.extra_material_refs.append(animation_id)
            if hasattr(video_segment, "animation"):
                video_segment.animation = animation_id
            elif hasattr(video_segment, "animations"):
                video_segment.animations = animation_id
            else:
                try:
                    if hasattr(video_segment, "_data") and isinstance(video_segment._data, dict):
                        video_segment._data["animation"] = animation_id
                except:
                    pass
        elif "animation" in video:
            video_segment.add_animation(getattr(Intro_type, video["animation"]))
        if params.get("effects"):
            for effect in params.get("effects", []):
                effect_id = str(uuid.uuid4()).upper().replace("-", "-")
                effect_start = tim(effect.get("start", "0s"))
                effect_duration = tim(effect.get("duration", "5s"))
                effect_name = effect.get("effect_id", "负片频闪")
                effect_resource_id = ""
                effect_video_id = ""
                effect_mapping = {
                    "负片频闪": {
                        "resource_id": "7153575555554611720", 
                        "effect_id": "5155369", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/5155369/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "黑白": {
                        "resource_id": "6963300537578685966", 
                        "effect_id": "1234567", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1234567/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "胶片闪切": {
                        "resource_id": "7384745950608101924", 
                        "effect_id": "7891011", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/7891011/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "故障": {
                        "resource_id": "7293825162840457746", 
                        "effect_id": "1213141", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1213141/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "灵魂出窍": {
                        "resource_id": "7184370308057097246", 
                        "effect_id": "5161718", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/5161718/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "万圣4": {
                        "resource_id": "6748285953393037837", 
                        "effect_id": "369473", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/369473/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "星火炸开": {
                        "resource_id": "7055069349118148877", 
                        "effect_id": "1238910", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1238910/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "金粉闪闪": {
                        "resource_id": "7034048554318434830", 
                        "effect_id": "1453820", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1453820/a552dfa820b5aba27e4f09e3d83b8643"
                    }
                }
                if effect_name in effect_mapping:
                    effect_resource_id = effect_mapping[effect_name]["resource_id"]
                    effect_video_id = effect_mapping[effect_name]["effect_id"]
                else:
                    print(f"警告: 未知的特效 '{effect_name}'，使用'负片频闪'作为替代")
                    effect_resource_id = "7153575555554611720" 
                    effect_video_id = "5155369"
                    effect_name = "负片频闪"
                effect_data = {
                    "id": effect_id,
                    "adjust_params": [
                        {"default_value": 0.0, "name": "effects_adjust_color", "value": 0.0},
                        {"default_value": 0.45, "name": "effects_adjust_speed", "value": 0.45},
                        {"default_value": 0.85, "name": "effects_adjust_filter", "value": 0.85}
                    ],
                    "apply_target_type": 0,
                    "apply_time_range": None,
                    "category_id": "39654",
                    "category_name": "热门",
                    "effect_id": effect_video_id,
                    "formula_id": "",
                    "name": effect_name,
                    "platform": "all",
                    "render_index": 0,
                    "resource_id": effect_resource_id,
                    "source_platform": 0,
                    "time_range": None,
                    "track_render_index": 0,
                    "type": "video_effect",
                    "value": 1.0,
                    "version": "",
                    "path": effect_mapping[effect_name]["path"] if effect_name in effect_mapping else f"/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/5155369/a552dfa820b5aba27e4f09e3d83b8643"
                }
                video_effects_data.append(effect_data)
                video_segment.extra_material_refs.append(effect_id)
        if "effects" in video:
            for effect in video.get("effects", []):
                effect_id = str(uuid.uuid4()).upper().replace("-", "-")
                effect_start = tim(effect.get("start", "0s"))
                effect_duration = tim(effect.get("duration", "5s"))
                effect_name = effect.get("effect_id", "负片频闪")
                effect_resource_id = ""
                effect_video_id = ""
                effect_mapping = {
                    "负片频闪": {
                        "resource_id": "7153575555554611720", 
                        "effect_id": "5155369", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/5155369/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "黑白": {
                        "resource_id": "6963300537578685966", 
                        "effect_id": "1234567", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1234567/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "胶片闪切": {
                        "resource_id": "7384745950608101924", 
                        "effect_id": "7891011", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/7891011/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "故障": {
                        "resource_id": "7293825162840457746", 
                        "effect_id": "1213141", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1213141/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "灵魂出窍": {
                        "resource_id": "7184370308057097246", 
                        "effect_id": "5161718", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/5161718/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "万圣4": {
                        "resource_id": "6748285953393037837", 
                        "effect_id": "369473", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/369473/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "星火炸开": {
                        "resource_id": "7055069349118148877", 
                        "effect_id": "1238910", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1238910/a552dfa820b5aba27e4f09e3d83b8643"
                    },
                    "金粉闪闪": {
                        "resource_id": "7034048554318434830", 
                        "effect_id": "1453820", 
                        "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1453820/a552dfa820b5aba27e4f09e3d83b8643"
                    }
                }
                if effect_name in effect_mapping:
                    effect_resource_id = effect_mapping[effect_name]["resource_id"]
                    effect_video_id = effect_mapping[effect_name]["effect_id"]
                else:
                    print(f"警告: 未知的特效 '{effect_name}'，使用'负片频闪'作为替代")
                    effect_resource_id = "7153575555554611720" 
                    effect_video_id = "5155369"
                    effect_name = "负片频闪"
                effect_data = {
                    "id": effect_id,
                    "adjust_params": [
                        {"default_value": 0.0, "name": "effects_adjust_color", "value": 0.0},
                        {"default_value": 0.45, "name": "effects_adjust_speed", "value": 0.45},
                        {"default_value": 0.85, "name": "effects_adjust_filter", "value": 0.85}
                    ],
                    "apply_target_type": 0,
                    "apply_time_range": None,
                    "category_id": "39654",
                    "category_name": "热门",
                    "effect_id": effect_video_id,
                    "formula_id": "",
                    "name": effect_name,
                    "platform": "all",
                    "render_index": 0,
                    "resource_id": effect_resource_id,
                    "source_platform": 0,
                    "time_range": None,
                    "track_render_index": 0,
                    "type": "video_effect",
                    "value": 1.0,
                    "version": "",
                    "path": effect_mapping[effect_name]["path"] if effect_name in effect_mapping else f"/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/5155369/a552dfa820b5aba27e4f09e3d83b8643"
                }
                video_effects_data.append(effect_data)
                video_segment.extra_material_refs.append(effect_id)
        video_segments.append(video_segment)
        script.add_segment(video_segment)
    for gif in params.get("gifs", []):
        gif_path = download_file_if_needed(gif["file_path"], new_draft_folder)
        gif_material = draft.Video_material(gif_path)
        gif_segment = draft.Video_segment(
            gif_material,
            trange(gif.get("start", "0s"), gif.get("duration", "5s"))
        )
        if "transition" in gif:
            gif_segment.add_transition(getattr(Transition_type, gif["transition"]))
        video_segments.append(gif_segment)
        script.add_segment(gif_segment)
    for text in params.get("texts", []):
        print(f"[DEBUG] 处理主字幕: {text['text']}")
        print(f"[DEBUG] intro_animation: {text.get('intro_animation')}, outro_animation: {text.get('outro_animation')}")
        
        # 创建文本片段
        text_segment = create_text_segment(text, script, new_draft_folder)
        
        # 显式设置到主字幕轨道
        if hasattr(text_segment, "track_name"):
            text_segment.track_name = "主字幕"
        elif hasattr(text_segment, "_data") and isinstance(text_segment._data, dict):
            text_segment._data["track_name"] = "主字幕"
        
        # 添加到脚本
        script.add_segment(text_segment, track_name="主字幕")
        
        print(f"[DEBUG] 主字幕已添加到轨道")

    # 处理翻译字幕
    print(f"\n[DEBUG] ===== 开始检查翻译字幕 =====")
    print(f"[DEBUG] translated_texts 类型: {type(params.get('translated_texts'))}")
    print(f"[DEBUG] translated_texts 值: {params.get('translated_texts')}")
    
    if params.get("translated_texts"):
        print(f"\n[DEBUG] ===== 开始处理翻译字幕 =====")
        print(f"[DEBUG] 发现 {len(params['translated_texts'])} 个翻译字幕")
        
        for text in params.get("translated_texts", []):
            print(f"\n[DEBUG] ----- 处理新的翻译字幕 -----")
            print(f"[DEBUG] 处理翻译字幕: {text['text']}")
            print(f"[DEBUG] 字幕时间: start={text.get('start')}, duration={text.get('duration')}")
            print(f"[DEBUG] intro_animation: {text.get('intro_animation')}, outro_animation: {text.get('outro_animation')}")
            
            # 确保翻译字幕有正确的位置设置
            if "position" not in text:
                text["position"] = {"x": 0.5, "y": 0.807}
                print(f"[DEBUG] 使用默认位置设置: x={text['position']['x']}, y={text['position']['y']}")
            else:
                print(f"[DEBUG] 使用配置的位置设置: x={text['position']['x']}, y={text['position']['y']}")
            
            # 标记为翻译字幕
            text["is_translation"] = True
            print(f"[DEBUG] 已标记为翻译字幕")
            
            # 确保翻译字幕有正确的样式设置
            if "style" not in text:
                text["style"] = {
                    "color": [0.5, 0.8, 1.0],  # 淡蓝色
                    "size": 28  # 稍小的字号
                }
                print(f"[DEBUG] 使用默认样式设置: color={text['style']['color']}, size={text['style']['size']}")
            else:
                # 如果已有样式，确保颜色和大小符合翻译字幕规范
                text["style"] = text["style"].copy()  # 创建副本避免修改原始数据
                text["style"]["color"] = text["style"].get("color", [0.5, 0.8, 1.0])
                text["style"]["size"] = text["style"].get("size", 28)
                print(f"[DEBUG] 使用配置的样式设置: color={text['style']['color']}, size={text['style']['size']}")
            
            try:
                # 创建文本片段
                print(f"[DEBUG] 开始创建翻译字幕文本片段...")
                text_segment = create_text_segment(text, script, new_draft_folder)
                print(f"[DEBUG] 文本片段创建成功")
                
                # 显式设置到翻译字幕轨道
                if hasattr(text_segment, "track_name"):
                    text_segment.track_name = "翻译字幕"
                elif hasattr(text_segment, "_data") and isinstance(text_segment._data, dict):
                    text_segment._data["track_name"] = "翻译字幕"
                print(f"[DEBUG] 已设置轨道名称为: 翻译字幕")
                
                # 添加到脚本
                script.add_segment(text_segment, track_name="翻译字幕")
                print(f"[DEBUG] 翻译字幕已成功添加到轨道")
                
                # 设置字体和大小
                if hasattr(script.materials, "texts") and script.materials.texts:
                    t = script.materials.texts[-1]
                    if isinstance(t, dict):
                        t["font_size"] = text["style"]["size"]
                        t["font_name"] = text.get("font", "系统")
                        print(f"[DEBUG] 已设置字体属性: size={t['font_size']}, font={t['font_name']}")
                
                print(f"[DEBUG] ----- 翻译字幕处理完成 -----\n")
                
            except Exception as e:
                print(f"[ERROR] 处理翻译字幕时发生错误: {str(e)}")
                import traceback
                print(f"[ERROR] 错误详情:\n{traceback.format_exc()}")
                raise
        
        print(f"[DEBUG] ===== 翻译字幕处理完成 =====\n")
    else:
        print(f"[DEBUG] 未找到翻译字幕配置\n")

    filter_ids = {}
    if params.get("filters"):
        for filter_ in params.get("filters", []):
            filter_type = getattr(Filter_type, filter_["filter_id"])
            filter_segment = draft.Filter_segment(
                filter_type,
                trange(filter_.get("start", "0s"), filter_.get("duration", "5s")),
                intensity=filter_.get("intensity", 100)
            )
            filter_id = filter_segment.material_id
            filter_ids[filter_["filter_id"]] = filter_id
            script.add_segment(filter_segment)
    script._video_effects_data = video_effects_data
    return script

def create_text_segment(text, script, new_draft_folder):
    """创建文本片段
    
    Args:
        text: 文本配置
        script: 草稿脚本对象
        new_draft_folder: 新草稿文件夹路径
        
    Returns:
        创建的文本片段对象
    """
    # 计算位置（方案A：左上角为(0,0)，支持像素和归一化输入，自动转为中心为(0,0)）
    canvas_w, canvas_h = 1920, 1080
    x = text.get("position", {}).get("x", 0)
    y = text.get("position", {}).get("y", 0)
    
    # 支持归一化输入
    if isinstance(x, float) and abs(x) <= 1.0:
        x = int(x * canvas_w)
    if isinstance(y, float) and abs(y) <= 1.0:
        y = int(y * canvas_h)
    
    # 如果是翻译字幕，应用特殊样式和位置偏移
    is_translation = text.get("is_translation", False)
    if is_translation:
        # 翻译字幕默认样式：较小字号，浅蓝色
        font_size = text.get("style", {}).get("size", 28)  # 默认28号字体
        color = text.get("style", {}).get("color", (0.5, 0.8, 1.0))  # 浅蓝色
        # 向上偏移60像素（可以根据需要调整）
        y = y - 60
    else:
        # 原文字幕默认样式
        font_size = text.get("style", {}).get("size", 36)  # 默认36号字体
        color = text.get("style", {}).get("color", (1.0, 1.0, 1.0))  # 白色
    
    # 转换为以中心为原点，分母为画布宽/高，±0.5为边界
    transform_x = (x - canvas_w // 2) / canvas_w
    transform_y = (y - canvas_h // 2) / canvas_h
    
    # 打印文本定位日志
    print(f"[文本定位] text: {text['text']}")
    print(f"[文本定位] is_translation: {is_translation}")
    print(f"[文本定位] position.x: {x}, position.y: {y}")
    print(f"[文本定位] transform_x: {transform_x}, transform_y: {transform_y}")
    print(f"[文本定位] font_size: {font_size}, color: {color}")

    if "Template Old" in new_draft_folder:
        text_style_id = str(uuid.uuid4()).replace("-", "")
        text_style = {
            "id": text_style_id,
            "type": "text_style",
            "multi_language_current": "none",
            "font": text.get("font", "默认"),
            "color": color,
            "font_size": font_size
        }
        if not hasattr(script.materials, "material_animations"):
            script.materials.material_animations = []
        script.materials.material_animations.append(text_style)
        
        text_segment = draft.Text_segment(
            text["text"],
            trange(text.get("start", "0s"), text.get("duration", "5s")),
            font=getattr(draft.Font_type, text.get("font", "默认")),
            style=draft.Text_style(
                color=color,
                size=font_size
            ),
            clip_settings=draft.Clip_settings(
                transform_x=transform_x,
                transform_y=transform_y
            )
        )
        text_segment.extra_material_refs.append(text_style_id)
    else:
        text_segment = draft.Text_segment(
            text["text"],
            trange(text.get("start", "0s"), text.get("duration", "5s")),
            font=getattr(draft.Font_type, text.get("font", "默认")),
            style=draft.Text_style(
                color=color,
                size=font_size
            ),
            clip_settings=draft.Clip_settings(
                transform_x=transform_x,
                transform_y=transform_y
            )
        )

    # 处理文本动画
    if "intro_animation" in text or "outro_animation" in text:
        try:
            # 先添加入场动画
            if "intro_animation" in text:
                intro_anim = getattr(Text_intro, text["intro_animation"])
                text_segment.add_animation(intro_anim)
                print(f"[DEBUG] 添加入场动画: {text['intro_animation']}")

            # 再添加出场动画
            if "outro_animation" in text:
                outro_anim = getattr(Text_outro, text["outro_animation"])
                text_segment.add_animation(outro_anim)
                print(f"[DEBUG] 添加出场动画: {text['outro_animation']}")

            # 最后添加循环动画（如果有）
            if "loop_animation" in text:
                loop_anim = getattr(Text_loop_anim, text["loop_animation"])
                text_segment.add_animation(loop_anim)
                print(f"[DEBUG] 添加循环动画: {text['loop_animation']}")

        except AttributeError as e:
            print(f"[DEBUG] 动画类型不存在: {e}")
        except Exception as e:
            print(f"[DEBUG] 添加动画失败: {e}")

    return text_segment

def batch_generate_drafts(draft_params_list, template_folder, drafts_root):
    for params in draft_params_list:
        # Generate unique draft name with timestamp
        draft_name = f"{params.get('draft_name')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        new_draft_folder = os.path.join(drafts_root, draft_name)
        # Create new draft folder
        if os.path.exists(new_draft_folder):
            raise FileExistsError(f"目标草稿文件夹已存在: {new_draft_folder}")
        def tim(time_str):
            if isinstance(time_str, int):
                return time_str
            if hasattr(draft, 'tim'):
                return draft.tim(time_str)
            if 's' in time_str:
                return int(float(time_str.rstrip('s')) * 1000000)
            return 0
        try:
            shutil.copytree(template_folder, new_draft_folder)
        except Exception as e:
            print(f"复制模板时出错: {str(e)}")
            if os.path.exists(new_draft_folder):
                shutil.rmtree(new_draft_folder)
            raise
        try:
            script = create_draft_from_params(params, new_draft_folder)
            temp_dir = os.path.join(new_draft_folder, "_temp")
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, "new_draft_content.json")
            script.dump(temp_file)
            with open(os.path.join(new_draft_folder, "draft_content.json"), "r", encoding="utf-8") as f:
                original_content = json.load(f)
            with open(temp_file, "r", encoding="utf-8") as f:
                new_content = json.load(f)
            if hasattr(script, "_video_effects_data") and script._video_effects_data:
                pass
            if "Template Old" in template_folder:
                original_content["version"] = 360000
                original_content["new_version"] = "3.1.0-beta7"
                original_content["canvas_config"] = {
                    "height": 1080,
                    "ratio": "original",
                    "width": 1920
                }
                original_content["color_space"] = 0
                original_content["id"] = original_content.get("id", str(uuid.uuid4()).upper().replace("-", "-"))
                old_platform = {
                    "app_id": 3704,
                    "app_version": "3.1.0-beta7",
                    "os": "mac",
                    "os_version": "15.4.1",
                    "device_id": original_content.get("platform", {}).get("device_id", ""),
                    "hard_disk_id": original_content.get("platform", {}).get("hard_disk_id", ""),
                    "mac_address": original_content.get("platform", {}).get("mac_address", ""),
                    "app_source": original_content.get("platform", {}).get("app_source", "lv")
                }
                original_content["platform"] = old_platform
                original_content["last_modified_platform"] = old_platform.copy()
                original_content["duration"] = new_content["duration"]
                for key in ["material_animations", "transitions", "video_effects"]:
                    if key in new_content["materials"]:
                        original_content["materials"][key] = new_content["materials"][key]
                for material_type in new_content["materials"]:
                    if material_type not in ["material_animations", "transitions", "video_effects"]:
                        if material_type in original_content["materials"]:
                            original_content["materials"][material_type] = new_content["materials"][material_type]
                        else:
                            original_content["materials"][material_type] = new_content["materials"][material_type]
                if "tracks" in new_content:
                    for track in new_content.get("tracks", []):
                        if track.get("type") == "video":
                            for segment in track.get("segments", []):
                                if "extra_material_refs" in segment:
                                    for ref in segment["extra_material_refs"]:
                                        effect_exists = False
                                        if "video_effects" in original_content["materials"]:
                                            for effect in original_content["materials"]["video_effects"]:
                                                if effect.get("id") == ref:
                                                    effect_exists = True
                                                    break
                                        if not effect_exists and "video_effects" in new_content["materials"]:
                                            for effect in new_content["materials"]["video_effects"]:
                                                if effect.get("id") == ref:
                                                    if "video_effects" not in original_content["materials"]:
                                                        original_content["materials"]["video_effects"] = []
                                                    original_content["materials"]["video_effects"].append(effect)
                                                    break
                                        if not effect_exists and "video_effects" not in original_content["materials"]:
                                            original_content["materials"]["video_effects"] = []
                                            default_effect = {
                                                "id": ref,
                                                "adjust_params": [
                                                    {"default_value": 0.0, "name": "effects_adjust_color", "value": 0.0},
                                                    {"default_value": 0.45, "name": "effects_adjust_speed", "value": 0.45},
                                                    {"default_value": 0.85, "name": "effects_adjust_filter", "value": 0.85}
                                                ],
                                                "apply_target_type": 0,
                                                "apply_time_range": None,
                                                "category_id": "39654",
                                                "category_name": "热门",
                                                "effect_id": "5155369",
                                                "formula_id": "",
                                                "name": "负片频闪",
                                                "platform": "all",
                                                "render_index": 0,
                                                "resource_id": "7153575555554611720",
                                                "source_platform": 0,
                                                "time_range": None,
                                                "track_render_index": 0,
                                                "type": "video_effect",
                                                "value": 1.0,
                                                "version": "",
                                                "path": "/Users/danielwang/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/5155369/a552dfa820b5aba27e4f09e3d83b8643"
                                            }
                                            original_content["materials"]["video_effects"].append(default_effect)
                for special_type in ["effects", "filters"]:
                    if special_type in new_content["materials"] and new_content["materials"][special_type]:
                        if special_type not in original_content["materials"]:
                            original_content["materials"][special_type] = []
                        original_content["materials"][special_type] = new_content["materials"][special_type]
                if "tracks" in new_content:
                    for track in new_content.get("tracks", []):
                        if track.get("type") == "effect":
                            for segment in track.get("segments", []):
                                material_id = segment.get("material_id")
                                if material_id:
                                    effect_exists = False
                                    if "effects" in original_content["materials"]:
                                        for effect in original_content["materials"]["effects"]:
                                            if effect.get("id") == material_id:
                                                effect_exists = True
                                                break
                                    if not effect_exists:
                                        effect_material = {
                                            "id": material_id,
                                            "category_id": "",
                                            "category_name": "effect",
                                            "check_flag": 1,
                                            "effect_id": "7207212289348166686",
                                            "name": "胶片闪切",
                                            "platform": "all",
                                            "resource_id": "7207212289348166686",
                                            "type": "effect"
                                        }
                                        if "effects" not in original_content["materials"]:
                                            original_content["materials"]["effects"] = []
                                        original_content["materials"]["effects"].append(effect_material)
                                        print(f"Manually added missing effect material: {material_id}")
                        elif track.get("type") == "filter":
                            for segment in track.get("segments", []):
                                material_id = segment.get("material_id")
                                if material_id:
                                    filter_exists = False
                                    if "filters" in original_content["materials"]:
                                        for filter_ in original_content["materials"]["filters"]:
                                            if filter_.get("id") == material_id:
                                                filter_exists = True
                                                break
                                    if not filter_exists:
                                        filter_material = {
                                            "id": material_id,
                                            "category_id": "",
                                            "category_name": "filter",
                                            "check_flag": 1,
                                            "filter_id": "1001",
                                            "name": "中性",
                                            "platform": "all",
                                            "resource_id": "1001",
                                            "type": "filter"
                                        }
                                        if "filters" not in original_content["materials"]:
                                            original_content["materials"]["filters"] = []
                                        original_content["materials"]["filters"].append(filter_material)
                                        print(f"Manually added missing filter material: {material_id}")
                if "tracks" in new_content:
                    original_content["tracks"] = new_content["tracks"]
                    for track in original_content["tracks"]:
                        if track.get("type") == "effect" and "segments" in track:
                            if not track["segments"] and "effects" in original_content["materials"] and original_content["materials"]["effects"]:
                                for effect in original_content["materials"]["effects"]:
                                    for param_effect in params.get("effects", []):
                                        effect_segment = {
                                            "enable_adjust": True,
                                            "enable_color_correct_adjust": False,
                                            "enable_color_curves": True,
                                            "enable_color_match_adjust": False,
                                            "enable_color_wheels": True,
                                            "enable_lut": True,
                                            "enable_smart_color_adjust": False,
                                            "last_nonzero_volume": 1.0,
                                            "reverse": False,
                                            "track_attribute": 0,
                                            "track_render_index": 0,
                                            "visible": True,
                                            "id": str(uuid.uuid4()).replace("-", ""),
                                            "material_id": effect["id"],
                                            "target_timerange": {
                                                "start": tim(param_effect.get("start", "0s")),
                                                "duration": tim(param_effect.get("duration", "5s"))
                                            },
                                            "render_index": 10000,
                                            "common_keyframes": [],
                                            "keyframe_refs": []
                                        }
                                        track["segments"].append(effect_segment)
                        if track.get("type") == "filter" and "segments" in track:
                            if not track["segments"] and "filters" in original_content["materials"] and original_content["materials"]["filters"]:
                                for filter_item in original_content["materials"]["filters"]:
                                    for param_filter in params.get("filters", []):
                                        filter_segment = {
                                            "enable_adjust": True,
                                            "enable_color_correct_adjust": False,
                                            "enable_color_curves": True,
                                            "enable_color_match_adjust": False,
                                            "enable_color_wheels": True,
                                            "enable_lut": True,
                                            "enable_smart_color_adjust": False,
                                            "last_nonzero_volume": 1.0,
                                            "reverse": False,
                                            "track_attribute": 0,
                                            "track_render_index": 0,
                                            "visible": True,
                                            "id": str(uuid.uuid4()).replace("-", ""),
                                            "material_id": filter_item["id"],
                                            "target_timerange": {
                                                "start": tim(param_filter.get("start", "0s")),
                                                "duration": tim(param_filter.get("duration", "5s"))
                                            },
                                            "render_index": 11000,
                                            "common_keyframes": [],
                                            "keyframe_refs": []
                                        }
                                        track["segments"].append(filter_segment)
                        if track.get("type") == "text" and "segments" in track:
                            for segment in track["segments"]:
                                if "extra_material_refs" in segment:
                                    animation_refs = []
                                    for ref in segment["extra_material_refs"]:
                                        for anim in original_content["materials"].get("material_animations", []):
                                            if anim["id"] == ref:
                                                animation_refs.append(anim)
                                                break
                                    if animation_refs:
                                        for anim in animation_refs:
                                            if "animations" in anim:
                                                for animation in anim.get("animations", []):
                                                    if animation.get("type") == "out":
                                                        segment["text_animation"] = {
                                                            "id": animation.get("id", ""),
                                                            "type": "out",
                                                            "duration": animation.get("duration", 1000000)
                                                        }
                                                        if "clip" not in segment:
                                                            segment["clip"] = {}
                                                        if "text_animation" not in segment["clip"]:
                                                            segment["clip"]["text_animation"] = {
                                                                "id": animation.get("id", ""),
                                                                "duration": animation.get("duration", 1000000)
                                                            }
                        elif track.get("type") == "video" and "segments" in track:
                            for segment in track["segments"]:
                                if "material_id" in segment and any(v["id"] == segment["material_id"] for v in original_content["materials"].get("videos", [])):
                                    if "extra_material_refs" in segment:
                                        animation_refs = []
                                        transition_refs = []
                                        animation_material_ref = None
                                        for ref in segment["extra_material_refs"]:
                                            for anim in original_content["materials"].get("material_animations", []):
                                                if anim["id"] == ref:
                                                    animation_refs.append(ref)
                                                    animation_material_ref = anim
                                                    break
                                            for trans in original_content["materials"].get("transitions", []):
                                                if trans["id"] == ref:
                                                    transition_refs.append(ref)
                                                    break
                                        if animation_refs:
                                            segment["animation"] = animation_refs[0]
                                        elif "animation" in params.get("videos", [{}])[0]:
                                            video_params = params.get("videos", [{}])[0]
                                            animation_type = getattr(Intro_type, video_params["animation"])
                                            animation_id = str(uuid.uuid4()).replace("-", "")
                                            animation_material = {
                                                "id": animation_id,
                                                "type": "sticker_animation",
                                                "multi_language_current": "none",
                                                "animations": [
                                                    {
                                                        "anim_adjust_params": None,
                                                        "platform": "all",
                                                        "panel": "video",
                                                        "material_type": "video",
                                                        "name": video_params["animation"],
                                                        "id": str(animation_type.value.resource_id),
                                                        "type": "in",
                                                        "resource_id": str(animation_type.value.resource_id),
                                                        "start": 0,
                                                        "duration": animation_type.value.duration
                                                    }
                                                ]
                                            }
                                            if "material_animations" not in original_content["materials"]:
                                                original_content["materials"]["material_animations"] = []
                                            original_content["materials"]["material_animations"].append(animation_material)
                                            segment["extra_material_refs"].append(animation_id)
                                            segment["animation"] = animation_id
                                        if transition_refs:
                                            segment["transition"] = transition_refs[0]
                if "texts" in original_content["materials"]:
                    for text in original_content["materials"]["texts"]:
                        if "content" in text:
                            try:
                                if text["content"].startswith("{") and text["content"].endswith("}"):
                                    content_json = json.loads(text["content"])
                                    if isinstance(content_json, dict) and "text" in content_json:
                                        plain_text = content_json.get("text", "")
                                        text["content"] = plain_text
                                text["content_format"] = 0
                            except:
                                pass
                if "materials" in original_content:
                    unsupported_material_types = [
                        "ai_translates", "digital_humans", "flowers", "green_screens", 
                        "log_color_wheels", "manual_deformations", "material_colors", 
                        "multi_language_refs", "plugin_effects", "primary_color_wheels", 
                        "shapes", "smart_crops", "smart_relights", "time_marks", 
                        "vocal_beautifys", "vocal_separations"
                    ]
                    for material_type in unsupported_material_types:
                        if material_type in original_content["materials"]:
                            original_content["materials"][material_type] = []
            else:
                original_content["tracks"] = new_content["tracks"]
                original_content["materials"] = new_content["materials"]
                original_content["duration"] = new_content["duration"]
            if hasattr(script, "_video_effects_data") and script._video_effects_data:
                print(f"Final step: Adding {len(script._video_effects_data)} video effects")
                if "video_effects" not in original_content["materials"]:
                    original_content["materials"]["video_effects"] = []
                for effect_data in script._video_effects_data:
                    effect_id = effect_data["id"]
                    effect_name = effect_data["name"]
                    print(f"Adding effect {effect_id} ({effect_name})")
                    exists = False
                    for existing_effect in original_content["materials"]["video_effects"]:
                        if existing_effect.get("id") == effect_id:
                            exists = True
                            break
                    if not exists:
                        original_content["materials"]["video_effects"].append(effect_data)
            with open(os.path.join(new_draft_folder, "draft_content.json"), "w", encoding="utf-8") as f:
                json.dump(original_content, f, ensure_ascii=False, indent=2)
                print("Saved draft_content.json with effects")
            meta_paths = [
                os.path.join(new_draft_folder, "draft_meta.json"),
                os.path.join(new_draft_folder, "draft_meta_info.json")
            ]
            for meta_path in meta_paths:
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta["draft_name"] = draft_name
                    meta["draft_fold_path"] = new_draft_folder
                    meta["draft_root_path"] = drafts_root
                    current_timestamp = int(datetime.datetime.now().timestamp() * 1000000)
                    meta["tm_draft_create"] = current_timestamp
                    meta["tm_draft_modified"] = current_timestamp
                    meta["tm_duration"] = script.duration
                    if "Template Old" in template_folder:
                        meta["draft_id"] = meta.get("draft_id", "")
                        if "draft_materials" not in meta:
                            meta["draft_materials"] = [
                                {"type": 0, "value": []},
                                {"type": 1, "value": []},
                                {"type": 2, "value": []},
                                {"type": 3, "value": []},
                                {"type": 6, "value": []},
                                {"type": 7, "value": []},
                                {"type": 8, "value": []}
                            ]
                        meta["draft_new_version"] = "3.1.0-beta7"
                        meta["draft_version"] = "3.1.0-beta7"
                        meta["draft_timeline_materials_size_"] = meta.get("draft_timeline_materials_size_", 0)
                        meta["draft_cloud_last_action_download"] = False
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"生成草稿内容时出错: {str(e)}")
            if os.path.exists(new_draft_folder):
                shutil.rmtree(new_draft_folder)
            raise
        print(f"草稿已生成：{new_draft_folder}")
