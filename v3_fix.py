import os
import json
import shutil
import datetime
import uuid
import random
import string

def generate_draft_id():
    """生成剪映草稿ID"""
    return str(uuid.uuid4()).upper().replace("-", "-")

def create_v3_compatible_draft(template_folder, media_path, output_folder, name="V3兼容草稿"):
    """创建一个与v3.1.0-beta7兼容的草稿"""
    # 生成带时间戳的草稿名称
    draft_name = f"{name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    new_draft_folder = os.path.join(output_folder, draft_name)
    
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
        # 更新 draft_content.json - 最关键的部分
        content_file = os.path.join(new_draft_folder, "draft_content.json")
        if os.path.exists(content_file):
            with open(content_file, "r", encoding="utf-8") as f:
                content = json.load(f)
            
            # 1. 设置v3.1.0-beta7兼容版本
            content["version"] = 360000
            content["new_version"] = "52.0.0"  # 从分析结果看到v3.1.0-beta7使用52.0.0
            
            # 2. 设置正确的平台信息
            platform_info = {
                "app_id": 3704,
                "app_version": "3.1.0-beta7",
                "os": "mac",
                "os_version": "15.4.1",
                "app_source": "lv",
                "device_id": "".join(random.choices(string.ascii_lowercase + string.digits, k=16)),
                "hard_disk_id": "".join(random.choices(string.ascii_lowercase + string.digits, k=16)),
                "mac_address": ":".join(["%02x" % random.randint(0, 255) for _ in range(6)])
            }
            content["platform"] = platform_info
            content["last_modified_platform"] = platform_info.copy()
            
            # 3. 设置草稿ID
            content["id"] = generate_draft_id()
            
            # 4. 确保基本字段存在
            if "keyframes" not in content:
                content["keyframes"] = {
                    "adjusts": [],
                    "audios": [],
                    "effects": [],
                    "filters": [],
                    "handwrites": [],
                    "stickers": [],
                    "texts": [],
                    "videos": []
                }
            
            # 5. 清空轨道，创建新轨道
            content["tracks"] = []
            
            # 添加轨道 - 根据分析v3.1.0-beta7的草稿包含3个轨道
            content["tracks"].append({
                "type": "video",
                "segments": []
            })
            content["tracks"].append({
                "type": "audio",
                "segments": []
            })
            content["tracks"].append({
                "type": "text",
                "segments": []
            })
            
            # 6. 清空素材列表，保留结构
            for key in content["materials"]:
                content["materials"][key] = []
            
            # 7. 如果提供了媒体文件，添加到草稿中
            if os.path.exists(media_path):
                # 复制媒体文件到草稿文件夹中的素材目录
                media_name = os.path.basename(media_path)
                material_dir = os.path.join(new_draft_folder, "material")
                os.makedirs(material_dir, exist_ok=True)
                local_media_path = os.path.join(material_dir, media_name)
                shutil.copy2(media_path, local_media_path)
                
                # 添加视频素材和片段
                material_id = str(uuid.uuid4()).upper().replace("-", "-")
                duration_us = 5000000  # 5秒
                
                # 添加视频素材
                content["materials"]["videos"].append({
                    "extra_info": {},
                    "filepath": local_media_path,
                    "id": material_id,
                    "metainfo": {
                        "duration": duration_us,
                        "height": 1080,
                        "width": 1920
                    },
                    "source": "local",
                    "type": "video"
                })
                
                # 添加视频片段到轨道
                for track in content["tracks"]:
                    if track["type"] == "video":
                        track["segments"].append({
                            "begin": 0,
                            "duration": duration_us,
                            "material_id": material_id,
                            "material_type": "videos",
                            "source_timerange": {
                                "duration": duration_us,
                                "start": 0
                            },
                            "speed": 1.0,
                            "volume": 1.0
                        })
                        break
                
                # 设置草稿时长
                content["duration"] = duration_us
            else:
                # 没有媒体文件，设置最小时长
                content["duration"] = 0
            
            # 保存更新的内容
            with open(content_file, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            print(f"已更新草稿内容: {content_file}")
        
        # 更新元数据文件
        meta_files = ["draft_meta.json", "draft_meta_info.json"]
        for meta_file in meta_files:
            meta_path = os.path.join(new_draft_folder, meta_file)
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                
                # 更新基本元数据
                meta["draft_name"] = draft_name
                meta["draft_fold_path"] = new_draft_folder
                meta["draft_root_path"] = output_folder
                current_timestamp = int(datetime.datetime.now().timestamp() * 1000000)
                meta["tm_draft_create"] = current_timestamp
                meta["tm_draft_modified"] = current_timestamp
                meta["tm_duration"] = content["duration"]
                
                # 设置v3.1.0-beta7兼容的版本信息
                meta["draft_new_version"] = "52.0.0"
                meta["draft_version"] = "52.0.0"
                
                # 保存更新的元数据
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                
                print(f"已更新元数据: {meta_path}")
        
        print(f"兼容v3.1.0-beta7的草稿已生成: {new_draft_folder}")
        return new_draft_folder
    
    except Exception as e:
        print(f"创建兼容草稿时出错: {str(e)}")
        if os.path.exists(new_draft_folder):
            shutil.rmtree(new_draft_folder)
        raise

def main():
    # 设置路径
    template_folder = "/Users/danielwang/Documents/jianyan/JianyingPro Drafts/MinimalTemplate_20250511_195017"
    output_folder = "/Users/danielwang/Documents/jianyan/JianyingPro Drafts"
    
    # 使用下载的示例媒体或指定一个本地文件
    media_path = os.path.expanduser("~/Downloads/sample.mp4")
    if not os.path.exists(media_path):
        print(f"未找到媒体文件: {media_path}")
        media_path = ""
    
    # 创建兼容草稿
    create_v3_compatible_draft(template_folder, media_path, output_folder)

if __name__ == "__main__":
    main() 