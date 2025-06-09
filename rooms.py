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
            str: "是"或"否"的决定
        """
        round_number = game_state.get("round", 1)
        prev_contributions = game_state.get("prev_round_contributions", {})
        base_endowment = game_state.get("base_endowment", 100)
        
        # 如果有历史贡献数据，计算统计信息
        stats = {}
        if prev_contributions:
            contributions = list(prev_contributions.values())
            avg_contribution = sum(contributions) / len(contributions)
            max_contribution = max(contributions)
            min_contribution = min(contributions)
            agent_contribution = prev_contributions.get(agent.name, 0)
            
            stats.update({
                "average_contribution": f"{avg_contribution:.1f}",
                "max_contribution": max_contribution,
                "min_contribution": min_contribution,
                "my_contribution": agent_contribution,
                "relative_position": "高于" if agent_contribution > avg_contribution else "低于" if agent_contribution < avg_contribution else "等于"
            })
        
        # 构建提示信息
        prompt = f"""你是玩家"{agent.name}"，现在需要决定是否参与讨论。请用一个字回答："是"或"否"。

你的背景信息：
```json
{json.dumps(agent.profile, ensure_ascii=False, indent=2)}
```

当前游戏状态：{" " if not prev_contributions else f'''
- 你上轮投入了：{stats["my_contribution"]}（{stats["relative_position"]}平均值）
- 本轮是第 {round_number} 轮
- 平均投入：{stats["average_contribution"]}
- 最高投入：{stats["max_contribution"]}
- 最低投入：{stats["min_contribution"]}'''}"""

        messages = [
            {"role": "system", "content": "你扮演游戏中的玩家，根据性格和状况决定是否参与讨论。只能回答'是'或'否'。"},
            {"role": "user", "content": prompt}
        ]
        
        response = agent._call_llm(messages)
        return response.strip()
    
    def handle(self, agent, round_number, context):
        """Handle player discussion.
        
        Args:
            agent: Agent instance
            round_number: current round number
            context: dict containing game state info
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
        """Record non-participating player.
        
        Args:
            agent: Agent instance
            round_number: current round number
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
        """Get discussion summary for influencing subsequent decisions."""
        return {
            "history": self.discussion_history,
            "participants": list(self.participants)
        }
