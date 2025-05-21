"""
剪映模板配置管理器HTTP API使用示例

这个示例展示了如何通过HTTP请求逐步构建草稿。
"""

import requests
import json

def main():
    """主函数，展示HTTP API的使用"""
    # API基础URL
    base_url = "http://localhost:8001"
    
    # 1. 创建新草稿
    create_draft_response = requests.post(
        f"{base_url}/drafts",
        json={
            "draft_name": "my_awesome_video",
            "width": 1080,
            "height": 1920
        }
    )
    draft_id = create_draft_response.json()["draft_id"]
    print(f"创建草稿成功，ID: {draft_id}")
    
    # 2. 添加视频轨道
    video_response = requests.post(
        f"{base_url}/drafts/{draft_id}/videos",
        json={
            "file_path": "https://example.com/video1.mp4",
            "start": "0s",
            "duration": "5s",
            "target_start": "0s",
            "transition": "叠化",
            "effects": [
                {
                    "effect_id": "金粉闪闪",
                    "start": "0s",
                    "duration": "5s"
                }
            ]
        }
    )
    print("添加视频轨道成功")
    
    # 3. 添加音频轨道
    audio_response = requests.post(
        f"{base_url}/drafts/{draft_id}/audio",
        json={
            "url": "https://example.com/audio1.mp3",
            "enabled": True,
            "volume": 1.0,
            "start": "0s",
            "target_start": "0s"
        }
    )
    print("添加音频轨道成功")
    
    # 4. 添加文本轨道
    text_response = requests.post(
        f"{base_url}/drafts/{draft_id}/text",
        json={
            "track_name": "主字幕",
            "text": "这是一个示例字幕",
            "start": "0s",
            "duration": "5s",
            "font": "后现代体",
            "style": {
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
            },
            "position": {
                "x": 0.5,
                "y": 0.907
            },
            "intro_animation": "随机打字机",
            "outro_animation": "滑动下落",
            "linebreak": {
                "mode": "manual",
                "zh_length": 8,
                "en_words": 3
            }
        }
    )
    print("添加文本轨道成功")
    
    # 5. 获取草稿信息
    draft_info = requests.get(f"{base_url}/drafts/{draft_id}").json()
    print("\n草稿信息:")
    print(json.dumps(draft_info, indent=2, ensure_ascii=False))
    
    # 6. 保存草稿
    save_response = requests.post(f"{base_url}/drafts/{draft_id}/save")
    print(f"\n保存草稿成功: {save_response.json()['output_path']}")

if __name__ == "__main__":
    main() 