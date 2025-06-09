import os
import json
from datetime import datetime

class GameRecorder:
    def __init__(self, output_dir="game_history"):
        """
        初始化游戏记录器
        
        Args:
            output_dir: 输出目录的路径
        """
        self.output_dir = output_dir
        self.round_records = []
        os.makedirs(output_dir, exist_ok=True)
    
    def record_round(self, round_number, stats, agents_data):
        """
        记录一轮游戏的数据
        
        Args:
            round_number: 当前回合数
            stats: 本轮统计数据（总贡献、公共池、每人分成等）
            agents_data: 玩家数据列表，每个玩家包含投入、收益等信息
        """
        round_record = {
            "round": round_number,
            "stats": stats,
            "agents": agents_data
        }
        self.round_records.append(round_record)
        
    def save_game_history(self, game_config, agents, interrupted=False):
        """
        保存游戏历史到文件
        
        Args:
            game_config: 游戏配置信息
            agents: 参与游戏的所有agent
            interrupted: 是否是因为中断而保存（默认False）
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建游戏记录
        game_record = {
            "game_config": game_config,
            "game_status": "interrupted" if interrupted else "completed",
            "rounds": self.round_records,
            "agents": []
        }
        
        # 收集每个agent的完整历史记录
        for agent in agents:
            agent_record = {
                "name": agent.name,
                "profile": agent.profile,
                "game_history": agent.history,
                "dialogue_history": agent.dialogue_history
            }
            game_record["agents"].append(agent_record)
        
        # 根据游戏状态选择文件名
        if interrupted:
            filename = f"game_history_{timestamp}_interrupted_round_{game_config['completed_rounds']}.json"
        else:
            filename = f"game_history_{timestamp}_completed.json"
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(game_record, f, ensure_ascii=False, indent=2)
        
        print(f"\n游戏历史已保存到：{filepath}")
        return filepath

    def format_round_summary(self, round_number, stats, agents_data):
        """
        格式化一轮游戏的摘要信息
        
        Args:
            round_number: 当前回合数
            stats: 本轮统计数据
            agents_data: 玩家数据列表
        """
        summary = [f"\n=== Round {round_number} ==="]
        
        # 添加总体统计信息
        summary.append(
            f"\n[GameRoom] 总贡献 {stats['total_contribution']:.2f} → "
            f"公共池 {stats['public_pool']:.2f} → "
            f"每人回报 {stats['share_per_player']:.2f}\n"
        )
        
        # 添加每个玩家的详细信息
        for data in agents_data:
            summary.append(
                f"{data['name']} - 初始: {data['initial_endowment']:.2f}, "
                f"投入: {data['contribution']:.2f}, 收益: {data['payoff']:.2f}"
            )
        
        return "\n".join(summary)
