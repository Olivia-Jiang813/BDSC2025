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
                "personality_type": agent.personality_type,
                "is_anchor": agent.is_anchor,
                "game_history": agent.history,
                "belief_memory": agent.belief_memory,      # 信念记忆
                "current_total_money": agent.current_total_money,  # 当前总金额
                "final_decision": game_config.get("final_decisions", {}).get(agent.id) if game_config.get("final_decisions") else None
            }
            game_record["agents"].append(agent_record)
        
        # 添加详细的LLM交互记录
        game_record["llm_interactions"] = {
            "summary": {
                "total_interactions": sum(len(agent.llm_interactions) for agent in agents),
                "agents_count": len(agents)
            },
            "interactions_by_agent": {}
        }
        
        # 额外添加一个独立的reasoning摘要部分，便于查看思考过程
        game_record["reasoning_summary"] = {}
        
        for agent in agents:
            if hasattr(agent, 'llm_interactions') and agent.llm_interactions:
                # 保存完整交互记录
                game_record["llm_interactions"]["interactions_by_agent"][agent.id] = {
                    "agent_name": agent.name,
                    "personality_type": agent.personality_type,
                    "total_interactions": len(agent.llm_interactions),
                    "interactions": agent.llm_interactions
                }
                
                # 创建reasoning摘要
                reasoning_by_round = {}
                for interaction in agent.llm_interactions:
                    debug_label = interaction.get("debug_label", "未知")
                    reasoning = interaction.get("output", {}).get("reasoning")
                    if reasoning:
                        if debug_label not in reasoning_by_round:
                            reasoning_by_round[debug_label] = []
                        reasoning_by_round[debug_label].append({
                            "timestamp": interaction.get("timestamp"),
                            "reasoning": reasoning
                        })
                
                game_record["reasoning_summary"][agent.id] = {
                    "agent_name": agent.name,
                    "reasoning_by_type": reasoning_by_round
                }
        
        # 根据config信息和游戏状态构建文件名
        # 格式: [模型]_[personality]_[players]p_[rounds]r_[status]_[timestamp].json
        model_name = game_config.get("model", "unknown")
        personality = game_config.get("personality_type", "unknown")
        num_players = game_config.get("num_players", len(agents))
        total_rounds = game_config.get("rounds", "unknown")
        completed_rounds = game_config.get("completed_rounds", len(self.round_records))
        reveal_mode = game_config.get("reveal_mode", "unknown")
        # 移除讨论相关的文件名
        
        if interrupted:
            filename = f"{model_name}_{personality}_{num_players}p_{total_rounds}r_{reveal_mode}_interrupted_r{completed_rounds}_{timestamp}.json"
        else:
            filename = f"{model_name}_{personality}_{num_players}p_{total_rounds}r_{reveal_mode}_completed_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(game_record, f, ensure_ascii=False, indent=2)
        
        print(f"\n游戏历史JSON格式已保存到：{filepath}")
        
        # 同时保存文本格式的历史记录
        text_filepath = self.save_text_history(game_config, agents, game_record, filepath)
        
        return filepath, text_filepath

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
            # 优先用每轮记录的total_money_before_round
            initial_money = data.get('total_money_before_round', data.get('initial_total_money', data.get('initial_endowment', 10)))
            net_gain = data['payoff'] - initial_money
            summary.append(
                f"{data['id']}:\n"
                f"  初始金额: {initial_money:.2f}\n"
                f"  投入金额: {data['contribution']:.2f}\n"
                f"  最终收益: {data['payoff']:.2f}\n"
                f"  净收益: {net_gain:+.2f}\n")
        
        return "\n".join(summary)

    def format_game_history_text(self, game_config, agents):
        """
        生成可读性更强的文本格式游戏历史
        
        Args:
            game_config: 游戏配置信息
            agents: 参与游戏的所有agent
            
        Returns:
            str: 格式化的游戏历史文本
        """
        lines = []
        
        # === 1. 游戏概况 ===
        lines.append("="*50)
        lines.append("游戏概况")
        lines.append("="*50)
        lines.append(f"模型: {game_config.get('model', 'unknown')}")
        lines.append(f"性格类型: {game_config.get('personality_type', 'unknown')}")
        lines.append(f"玩家数量: {game_config.get('num_players', len(agents))}")
        lines.append(f"总轮数: {game_config.get('rounds', 'unknown')}")
        lines.append(f"完成轮数: {len(self.round_records)}")
        lines.append(f"公共池倍数: {game_config.get('r', 'unknown')}")
        lines.append(f"信息模式: {game_config.get('reveal_mode', 'unknown')}")
        lines.append("\n")

        # === 2. 玩家信息 ===
        for agent in agents:
            lines.append(f"- 玩家: {agent.name}")
            lines.append(f"  性格类型: {agent.personality_type}")
            lines.append(f"  是否锚定: {'是' if agent.is_anchor else '否'}")
            if not agent.is_anchor:
                lines.append(f"- 系统提示: {agent.get_current_system_prompt()}")
            else:
                lines.append(f"- 系统提示: [锚定智能体无需提示]")
            lines.append("-"*30)
        lines.append("\n")

        # === 3. 轮次记录 ===
        lines.append("="*50)
        lines.append("轮次记录")
        lines.append("="*50)
        for round_record in self.round_records:
            round_num = round_record["round"]
            stats = round_record["stats"]
            lines.append(f"\n--- 第 {round_num} 轮 ---")
            lines.append(f"总贡献: {stats['total_contribution']}")
            lines.append(f"公共池: {stats['public_pool']}")
            lines.append(f"人均回报: {stats['share_per_player']}")
            # 每个玩家的投入记录
            lines.append("\n各玩家投入:")
            if game_config.get('reveal_mode', 'public') == 'anonymous':
                # 匿名模式，输出他人平均贡献比例（基于每个玩家本轮初始金额）
                agents_data = round_record["agents"]
                ratios = []
                for a in agents_data:
                    initial_money = a.get('total_money_before_round', a.get('initial_total_money', a.get('initial_endowment', 10)))
                    ratio = a['contribution'] / initial_money if initial_money else 0
                    ratios.append(ratio)
                avg_ratio = sum(ratios) / len(ratios) if ratios else 0
                avg_contrib = sum(a['contribution'] for a in agents_data) / len(agents_data)
                total_contrib = sum(a['contribution'] for a in agents_data)
                lines.append(f"他人平均贡献: {avg_contrib:.2f} (平均贡献比例: {avg_ratio:.2%})")
                lines.append(f"他人总贡献: {total_contrib:.2f}")
            else:
                for agent_data in round_record["agents"]:
                    lines.append(f"玩家{agent_data['id']}贡献 {agent_data['contribution']}/{agent_data.get('total_money_before_round', game_config.get('endowment', 10))}")
            lines.append("-"*30)

        # === 4. 信念记录 ===
        lines.append("\n" + "="*50)
        lines.append("信念记录")
        lines.append("="*50)
        for agent in agents:
            if agent.is_anchor:
                lines.append(f"\n玩家 {agent.name}（锚定智能体）不参与信念记忆更新。")
                lines.append("-"*30)
                continue
            lines.append(f"\n玩家 {agent.name} 的信念记忆:")
            for belief in agent.belief_memory:
                lines.append(f"- 轮次 {belief.get('round', belief.get('end_round', '?'))}: {belief.get('updated_personality', belief.get('updated_personality',''))}")
            lines.append("-"*30)

        # === 5. AI交互记录 ===
        lines.append("\n" + "="*50)
        lines.append("AI交互记录")
        lines.append("="*50)
        for agent in agents:
            if agent.is_anchor:
                lines.append(f"\n玩家 {agent.name}（锚定智能体）无AI交互记录。")
                continue
            if hasattr(agent, 'llm_interactions'):
                lines.append(f"\n玩家 {agent.name} 的交互记录:")
                for interaction in agent.llm_interactions:
                    lines.append(f"\n时间: {interaction['timestamp']}")
                    lines.append(f"阶段: {interaction['debug_label']}")
                    # 输入信息
                    lines.append("\n输入:")
                    for msg in interaction['input']['messages']:
                        lines.append(f"[{msg['role']}] {msg['content']}")
                    # 思考过程和输出
                    output_info = interaction['output']
                    if output_info.get('reasoning'):
                        lines.append(f"\n思考过程:")
                        lines.append(output_info['reasoning'])
                    lines.append(f"\n输出结果:")
                    lines.append(output_info['content'])
                    lines.append("-"*30)

        return "\n".join(lines)

    def format_game_history_text(self, game_config, agents, game_record):
        """
        将游戏历史格式化为可读性强的文本格式
        
        Args:
            game_config: 游戏配置信息
            agents: 参与游戏的所有agent
            game_record: 完整的游戏记录
            
        Returns:
            str: 格式化后的文本
        """
        sections = []
        
        # 1. 游戏概况
        sections.append("="*50)
        sections.append("公共品博弈实验记录")
        sections.append("="*50)
        sections.append("\n[实验配置]")
        sections.append(f"模型: {game_config.get('model', 'unknown')}")
        sections.append(f"性格特征: {game_config.get('personality_type', 'unknown')}")
        sections.append(f"玩家数量: {game_config.get('num_players', len(agents))}")
        sections.append(f"总回合数: {game_config.get('rounds', 'unknown')}")
        sections.append(f"完成回合: {len(self.round_records)}")
        sections.append(f"公开方式: {game_config.get('reveal_mode', 'unknown')}")
        sections.append(f"游戏状态: {'已中断' if game_record['game_status'] == 'interrupted' else '已完成'}")
        
        # 2. 玩家信息
        sections.append("\n" + "="*20 + " 玩家信息 " + "="*20)
        for agent_record in game_record["agents"]:
            sections.append(f"\n[玩家 {agent_record['id']}]")
            sections.append(f"名称: {agent_record['name']}")
            sections.append(f"性格类型: {agent_record['personality_type']}")
            sections.append(f"是否锚定: {'是' if agent_record['is_anchor'] else '否'}")
            sections.append(f"最终总金额: {agent_record['current_total_money']:.2f}")
            if agent_record.get('final_decision'):
                sections.append(f"最终决策: {agent_record['final_decision']}")
            # 避免直接append dict
            # sections.append(agent_record)  # 错误写法，已移除

        # 3. 每轮详情
        sections.append("\n" + "="*20 + " 回合详情 " + "="*20)
        for round_record in self.round_records:
            round_num = round_record["round"]
            stats = round_record["stats"]
            agents_data = round_record["agents"]
            sections.append(self.format_round_summary(round_num, stats, agents_data))
        
        # 4. History
        sections.append("\n" + "="*20 + " AI交互记录 " + "="*20)
        for agent_id, data in game_record["llm_interactions"]["interactions_by_agent"].items():
            sections.append(f"\n[玩家 {agent_id} - {data['agent_name']}]")
            sections.append(f"交互总次数: {data['total_interactions']}")
            sections.append("\n各轮交互详情:")
            for interaction in data["interactions"]:
                sections.append(f"\n时间: {interaction.get('timestamp', 'unknown')}")
                sections.append(f"类型: {interaction.get('debug_label', 'unknown')}")
                sections.append("输入:")
                input_content = interaction.get("input", "")
                if isinstance(input_content, dict):
                    # 兼容 input 为 dict（如包含 messages）
                    if "messages" in input_content and isinstance(input_content["messages"], list):
                        for msg in input_content["messages"]:
                            role = msg.get("role", "?")
                            content = msg.get("content", "")
                            sections.append(f"[{role}] {content}")
                    else:
                        sections.append(str(input_content))
                elif isinstance(input_content, list):
                    for item in input_content:
                        sections.append(str(item))
                else:
                    sections.append(str(input_content))
                if "output" in interaction:
                    output = interaction["output"]
                    if isinstance(output, dict):
                        sections.append("\nReasoning:")
                        sections.append(str(output.get("reasoning", "无")))
                        sections.append("\n输出:")
                        sections.append(str(output.get("output", output.get("content", "无"))))
                    else:
                        sections.append("\n输出:")
                        sections.append(str(output))
                sections.append("-" * 40)
        
        
        return "\n".join(sections)

    def save_text_history(self, game_config, agents, game_record, filepath):
        """
        保存游戏历史的文本格式到文件
        
        Args:
            game_config: 游戏配置信息
            agents: 参与游戏的所有agent
            game_record: 完整的游戏记录
            filepath: JSON文件路径
        """
        # 生成文本格式的历史记录
        text_content = self.format_game_history_text(game_config, agents, game_record)
        
        # 构造文本文件路径（将.json替换为.txt）
        text_filepath = filepath.rsplit('.', 1)[0] + '.txt'
        
        # 保存文本文件
        with open(text_filepath, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        print(f"游戏历史文本版本已保存到：{text_filepath}")
        return text_filepath
