# main.py
import sys
import traceback
from agents import Agent
from profiles import PROFILES
from game_controller import GameController
from config import validate_config

def main():
    """游戏主入口函数"""
    try:
        # 验证配置
        print("正在验证游戏配置...")
        validate_config()
        
        # 创建agents
        print("正在初始化游戏角色...")
        agents = [Agent(profile) for profile in PROFILES]
        
        # 创建并运行游戏
        print("正在启动游戏控制器...")
        game = GameController(agents)
        print("\n=== 游戏开始 ===\n")
        game.play()
        print("\n=== 游戏正常结束 ===\n")
        
    except ValueError as ve:
        print(f"\n配置错误: {str(ve)}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n检测到用户中断，正在保存进度...")
        if 'game' in locals():
            game.save_game_state()
        sys.exit(0)
    except Exception as e:
        print(f"\n游戏运行出错: {str(e)}")
        print("\n错误详情:")
        traceback.print_exc()
        if 'game' in locals():
            print("\n正在保存当前游戏状态...")
            game.save_game_state()
        sys.exit(1)

if __name__ == "__main__":
    main()
