# profiles.py

import json
import random
from config import GAME_CONFIG
from pathlib import Path

def load_profiles(json_file="beijing_agent_profile.json"):
    """从JSON文件加载所有角色配置"""
    try:
        filepath = Path(__file__).parent / json_file
        with open(filepath, 'r', encoding='utf-8') as f:
            all_profiles = json.load(f)
            if not isinstance(all_profiles, list):
                raise ValueError("JSON文件必须包含角色配置列表")
            return all_profiles
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到配置文件：{json_file}")
    except json.JSONDecodeError:
        raise ValueError(f"配置文件 {json_file} 不是有效的JSON格式")

def get_random_profiles():
    """从配置文件中随机选择指定数量的角色配置"""
    all_profiles = load_profiles()
    num_players = GAME_CONFIG["num_players"]
    
    if len(all_profiles) < num_players:
        raise ValueError(f"配置文件中的角色数量({len(all_profiles)})少于所需数量({num_players})")
    
    # 随机选择指定数量的角色
    selected_profiles = random.sample(all_profiles, num_players)
    
    print(f"\n本局游戏随机选择了 {num_players} 名角色：")
    for profile in selected_profiles:
        print(f"- {profile['name']} ({profile.get('occupation', '职业未知')})")
    print("")
    
    return selected_profiles

# 导出随机选择的角色配置
PROFILES = get_random_profiles()

import json
import random
from config import GAME_CONFIG

def load_profiles(json_file="beijing_agent_profile.json"):
    """从JSON文件加载所有角色配置"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            profiles = json.load(f)
            if not isinstance(profiles, list):
                raise ValueError("JSON文件必须包含角色配置列表")
            return profiles
    except FileNotFoundError:
        raise FileNotFoundError(f"找不到配置文件：{json_file}")
    except json.JSONDecodeError:
        raise ValueError(f"配置文件 {json_file} 不是有效的JSON格式")

def get_random_profiles():
    """随机选择指定数量的角色配置"""
    all_profiles = load_profiles()
    num_players = GAME_CONFIG["num_players"]
    
    if len(all_profiles) < num_players:
        raise ValueError(f"配置文件中的角色数量({len(all_profiles)})少于所需数量({num_players})")
    
    # 随机选择指定数量的角色
    selected_profiles = random.sample(all_profiles, num_players)
    print("\n本局游戏角色：")
    for profile in selected_profiles:
        print(f"- {profile['name']}")
    print("")
    
    return selected_profiles

