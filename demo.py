# 导入模块
import os
import pyJianYingDraft as draft
from pyJianYingDraft import Intro_type, Transition_type, trange, tim
from pyJianYingDraft.metadata.video_effect_meta import Video_scene_effect_type
from pyJianYingDraft.metadata.filter_meta import Filter_type
import shutil
import json
import datetime
import requests
from urllib.parse import urlparse
import uuid
from jianying_utils import batch_generate_drafts


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
        # Set old version compatible settings
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
        script.add_track(draft.Track_type.audio)
    if params.get("videos") or params.get("gifs"):
        script.add_track(draft.Track_type.video)
    if params.get("texts"):
        script.add_track(draft.Track_type.text)
    # No longer add separate effect track as effects will be added to video segments
    if params.get("filters"):
        script.add_track(draft.Track_type.filter)
    
    # Store video segments to apply effects later
    video_segments = []
    # Store video effects for later manual addition
    video_effects_data = []
    
    # Process audios
    for audio in params.get("audios", []):
        audio_path = download_file_if_needed(audio["file_path"], new_draft_folder)
        audio_material = draft.Audio_material(audio_path)
        audio_segment = draft.Audio_segment(
            audio_material,
            trange(audio.get("start", "0s"), audio.get("duration", "5s")),
            volume=audio.get("volume", 1.0)
        )
        # Only apply one fade effect - prioritize fade_in if both are specified
        if "fade_in" in audio:
            audio_segment.add_fade(tim(audio["fade_in"]), tim("0s"))
        elif "fade_out" in audio:
            audio_segment.add_fade(tim("0s"), tim(audio["fade_out"]))
        script.add_segment(audio_segment)
    
    # Process videos
    for video in params.get("videos", []):
        video_path = download_file_if_needed(video["file_path"], new_draft_folder)
        video_material = draft.Video_material(video_path)
        
        # 如果指定了target_start，则使用它来创建不重叠的时间线
        if "target_start" in video:
            # 创建源时间范围
            source_timerange = trange(video.get("start", "0s"), video.get("duration", "5s"))
            
            # 创建目标时间范围
            target_timerange = draft.Timerange(
                tim(video.get("target_start", "0s")),
                tim(video.get("duration", "5s"))
            )
            
            # 正确的参数顺序是 material, target_timerange, source_timerange
            video_segment = draft.Video_segment(
                video_material,
                target_timerange,
                source_timerange=source_timerange
            )
        else:
            # 旧的方式，源和目标时间范围相同
            video_segment = draft.Video_segment(
                video_material,
                trange(video.get("start", "0s"), video.get("duration", "5s"))
            )
        
        # Add transition
        if "transition" in video:
            video_segment.add_transition(getattr(Transition_type, video["transition"]))
        
        # For old template, ensure animations are properly created and linked
        if "animation" in video and "Template Old" in new_draft_folder:
            animation_type = getattr(Intro_type, video["animation"])
            # Create animation material directly
            animation_id = str(uuid.uuid4()).replace("-", "")
            
            # Create animation material
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
            
            # Add animation to materials
            if "material_animations" not in script.materials:
                script.materials.material_animations = []
            script.materials.material_animations.append(animation_material)
            
            # Add animation reference to segment
            video_segment.extra_material_refs.append(animation_id)
            if hasattr(video_segment, "animation"):
                video_segment.animation = animation_id
            elif hasattr(video_segment, "animations"):
                video_segment.animations = animation_id
            else:
                # If there's no attribute, it might be a property or not exist at all
                try:
                    if hasattr(video_segment, "_data") and isinstance(video_segment._data, dict):
                        video_segment._data["animation"] = animation_id
                except:
                    pass  # Silently continue if we can't set the animation directly
        elif "animation" in video:
            # Normal animation processing for non-old templates
            video_segment.add_animation(getattr(Intro_type, video["animation"]))
        
        # Process effects for this video segment if applicable
        if params.get("effects"):
            for effect in params.get("effects", []):
                # Create effect ID and store it
                effect_id = str(uuid.uuid4()).upper().replace("-", "-")
                
                # Get appropriate time range
                effect_start = tim(effect.get("start", "0s"))
                effect_duration = tim(effect.get("duration", "5s"))
                
                # Special case for specific effects with known resource IDs
                effect_name = effect.get("effect_id", "负片频闪")
                effect_resource_id = ""
                effect_video_id = ""
                
                # Map common effects to their resource IDs
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
                    # Default to 负片频闪 as fallback but print warning
                    print(f"警告: 未知的特效 '{effect_name}'，使用'负片频闪'作为替代")
                    effect_resource_id = "7153575555554611720" 
                    effect_video_id = "5155369"
                    effect_name = "负片频闪"  # 替换特效名称为实际使用的
                
                # Store effect data for manual addition later
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
                
                # Add the effect reference to the video segment
                video_segment.extra_material_refs.append(effect_id)
        
        # 添加视频片段特定的效果（这是新增的代码）
        if "effects" in video:
            for effect in video.get("effects", []):
                # Create effect ID and store it
                effect_id = str(uuid.uuid4()).upper().replace("-", "-")
                
                # Get appropriate time range
                effect_start = tim(effect.get("start", "0s"))
                effect_duration = tim(effect.get("duration", "5s"))
                
                # Special case for specific effects with known resource IDs
                effect_name = effect.get("effect_id", "负片频闪")
                effect_resource_id = ""
                effect_video_id = ""
                
                # Map common effects to their resource IDs
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
                    # Default to 负片频闪 as fallback but print warning
                    print(f"警告: 未知的特效 '{effect_name}'，使用'负片频闪'作为替代")
                    effect_resource_id = "7153575555554611720" 
                    effect_video_id = "5155369"
                    effect_name = "负片频闪"  # 替换特效名称为实际使用的
                
                # Store effect data for manual addition later
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
                
                # Add the effect reference to the video segment
                video_segment.extra_material_refs.append(effect_id)
        
        # Store the video segment to apply effects later
        video_segments.append(video_segment)
        
        # Add the segment to the script
        script.add_segment(video_segment)
    
    # Process GIFs (treated as videos)
    for gif in params.get("gifs", []):
        gif_path = download_file_if_needed(gif["file_path"], new_draft_folder)
        gif_material = draft.Video_material(gif_path)
        gif_segment = draft.Video_segment(
            gif_material,
            trange(gif.get("start", "0s"), gif.get("duration", "5s"))
        )
        if "transition" in gif:
            gif_segment.add_transition(getattr(Transition_type, gif["transition"]))
        video_segments.append(gif_segment)  # Also store gif segments
        script.add_segment(gif_segment)
    
    # Process texts with compatibility for old version
    for text in params.get("texts", []):
        # For old template, create text segment with rich formatting support
        if "Template Old" in new_draft_folder:
            # Create text style reference for styling support
            text_style_id = str(uuid.uuid4()).replace("-", "")
            text_style = {
                "id": text_style_id,
                "type": "text_style",
                "multi_language_current": "none",
                "font": text.get("font", "默认"),
                "color": text.get("style", {}).get("color", (1.0, 1.0, 1.0)),
                "font_size": text.get("style", {}).get("size", 36)
            }
            
            # Add the style to material_animations
            if "material_animations" not in script.materials:
                script.materials.material_animations = []
            script.materials.material_animations.append(text_style)
            
            # Create text segment with style reference
            text_segment = draft.Text_segment(
                text["text"],
                trange(text.get("start", "0s"), text.get("duration", "5s")),
                font=getattr(draft.Font_type, text.get("font", "默认")),
                style=draft.Text_style(color=text.get("style", {}).get("color", (1.0, 1.0, 1.0))),
                clip_settings=draft.Clip_settings(
                    transform_x=text.get("position", {}).get("x", 0),
                    transform_y=text.get("position", {}).get("y", 0)
                )
            )
            
            # Manually add style reference
            text_segment.extra_material_refs.append(text_style_id)
        else:
            # For new template, use the standard approach
            text_segment = draft.Text_segment(
                text["text"],
                trange(text.get("start", "0s"), text.get("duration", "5s")),
                font=getattr(draft.Font_type, text.get("font", "默认")),
                style=draft.Text_style(color=text.get("style", {}).get("color", (1.0, 1.0, 1.0))),
                clip_settings=draft.Clip_settings(
                    transform_x=text.get("position", {}).get("x", 0),
                    transform_y=text.get("position", {}).get("y", 0)
                )
            )
            
        if "animation" in text:
            text_segment.add_animation(
                getattr(draft.Text_outro, text["animation"]),
                duration=tim(text.get("animation_duration", "1s"))
            )
        script.add_segment(text_segment)
    
    # Process filters
    filter_ids = {}
    if params.get("filters"):
        # First create all the filter materials
        for filter_ in params.get("filters", []):
            filter_type = getattr(Filter_type, filter_["filter_id"])
            
            # Create filter segment first to get its material
            filter_segment = draft.Filter_segment(
                filter_type,
                trange(filter_.get("start", "0s"), filter_.get("duration", "5s")),
                intensity=filter_.get("intensity", 100)
            )
            
            # Get the auto-generated material_id and save it for later use
            filter_id = filter_segment.material_id
            filter_ids[filter_["filter_id"]] = filter_id
            
            # Add the segment to the script
            script.add_segment(filter_segment)
    
    # Add video_effects_data to temp field for batch_generate_drafts to handle
    script._video_effects_data = video_effects_data
    
    return script


def create_simplified_draft(template_folder, drafts_root, name="简化草稿"):
    """创建一个极简草稿，只更新必要的元数据字段，不修改内容结构"""
    
    # 生成带时间戳的草稿名称
    draft_name = f"{name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    new_draft_folder = os.path.join(drafts_root, draft_name)
    
    # 如果已存在同名草稿，则报错
    if os.path.exists(new_draft_folder):
        raise FileExistsError(f"目标草稿文件夹已存在: {new_draft_folder}")
    
    # 直接复制整个模板文件夹
    try:
        print(f"复制模板: {template_folder} 到 {new_draft_folder}")
        shutil.copytree(template_folder, new_draft_folder)
    except Exception as e:
        print(f"复制模板时出错: {str(e)}")
        if os.path.exists(new_draft_folder):
            shutil.rmtree(new_draft_folder)
        raise
    
    try:
        # 更新 draft_meta.json 和 draft_meta_info.json
        meta_files = ["draft_meta.json", "draft_meta_info.json"]
        for meta_file in meta_files:
            meta_path = os.path.join(new_draft_folder, meta_file)
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                
                # 只更新最基本的元信息
                meta["draft_name"] = draft_name
                meta["draft_fold_path"] = new_draft_folder
                meta["draft_root_path"] = drafts_root
                current_timestamp = int(datetime.datetime.now().timestamp() * 1000000)
                meta["tm_draft_create"] = current_timestamp
                meta["tm_draft_modified"] = current_timestamp
                
                # 确保duration有效
                if "tm_duration" in meta and meta["tm_duration"] == 0:
                    # 从草稿内容中获取实际时长
                    draft_content_path = os.path.join(new_draft_folder, "draft_content.json") 
                    if os.path.exists(draft_content_path):
                        try:
                            with open(draft_content_path, "r", encoding="utf-8") as f:
                                content = json.load(f)
                                if "duration" in content and content["duration"] > 0:
                                    meta["tm_duration"] = content["duration"]
                                else:
                                    # 设置一个默认值
                                    meta["tm_duration"] = 5000000  # 5秒
                        except:
                            # 如果无法读取，设置默认值
                            meta["tm_duration"] = 5000000  # 5秒
                
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                
                print(f"已更新元数据: {meta_path}")
        
        # 检查并修复draft_content.json
        draft_content_path = os.path.join(new_draft_folder, "draft_content.json")
        if os.path.exists(draft_content_path):
            try:
                with open(draft_content_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                
                # 修复canvas_config
                if "canvas_config" in content and (content["canvas_config"].get("width", 0) == 0 or content["canvas_config"].get("height", 0) == 0):
                    content["canvas_config"] = {
                        "height": 1080,
                        "ratio": "original",
                        "width": 1920
                    }
                
                # 修复color_space
                if "color_space" in content and content["color_space"] < 0:
                    content["color_space"] = 0
                
                # 确保duration有效
                if "duration" in content and content["duration"] == 0:
                    content["duration"] = 5000000  # 5秒
                
                with open(draft_content_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                
                print(f"已修复草稿内容: {draft_content_path}")
            except Exception as e:
                print(f"修复草稿内容时出错: {str(e)}")
        
        print(f"草稿已生成: {new_draft_folder}")
        return new_draft_folder
    except Exception as e:
        print(f"创建草稿时出错: {str(e)}")
        if os.path.exists(new_draft_folder):
            shutil.rmtree(new_draft_folder)
        raise


if __name__ == "__main__":
    # Example usage
    draft_params_list = [
        {
            "draft_name": "511_",
            "audios": [
                {
                    "file_path": "https://lf26-appstore-sign.oceancloudapi.com/ocean-cloud-tos/VolcanoUserVoice/speech_7426725529589661723_b8913d29-194b-4ed5-872e-11fe8612b183.mp3?lk3s=da27ec82&x-expires=1747022835&x-signature=ND90fGxIzoLkiBuR0v9ODfHfgYA%3D",
                    "start": "0s",
                    "duration": "5s",
                    "volume": 0.8,
                    "fade_in": "1s",
                    "fade_out": "1s"
                }
            ],
            "videos": [
                {
                    "file_path": "https://video-snot-12220.oss-cn-shanghai.aliyuncs.com/2025-05-09/video/2222a427-37a2-4974-ae13-cdcafc1c543a.mp4",
                    "start": "0s",
                    "duration": "5s",
                    "transition": "信号故障",
                    "animation": "斜切"
                }
            ],
            "texts": [
                {
                    "text": "你有没有过这种情况？和人聊天时，对方笑着说'没事'，但眉毛却皱成小括号？",
                    "start": "0s",
                    "duration": "2s",
                    "font": "后现代体",
                    "style": {"color": (1.0, 1.0, 0.0)},
                    "animation": "故障闪动",
                    "animation_duration": "1s",
                    "position": {"x": 0, "y": -0.8}
                }
            ],
            "effects": [
                {
                    "effect_id": "星火炸开",
                    "start": "0s",
                    "duration": "5s"
                }
            ],
            "filters": [
                {
                    "filter_id": "中性",
                    "start": "0s",
                    "duration": "5s",
                    "intensity": 80
                }
            ],
            "mosaics": [
                {
                    "region": [0.1, 0.1, 0.5, 0.5],
                    "start": "3s",
                    "duration": "2s"
                }
            ]
        }
    ]
    
    template_folder = "/Users/danielwang/Documents/jianyan/JianyingPro Drafts/Draft Template Old"
    drafts_root = "/Users/danielwang/Documents/jianyan/JianyingPro Drafts"
    
    # Try the simplified approach
    # create_simplified_draft(template_folder, drafts_root, "简单测试")
    batch_generate_drafts(draft_params_list, template_folder, drafts_root)
