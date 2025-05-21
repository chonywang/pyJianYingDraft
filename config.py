"""
配置文件，用于存储API密钥和其他配置信息
"""

# API密钥配置
API_KEYS = {
    "ARK_API_KEY": "c973941c-1508-4712-b98a-fdb07ffeb2bc",  # 方舟API密钥
    "OPENAI_API_KEY": "",  # OpenAI API密钥
}

# 方舟API配置
ARK_CONFIG = {
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "ep-20250520221009-7dtgd"
}

# OpenAI配置
OPENAI_CONFIG = {
    "model": "gpt-3.5-turbo"
}

# 剪映API配置
JIANYING_CONFIG = {
    "base_url": "http://localhost:8001"
} 