# agent.py

import os
import json
import openai
from zhipuai import ZhipuAI
from config import API_KEYS, MODEL_CONFIG, GAME_CONFIG
from personality_traits import PERSONALITY_PROMPTS
import datetime
import time

class Agent:
    def __init__(self, agent_id, personality_type, is_anchor=False, model=None, provider=None):
        """
        Args:
            agent_id: str，智能体的唯一标识符
            personality_type: str，性格类型（例如：high-altruism, medium-altruism, low-altruism, anchor）
            is_anchor: 是否是锚定智能体
            model: 使用的模型名称
            provider: 模型提供商
        """
        self.id = agent_id
        self.name = f"Agent_{agent_id}"
        self.is_anchor = is_anchor
        
        # 设置智能体的系统提示（性格特征）
        if personality_type in PERSONALITY_PROMPTS:
            self.system_prompt = PERSONALITY_PROMPTS[personality_type]
        else:
            raise ValueError(f"不支持的性格类型: {personality_type}")
        
        # 记忆和历史
        self.history = []   # 存储每轮的基本数据
        self.memory_log = []  # 存储每轮的详细记忆
        self.dialogue_history = []  # 存储对话历史
        self.current_endowment = GAME_CONFIG["endowment"]  # 当前禀赋
        
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
        """决定本轮的投入金额"""
        # 锚定智能体直接返回全部禀赋
        if self.is_anchor:
            return endowment

        # 构建提示信息
        base_prompt = f"""你是玩家"{self.name}"。

            游戏规则：
            - 当前第 {round_number} 轮
            - 你有 {endowment} 枚代币可投入公共池
            - 公共池总额 × {r} 后平分给 {num_players} 名玩家

            你的记忆："""

        # 添加最近一轮的记忆（如果有）
        if self.memory_log:
            last_memory = self.memory_log[-1]
            if isinstance(last_memory, dict) and "content" in last_memory:
                base_prompt += f"\n上一轮记忆：{last_memory['content']}"
            elif isinstance(last_memory, str):
                base_prompt += f"\n上一轮记忆：{last_memory}"

        # 如果有讨论信息，添加到背景中
        if discussion_summary and discussion_summary.get("history"):
            discussions = []
            for entry in discussion_summary["history"]:
                speaker = "你" if entry["agent"] == self.name else entry["agent"]
                discussions.append(f"- {speaker}：{entry['message']}")
            
            base_prompt += f"\n\n本轮讨论内容：\n{chr(10).join(discussions)}"
            
        base_prompt += f"\n\n请基于你的性格特征和上述信息，决定本轮投入金额。\n请严格输出一个整数（0–{endowment}），不要带任何多余说明。"
        
        messages = [
            {"role": "system", "content": f"{self.system_prompt}\n你是一个游戏玩家，正在参与公共品博弈。请根据你的性格特征和场景做出合理决策。"},
            {"role": "user", "content": base_prompt}
        ]
        
        answer = self._call_llm(messages)
        try:
            value = int(answer)
        except ValueError:
            value = 0
        return max(0, min(endowment, value))

    def speak_in_discussion(self, round_number, last_contribution, last_payoff, others):
        # 计算一些统计信息
        if isinstance(others, dict):  # anonymous mode
            prompt = f"""你是玩家"{self.name}"，在公共品博弈游戏第{round_number}轮讨论环节发表意见。
            
            情况概述：
            - 你的当前禀赋：{self.get_current_endowment()}
            - 总玩家数：{others.get('total_agents', 0) + 1}
            - 上轮总贡献：{others.get('total_contribution', '未知')}
            - 平均贡献：{others.get('avg_contribution', '未知')}
            
            请简要发表对当前局势的看法和建议。如果这是第一轮，可以谈谈你的合作策略。"""
        
        else:  # public mode
            # 收集所有有效的贡献数据
            valid_contributions = [o.get("last_contribution", 0) for o in others 
                                if o.get("last_contribution") is not None]
            if last_contribution is not None:
                valid_contributions.append(last_contribution)
            
            # 只有当有有效的贡献数据时才计算统计信息
            if valid_contributions:
                avg_contribution = sum(valid_contributions) / len(valid_contributions)
                max_contribution = max(valid_contributions)
                min_contribution = min(valid_contributions)
                total_contribution = sum(valid_contributions)
            else:
                avg_contribution = max_contribution = min_contribution = total_contribution = 0
                
            prompt = f"""你是玩家"{self.name}"，在公共品博弈游戏讨论环节发表意见。

            游戏数据（第{round_number}轮）：
            - 你的当前禀赋：{self.get_current_endowment()}
            - 你上轮投入：{last_contribution if last_contribution is not None else '这是第一轮'}
            - 你上轮收益：{last_payoff if last_payoff is not None else '这是第一轮'}
            - 本轮平均投入：{'%.1f' % avg_contribution if 'avg_contribution' in locals() else '还未开始'}
            - 总投入：{'%.1f' % total_contribution if 'total_contribution' in locals() else '还未开始'}
            - 最高投入：{'%.1f' % max_contribution if 'max_contribution' in locals() else '还未开始'}
            - 最低投入：{'%.1f' % min_contribution if 'min_contribution' in locals() else '还未开始'}

            其他玩家情况:
            {json.dumps(others, ensure_ascii=False, indent=2)}"""
                
        messages = [
            {"role": "system", "content": f"{self.system_prompt}\n你是参与公共品博弈的玩家，请基于提供的背景信息简要发表观点。"},
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

    def record_memory(self, round_number, event_type, content):
        """记录事件到记忆日志
        
        Args:
            round_number: 当前回合数
            event_type: 事件类型（'contribution', 'discussion', 'outcome'等）
            content: 事件内容
        """
        memory = {
            "round": round_number,
            "type": event_type,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.memory_log.append(memory)

    def record_round_data(self, round_num, contribution, group_total, payoff):
        """
        记录每轮的基本数据
        Args:
            round_num: 当前轮次
            contribution: 个人贡献
            group_total: 组总贡献
            payoff: 收益
        """
        round_data = {
            'round': round_num,
            'contribution': contribution,
            'group_total': group_total,
            'payoff': payoff
        }
        self.history.append(round_data)

    def get_current_endowment(self):
        """获取当前禀赋"""
        if not self.history:
            return self.current_endowment
        return self.history[-1]["payoff"]

    def get_memory_summary(self, num_rounds=None):
        """
        获取记忆摘要
        Args:
            num_rounds: 获取最近几轮的记忆，如果为None则获取全部
        Returns:
            str: 记忆摘要
        """
        if num_rounds is None:
            relevant_memories = self.memory_log
        else:
            relevant_memories = self.memory_log[-num_rounds:]
            
        summary = []
        for memory in relevant_memories:
            summary.append(f"第{memory['round']}轮 - {memory['type']}: {memory['details']}")
            
        return "\n".join(summary)

    def update_memory(self, round_number, own_contribution, own_measurement,
                     reveal_mode, public_pool_share, others_contributions=None, discussion_messages=None):
        """更新智能体的记忆
        
        Args:
            round_number: 当前回合数
            own_contribution: 自己的贡献
            own_measurement: 自己的测量数据（估计等）
            reveal_mode: 信息公开模式 ("public" 或 "anonymous")
            public_pool_share: 从公共池获得的分成
            others_contributions: 其他玩家的贡献信息（如果reveal_mode为"public"）
            discussion_messages: 讨论内容列表
        """
        # 准备基础信息
        current_round_info = {
            "我的贡献": own_contribution,
            "我从公共池获得的分成": public_pool_share,
            "我估计的他人平均贡献": own_measurement['estimated_avg_contribution']
        }
        
        # 根据信息公开模式添加其他玩家的贡献信息
        if others_contributions:
            if reveal_mode == "public":
                contributions = list(others_contributions.values())
                current_round_info.update({
                    "其他玩家的具体贡献": others_contributions,
                    "他人实际平均贡献": sum(contributions) / len(contributions),
                    "最高贡献": max(contributions),
                    "最低贡献": min(contributions)
                })
            else:  # anonymous mode
                current_round_info["总贡献"] = sum(others_contributions.values()) + own_contribution
                
        # 添加讨论内容（如果有）
        if discussion_messages:
            current_round_info["讨论记录"] = [
                f"{msg['agent_id']}: {msg['message']}"
                for msg in discussion_messages
            ]
            
        # 构建记忆更新提示
        prompt = f"""作为玩家 {self.name}，请根据以下新信息更新你对当前局势的理解：

        第 {round_number} 轮信息：
        {json.dumps(current_round_info, ensure_ascii=False, indent=2)}

        {'这是第一轮。' if round_number == 1 else '上一轮你的记忆：' + self.memory_log[-1]['summary'] if self.memory_log else '这是新的开始。'}

        请简要总结你对当前局势的理解，包括：
        1. 你对其他玩家行为的评估
        2. 你对群体合作水平的判断
        3. 这些观察对你未来决策的影响"""

        messages = [
            {"role": "system", "content": self.system_prompt + "\n作为一个有记忆的智能体，你需要整合新的信息来更新对局势的理解。"},
            {"role": "user", "content": prompt}
        ]
        
        summary = self._call_llm(messages)
        
        # 记录新的记忆
        memory = {
            "round": round_number,
            "timestamp": datetime.datetime.now().isoformat(),
            "own_contribution": own_contribution,
            "own_measurement": own_measurement,
            "others_contributions": others_contributions,
            "summary": summary
        }
        self.memory_log.append(memory)
