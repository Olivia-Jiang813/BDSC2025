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
                "id": agent.id,
                "name": agent.name,
                "personality_type": "anchor" if agent.is_anchor else getattr(agent, "personality_type", "unknown"),
                "is_anchor": agent.is_anchor,
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
        summary = [f"\n{'='*20} 第 {round_number} 轮总结 {'='*20}"]
        
        # 添加总体统计信息
        summary.append(
            f"\n[本轮概况]\n"
            f"总贡献: {stats['total_contribution']:.2f}\n"
            f"公共池: {stats['public_pool']:.2f}\n"
            f"人均回报: {stats['share_per_player']:.2f}\n"
        )
        
        # 添加每个玩家的详细信息
        summary.append("\n[玩家详情]")
        for data in agents_data:
            net_gain = data['payoff'] - data['initial_endowment']
            summary.append(
                f"{data['id']}:\n"
                f"  初始禀赋: {data['initial_endowment']:.2f}\n"
                f"  投入金额: {data['contribution']:.2f}\n"
                f"  最终收益: {data['payoff']:.2f}\n"
                f"  净收益: {net_gain:+.2f}\n")
        
        return "\n".join(summary)

    def analyze_discussion_participation(self, round_number=None):
        """分析讨论参与度
        
        Args:
            round_number: 如果提供，只分析特定回合；否则分析所有回合
            
        Returns:
            dict: 包含参与度统计信息
        """
        if not self.round_records:
            return {"error": "No game records available"}
            
        participation_stats = {
            "total_rounds": len(self.round_records),
            "participation_by_round": {},
            "participation_rate_by_agent": {}
        }
        
        rounds_to_analyze = [round_number] if round_number else range(1, len(self.round_records) + 1)
        agent_participation_count = {}
        
        for r in rounds_to_analyze:
            if r <= 1:  # 跳过第一轮（没有讨论）
                continue
                
            # 统计该轮参与讨论的玩家
            participants = set()
            for agent in self.round_records[r-1].get("discussion_participants", []):
                participants.add(agent)
                agent_participation_count[agent] = agent_participation_count.get(agent, 0) + 1
            
            participation_stats["participation_by_round"][r] = {
                "participant_count": len(participants),
                "participants": list(participants)
            }
        
        # 计算每个玩家的参与率
        total_discussion_rounds = len(rounds_to_analyze) - 1  # 减去第一轮
        if total_discussion_rounds > 0:
            for agent, count in agent_participation_count.items():
                participation_stats["participation_rate_by_agent"][agent] = count / total_discussion_rounds
        
        return participation_stats
