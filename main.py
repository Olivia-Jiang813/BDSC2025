# main.py
from agents import Agent
from profiles import PROFILES
from game_controller import GameController
from config import validate_config

def main():
    """游戏主入口函数"""
    # 验证配置
    validate_config()
    
    try:
        # 创建agents
        agents = [Agent(profile) for profile in PROFILES]
        
        # 创建并运行游戏
        game = GameController(agents)
        game.play()
        
    except Exception as e:
        print(f"\n游戏运行出错: {str(e)}")
        raise

if __name__ == "__main__":
    main()
