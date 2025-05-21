"""
使用template_config.json中的内容测试剪映模板配置管理器HTTP API

这个示例读取现有的template_config.json文件，然后通过HTTP API逐步构建草稿。
"""

import requests
import json
import os

def main():
    """主函数，展示如何使用template_config.json中的内容进行测试"""
    # 读取template_config.json
    with open('template_config.json', 'r', encoding='utf-8') as f:
        template_config = json.load(f)
    
    # API基础URL
    base_url = "http://localhost:8001"
    
    # 1. 创建新草稿
    create_draft_response = requests.post(
        f"{base_url}/drafts",
        json={
            "draft_name": template_config["draft_name"],
            "width": template_config["resolution"]["width"],
            "height": template_config["resolution"]["height"]
        }
    )
    draft_id = create_draft_response.json()["draft_id"]
    print(f"创建草稿成功，ID: {draft_id}")
    
    # 2. 添加多个视频轨道
    for video in template_config["videos"]:
        video_response = requests.post(
            f"{base_url}/drafts/{draft_id}/videos",
            json=video
        )
        print(f"添加视频轨道成功: {video['file_path']}")
    
    # 3. 添加多个音频轨道
    for audio in template_config["audio"]:
        audio_response = requests.post(
            f"{base_url}/drafts/{draft_id}/audio",
            json=audio
        )
        print(f"添加音频轨道成功: {audio['url']}")
    
    # 4. 添加多个文本轨道
    for text_track in template_config["text_tracks"]:
        # 为每个轨道添加多个文本
        for text in text_track["texts"]:
            # 添加轨道名称到文本数据
            text_data = text.copy()
            text_data["track_name"] = text_track["name"]
            
            text_response = requests.post(
                f"{base_url}/drafts/{draft_id}/text",
                json=text_data
            )
            print(f"添加文本成功: {text_track['name']} - \"{text['text'][:20]}...\"")
    
    # 5. 获取草稿信息
    draft_info = requests.get(f"{base_url}/drafts/{draft_id}").json()
    print("\n草稿信息:")
    print(f"总时长: {draft_info['timeline']['total_duration']}")
    print(f"视频轨道数: {len(draft_info['videos'])}")
    print(f"音频轨道数: {len(draft_info['audio'])}")
    print(f"文本轨道数: {len(draft_info['text_tracks'])}")
    
    # 6. 保存草稿
    save_response = requests.post(f"{base_url}/drafts/{draft_id}/save")
    print(f"\n保存草稿成功: {save_response.json()['output_path']}")
    
    # 7. 将完整草稿内容保存到文件
    output_file = f"draft_{draft_id}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(draft_info, f, indent=2, ensure_ascii=False)
    print(f"草稿详细内容已保存到: {output_file}")

if __name__ == "__main__":
    main() 