"""
剪映AI MCP使用示例

这个示例展示了如何使用AI MCP自动创建一个简单的视频草稿，
无需手动调用各个API，只需提供自然语言指令。
"""

import asyncio
from jianying_ai_mcp import JianyingAIMCP

async def automated_example():
    """自动化示例函数"""
    mcp = JianyingAIMCP()
    
    print("=" * 50)
    print("剪映AI MCP自动化示例")
    print("=" * 50)
    
    # 使用自然语言指令创建草稿
    commands = [
        "创建一个1080p的新视频草稿，名称是'AI自动创建的视频'",
        "添加视频https://test-videos.co.uk/vids/jellyfish/mp4/h264/360/Jellyfish_360_10s_1MB.mp4，从0秒开始，持续5秒",
        "添加视频https://test-videos.co.uk/vids/sintel/mp4/h264/360/Sintel_360_10s_1MB.mp4，从5秒开始，持续5秒，使用叠化转场",
        "添加背景音乐https://example.com/background.mp3，音量设为0.8",
        "在第一个视频上添加文本'海底世界'，字体大小36，显示在顶部中间",
        "在第二个视频上添加文本'奇幻冒险'，字体大小36，显示在底部中间",
        "保存当前草稿"
    ]
    
    # 依次执行命令
    for i, command in enumerate(commands, 1):
        print(f"\n[命令 {i}/{len(commands)}] {command}")
        response = await mcp.process_user_command(command)
        print(f"[结果] {response}")
        await asyncio.sleep(1)  # 稍作停顿
    
    print("\n=" * 50)
    print("自动化流程完成！")
    print("=" * 50)

if __name__ == "__main__":
    # 确保服务器已经启动: uvicorn template_config_manager:app --reload --port 8001
    # 设置OpenAI API密钥: export OPENAI_API_KEY="你的API密钥"
    asyncio.run(automated_example()) 