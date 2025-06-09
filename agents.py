# agent.py

import os
import json
import openai
from zhipuai import ZhipuAI
from config import API_KEYS, MODEL_CONFIG
import datetime

class Agent:
    def __init__(self, profile, model=None, provider=None):
        """
        profile: dict，包含 name, gender, age_group, education,
                 occupation, marriage_status, persona, background_story 等字段。
        model: 使用的模型名称，如 "gpt-4" 或 "glm-4"
        provider: 模型提供商，支持 "openai" 或 "zhipuai"
        """
        self.profile = profile
        self.name = profile["name"]
        self.history = []   # 存储每回合贡献、回报等
        self.dialogue_history = []  # 存储对话和行为历史
        
        # 使用配置文件中指定的模型
        self.provider = provider or MODEL_CONFIG["provider"]
        self.model = model or MODEL_CONFIG["model"]
        
        if self.provider == "openai":
            openai.api_key = API_KEYS["openai"]
        elif self.provider == "zhipuai":
            self.client = ZhipuAI(api_key=API_KEYS["zhipuai"])

    def _call_llm(self, messages, temperature=None, max_tokens=None): 
        if self.provider == "openai":
            params = {
                "model": self.model,
                "messages": messages
            }
            if temperature is not None:
                params["temperature"] = temperature
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
                
            response = openai.ChatCompletion.create(**params)
            return response.choices[0].message["content"].strip()
        elif self.provider == "zhipuai":
            params = {
                "model": self.model,
                "messages": messages
            }
            if temperature is not None:
                params["temperature"] = temperature
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
                
            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content.strip()
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def decide_contribution(self, round_number, endowment, r, num_players, discussion_summary=None):
        base_prompt = f"""你是玩家"{self.name}"。
你的个人信息：  
```json
{json.dumps(self.profile, ensure_ascii=False, indent=2)}
```

游戏规则：
- 当前第 {round_number} 轮
- 你有 {endowment} 枚代币可投入公共池
- 公共池总额 × {r} 后平分给 {num_players} 名玩家
"""

        # 如果有讨论信息，添加到背景中
        if discussion_summary and discussion_summary["history"]:
            discussions = []
            for entry in discussion_summary["history"]:
                speaker = "你" if entry["agent"] == self.name else entry["agent"]
                discussions.append(f"- {speaker}：{entry['message']}")
            
            discussion_context = f"""
本轮讨论内容：
{chr(10).join(discussions)}

请基于你的个性特征和上述讨论内容，决定你的投入金额。"""
            prompt = base_prompt + discussion_context
        else:
            prompt = base_prompt + "\n请基于你的个性特征，决定你的投入金额。"
            
        prompt += f"\n\n严格输出一个整数（0–{endowment}），不要带任何多余说明。"
        
        messages = [
            {"role": "system", "content": f"你是一个游戏玩家，正在参与公共品博弈。请根据个性和场景做出合理决策。严格只输出一个整数，范围 0–{endowment}。"},
            {"role": "user", "content": prompt}
        ]
        
        messages = [
            {"role": "system", "content": f"严格只输出一个整数，范围 0–{endowment}。"},
            {"role": "user", "content": prompt}
        ]
        
        answer = self._call_llm(messages)
        try:
            value = int(answer)
        except ValueError:
            value = 0
        return max(0, min(endowment, value))

    def speak_in_discussion(self, round_number, last_contribution, last_payoff, others):
        # 计算一些统计信息
        if others:
            all_contributions = [o.get("contribution", 0) for o in others]
            all_contributions.append(last_contribution)
            avg_contribution = sum(all_contributions) / len(all_contributions)
            max_contribution = max(all_contributions)
            min_contribution = min(all_contributions)
            total_contribution = sum(all_contributions)
            
            all_payoffs = [o.get("payoff", 0) for o in others if o.get("payoff") is not None]
            if last_payoff is not None:
                all_payoffs.append(last_payoff)
            avg_payoff = sum(all_payoffs) / len(all_payoffs) if all_payoffs else 0
        
        prompt = f"""你是玩家"{self.name}"，在公共品博弈游戏讨论环节发表意见。

                你的背景：
                ```json
                {json.dumps(self.profile, ensure_ascii=False, indent=2)}
                ```

                游戏数据（第{round_number}轮）：
                - 你的投入：{last_contribution}，收益：{last_payoff if last_payoff is not None else '未知'}
                - 本轮平均投入：{avg_contribution:.1f}，总投入：{total_contribution}
                - 最高投入：{max_contribution}，最低投入：{min_contribution}

                其他玩家情况：
                {json.dumps(others, ensure_ascii=False, indent=2)}"""

        messages = [
            {"role": "system", "content": "你是参与公共品博弈的玩家，基于你的角色特征和当前游戏状况发表观点。"},
            {"role": "user", "content": prompt}
        ]
        
        return self._call_llm(messages)

    def add_to_history(self, round_number, event_type, content, room_type=None):
        """记录事件到对话历史"""
        self.dialogue_history.append({
            "round": round_number,
            "room": room_type,
            "type": event_type,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        })


def load_agents(profiles):
    """
    根据 profiles（一个包含所有 profile 的列表）实例化所有 Agent。
    使用config.py中指定的模型配置。
    """
    return [Agent(profile) for profile in profiles]
