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
            event_type="contribution",
            content={
                "contribution": c
            },
            room_type="ContributeRoom"
        )
        return c
