# 剪映AI MCP (Master Control Program)

这个项目实现了一个AI驱动的剪映模板配置管理器，允许用户通过自然语言指令来创建和编辑视频草稿。

## 功能特点

- **自然语言控制**：使用自然语言指令创建和编辑视频草稿
- **组件化设计**：独立管理视频、音频和文本轨道
- **时间轴管理**：自动协调各个轨道的时间关系
- **API支持**：提供RESTful API接口
- **状态追踪**：通过唯一ID串联不同的操作
- **交互式界面**：提供简单的命令行交互界面

## 系统组件

1. **template_config_manager.py**：核心配置管理器，提供API接口
2. **jianying_ai_mcp.py**：AI主控程序，处理自然语言指令
3. **example_ai_mcp.py**：示例代码，展示自动化视频创建流程
4. **example_http_usage.py**：API使用示例，展示如何直接调用API

## 安装步骤

```bash
# 安装依赖
pip install fastapi uvicorn requests openai pydantic asyncio

# 设置OpenAI API密钥
export OPENAI_API_KEY="你的API密钥"
```

## 使用方法

### 启动服务器

```bash
# 启动API服务器
uvicorn template_config_manager:app --reload --port 8001
```

### 使用AI MCP

```bash
# 启动交互式命令行界面
python jianying_ai_mcp.py

# 或者运行自动化示例
python example_ai_mcp.py
```

### 示例命令

以下是一些可以在AI MCP中使用的自然语言命令示例：

- "创建一个1080p的新视频草稿，名称是'我的旅行视频'"
- "添加视频https://example.com/video.mp4，从0秒开始，持续5秒"
- "在5秒处添加文本'精彩时刻'，持续3秒，字体大小36"
- "添加背景音乐https://example.com/music.mp3，音量设为0.8"
- "获取当前草稿信息"
- "保存当前草稿"

## API文档

启动服务器后，可以访问以下地址查看API文档：
- http://localhost:8001/docs

主要API端点包括：

| 方法   | 端点                        | 描述           |
|--------|----------------------------|----------------|
| POST   | /drafts                    | 创建新草稿      |
| GET    | /drafts                    | 列出所有草稿    |
| GET    | /drafts/{draft_id}         | 获取草稿信息    |
| POST   | /drafts/{draft_id}/videos  | 添加视频轨道    |
| POST   | /drafts/{draft_id}/audio   | 添加音频轨道    |
| POST   | /drafts/{draft_id}/text    | 添加文本轨道    |
| DELETE | /drafts/{draft_id}         | 删除草稿        |
| POST   | /drafts/{draft_id}/save    | 保存草稿        |

## 架构设计

系统采用三层架构设计：

1. **API层**：提供RESTful接口，处理HTTP请求
2. **业务逻辑层**：管理草稿、轨道和时间线
3. **自然语言处理层**：将自然语言转换为API调用

## 示例工作流

1. 启动API服务器：`uvicorn template_config_manager:app --reload --port 8001`
2. 启动AI MCP：`python jianying_ai_mcp.py`
3. 输入自然语言命令：`创建一个1080p的新视频草稿，名称是'我的旅行视频'`
4. AI MCP将解析命令并调用相应的API
5. 继续添加视频、音频和文本
6. 保存草稿：`保存当前草稿`

## 高级功能

- **批处理操作**：使用`example_ai_mcp.py`执行一系列命令
- **直接API调用**：使用`example_http_usage.py`直接调用API
- **使用现有配置**：使用`test_with_template_config.py`导入现有的剪映配置 