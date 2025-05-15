import json
import os
import subprocess
from typing import Dict, List, Optional, Tuple
import shutil
import requests
from urllib.parse import urlparse
import time
import numpy as np
from PIL import Image
import ffmpeg
import hashlib

class DraftProcessor:
    def __init__(self, draft_path: str):
        """
        初始化草稿处理器
        :param draft_path: 剪映草稿目录路径
        """
        self.draft_path = draft_path
        self.draft_content = None
        self.temp_dir = None
        self.downloaded_dir = None
        self.materials = {}
        self.load_draft()

    def load_draft(self):
        """加载草稿文件"""
        draft_content_path = os.path.join(self.draft_path, "draft_content.json")
        if not os.path.exists(draft_content_path):
            draft_content_path = "sample_config.json"  # 尝试使用示例配置
            
        if not os.path.exists(draft_content_path):
            raise FileNotFoundError(f"找不到草稿文件: {draft_content_path}")

        with open(draft_content_path, "r", encoding="utf-8") as f:
            self.draft_content = json.load(f)

    def download_file(self, url: str, output_path: str) -> str:
        """下载文件到指定路径"""
        if os.path.exists(output_path):
            print(f"文件已存在，验证文件完整性: {output_path}")
            # Verify file is valid
            try:
                if output_path.endswith(('.mp4', '.mov', '.video')):
                    # For video files, check duration and size
                    probe = subprocess.run([
                        "ffprobe",
                        "-v", "error",
                        "-show_entries", "format=duration,size",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        output_path
                    ], capture_output=True, text=True, check=True)
                    try:
                        duration, size = probe.stdout.strip().split('\n')
                        duration = float(duration)
                        size = int(size)
                        if duration < 0.1 or size < 1000:  # Too short or too small
                            print(f"文件无效（时长太短或文件太小），重新下载: {output_path}")
                            os.remove(output_path)
                        else:
                            return output_path
                    except ValueError:
                        os.remove(output_path)
                elif output_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    img = Image.open(output_path)
                    img.verify()
                    return output_path
            except Exception as e:
                print(f"文件验证失败，重新下载: {str(e)}")
                if os.path.exists(output_path):
                    os.remove(output_path)
            
        print(f"开始下载: {url}")
        print(f"保存到: {output_path}")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use a session to handle redirects
                session = requests.Session()
                response = session.get(url, stream=True, allow_redirects=True, timeout=30)
                response.raise_for_status()
                
                # Get the final URL after redirects
                final_url = response.url
                print(f"最终URL: {final_url}")
                
                # Check content type and size
                content_type = response.headers.get('content-type', '').lower()
                content_length = int(response.headers.get('content-length', 0))
                
                if content_length < 1000:  # Less than 1KB
                    raise ValueError(f"File too small: {content_length} bytes")
                
                if 'image' in content_type:
                    # If it's an image but has a video extension, change it to .png
                    if output_path.endswith(('.mp4', '.mov', '.video')):
                        output_path = os.path.splitext(output_path)[0] + '.png'
                
                # Create directory (if it doesn't exist)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Download file with progress
                total_size = 0
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total_size += len(chunk)
                            print(f"已下载: {total_size/1024/1024:.2f}MB", end='\r')
                print(f"\n下载完成: {output_path}")
                
                # Verify downloaded file
                if output_path.endswith(('.mp4', '.mov', '.video')):
                    probe = subprocess.run([
                        "ffprobe",
                        "-v", "error",
                        "-show_entries", "format=duration,size",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        output_path
                    ], capture_output=True, text=True, check=True)
                    try:
                        duration, size = probe.stdout.strip().split('\n')
                        duration = float(duration)
                        size = int(size)
                        if duration < 0.1 or size < 1000:
                            raise ValueError(f"Invalid video file: duration={duration}s, size={size}bytes")
                    except ValueError as e:
                        raise ValueError(f"Failed to verify video file: {str(e)}")
                elif output_path.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    img = Image.open(output_path)
                    img.verify()
                
                return output_path
                
            except Exception as e:
                print(f"下载失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                retry_count += 1
                if retry_count < max_retries:
                    print(f"等待 {retry_count * 2} 秒后重试...")
                    time.sleep(retry_count * 2)
                else:
                    raise
    
    def get_downloaded_path(self, url: str, file_type: str) -> str:
        """获取下载文件的本地路径"""
        if not self.downloaded_dir:
            self.downloaded_dir = os.path.join(self.draft_path, "downloaded_media")
            os.makedirs(self.downloaded_dir, exist_ok=True)
        
        # 使用URL的hash作为文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # 从URL中获取原始文件扩展名
        original_ext = os.path.splitext(urlparse(url).path)[1].lower()
        if not original_ext:
            original_ext = f".{file_type}"  # 使用默认扩展名
        
        return os.path.join(self.downloaded_dir, f"{url_hash}{original_ext}")

    def get_effect_filters(self, effect_id: str) -> List[str]:
        """Return FFmpeg filters for the given effect ID"""
        # Map effect IDs directly to filters
        effects = {
            "负片频闪": [
                "negate",  # 负片效果
                "hue=h=t*90:s=1",  # 颜色变化
                "eq=brightness=0.1:saturation=1.5"  # 亮度和饱和度调整
            ],
            "故障": [
                "rgbashift=rh=10:bv=-10",  # RGB通道偏移
                "eq=contrast=1.5:brightness=0.1",  # 对比度和亮度调整
                "hue=h=t*60"  # 色相变化
            ],
            "金粉闪闪": [
                "colorbalance=rs=0.3:gs=0.3:bs=0.3",  # 颜色平衡
                "eq=brightness=1.2:contrast=1.3",  # 亮度和对比度增强
                "hue=h=t*30:s=1.5"  # 色相和饱和度变化
            ]
        }
        
        return effects.get(effect_id, [])

    def get_transition_filters(self, transition_id: str) -> List[str]:
        """Return FFmpeg filters for the given transition name"""
        # Map transition names directly to filters
        transitions = {
            "上移": [
                "fade=t=in:st=0:d=1"  # 简单淡入效果替代上移
            ],
            "闪白": [
                "fade=t=in:st=0:d=0.3:c=white",  # 白色淡入
                "fade=t=out:st=0.3:d=0.2:c=white"  # 白色淡出
            ],
            "叠化": [
                "fade=t=in:st=0:d=0.5",  # 淡入
                "fade=t=out:st=4.5:d=0.5"  # 淡出
            ]
        }
        
        return transitions.get(transition_id, [])

    def create_subtitle_track(self, text_track: List[Dict], video_start: float, video_duration: float, track_index: int) -> List[str]:
        """Generate subtitle filters for an entire track"""
        subtitle_filters = []
        
        for text in text_track:
            content = text.get("content", "")
            if not content:
                continue
                
            # Clean text content
            content = self._clean_text_content(content)
            
            # Get text style
            style = text.get("style", {})
            fontsize = style.get("font_size", 36)
            font_color = style.get("color", "white")
            font_path = style.get("font_path", "/System/Library/Fonts/PingFang.ttc")
            
            # Position and transform
            transform = text.get("transform", {})
            position = self._calculate_text_position(transform, track_index)
            
            # Timing
            timing = self._calculate_text_timing(text, video_start, video_duration)
            if not timing:
                continue
                
            start_time, duration = timing
            
            # Generate drawtext filter with enhanced styling
            filter_str = (
                f"drawtext=text='{content}'"
                f":fontfile='{font_path}'"
                f":fontcolor={font_color}"
                f":fontsize={fontsize}"
                f":x={position['x']}"
                f":y={position['y']}"
                f":alpha={style.get('opacity', '1')}"
                f":enable='between(t,{start_time},{start_time+duration})'"
            )
            
            # Add effects if specified
            if "effects" in style:
                filter_str = self._add_text_effects(filter_str, style["effects"])
            
            subtitle_filters.append(filter_str)
        
        return subtitle_filters

    def _clean_text_content(self, content: str) -> str:
        """Clean text content by removing markup and escaping special characters"""
        replacements = [
            ("<size=15>", ""), ("</size>", ""),
            ("<color=(1,1,1,1)>", ""), ("</color>", ""),
            ("<font id=\"\" path=\"\">", ""), ("</font>", ""),
            ("[", ""), ("]", ""),
            ("'", "\\'")
        ]
        for old, new in replacements:
            content = content.replace(old, new)
        return content

    def _calculate_text_position(self, transform: Dict, track_index: int) -> Dict[str, str]:
        """Calculate text position considering track index for vertical stacking"""
        base_y_offset = track_index * 50  # Vertical spacing between tracks
        x = f"(w-text_w)/2+{transform.get('x', 0)*100}"
        y = f"h*0.8+{base_y_offset}+{transform.get('y', 0)*100}"
        return {"x": x, "y": y}

    def _calculate_text_timing(self, text: Dict, video_start: float, video_duration: float) -> Optional[Tuple[float, float]]:
        """Calculate timing for text display"""
        target_timerange = text.get("target_timerange", {})
        start_time = target_timerange.get("start", 0) / 1000000
        duration = target_timerange.get("duration", 0) / 1000000
        
        if start_time >= video_start and start_time + duration <= video_start + video_duration:
            adjusted_start = start_time - video_start
            return (adjusted_start, duration)
        return None

    def _add_text_effects(self, filter_str: str, effects: List[Dict]) -> str:
        """Add text effects to the filter string"""
        for effect in effects:
            effect_type = effect.get("type")
            if effect_type == "fade":
                fade_in = effect.get("fade_in", 0)
                fade_out = effect.get("fade_out", 0)
                filter_str += f":alpha='if(lt(t,{fade_in}),t/{fade_in},if(gt(t,{fade_out}),(1-t)/{fade_out},1))'"
            elif effect_type == "scroll":
                speed = effect.get("speed", 100)
                filter_str += f":x='if(lt(t,1),0,mod(t*{speed},w))'"
        return filter_str

    def process_image_track(self, track: Dict, video_start: float, video_duration: float, track_index: int) -> List[str]:
        """Process an image track and generate overlay filters"""
        image_filters = []
        
        for image in track.get("segments", []):
            # Get image path and verify existence
            image_path = self._get_image_path(image)
            if not image_path:
                continue
            
            # Calculate timing
            timing = self._calculate_timing(image, video_start, video_duration)
            if not timing:
                continue
            
            start_time, duration = timing
            
            # Get transform parameters
            transform = image.get("transform", {})
            scale = transform.get("scale", 1.0)
            rotation = transform.get("rotation", 0)
            opacity = transform.get("opacity", 1.0)
            position = transform.get("position", {"x": 0, "y": 0})
            
            # Generate filter string for this image
            filter_str = (
                f"movie='{image_path}'"
                f"[img{track_index}];"
                f"[img{track_index}]"
                f"scale=iw*{scale}:ih*{scale}"
                f",rotate={rotation}*PI/180:c=none:ow=rotw({rotation}*PI/180):oh=roth({rotation}*PI/180)"
                f"[rot{track_index}];"
                f"[rot{track_index}]"
                f"format=rgba,colorchannelmixer=aa={opacity}"
                f"[fmt{track_index}];"
                f"[prev][fmt{track_index}]"
                f"overlay=x={position['x']}:y={position['y']}"
                f":enable='between(t,{start_time},{start_time+duration})'"
            )
            
            image_filters.append(filter_str)
        
        return image_filters

    def _get_image_path(self, image: Dict) -> Optional[str]:
        """Get and validate image path"""
        if "path" not in image:
            return None
            
        image_path = image["path"].replace(
            "##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##",
            self.draft_path
        )
        
        if not os.path.exists(image_path):
            # Try to download if it's a URL
            if image_path.startswith(("http://", "https://")):
                try:
                    local_path = os.path.join(self.temp_dir, f"image_{hash(image_path)}.png")
                    self.download_file(image_path, local_path)
                    return local_path
                except Exception:
                    return None
            return None
            
        return image_path

    def process_video_segment(self, video: Dict, segment_index: int) -> str:
        """Process a single video segment"""
        # Get video/image path
        source_path = video.get("file_path")
        if not source_path:
            raise ValueError(f"No source path found for segment {segment_index}")
        
        # If it's a URL, download it first
        if source_path.startswith(("http://", "https://")):
            try:
                # Get local path and download
                local_path = self.get_downloaded_path(source_path, "video")
                source_path = self.download_file(source_path, local_path)
                print(f"使用下载的文件: {source_path}")
            except Exception as e:
                raise ValueError(f"Failed to download source for segment {segment_index}: {str(e)}")
        
        # Get timing information from configuration
        duration = self._time_to_microseconds(video["duration"]) / 1000000  # Convert to seconds
        start_time = self._time_to_microseconds(video["start"]) / 1000000  # Convert to seconds
        
        # Output file path
        output_file = os.path.join(self.temp_dir, f"segment_{segment_index}.mov")
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-ss", str(start_time),
            "-t", str(duration),
            "-vf", "format=yuv420p,scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_file
        ]
        
        try:
            print(f"\n处理视频片段 {segment_index + 1}...")
            print(f"输入文件: {source_path}")
            print(f"输出文件: {output_file}")
            print(f"开始时间: {start_time}秒")
            print(f"持续时间: {duration}秒")
            print(f"FFmpeg命令: {' '.join(cmd)}\n")
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Verify the output file
            if os.path.exists(output_file):
                probe = subprocess.run([
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    output_file
                ], capture_output=True, text=True, check=True)
                output_duration = float(probe.stdout.strip())
                print(f"输出视频时长: {output_duration}秒")
                
                if abs(output_duration - duration) > 0.1:
                    raise ValueError(f"Output duration ({output_duration}s) does not match expected duration ({duration}s)")
            else:
                raise ValueError(f"Output file not found: {output_file}")
            
            return output_file
        except subprocess.CalledProcessError as e:
            print(f"Error processing video segment: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        except Exception as e:
            print(f"Error processing video segment: {str(e)}")
            raise

    def process_audio_segment(self, segment: Dict, segment_index: int) -> Tuple[str, float]:
        """Process a single audio segment"""
        # Get audio path
        audio_path = segment.get("url")
        if not audio_path:
            raise ValueError(f"No audio path found for segment {segment_index}")
        
        # If it's a URL, download it first
        if audio_path.startswith(("http://", "https://")):
            try:
                local_path = self.get_downloaded_path(audio_path, "audio")
                audio_path = self.download_file(audio_path, local_path)
                print(f"使用下载的音频: {audio_path}")
            except Exception as e:
                raise ValueError(f"Failed to download audio for segment {segment_index}: {str(e)}")
        
        # Get timing information from configuration
        source_start = self._time_to_microseconds(segment.get("start", "0s")) / 1000000  # Convert to seconds
        target_start = self._time_to_microseconds(segment.get("target_start", "0s")) / 1000000  # Convert to seconds
        
        # Get audio duration from source file
        try:
            probe = subprocess.run([
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ], capture_output=True, text=True, check=True)
            source_duration = float(probe.stdout.strip())
            duration = source_duration  # Use full duration
        except Exception as e:
            print(f"Warning: Could not get audio duration: {str(e)}")
            duration = 5.0  # Default duration as fallback
        
        # Output file path
        output_file = os.path.join(self.temp_dir, f"audio_{segment_index}.aac")
        
        # Use FFmpeg to process audio - simplified version
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            "-filter:a", f"volume={segment.get('volume', 1.0)}",
            output_file
        ]
        
        try:
            print(f"处理音频片段 {segment_index}...")
            print(f"输入文件: {audio_path}")
            print(f"输出文件: {output_file}")
            print(f"源文件开始时间: {source_start}秒")
            print(f"目标开始时间: {target_start}秒")
            print(f"持续时间: {duration}秒")
            
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Verify the output file exists and has content
            if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
                raise ValueError(f"Failed to generate audio file: {output_file}")
                
            return output_file, target_start
        except subprocess.CalledProcessError as e:
            print(f"音频处理错误: {e.stderr.decode() if e.stderr else str(e)}")
            raise

    def generate_video(self, output_path: str):
        """Generate the final video"""
        if not os.path.exists(output_path):
            os.makedirs(output_path)
        
        self.temp_dir = os.path.join(output_path, "temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        
        try:
            # Process video segments
            video_segments = []
            if "videos" in self.draft_content:
                for i, video in enumerate(self.draft_content["videos"]):
                    print(f"Processing video segment {i+1}/{len(self.draft_content['videos'])}...")
                    video_file = self.process_video_segment(video, i)
                    target_start = self._time_to_microseconds(video.get("target_start", "0s")) / 1000000
                    video_segments.append({
                        "file": video_file,
                        "target_start": target_start,
                        "duration": self._time_to_microseconds(video["duration"]) / 1000000
                    })
            
            # Sort segments by target_start time
            video_segments.sort(key=lambda x: x["target_start"])
            
            # Calculate total duration
            total_duration = max(
                segment["target_start"] + segment["duration"]
                for segment in video_segments
            ) if video_segments else 0
            
            # Process audio segments
            audio_segments = []
            if "audio" in self.draft_content:
                for i, audio in enumerate(self.draft_content["audio"]):
                    print(f"Processing audio segment {i+1}/{len(self.draft_content['audio'])}...")
                    try:
                        audio_file, target_start = self.process_audio_segment(audio, i)
                        audio_segments.append((audio_file, target_start))
                    except Exception as e:
                        print(f"Warning: Failed to process audio segment {i+1}: {str(e)}")
                        print("Continuing without this audio segment...")
                        continue
            
            # Generate ASS subtitle file
            subtitle_file = None
            if "text_tracks" in self.draft_content:
                subtitle_file = os.path.join(output_path, "subtitles.ass")
                self.generate_ass_subtitles(subtitle_file)
            
            # Merge all segments
            if video_segments:
                # Create complex filter for positioning segments
                filter_complex = []
                input_args = []
                
                # Add input arguments and prepare filter inputs
                for i, segment in enumerate(video_segments):
                    input_args.extend(["-i", segment["file"]])
                    # Add trim and setpts filters with SAR correction
                    filter_complex.append(
                        f"[{i}:v]format=yuv420p,scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2,setpts=PTS-STARTPTS+{segment['target_start']}/TB[v{i}];"
                    )
                
                # Create base video with proper duration
                filter_complex.append(f"color=c=black:s=854x480:d={total_duration}[base];")
                
                # Add videos on top of base with proper timing
                current = "base"
                for i in range(len(video_segments)):
                    next_output = "outv" if i == len(video_segments) - 1 else f"tmp{i}"
                    filter_complex.append(
                        f"[{current}][v{i}]overlay=shortest=0:eof_action=pass:repeatlast=1[{next_output}];"
                    )
                    current = next_output
                
                # Build the complete filter string
                filter_str = "".join(filter_complex)
                
                # Merge video segments
                output_video = os.path.join(output_path, "output.mov")
                cmd = ["ffmpeg", "-y"]
                cmd.extend(input_args)
                cmd.extend([
                    "-filter_complex", filter_str,
                    "-map", "[outv]",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    output_video
                ])
                print("Merging video segments...")
                print("FFmpeg command:", " ".join(cmd))
                subprocess.run(cmd, check=True)
                
                # Add subtitles and audio
                final_output = os.path.join(output_path, "final_output.mov")
                cmd = ["ffmpeg", "-y", "-i", output_video]
                
                # Add audio inputs if present
                for audio_file, _ in audio_segments:
                    cmd.extend(["-i", audio_file])
                
                # Add subtitle file if present
                if subtitle_file:
                    cmd.extend(["-vf", f"ass={subtitle_file}"])
                
                # Add audio mixing if we have audio segments
                if audio_segments:
                    # Add video input first
                    cmd = ["ffmpeg", "-y", "-i", output_video]
                    
                    # Add audio inputs
                    for audio_file, _ in audio_segments:
                        cmd.extend(["-i", audio_file])
                    
                    # Add subtitle filter
                    filter_complex = []
                    if subtitle_file:
                        filter_complex.append(f"[0:v]ass={subtitle_file}[outv]")
                    else:
                        filter_complex.append("[0:v]copy[outv]")
                    
                    # Add audio filter complex
                    audio_parts = []
                    for i, (_, target_start) in enumerate(audio_segments):
                        # Convert target start time to milliseconds and create silent padding
                        delay_ms = int(target_start * 1000)
                        # Create a delayed audio stream with apad to ensure proper length
                        audio_parts.append(f"[{i+1}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,apad,adelay={delay_ms}|{delay_ms}[adelayed{i}]")
                    
                    # Add all audio parts to filter complex
                    filter_complex.extend(audio_parts)
                    
                    # Mix all delayed audio streams
                    if len(audio_segments) > 1:
                        # Create the mix command with proper volume normalization
                        mix_inputs = "".join(f"[adelayed{i}]" for i in range(len(audio_segments)))
                        filter_complex.append(f"{mix_inputs}amix=inputs={len(audio_segments)}:duration=longest:normalize=0[outa]")
                    else:
                        # If only one audio stream, just use it directly
                        filter_complex.append("[adelayed0]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[outa]")
                    
                    # Join all filter complex parts
                    cmd.extend([
                        "-filter_complex", ";".join(filter_complex),
                        "-map", "[outv]",
                        "-map", "[outa]",
                        "-c:v", "libx264",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-shortest",
                        "-movflags", "+faststart",
                        final_output
                    ])
                else:
                    # No audio segments, just copy video and add subtitles if present
                    if subtitle_file:
                        cmd.extend([
                            "-vf", f"ass={subtitle_file}",
                            "-c:v", "libx264",
                            "-movflags", "+faststart",
                            final_output
                        ])
                    else:
                        cmd.extend([
                            "-c:v", "copy",
                            "-movflags", "+faststart",
                            final_output
                        ])
                
                print("Adding audio and subtitles...")
                print("FFmpeg command:", " ".join(cmd))
                subprocess.run(cmd, check=True)
                
                # Clean up intermediate files
                os.remove(output_video)
                for audio_file, _ in audio_segments:
                    if os.path.exists(audio_file):
                        os.remove(audio_file)
                
                print(f"Final output saved to: {final_output}")
            else:
                print("No video segments found in the draft.")
        
        except Exception as e:
            print(f"Error generating video: {str(e)}")
            raise
        finally:
            # Clean up temporary directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)

    def generate_ass_subtitles(self, output_file: str):
        """Generate ASS subtitle file"""
        ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 854
PlayResY: 480
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1
Style: Main,STHeiti,40,&H00FFFFFF,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,100,100,0,0,1,3,1,2,10,10,10,1
Style: English,Arial,32,&H00FFFFFF,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,100,100,0,0,1,3,1,2,10,10,10,1
Style: Note,STHeiti,28,&H00FFFFFF,&H000000FF,&H00000000,&HC0000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(ass_header)
            
            if "text_tracks" in self.draft_content:
                for track in self.draft_content["text_tracks"]:
                    style = "Main" if track["name"] == "主字幕" else "English" if track["name"] == "英文字幕" else "Note"
                    
                    for text in track["texts"]:
                        start_time = self._time_to_microseconds(text["start"]) / 1000000
                        duration = self._time_to_microseconds(text["duration"]) / 1000000
                        end_time = start_time + duration
                        
                        # Convert times to ASS format (h:mm:ss.cc)
                        start_str = self._seconds_to_ass_time(start_time)
                        end_str = self._seconds_to_ass_time(end_time)
                        
                        # Get text style
                        text_style = text.get("style", {})
                        color = text_style.get("color", [1.0, 1.0, 1.0])
                        color_hex = f"&H00{int(color[2]*255):02X}{int(color[1]*255):02X}{int(color[0]*255):02X}"
                        
                        # Get position
                        position = text.get("position", {"x": 0.5, "y": 0.907})
                        # Adjust y position based on style
                        if style == "Main":
                            y_pos = 435  # 中文字幕位置
                        elif style == "English":
                            y_pos = 380  # 英文字幕位置
                        else:
                            y_pos = 330  # 注释位置
                        
                        # Add text effects
                        effects = []
                        effects.append(f"\\pos({int(854*position['x'])},{y_pos})")  # 位置
                        effects.append("\\blur0.6")  # 轻微模糊，提高可读性
                        effects.append(f"\\c{color_hex}")  # 颜色
                        effects.append("\\3c&H000000&")  # 黑色边框
                        effects.append("\\bord3")  # 边框宽度
                        
                        # Clean and escape text content
                        content = text['text']
                        content = content.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
                        
                        # Write ASS event line with effects
                        f.write(f"Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,{{{' '.join(effects)}}}{content}\n")

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convert seconds to ASS time format (h:mm:ss.cc)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        centiseconds = int((seconds % 1) * 100)
        seconds = int(seconds)
        return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"

    def _time_to_microseconds(self, time_str: str) -> int:
        """Convert time string (e.g., '5s', '1.5s') to microseconds"""
        if isinstance(time_str, (int, float)):
            return int(time_str * 1000000)
        time_str = time_str.lower().strip()
        if time_str.endswith('s'):
            seconds = float(time_str[:-1])
            return int(seconds * 1000000)
        return int(time_str)

if __name__ == "__main__":
    # Use sample configuration and local output directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(current_dir, "output")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    print("Starting video processing...")
    print(f"Output will be saved to: {output_path}")
    
    processor = DraftProcessor(".")  # Use current directory for sample config
    processor.generate_video(output_path) 