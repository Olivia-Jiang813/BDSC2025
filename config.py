import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# API Keys配置
API_KEYS = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "zhipuai": os.getenv("ZHIPUAI_API_KEY")
}

# 模型配置
MODEL_CONFIG = {
    "provider": "zhipuai",          # 当前使用的模型提供商
    "model": "glm-4-flash",        # 当前使用的具体模型
    "available_models": {
        "openai": ["gpt-4", "gpt-4.1", "gpt-4omini"],
        "zhipuai": ["glm-4-flash", "glm-3-turbo"]
    }
}

# 游戏参数配置
GAME_CONFIG = {
    "endowment": 10,      # 每轮初始代币数
    "r": 1.6,            # 公共池倍数
    "rounds": 10,        # 游戏轮数
    "num_players": 10,    # 游戏玩家数量
    
    # 实验控制参数
    "use_anchor_agent": False,  # 是否使用锚定智能体
    "allow_discussion": True,   # 是否允许讨论
    "reveal_mode": "public",    # 信息公开模式：public（完全公开）或 anonymous（只显示总量）
    
    # 智能体性格特征设置
    "personality_type": "low-altruism"  # 可选：high-altruism, medium-altruism, low-altruism, anchor
}

# 房间配置
ROOM_CONFIG = {
    "available_rooms": ["ContributeRoom", "DiscussionRoom"],
    "default_room": "ContributeRoom"
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
        raise ValueError(f"提供商 {provider} 不支持模型: {model}")            # 检查必要的API keys
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
