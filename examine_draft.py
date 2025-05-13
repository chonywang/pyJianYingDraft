import os
import json
import shutil
import datetime

def find_drafts(drafts_root):
    """查找并列出剪映草稿文件夹中的所有草稿"""
    drafts = []
    if not os.path.exists(drafts_root):
        print(f"草稿文件夹不存在: {drafts_root}")
        return drafts
    
    for folder in os.listdir(drafts_root):
        folder_path = os.path.join(drafts_root, folder)
        if not os.path.isdir(folder_path):
            continue
        
        # 检查是否包含草稿元数据文件
        meta_file = os.path.join(folder_path, "draft_meta.json")
        if not os.path.exists(meta_file):
            meta_file = os.path.join(folder_path, "draft_meta_info.json")
            if not os.path.exists(meta_file):
                continue
        
        # 检查是否包含草稿内容文件
        content_file = os.path.join(folder_path, "draft_content.json")
        if not os.path.exists(content_file):
            continue
        
        # 读取元数据以获取草稿名称
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                draft_name = meta.get('draft_name', folder)
                drafts.append({
                    'name': draft_name,
                    'folder': folder,
                    'path': folder_path,
                    'meta_file': meta_file,
                    'content_file': content_file
                })
        except Exception as e:
            print(f"读取草稿元数据失败: {folder_path}, 错误: {str(e)}")
    
    return drafts

def extract_version_info(draft_path):
    """从草稿中提取版本信息"""
    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        return None
    
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
            version_info = {
                'version': content.get('version'),
                'new_version': content.get('new_version'),
                'platform': content.get('platform', {}),
                'last_modified_platform': content.get('last_modified_platform', {})
            }
            return version_info
    except Exception as e:
        print(f"读取草稿内容失败: {draft_path}, 错误: {str(e)}")
        return None

def extract_minimal_template(draft_path, output_folder):
    """提取草稿的关键部分，创建最小化模板"""
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    
    # 复制关键文件
    for filename in ["draft_content.json", "draft_meta.json", "draft_meta_info.json"]:
        src_file = os.path.join(draft_path, filename)
        if os.path.exists(src_file):
            dst_file = os.path.join(output_folder, filename)
            shutil.copy2(src_file, dst_file)
            print(f"已复制: {filename}")
    
    # 读取并简化 draft_content.json
    content_file = os.path.join(output_folder, "draft_content.json")
    if os.path.exists(content_file):
        try:
            with open(content_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # 清空轨道和素材，保留结构
            if 'tracks' in content:
                content['tracks'] = []
            
            if 'materials' in content:
                for key in content['materials']:
                    content['materials'][key] = []
            
            # 重置其他可能影响兼容性的字段
            content['duration'] = 0
            if 'keyframes' in content:
                for key in content['keyframes']:
                    content['keyframes'][key] = []
            
            # 保存简化后的内容
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            print(f"已简化 draft_content.json")
        except Exception as e:
            print(f"处理 draft_content.json 失败: {str(e)}")
    
    print(f"最小化模板已创建: {output_folder}")
    return output_folder

def analyze_draft(draft_path):
    """分析草稿结构并输出关键信息"""
    content_file = os.path.join(draft_path, "draft_content.json")
    if not os.path.exists(content_file):
        print(f"草稿内容文件不存在: {content_file}")
        return
    
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        # 提取关键版本信息
        version_info = {
            'version': content.get('version'),
            'new_version': content.get('new_version'),
            'platform': content.get('platform', {}),
            'last_modified_platform': content.get('last_modified_platform', {})
        }
        
        # 输出分析结果
        print("\n===== 草稿版本信息 =====")
        print(f"版本号: {version_info['version']}")
        print(f"新版本号: {version_info['new_version']}")
        platform = version_info['platform']
        if platform:
            print(f"平台: {platform.get('os', 'unknown')} {platform.get('os_version', 'unknown')}")
            print(f"应用版本: {platform.get('app_version', 'unknown')}")
            print(f"应用ID: {platform.get('app_id', 'unknown')}")
        
        # 输出结构信息
        print("\n===== 草稿结构信息 =====")
        print(f"轨道数量: {len(content.get('tracks', []))}")
        materials = content.get('materials', {})
        print(f"素材类型: {', '.join(materials.keys())}")
        
        # 输出关键字段的存在情况
        print("\n===== 关键字段检查 =====")
        important_fields = [
            'canvas_config', 'id', 'config', 'duration', 'fps', 
            'keyframes', 'materials', 'tracks'
        ]
        for field in important_fields:
            print(f"{field}: {'存在' if field in content else '不存在'}")
        
        # 保存分析报告
        report_path = os.path.join(os.path.dirname(draft_path), f"draft_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                'version_info': version_info,
                'structure': {
                    'has_tracks': 'tracks' in content,
                    'tracks_count': len(content.get('tracks', [])),
                    'material_types': list(materials.keys()),
                    'fields': {field: field in content for field in important_fields}
                }
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n分析报告已保存: {report_path}")
        
    except Exception as e:
        print(f"分析草稿失败: {str(e)}")

def main():
    # 剪映草稿文件夹路径
    drafts_root = "/Users/danielwang/Documents/jianyan/JianyingPro Drafts"
    
    # 查找所有草稿
    drafts = find_drafts(drafts_root)
    
    if not drafts:
        print("未找到任何草稿")
        return
    
    # 显示找到的草稿
    print(f"找到 {len(drafts)} 个草稿:")
    for i, draft in enumerate(drafts):
        version_info = extract_version_info(draft['path'])
        version_str = "未知版本"
        if version_info:
            platform = version_info.get('platform', {})
            version_str = f"v{version_info.get('new_version', '?')} ({platform.get('app_version', '?')})"
        
        print(f"{i + 1}. {draft['name']} - {version_str}")
    
    # 让用户选择要分析的草稿
    choice = input("\n请选择要分析的草稿编号 (1-{}): ".format(len(drafts)))
    try:
        index = int(choice) - 1
        if 0 <= index < len(drafts):
            selected_draft = drafts[index]
            print(f"\n分析草稿: {selected_draft['name']}")
            
            # 分析草稿
            analyze_draft(selected_draft['path'])
            
            # 创建最小化模板
            minimal_template_path = os.path.join(drafts_root, f"MinimalTemplate_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
            extract_minimal_template(selected_draft['path'], minimal_template_path)
        else:
            print("无效的选择")
    except ValueError:
        print("请输入有效的编号")

if __name__ == "__main__":
    main() 