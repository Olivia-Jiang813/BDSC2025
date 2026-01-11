"""
公共品博弈游戏配置文件
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# API Keys配置
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "zhipuai": os.getenv("ZHIPUAI_API_KEY"),
    "gemini": os.getenv("GEMINI_API_KEY"),
    "deepseek": os.getenv("DEEPSEEK_API_KEY")
}

# 模型配置
MODEL_CONFIG = {
    "provider": "openai",          # 当前使用的模型提供商
    "model": "gpt-4.1",            # 当前使用的具体模型
    "available_models": {
        "openai": ["gpt-4", "gpt-4.1", "gpt-4omini", "gpt-4.1-mini"],
        "zhipuai": ["glm-4-flash", "glm-3-turbo"],
        "gemini": ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"],
        "deepseek": ["deepseek-chat", "deepseek-reasoner"]
    },
    "temperature": 0  # 温度参数
}

# 游戏参数配置
GAME_CONFIG = {
    "model": "gemini-2.5-flash",              # 模型名称
    "endowment": 10,                 # 每轮初始代币数
    "r": 3,                          # 公共池倍数
    "rounds": 10,                    # 游戏轮数
    "num_players": 10,               # 游戏玩家数量
    "anchor_ratio": 0.2,             # Anchor智能体比例（0~1）
    "reveal_mode": "anonymous",      # 信息公开模式：public 或 anonymous
    "instruction_type": "certain",   # 指导语类型：certain 或 uncertain
    "personality_type": "neutral"    # 性格类型：selfish, altruistic, neutral
}

def validate_config():
    """验证配置是否有效"""
    # 检查模型配置
    provider = MODEL_CONFIG["provider"]
    model = MODEL_CONFIG["model"]
    
    # 检查提供商是否有效
    if provider not in MODEL_CONFIG["available_models"]:
        raise ValueError(f"不支持的模型提供商: {provider}")
    
    # 检查模型是否可用
    if model not in MODEL_CONFIG["available_models"][provider]:
        raise ValueError(f"提供商 {provider} 不支持模型: {model}")
    
    # 检查必要的API keys
    if not API_KEYS.get(provider):
        raise ValueError(f"缺少 {provider} 的API密钥")
    
    # 检查游戏参数是否在合理范围内
    if GAME_CONFIG["r"] <= 1:
        raise ValueError("r必须大于1")
    if GAME_CONFIG["endowment"] <= 0:
        raise ValueError("endowment必须为正数")
    if GAME_CONFIG["rounds"] <= 0:
        raise ValueError("rounds必须为正数")
    if GAME_CONFIG["num_players"] <= 0:
        raise ValueError("num_players必须为正数")
