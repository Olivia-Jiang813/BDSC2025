# rooms.py
import random
import datetime
import json

class ContributeRoom:
    def __init__(self, endowment, r, num_players):
        self.endowment = endowment
        self.r = r
        self.num_players = num_players

    def handle(self, agent, round_number, last_payoff, discussion_summary=None):
        c = agent.decide_contribution(
            round_number, 
            self.endowment, 
            self.r, 
            self.num_players,
            discussion_summary
        )
        message = f"{agent.name} 投入：{c}"
        print(f"[ContributeRoom] {message}\n")
        
        # 记录到历史
        agent.add_to_history(
            round_number=round_number,
            event_type="contribution",                content={
                "contribution": c
            },
            room_type="ContributeRoom"
        )
        return c

class DiscussionRoom:
    def __init__(self):
        self.discussion_history = []  # 存储本轮讨论历史
        self.participants = set()  # 存储本轮参与讨论的玩家
    
    def should_enter_discussion(self, agent, game_state):
        """决定是否进入讨论室
        
        Args:
            agent: Agent对象
            game_state: dict, 包含游戏状态信息
        Returns:
            bool: 是否应该参与讨论
        """
        round_number = game_state.get("round", 1)
        prev_contributions = game_state.get("prev_round_contributions", {})
        base_endowment = game_state.get("base_endowment", 100)
        
        # 如果有历史贡献数据，计算一些统计信息
        stats = {}
        if prev_contributions:
            contributions = list(prev_contributions.values())
            avg_contribution = sum(contributions) / len(contributions)
            max_contribution = max(contributions)
            min_contribution = min(contributions)
            agent_contribution = prev_contributions.get(agent.name, 0)
            
            stats.update({
                "average_contribution": avg_contribution,
                "max_contribution": max_contribution,
                "min_contribution": min_contribution,
                "my_contribution": agent_contribution,
                "relative_position": "高于" if agent_contribution > avg_contribution else "低于" if agent_contribution < avg_contribution else "等于"
            })
        
        # 构建提示信息
        prompt = f"""作为玩家"{agent.name}"，你需要决定是否参与本轮讨论。

            你的背景信息：
            ```json
            {json.dumps(agent.profile, ensure_ascii=False, indent=2)}
            ```

            当前游戏状态：
            - 第 {round_number} 轮
            - 基础禀赋：{base_endowment}
            {"" if not prev_contributions else f'''
            上轮统计：
            - 平均贡献：{stats['average_contribution']}
            - 最高贡献：{stats['max_contribution']}
            - 最低贡献：{stats['min_contribution']}
            - 你的贡献：{stats['my_contribution']}（{stats['relative_position']}平均）'''}

            基于你的性格特征和当前游戏状态，你是否选择参与讨论？
            请只回答"是"或"否"。"""

        messages = [
            {"role": "system", "content": "你扮演游戏中的玩家，根据性格和状况决定是否参与讨论。只能回答'是'或'否'。"},
            {"role": "user", "content": prompt}
        ]
        
        response = agent._call_llm(messages)
        return response.strip() == "是"
    
    def handle(self, agent, round_number, context):
        """处理玩家的讨论
        
        Args:
            agent: Agent对象
            round_number: 当前轮次
            context: dict, 包含游戏状态信息
        """
        self.participants.add(agent.name)
        
        # 生成讨论消息
        msg = agent.speak_in_discussion(
            round_number,
            context.get("last_contribution", 0),
            context.get("last_payoff", 0),
            context.get("others", [])
        )
        print(f"[DiscussionRoom] {agent.name}：{msg}")
        
        # 记录讨论内容
        self.discussion_history.append({
            "agent": agent.name,
            "message": msg,
            "round": round_number,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # 记录到Agent历史
        agent.add_to_history(
            round_number=round_number,
            event_type="discussion",
            content={
                "message": msg,
                "context": context,
                "participated": True
            },
            room_type="DiscussionRoom"
        )
    
    def record_non_participant(self, agent, round_number):
        """记录未参与讨论的玩家
        
        Args:
            agent: Agent对象
            round_number: 当前轮次
        """
        agent.add_to_history(
            round_number=round_number,
            event_type="discussion",
            content={
                "participated": False,
                "reason": "chose_not_to_participate"
            },
            room_type="DiscussionRoom"
        )
    
    def get_discussion_summary(self):
        """获取本轮讨论的摘要，用于影响后续决策"""
        return {
            "history": self.discussion_history,
            "participants": list(self.participants)
        }

class InterventionRoom:
    def handle(self, agent, round_number, context):
        # 这里可以扩展更多外部干预逻辑
        intervention_msg = f"对 {agent.name} 应用外部干预"
        print(f"[InterventionRoom] {intervention_msg}\n")
        
        # 记录到历史
        agent.add_to_history(
            round_number=round_number,
            event_type="intervention",
            content={"intervention": "default_intervention"},
            room_type="InterventionRoom"
        )
        return None
