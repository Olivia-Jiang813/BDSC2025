"""
公共品博弈游戏配置文件

这个文件统一管理所有的游戏参数和实验配置。

使用方式：
1. 运行单次游戏：python main.py
2. 运行快速测试：python run_experiments.py quick
3. 运行完整参数扫描：python run_experiments.py sweep
4. 运行针对性实验：python run_experiments.py targeted

如果要修改游戏参数，请在这个文件中的相应配置部分进行修改：
- GAME_CONFIG: 单次游戏的默认参数
- EXPERIMENT_CONFIG: 批量实验的参数范围和特定实验配置
"""

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
    "provider": "openai",          # 当前使用的模型提供商
    "model": "gpt-4.1-mini",        # 当前使用的具体模型
    "available_models": {
        "openai": ["gpt-4", "gpt-4.1", "gpt-4omini","gpt-4.1-mini"],
        "zhipuai": ["glm-4-flash", "glm-3-turbo"]
    }
}

# 游戏参数配置
GAME_CONFIG = {
    "endowment": 10,      # 每轮初始代币数
    "r": 3,            # 公共池倍数
    "rounds": 10,        # 游戏轮数
    "num_players": 10,    # 游戏玩家数量
    # Anchor智能体比例（0~1），如0.1表示10%，0.2表示20%，0.3表示30%
    "anchor_ratio": 0.2,  # 默认10%，可调整为0.2、0.3等
    # 实验控制参数
    "reveal_mode": "anonymous",    # 信息公开模式：public（完全公开）或 anonymous（只显示总量）
    # 智能体性格特征设置
    "personality_type": "neutral"  # 可选：selfish, altruistic, neutral, anchor
}

# 房间配置
ROOM_CONFIG = {
    "available_rooms": ["ContributeRoom"],  # 已移除DiscussionRoom
    "default_room": "ContributeRoom"
}

# 实验参数扫描配置
EXPERIMENT_CONFIG = {
    # 基础参数扫描范围
    "endowment_values": [10, 20, 30, 50],      # 禀赋值范围
    "rounds_values": [5, 10, 15, 20],          # 轮数范围
    "num_players_values": [5, 10, 15, 20],     # 玩家数量范围
    "r_values": [1.2, 1.6, 2.0, 2.5],         # 公共池倍数范围
    "personality_types": ["selfish", "altruistic", "neutral"],  # 性格类型
    "reveal_modes": ["public", "anonymous"],   # 信息公开模式
    
    # 快速测试配置（用于开发和调试）
    "quick_test": {
        "endowment_values": [10],
        "rounds_values": [5],
        "num_players_values": [5],
        "r_values": [2.0],
        "personality_types": ["selfish", "altruistic"],
        "reveal_modes": ["public"]
    },
    
    # 针对性实验配置（测试特定假设）
    "targeted_experiments": [
        # 基础对比实验：自私 vs 利他
        {"endowment": 10, "rounds": 10, "num_players": 10, "r": 2.0, "personality_type": "selfish", "reveal_mode": "public"},
        {"endowment": 10, "rounds": 10, "num_players": 10, "r": 2.0, "personality_type": "altruistic", "reveal_mode": "public"},
        
        # 信息透明度影响
        {"endowment": 10, "rounds": 10, "num_players": 10, "r": 2.0, "personality_type": "selfish", "reveal_mode": "public"},
        {"endowment": 10, "rounds": 10, "num_players": 10, "r": 2.0, "personality_type": "selfish", "reveal_mode": "anonymous"},
        
        # 公共池倍数影响
        {"endowment": 10, "rounds": 10, "num_players": 10, "r": 1.2, "personality_type": "selfish", "reveal_mode": "public"},
        {"endowment": 10, "rounds": 10, "num_players": 10, "r": 2.5, "personality_type": "selfish", "reveal_mode": "public"},
        
        # 群体大小影响
        {"endowment": 10, "rounds": 10, "num_players": 5, "r": 2.0, "personality_type": "selfish", "reveal_mode": "public"},
        {"endowment": 10, "rounds": 10, "num_players": 20, "r": 2.0, "personality_type": "selfish", "reveal_mode": "public"},
        
        # 禀赋影响
        {"endowment": 5, "rounds": 10, "num_players": 10, "r": 2.0, "personality_type": "selfish", "reveal_mode": "public"},
        {"endowment": 20, "rounds": 10, "num_players": 10, "r": 2.0, "personality_type": "selfish", "reveal_mode": "public"},
    ]
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
