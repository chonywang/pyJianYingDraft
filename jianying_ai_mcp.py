"""
剪映AI MCP (Master Control Program)

这个模块提供了一个AI驱动的主控程序，可以：
1. 接收自然语言指令
2. 解析指令并转换为API调用
3. 管理整个视频创建流程
4. 提供简单的聊天式界面

通过整合openai/langchain与template_config_manager.py，它允许用户通过自然语言来创建和修改视频草稿。
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
import re
import asyncio
from config import API_KEYS, ARK_CONFIG, OPENAI_CONFIG, JIANYING_CONFIG

# 设置API客户端
def get_llm_client():
    """获取LLM客户端"""
    # 优先使用ARK API
    if API_KEYS["ARK_API_KEY"]:
        return OpenAI(
            base_url=ARK_CONFIG["base_url"],
            api_key=API_KEYS["ARK_API_KEY"]
        )
    # 如果没有ARK API Key，则使用OpenAI
    elif API_KEYS["OPENAI_API_KEY"]:
        return OpenAI(api_key=API_KEYS["OPENAI_API_KEY"])
    else:
        raise ValueError("未设置任何API密钥，请在config.py中配置ARK_API_KEY或OPENAI_API_KEY")

# API基础URL
BASE_URL = JIANYING_CONFIG["base_url"]

# 当前草稿追踪
current_drafts = {}

class DraftInfo(BaseModel):
    """草稿信息模型"""
    draft_id: str
    draft_name: str
    creation_time: datetime
    last_modified: datetime
    description: str = ""

class NLPProcessor:
    """自然语言处理器"""
    
    def __init__(self):
        """初始化NLP处理器"""
        self.client = get_llm_client()
    
    def process_command(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入命令
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            解析后的命令和参数
        """
        prompt = f"""
        你是一个视频编辑助手，需要将用户的自然语言指令转换为结构化的API调用信息。
        根据以下用户输入，判断用户想要执行的操作，并返回JSON格式的结构化数据。
        
        可能的操作类型包括：
        1. create_draft - 创建新草稿
        2. add_video - 添加视频
        3. add_audio - 添加音频
        4. add_text - 添加文本
        5. get_draft_info - 获取草稿信息
        6. save_draft - 保存草稿
        7. list_drafts - 列出所有草稿
        8. delete_draft - 删除草稿
        9. unknown - 无法识别的命令
        
        用户输入: {user_input}
        
        请返回JSON格式的响应，例如：
        对于创建草稿：
        {{
            "action": "create_draft",
            "draft_name": "我的旅行视频",
            "width": 1080,
            "height": 1920,
            "description": "一个旅行视频草稿"
        }}
        
        对于添加视频：
        {{
            "action": "add_video",
            "file_path": "https://example.com/video.mp4",
            "start": "0s",
            "duration": "5s",
            "target_start": "0s",
            "transition": "叠化"
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=ARK_CONFIG["model"] if API_KEYS["ARK_API_KEY"] else OPENAI_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你是视频编辑助手，负责将自然语言转换为API调用。请始终返回有效的JSON格式响应。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # 尝试提取JSON
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content
            
            try:
                result = json.loads(json_str)
                return result
            except json.JSONDecodeError:
                print(f"无法解析JSON响应: {content}")  # 添加调试信息
                return {"action": "unknown", "error": "无法解析响应"}
        
        except Exception as e:
            print(f"API调用错误: {str(e)}")  # 添加错误日志
            return {"action": "unknown", "error": str(e)}

class JianyingAIMCP:
    """剪映AI主控程序"""
    
    def __init__(self):
        """初始化主控程序"""
        self.nlp_processor = NLPProcessor()
        self.current_draft_id = None
    
    def process_user_command(self, user_input: str) -> str:
        """处理用户命令并执行相应操作
        
        Args:
            user_input: 用户的自然语言输入
            
        Returns:
            处理结果的描述
        """
        # 解析命令
        command = self.nlp_processor.process_command(user_input)
        action = command.get("action", "unknown")
        
        # 执行相应操作
        if action == "create_draft":
            return self._create_draft(command)
        elif action == "add_video":
            return self._add_video(command)
        elif action == "add_audio":
            return self._add_audio(command)
        elif action == "add_text":
            return self._add_text(command)
        elif action == "get_draft_info":
            return self._get_draft_info(command)
        elif action == "save_draft":
            return self._save_draft(command)
        elif action == "list_drafts":
            return self._list_drafts()
        elif action == "delete_draft":
            return self._delete_draft(command)
        else:
            return f"抱歉，我无法理解您的命令。错误信息: {command.get('error', '未知错误')}"
    
    def _create_draft(self, command: Dict[str, Any]) -> str:
        """创建新草稿"""
        draft_name = command.get("draft_name", f"草稿_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        width = command.get("width", 1080)
        height = command.get("height", 1920)
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts",
                json={
                    "draft_name": draft_name,
                    "width": width,
                    "height": height
                }
            )
            
            if response.status_code == 200:
                draft_id = response.json()["draft_id"]
                self.current_draft_id = draft_id
                current_drafts[draft_id] = DraftInfo(
                    draft_id=draft_id,
                    draft_name=draft_name,
                    creation_time=datetime.now(),
                    last_modified=datetime.now(),
                    description=command.get("description", "")
                )
                return f"成功创建草稿 '{draft_name}'，ID: {draft_id}"
            else:
                return f"创建草稿失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"创建草稿时发生错误: {str(e)}"
    
    def _add_video(self, command: Dict[str, Any]) -> str:
        """添加视频"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        file_path = command.get("file_path", "")
        if not file_path:
            return "错误: 未提供视频路径或URL。"
        
        # 构建请求数据，包含必要的默认值
        request_data = {
            "file_path": file_path,
            "start": command.get("start", "0s"),
            "duration": command.get("duration", "10s"),
            "target_start": command.get("target_start", "0s"),
            "transition": "左移",  # 使用"左移"作为默认转场效果
            "effects": []  # 空列表作为默认值
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts/{draft_id}/videos",
                json=request_data
            )
            
            if response.status_code == 200:
                return f"成功添加视频 '{file_path}'"
            else:
                return f"添加视频失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"添加视频时发生错误: {str(e)}"
    
    def _add_audio(self, command: Dict[str, Any]) -> str:
        """添加音频"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        url = command.get("url", "")
        if not url:
            return "错误: 未提供音频URL。"
        
        # 构建请求数据，只包含非空属性
        request_data = {
            "url": url
        }
        
        # 只添加非空的属性
        if command.get("enabled") is not None:
            request_data["enabled"] = command["enabled"]
        if command.get("volume") is not None:
            request_data["volume"] = command["volume"]
        if command.get("start"):
            request_data["start"] = command["start"]
        if command.get("target_start"):
            request_data["target_start"] = command["target_start"]
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts/{draft_id}/audio",
                json=request_data
            )
            
            if response.status_code == 200:
                return f"成功添加音频 '{url}'"
            else:
                return f"添加音频失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"添加音频时发生错误: {str(e)}"
    
    def _add_text(self, command: Dict[str, Any]) -> str:
        """添加文本"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        text = command.get("text", "")
        if not text:
            return "错误: 未提供文本内容。"
        
        track_name = command.get("track_name", "主字幕")
        
        # 构建请求数据，包含必要的默认值
        request_data = {
            "track_name": track_name,
            "text": text,
            "start": command.get("start", "0s"),
            "duration": command.get("duration", "5s"),
            "font": command.get("font", "后现代体"),
            "style": command.get("style", {
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
            }),
            "position": command.get("position", {
                "x": 0.5,
                "y": 0.907
            }),
            "intro_animation": command.get("intro_animation", "随机打字机"),
            "outro_animation": command.get("outro_animation", "滑动下落"),
            "linebreak": command.get("linebreak", {
                "mode": "manual",
                "zh_length": 8,
                "en_words": 3
            })
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/drafts/{draft_id}/text",
                json=request_data
            )
            
            if response.status_code == 200:
                return f"成功添加文本 '{text[:20]}...' 到轨道 '{track_name}'"
            else:
                return f"添加文本失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"添加文本时发生错误: {str(e)}"
    
    def _get_draft_info(self, command: Dict[str, Any]) -> str:
        """获取草稿信息"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        try:
            response = requests.get(f"{BASE_URL}/drafts/{draft_id}")
            
            if response.status_code == 200:
                draft_info = response.json()
                return f"""
草稿信息:
- 名称: {draft_info['draft_name']}
- 分辨率: {draft_info['resolution']['width']}x{draft_info['resolution']['height']}
- 视频数量: {len(draft_info['videos'])}
- 音频数量: {len(draft_info['audio'])}
- 文本轨道数量: {len(draft_info['text_tracks'])}
- 总时长: {draft_info['timeline']['total_duration']}
                """
            else:
                return f"获取草稿信息失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"获取草稿信息时发生错误: {str(e)}"
    
    def _save_draft(self, command: Dict[str, Any]) -> str:
        """保存草稿"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        try:
            response = requests.post(f"{BASE_URL}/drafts/{draft_id}/save")
            
            if response.status_code == 200:
                output_path = response.json()["output_path"]
                return f"草稿已成功保存到: {output_path}"
            else:
                return f"保存草稿失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"保存草稿时发生错误: {str(e)}"
    
    def _list_drafts(self) -> str:
        """列出所有草稿"""
        try:
            response = requests.get(f"{BASE_URL}/drafts")
            
            if response.status_code == 200:
                drafts = response.json()
                if not drafts:
                    return "目前没有可用的草稿。"
                
                result = "可用的草稿:\n"
                for i, draft in enumerate(drafts, 1):
                    result += f"{i}. {draft['draft_name']} (ID: {draft['draft_id']}, 时长: {draft['total_duration']})\n"
                
                return result
            else:
                return f"获取草稿列表失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"获取草稿列表时发生错误: {str(e)}"
    
    def _delete_draft(self, command: Dict[str, Any]) -> str:
        """删除草稿"""
        draft_id = command.get("draft_id", self.current_draft_id)
        if not draft_id:
            return "错误: 未指定草稿ID。请先创建或选择一个草稿。"
        
        try:
            response = requests.delete(f"{BASE_URL}/drafts/{draft_id}")
            
            if response.status_code == 200:
                if draft_id in current_drafts:
                    del current_drafts[draft_id]
                
                if self.current_draft_id == draft_id:
                    self.current_draft_id = None
                
                return f"草稿 (ID: {draft_id}) 已成功删除。"
            else:
                return f"删除草稿失败，状态码: {response.status_code}, 错误: {response.text}"
        
        except Exception as e:
            return f"删除草稿时发生错误: {str(e)}"

# 简单的CLI界面
def main():
    """主函数"""
    mcp = JianyingAIMCP()
    
    print("=" * 50)
    print("欢迎使用剪映AI MCP (Master Control Program)")
    print("您可以使用自然语言来创建和编辑视频草稿")
    print("示例命令:")
    print("- 创建一个1080p的新视频草稿，叫做'我的旅行视频'")
    print("- 添加一个视频，URL是https://example.com/video.mp4")
    print("- 在5秒处添加文本'精彩时刻'，持续3秒")
    print("- 保存当前草稿")
    print("输入'退出'或'exit'结束程序")
    print("=" * 50)
    
    while True:
        user_input = input("\n> ")
        
        if user_input.lower() in ['退出', 'exit', 'quit']:
            print("谢谢使用，再见！")
            break
        
        response = mcp.process_user_command(user_input)
        print(response)

if __name__ == "__main__":
    main()
