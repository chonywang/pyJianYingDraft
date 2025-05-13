import os
import json
import pyJianYingDraft as draft
from pyJianYingDraft import trange, tim, Intro_type, Transition_type, Video_scene_effect_type, Video_character_effect_type, Filter_type

class DraftBuilder:
    def __init__(self, draft_name, draft_folder, resolution=(1920, 1080), version=None, new_version=None):
        self.draft_name = draft_name
        self.draft_folder = draft_folder
        self.resolution = resolution
        self.script = draft.Script_file(*resolution)
        # 兼容旧模板
        if version is not None:
            self.script.content["version"] = version
        if new_version is not None:
            self.script.content["new_version"] = new_version
        # 先创建轨道
        self.script.add_track(draft.Track_type.audio)
        self.script.add_track(draft.Track_type.video)
        self.script.add_track(draft.Track_type.text)
        self.script.add_track(draft.Track_type.effect)
        self.script.add_track(draft.Track_type.filter)
        # 再从 script.tracks 取出真正的轨道对象
        self.tracks = {
            "audio": self.script.tracks["audio"],
            "video": self.script.tracks["video"],
            "text": self.script.tracks["text"],
            "effect": self.script.tracks["effect"],
            "filter": self.script.tracks["filter"],
            "image": None,  # 可扩展
        }
        self.segments = []

    def add_audio(self, file_path, start, duration, volume=1.0, fade_in=None, fade_out=None, **kwargs):
        seg = draft.Audio_segment(
            draft.Audio_material(file_path),
            trange(start, duration),
            volume=volume
        )
        if fade_in:
            seg.add_fade(fade_in, "0s")
        if fade_out:
            seg.add_fade("0s", fade_out)
        self.script.add_segment(seg)
        self.segments.append(seg)
        return seg

    def add_video(self, file_path, start, duration, transition=None, animation=None, **kwargs):
        seg = draft.Video_segment(
            draft.Video_material(file_path),
            trange(start, duration)
        )
        if animation:
            seg.add_animation(getattr(Intro_type, animation) if isinstance(animation, str) else animation)
        # transition 应加在前一个视频片段上
        video_track = self.tracks["video"]
        if transition and video_track.segments:
            prev_seg = video_track.segments[-1]
            prev_seg.add_transition(getattr(Transition_type, transition) if isinstance(transition, str) else transition)
        self.script.add_segment(seg)
        self.segments.append(seg)
        return seg

    def add_gif(self, file_path, start, duration, **kwargs):
        seg = draft.Video_segment(
            draft.Video_material(file_path),
            trange(start, duration)
        )
        self.script.add_segment(seg)
        self.segments.append(seg)
        return seg

    def add_image(self, file_path, start, duration, **kwargs):
        seg = draft.Video_segment(
            draft.Video_material(file_path),
            trange(start, duration)
        )
        self.script.add_segment(seg)
        self.segments.append(seg)
        return seg

    def add_text(self, text, start, duration, font=None, style=None, bubble=None, effect=None, animation=None, **kwargs):
        clip_settings = kwargs.get("clip_settings")
        if clip_settings and isinstance(clip_settings, dict):
            clip_settings = draft.Clip_settings(**clip_settings)
        seg = draft.Text_segment(
            text,
            trange(start, duration),
            font=getattr(draft.Font_type, font) if font else None,
            style=draft.Text_style(**style) if style else None,
            clip_settings=clip_settings
        )
        if animation:
            seg.add_animation(getattr(draft.Text_outro, animation) if isinstance(animation, str) else animation, duration=kwargs.get("animation_duration"))
        if bubble:
            if isinstance(bubble, (list, tuple)) and len(bubble) == 2:
                seg.add_bubble(bubble[0], bubble[1])
            else:
                seg.add_bubble(bubble)
        if effect:
            seg.add_effect(effect)
        self.script.add_segment(seg)
        self.segments.append(seg)
        return seg

    def add_effect(self, effect_id, start, duration, **kwargs):
        # 自动将字符串 effect_id 转为枚举成员
        if isinstance(effect_id, str):
            effect_enum = getattr(Video_scene_effect_type, effect_id, None)
            if effect_enum is None:
                effect_enum = getattr(Video_character_effect_type, effect_id, None)
            if effect_enum is not None:
                effect_id = effect_enum
            else:
                raise ValueError(f"未知的 effect_id: {effect_id}")
        seg = draft.Effect_segment(
            effect_type=effect_id,
            target_timerange=trange(start, duration),
            **kwargs
        )
        self.script.add_segment(seg, track_name="effect")  # 指定特效轨道
        self.segments.append(seg)
        return seg

    def add_filter(self, filter_id, start, duration, **kwargs):
        # 自动将字符串 filter_id 转为枚举成员
        if isinstance(filter_id, str):
            filter_enum = getattr(Filter_type, filter_id, None)
            if filter_enum is not None:
                filter_id = filter_enum
            else:
                raise ValueError(f"未知的 filter_id: {filter_id}")
        seg = draft.Filter_segment(
            meta=filter_id,
            target_timerange=trange(start, duration),
            intensity=kwargs.get('intensity', 100.0) / 100.0  # 转换为0-1范围
        )
        self.script.add_segment(seg, track_name="filter")  # 使用滤镜轨道
        self.segments.append(seg)
        return seg

    def add_mosaic(self, region, start, duration, **kwargs):
        def _to_us(val):
            if isinstance(val, int):
                return val
            t = tim(val)
            return t.us if hasattr(t, 'us') else t
        params = [region[0], region[1], region[2], region[3]]
        # 获取 effect 轨道上所有已存在的 segment 的时间区间
        effect_track = self.tracks["effect"]
        existing_ranges = [(seg.target_timerange.start, seg.target_timerange.end) for seg in effect_track.segments]
        existing_ranges.sort()
        # 期望的起止时间（单位：微秒）
        start_us = _to_us(start)
        duration_us = _to_us(duration)
        end_us = start_us + duration_us
        # 查找下一个不重叠的区间
        idx = 0
        while idx < len(existing_ranges):
            exist_start, exist_end = existing_ranges[idx]
            if end_us <= exist_start:
                break  # 当前区间在已有区间前，无重叠
            if start_us >= exist_end:
                idx += 1
                continue  # 当前区间在已有区间后，继续
            # 有重叠，顺延到该区间后面
            start_us = exist_end
            end_us = start_us + duration_us
            idx += 1
        # 可选：如果顺延后超出5分钟（或自定义最大时长），则丢弃
        max_end_us = 5 * 60 * 1000000  # 5分钟
        if end_us > max_end_us:
            print(f"马赛克片段自动顺延后超出最大时长，已丢弃: start={start_us}, duration={duration_us}")
            return None
        # 构造新的 timerange
        from pyJianYingDraft import Timerange
        seg = draft.Effect_segment(
            effect_type=Video_scene_effect_type.马赛克,
            target_timerange=Timerange(start_us, end_us),
            params=params
        )
        self.script.add_segment(seg, track_name="effect")
        self.segments.append(seg)
        return seg

    def add_segment(self, seg):
        self.script.add_segment(seg)
        self.segments.append(seg)

    def save(self):
        # 1. 保存 draft_content.json
        os.makedirs(self.draft_folder, exist_ok=True)
        content_path = os.path.join(self.draft_folder, "draft_content.json")
        self.script.dump(content_path)
        print(f"已保存草稿内容到: {content_path}")

        # 2. 自动生成/更新 meta 文件
        meta_candidates = [
            os.path.join(self.draft_folder, "draft_meta_info.json"),
            os.path.join(self.draft_folder, "draft_meta.json")
        ]
        meta_file = None
        for candidate in meta_candidates:
            if os.path.exists(candidate):
                meta_file = candidate
                break
        if meta_file:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
            meta["draft_name"] = self.draft_name
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            print(f"已更新元数据文件: {meta_file}")
        else:
            print("警告：未找到元数据文件，草稿名未自动写入。")

    # 可扩展更多方法，如 add_track、add_transition_to_last、add_custom_segment 等 