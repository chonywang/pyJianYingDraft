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


def batch_generate_drafts(draft_params_list, template_folder, drafts_root):
    for params in draft_params_list:
        # Generate unique draft name with timestamp
        draft_name = f"{params.get('draft_name')}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        new_draft_folder = os.path.join(drafts_root, draft_name)
        
        # Create new draft folder
        if os.path.exists(new_draft_folder):
            raise FileExistsError(f"目标草稿文件夹已存在: {new_draft_folder}")
        
        # Helper function to convert time strings to microseconds
        def tim(time_str):
            if isinstance(time_str, int):
                return time_str
            # Use the existing pyJianYingDraft tim function if possible
            if hasattr(draft, 'tim'):
                return draft.tim(time_str)
            
            # Simple implementation if tim function is not available
            if 's' in time_str:
                return int(float(time_str.rstrip('s')) * 1000000)
            return 0
        
        # 1. Copy template to new draft folder
        try:
            shutil.copytree(template_folder, new_draft_folder)
        except Exception as e:
            print(f"复制模板时出错: {str(e)}")
            if os.path.exists(new_draft_folder):
                shutil.rmtree(new_draft_folder)
            raise
        
        try:
            # 2. Create draft with all materials
            script = create_draft_from_params(params, new_draft_folder)
            
            # 3. Create separate draft content file instead of modifying the existing one
            temp_dir = os.path.join(new_draft_folder, "_temp")
            os.makedirs(temp_dir, exist_ok=True)
            temp_file = os.path.join(temp_dir, "new_draft_content.json")
            
            script.dump(temp_file)
            
            # 4. Read both files
            with open(os.path.join(new_draft_folder, "draft_content.json"), "r", encoding="utf-8") as f:
                original_content = json.load(f)
            
            with open(temp_file, "r", encoding="utf-8") as f:
                new_content = json.load(f)
            
            # 4.5 Manually add video effects data if necessary
            if hasattr(script, "_video_effects_data") and script._video_effects_data:
                # Don't process effects here, we'll handle them at the end
                pass
            
            # 5. Update content for old version
            if "Template Old" in template_folder:
                # Set version to old format
                original_content["version"] = 360000
                original_content["new_version"] = "3.1.0-beta7"
                
                # Ensure canvas_config has proper dimensions
                original_content["canvas_config"] = {
                    "height": 1080,
                    "ratio": "original",
                    "width": 1920
                }
                
                # Set color_space to valid value
                original_content["color_space"] = 0
                
                # Preserve original id or generate a new one
                original_content["id"] = original_content.get("id", str(uuid.uuid4()).upper().replace("-", "-"))
                
                # Set platform to old version
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
                
                # Update both platform and last_modified_platform
                original_content["platform"] = old_platform
                original_content["last_modified_platform"] = old_platform.copy()
                
                # Preserve original properties that support animations and transitions
                original_content["duration"] = new_content["duration"]
                
                # Complete replacement of material_animations, transitions, and video_effects
                for key in ["material_animations", "transitions", "video_effects"]:
                    if key in new_content["materials"]:
                        original_content["materials"][key] = new_content["materials"][key]
                
                # Special handling for material format - all other materials
                for material_type in new_content["materials"]:
                    if material_type not in ["material_animations", "transitions", "video_effects"]:
                        if material_type in original_content["materials"]:
                            original_content["materials"][material_type] = new_content["materials"][material_type]
                        else:
                            # If it doesn't exist in original, add it (e.g., filters, effects)
                            original_content["materials"][material_type] = new_content["materials"][material_type]
                
                # Manually check for video segment effects and ensure they exist
                if "tracks" in new_content:
                    # Check all video segments
                    for track in new_content.get("tracks", []):
                        if track.get("type") == "video":
                            for segment in track.get("segments", []):
                                if "extra_material_refs" in segment:
                                    # Check each reference to see if it's an effect
                                    for ref in segment["extra_material_refs"]:
                                        # Look for this effect in video_effects materials
                                        effect_exists = False
                                        if "video_effects" in original_content["materials"]:
                                            for effect in original_content["materials"]["video_effects"]:
                                                if effect.get("id") == ref:
                                                    effect_exists = True
                                                    break
                                        
                                        # If not found but exists in new_content, add it
                                        if not effect_exists and "video_effects" in new_content["materials"]:
                                            for effect in new_content["materials"]["video_effects"]:
                                                if effect.get("id") == ref:
                                                    if "video_effects" not in original_content["materials"]:
                                                        original_content["materials"]["video_effects"] = []
                                                    original_content["materials"]["video_effects"].append(effect)
                                                    break
                                        
                                        # If still not found, use a default effect
                                        if not effect_exists and "video_effects" not in original_content["materials"]:
                                            original_content["materials"]["video_effects"] = []
                                            # Create a default effect
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
                
                # Make sure special materials like effects and filters are preserved
                for special_type in ["effects", "filters"]:
                    if special_type in new_content["materials"] and new_content["materials"][special_type]:
                        if special_type not in original_content["materials"]:
                            original_content["materials"][special_type] = []
                        original_content["materials"][special_type] = new_content["materials"][special_type]
                
                # Manually check for effect and filter segments and ensure materials exist
                if "tracks" in new_content:
                    # Check all segments in the effect tracks
                    for track in new_content.get("tracks", []):
                        if track.get("type") == "effect":
                            for segment in track.get("segments", []):
                                material_id = segment.get("material_id")
                                if material_id:
                                    # Does this effect material exist?
                                    effect_exists = False
                                    if "effects" in original_content["materials"]:
                                        for effect in original_content["materials"]["effects"]:
                                            if effect.get("id") == material_id:
                                                effect_exists = True
                                                break
                                    
                                    # If not, create it
                                    if not effect_exists:
                                        effect_material = {
                                            "id": material_id,
                                            "category_id": "",
                                            "category_name": "effect",
                                            "check_flag": 1,
                                            "effect_id": "7207212289348166686",  # Default to 胶片闪切
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
                                    # Does this filter material exist?
                                    filter_exists = False
                                    if "filters" in original_content["materials"]:
                                        for filter_ in original_content["materials"]["filters"]:
                                            if filter_.get("id") == material_id:
                                                filter_exists = True
                                                break
                                    
                                    # If not, create it
                                    if not filter_exists:
                                        filter_material = {
                                            "id": material_id,
                                            "category_id": "",
                                            "category_name": "filter",
                                            "check_flag": 1,
                                            "filter_id": "1001",  # Default to 中性
                                            "name": "中性",
                                            "platform": "all",
                                            "resource_id": "1001",
                                            "type": "filter"
                                        }
                                        if "filters" not in original_content["materials"]:
                                            original_content["materials"]["filters"] = []
                                        original_content["materials"]["filters"].append(filter_material)
                                        print(f"Manually added missing filter material: {material_id}")
                
                # Handle tracks and ensure animations/transitions are preserved
                if "tracks" in new_content:
                    original_content["tracks"] = new_content["tracks"]
                    
                    # Ensure effect and filter tracks have segments
                    for track in original_content["tracks"]:
                        # For effect tracks
                        if track.get("type") == "effect" and "segments" in track:
                            # Check if segments are empty, transfer segments from new_content if available
                            if not track["segments"] and "effects" in original_content["materials"] and original_content["materials"]["effects"]:
                                # Create segments for each effect in the materials section
                                for effect in original_content["materials"]["effects"]:
                                    # Find matching effect in the params
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
                        
                        # For filter tracks
                        if track.get("type") == "filter" and "segments" in track:
                            # Check if segments are empty, transfer segments from new_content if available
                            if not track["segments"] and "filters" in original_content["materials"] and original_content["materials"]["filters"]:
                                # Create segments for each filter in the materials section
                                for filter_item in original_content["materials"]["filters"]:
                                    # Find matching filter in the params
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
                        
                        # Make sure segment formats are correct for old version
                        if track.get("type") == "text" and "segments" in track:
                            # Special handling for text tracks with animations
                            for segment in track["segments"]:
                                if "extra_material_refs" in segment:
                                    # Find text animation references
                                    animation_refs = []
                                    
                                    for ref in segment["extra_material_refs"]:
                                        # Check material_animations references
                                        for anim in original_content["materials"].get("material_animations", []):
                                            if anim["id"] == ref:
                                                animation_refs.append(anim)
                                                break
                                    
                                    # Add direct animation attributes for text segments with animations
                                    if animation_refs:
                                        for anim in animation_refs:
                                            if "animations" in anim:
                                                for animation in anim.get("animations", []):
                                                    # Check if this is a Text_outro type animation (out animation)
                                                    if animation.get("type") == "out":
                                                        # Set direct animation attributes that old version can recognize
                                                        segment["text_animation"] = {
                                                            "id": animation.get("id", ""),
                                                            "type": "out",
                                                            "duration": animation.get("duration", 1000000)
                                                        }
                                                        
                                                        # Also add to clip settings to ensure it's visible
                                                        if "clip" not in segment:
                                                            segment["clip"] = {}
                                                        if "text_animation" not in segment["clip"]:
                                                            segment["clip"]["text_animation"] = {
                                                                "id": animation.get("id", ""),
                                                                "duration": animation.get("duration", 1000000)
                                                            }
                        
                        elif track.get("type") == "video" and "segments" in track:
                            # For video segments, ensure animations are applied
                            for segment in track["segments"]:
                                if "material_id" in segment and any(v["id"] == segment["material_id"] for v in original_content["materials"].get("videos", [])):
                                    if "extra_material_refs" in segment:
                                        # Find animation references
                                        animation_refs = []
                                        transition_refs = []
                                        animation_material_ref = None
                                        
                                        for ref in segment["extra_material_refs"]:
                                            # Check material_animations references 
                                            for anim in original_content["materials"].get("material_animations", []):
                                                if anim["id"] == ref:
                                                    animation_refs.append(ref)
                                                    animation_material_ref = anim
                                                    break
                                                    
                                            # Check transition references
                                            for trans in original_content["materials"].get("transitions", []):
                                                if trans["id"] == ref:
                                                    transition_refs.append(ref)
                                                    break
                                        
                                        # If we have animations or transitions, make sure they're recognized correctly
                                        if animation_refs:
                                            segment["animation"] = animation_refs[0]  # Old version expects direct reference
                                        
                                        # If we don't have an animation but there should be one, add it
                                        elif "animation" in params.get("videos", [{}])[0]:
                                            # Generate a new animation material id
                                            video_params = params.get("videos", [{}])[0]
                                            animation_type = getattr(Intro_type, video_params["animation"])
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
                                                        "name": video_params["animation"],
                                                        "id": str(animation_type.value.resource_id),
                                                        "type": "in",
                                                        "resource_id": str(animation_type.value.resource_id),
                                                        "start": 0,
                                                        "duration": animation_type.value.duration
                                                    }
                                                ]
                                            }
                                            
                                            # Add to materials and segment
                                            if "material_animations" not in original_content["materials"]:
                                                original_content["materials"]["material_animations"] = []
                                            original_content["materials"]["material_animations"].append(animation_material)
                                            segment["extra_material_refs"].append(animation_id)
                                            segment["animation"] = animation_id
                                        
                                        if transition_refs:
                                            segment["transition"] = transition_refs[0]  # Old version expects direct reference
                
                # Fix text content format for old version
                if "texts" in original_content["materials"]:
                    for text in original_content["materials"]["texts"]:
                        if "content" in text:
                            try:
                                # Check if the content is already JSON
                                if text["content"].startswith("{") and text["content"].endswith("}"):
                                    content_json = json.loads(text["content"])
                                    # Extract plain text from the JSON
                                    if isinstance(content_json, dict) and "text" in content_json:
                                        plain_text = content_json.get("text", "")
                                        # Replace the JSON content with plain text
                                        text["content"] = plain_text
                                else:
                                    # Content is already plain text
                                    pass
                                
                                # Add the format identifier for v3.1.0-beta7
                                text["content_format"] = 0  # 0 means plaintext in v3.1.0-beta7
                            except:
                                # If there's any error, keep the original content
                                pass
                
                # Ensure materials format is compatible with v3.1.0-beta7
                if "materials" in original_content:
                    # Remove any material types not supported in v3.1.0-beta7
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
                # For new templates, just copy all content
                original_content["tracks"] = new_content["tracks"]
                original_content["materials"] = new_content["materials"]
                original_content["duration"] = new_content["duration"]
            
            # FINAL STEP: Ensure video effects are in the materials section
            # This needs to happen after all other content updating
            if hasattr(script, "_video_effects_data") and script._video_effects_data:
                print(f"Final step: Adding {len(script._video_effects_data)} video effects")
                # Make sure video_effects exists in materials
                if "video_effects" not in original_content["materials"]:
                    original_content["materials"]["video_effects"] = []
                
                # Add each effect
                for effect_data in script._video_effects_data:
                    effect_id = effect_data["id"]
                    effect_name = effect_data["name"]
                    print(f"Adding effect {effect_id} ({effect_name})")
                    
                    # Check if effect already exists
                    exists = False
                    for existing_effect in original_content["materials"]["video_effects"]:
                        if existing_effect.get("id") == effect_id:
                            exists = True
                            break
                    
                    # Only add if it doesn't exist
                    if not exists:
                        original_content["materials"]["video_effects"].append(effect_data)
            
            # 7. Save back to draft_content.json
            with open(os.path.join(new_draft_folder, "draft_content.json"), "w", encoding="utf-8") as f:
                json.dump(original_content, f, ensure_ascii=False, indent=2)
                print("Saved draft_content.json with effects")
            
            # 8. Update draft_meta.json with only the minimum required fields while preserving format
            meta_paths = [
                os.path.join(new_draft_folder, "draft_meta.json"),
                os.path.join(new_draft_folder, "draft_meta_info.json")
            ]
            
            for meta_path in meta_paths:
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    
                    # Basic updates needed for all templates
                    meta["draft_name"] = draft_name
                    meta["draft_fold_path"] = new_draft_folder
                    meta["draft_root_path"] = drafts_root
                    current_timestamp = int(datetime.datetime.now().timestamp() * 1000000)
                    meta["tm_draft_create"] = current_timestamp
                    meta["tm_draft_modified"] = current_timestamp
                    
                    # Make sure duration is set properly
                    meta["tm_duration"] = script.duration
                    
                    # Specific updates for old templates
                    if "Template Old" in template_folder:
                        # Keep original draft_id if it exists
                        meta["draft_id"] = meta.get("draft_id", "")
                        
                        # Keep original draft_materials or set if missing
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
                        
                        # Set proper version for 3.1.0-beta7
                        meta["draft_new_version"] = "3.1.0-beta7"
                        meta["draft_version"] = "3.1.0-beta7"
                        
                        # Ensure other old-version specific fields exist
                        meta["draft_timeline_materials_size_"] = meta.get("draft_timeline_materials_size_", 0)
                        meta["draft_cloud_last_action_download"] = False
                    
                    # Save updated metadata
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, ensure_ascii=False, indent=2)
            
            # 9. Clean up temp files
            shutil.rmtree(temp_dir)
        
        except Exception as e:
            print(f"生成草稿内容时出错: {str(e)}")
            if os.path.exists(new_draft_folder):
                shutil.rmtree(new_draft_folder)
            raise
        
        print(f"草稿已生成：{new_draft_folder}")


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
