# main.py
import sys
import traceback
import argparse
import copy
from game_controller import GameController
from config import validate_config, GAME_CONFIG

def main(endowment=None, rounds=None, r=None, num_players=None, personality_type=None, 
         reveal_mode=None, debug_prompts=False):
    """游戏主入口函数
    
    Args:
        endowment: 每轮初始代币数
        rounds: 游戏轮数
        r: 公共池倍数
        num_players: 玩家数量
        personality_type: 性格类型
        reveal_mode: 信息公开模式
        debug_prompts: 是否启用调试输出
    """
    
    # 创建游戏配置的副本，避免修改全局配置
    game_config = copy.deepcopy(GAME_CONFIG)
    
    # 根据传入的参数更新配置
    if endowment is not None:
        game_config["endowment"] = endowment
    if rounds is not None:
        game_config["rounds"] = rounds
    if r is not None:
        game_config["r"] = r
    if num_players is not None:
        game_config["num_players"] = num_players
    if personality_type is not None:
        game_config["personality_type"] = personality_type
    if reveal_mode is not None:
        game_config["reveal_mode"] = reveal_mode
    
    try:
        # 显示当前配置
        print(f"运行游戏 - endowment={game_config['endowment']}, rounds={game_config['rounds']}, "
              f"r={game_config['r']}, players={game_config['num_players']}, "
              f"personality={game_config['personality_type']}")
        
        # 验证配置
        print("正在验证游戏配置...")
        # 临时更新全局配置用于验证
        original_config = copy.deepcopy(GAME_CONFIG)
        GAME_CONFIG.update(game_config)
        validate_config()
        GAME_CONFIG.update(original_config)  # 恢复原始配置
        
        # 创建游戏控制器
        print("正在初始化游戏控制器...")
        
        # 创建并运行游戏
        game = GameController(game_config)
        game.setup_game()  # 设置游戏，包括创建智能体
        
        # 根据参数设置调试模式
        if debug_prompts:
            print("启用PROMPT调试输出模式...")
            game.set_debug_mode(True)
        
        print("\n=== 游戏开始 ===\n")
        game.play()
        print("\n=== 游戏正常结束 ===\n")
        
    except ValueError as ve:
        print(f"\n配置错误: {str(ve)}")
        return False
    except KeyboardInterrupt:
        print("\n\n检测到用户中断，正在保存进度...")
        if 'game' in locals():
            game.save_game_state()
        return False
    except Exception as e:
        print(f"\n游戏运行出错: {str(e)}")
        print("\n错误详情:")
        traceback.print_exc()
        if 'game' in locals():
            print("\n正在保存当前游戏状态...")
            game.save_game_state(interrupted=True)
        return False
    
    return True



if __name__ == "__main__":
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description='公共品博弈游戏')
    parser.add_argument('--debug-prompts', action='store_true', 
                       help='启用prompt调试输出，显示发送给AI的完整提示内容')
    args = parser.parse_args()
    
    # 运行单次游戏
    main(debug_prompts=args.debug_prompts)

