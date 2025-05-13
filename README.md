# JianYing草稿创建工具

一个模块化、可配置的剪映草稿创建工具，支持添加多段视频、转场效果、特效、音频和文本。

## 功能特点

- 支持从配置文件或命令行参数创建草稿
- 支持添加多段视频和转场效果
- 支持添加音频（网络或本地）
- 支持添加文本和动画
- 完整的日志记录
- 错误处理和恢复机制

## 安装

### 依赖

- Python 3.6+
- 依赖库：requests
- 确保当前目录已安装pyJianYingDraft库

### 简易安装

1. 克隆并安装pyJianYingDraft（确保已在当前目录）
2. 将`jianying_draft_creator.py`和`sample_config.json`放置在pyJianYingDraft目录中

## 快速开始

### 使用配置文件

1. 准备一个配置文件（JSON格式）
2. 运行命令：
```
python jianying_draft_creator.py --config sample_config.json
```

### 使用命令行参数

创建一个简单草稿，包含一个视频和一个音频：
```
python jianying_draft_creator.py --name "我的视频" --video https://example.com/video.mp4 --audio https://example.com/audio.mp3
```

## 配置文件示例

```json
{
    "draft_name": "my_awesome_video",
    "drafts_root": "/Users/username/Documents/jianyan/JianyingPro Drafts",
    "template_folder": "/Users/username/Documents/jianyan/JianyingPro Drafts/Draft Template Old",
    "videos": [
        {
            "file_path": "https://example.com/video1.mp4",
            "start": "0s",
            "duration": "5s",
            "target_start": "0s",
            "transition": "上移",
            "effects": [
                {
                    "effect_id": "负片频闪",
                    "start": "0s",
                    "duration": "5s"
                }
            ]
        },
        {
            "file_path": "https://example.com/video2.mp4",
            "start": "0s",
            "duration": "5s",
            "target_start": "5s",
            "transition": "闪白"
        }
    ],
    "audio": {
        "url": "https://example.com/audio.mp3",
        "enabled": true
    },
    "texts": [
        {
            "text": "第一段视频",
            "start": "0s",
            "duration": "5s",
            "font": "后现代体",
            "style": {"color": [1.0, 1.0, 0.0]},
            "position": {"x": 0, "y": -0.8}
        }
    ]
}
```

## 命令行参数

```
usage: jianying_draft_creator.py [-h] [--config CONFIG] [--name NAME] [--output-dir OUTPUT_DIR] 
                                [--template TEMPLATE] [--video VIDEO] [--audio AUDIO] [--version]

选项：
  -h, --help            显示此帮助信息并退出
  --config CONFIG, -c CONFIG
                        配置文件路径
  --name NAME           草稿名称
  --output-dir OUTPUT_DIR
                        输出目录
  --template TEMPLATE   模板目录路径
  --video VIDEO         添加视频（可多次使用）
  --audio AUDIO         添加音频（URL或本地路径）
  --version, -v         显示版本信息
```

## 注意事项

1. 请确保视频和音频的URL可以正确访问
2. 确保模板目录包含有效的剪映模板
3. 请确保指定的输出目录有写入权限
4. 日志文件保存在`logs/jianying_draft_creator.log`

## 自动查找模板

程序会按以下顺序自动查找模板目录：
1. 配置文件中指定的`template_folder`
2. 命令行参数`--template`指定的目录
3. 当前目录下的`template`文件夹
4. 草稿根目录下的`Draft Template Old`文件夹
5. 草稿根目录下任何包含"template"的文件夹

## 日志

程序运行日志会保存在`logs/jianying_draft_creator.log`文件中 