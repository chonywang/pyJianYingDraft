import os
import json
import shutil
import datetime
import uuid

def direct_copy_draft(source_folder, target_folder, draft_name=None):
    """
    直接复制一个已存在的草稿，不做任何内容修改，仅更新必要的元数据
    这种方法避免了任何格式转换导致的兼容性问题
    """
    # 确保源草稿存在
    if not os.path.exists(source_folder) or not os.path.isdir(source_folder):
        raise FileNotFoundError(f"源草稿不存在: {source_folder}")
    
    # 生成目标草稿名称
    if draft_name is None:
        draft_name = f"Copy_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 确保目标文件夹不存在
    new_folder = os.path.join(target_folder, draft_name)
    if os.path.exists(new_folder):
        raise FileExistsError(f"目标草稿已存在: {new_folder}")
    
    # 完整复制草稿文件夹
    print(f"复制草稿: {source_folder} -> {new_folder}")
    shutil.copytree(source_folder, new_folder)
    
    # 仅更新元数据文件中的名称和路径，保留所有其他数据完全不变
    meta_files = ["draft_meta.json", "draft_meta_info.json"]
    for meta_file in meta_files:
        meta_path = os.path.join(new_folder, meta_file)
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                
                # 只修改草稿名称和路径，保留所有其他字段
                meta["draft_name"] = draft_name
                meta["draft_fold_path"] = new_folder
                meta["draft_root_path"] = target_folder
                
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
                
                print(f"已更新元数据: {meta_path}")
            except Exception as e:
                print(f"更新元数据失败: {e}")
    
    # 复制是否成功
    if os.path.exists(os.path.join(new_folder, "draft_content.json")):
        print(f"草稿复制成功: {new_folder}")
        return new_folder
    else:
        print(f"草稿复制失败")
        return None

def find_working_drafts(drafts_root, search_term=None):
    """查找可以正常打开的草稿作为模板"""
    working_drafts = []
    
    for item in os.listdir(drafts_root):
        folder_path = os.path.join(drafts_root, item)
        if not os.path.isdir(folder_path):
            continue
        
        # 检查是否是有效的草稿
        content_path = os.path.join(folder_path, "draft_content.json")
        if not os.path.exists(content_path):
            continue
        
        # 如果有搜索词，检查名称是否匹配
        if search_term and search_term.lower() not in item.lower():
            continue
        
        # 读取元数据获取草稿名称
        meta_name = item
        for meta_file in ["draft_meta.json", "draft_meta_info.json"]:
            meta_path = os.path.join(folder_path, meta_file)
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        if "draft_name" in meta:
                            meta_name = meta["draft_name"]
                            break
                except:
                    pass
        
        # 添加到列表
        working_drafts.append({
            "name": meta_name,
            "folder": item,
            "path": folder_path
        })
    
    return working_drafts

def main():
    # 设置默认路径
    drafts_root = "/Users/danielwang/Documents/jianyan/JianyingPro Drafts"
    
    # 查找能正常打开的草稿
    print("查找可用草稿...")
    drafts = find_working_drafts(drafts_root)
    
    if not drafts:
        print("未找到任何草稿")
        return
    
    # 显示所有草稿
    print(f"\n找到 {len(drafts)} 个草稿:")
    for i, draft in enumerate(drafts):
        print(f"{i+1}. {draft['name']} (文件夹: {draft['folder']})")
    
    # 让用户选择一个能正常打开的草稿作为源
    choice = input("\n请选择要复制的草稿编号 (1-{}): ".format(len(drafts)))
    try:
        index = int(choice) - 1
        if 0 <= index < len(drafts):
            source_draft = drafts[index]
            
            # 设置目标草稿名称
            new_name = input("输入新草稿名称 (默认为自动生成): ")
            if not new_name.strip():
                new_name = f"复制_{source_draft['name']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 直接复制草稿
            direct_copy_draft(source_draft['path'], drafts_root, new_name)
        else:
            print("无效的选择")
    except ValueError:
        print("请输入有效的编号")

if __name__ == "__main__":
    main() 