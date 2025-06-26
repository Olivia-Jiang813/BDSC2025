# agefrom openai import OpenAI
from zhipuai import ZhipuAI
from pydantic import BaseModel, Field
from config import API_KEYS, GAME_CONFIG, MODEL_CONFIG
from personality_traits import PERSONALITY_PROMPTS
import datetime
import time

# 把公用的描述提取到一个变量里
COMMON_REASONING_DESC = "思考过程：需要输出得到 output 的完整思考链路。"

# Pydantic模型定义
class ContributionDecision(BaseModel):
    reasoning: str = Field(
        ...,
        description=COMMON_REASONING_DESC
    )
    output: int = Field(
        ...,
        ge=0,
        description="本轮投入金额，必须是 0 到当前总金额之间的整数"
    )

class StrategyUpdate(BaseModel):
    reasoning: str = Field(
        ...,
        description=COMMON_REASONING_DESC
    )
    output: str = Field(
        ...,
        description="策略总结：简要描述整体资源投入趋势及潜在风险或机会（1-2句）"
    )

class BeliefUpdate(BaseModel):
    reasoning: str = Field(
        ...,
        description=COMMON_REASONING_DESC
    )
    output: str = Field(
        ...,
        description="更新后的性格和合作倾向描述"
    )
import os
import json
import openai
from openai import OpenAI
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
        self.personality_type = personality_type  # 保存性格类型
        self.debug_prompts = False  # 默认关闭调试
        # anchor智能体不需要prompt
        if not self.is_anchor:
            if personality_type in PERSONALITY_PROMPTS:
                self.system_prompt = PERSONALITY_PROMPTS[personality_type]
            else:
                raise ValueError(f"不支持的性格类型: {personality_type}")
        else:
            self.system_prompt = None
        
        # 记忆和历史
        self.history = []   # 存储每轮的基本数据
        self.strategy_memory = []  # 策略记忆：每2轮更新，存储策略相关思考
        self.belief_memory = []   # 信念记忆：每4轮更新，存储对合作的信念，影响系统提示
        self.llm_interactions = []  # LLM交互记录：存储每次AI交互的完整输入输出
        self.current_endowment = GAME_CONFIG["endowment"]  # 当前禀赋
        self.current_total_money = GAME_CONFIG["endowment"]  # 当前总金额（初始禀赋 + 累计收益）
        
        # 使用配置文件中指定的模型
        self.provider = provider or MODEL_CONFIG["provider"]
        self.model = model or MODEL_CONFIG["model"]
        
        if self.provider == "openai":
            # openai.api_key = API_KEYS["openai"]
            self.client = OpenAI(api_key=API_KEYS["openai"])
        elif self.provider == "zhipuai":
            self.client = ZhipuAI(api_key=API_KEYS["zhipuai"])

    def _call_llm(self, messages, temperature=None, max_tokens=None, debug_label="", structured_output=None): 
        # 记录交互开始时间
        start_time = datetime.datetime.now()
        
        # 添加调试输出
        if self.debug_prompts:
            try:
                print(f"\n{'='*80}")
                print(f"【{self.name} - {self.personality_type}】{debug_label}")
                print(f"{'='*80}")
                for i, msg in enumerate(messages):
                    role_name = "系统消息" if msg["role"] == "system" else "用户消息"
                    print(f"\n【{role_name}】")
                    print(f"{msg['content']}")
                if structured_output:
                    print(f"\n【结构化输出类型】: {structured_output.__name__}")
                print(f"{'='*80}\n")
            except Exception as debug_error:
                print(f"调试输出错误: {debug_error}")
        
        try:
            if self.provider == "openai":
                if structured_output:
                    # 使用结构化输出模式
                    params = {
                        "model": self.model,
                        "input": messages,
                        "text_format": structured_output
                    }
                    # if temperature is not None:
                    #     params["temperature"] = temperature
                    # if max_tokens is not None:
                    #     params["max_tokens"] = max_tokens
                        
                    response = self.client.responses.parse(**params)
                    # 保存原始响应和解析后的结果
                    # raw_response = response.raw_output_text if hasattr(response, 'raw_output_text') else str(response.output_parsed)
                    parsed_response = response.output_parsed
                    
                    # 从结构化输出中获取内容
                    if hasattr(parsed_response, "reasoning") and hasattr(parsed_response, "output"):
                        reasoning = parsed_response.reasoning  # 确保保存思考过程
                        output = parsed_response.output
                        # 根据输出类型构造最终返回的内容
                        if isinstance(output, (int, float)):
                            response_content = str(output)  # 对于决策阶段，直接返回数值
                        else:
                            response_content = output  # 对于策略和信念更新，返回字符串
                    else:
                        # 应对未预期的结构
                        reasoning = None
                        response_content = str(parsed_response)
                else:
                    # 普通文本输出模式
                    params = {
                        "model": self.model,
                        "input": messages
                    }
                    # if temperature is not None:
                    #     params["temperature"] = temperature
                    # if max_tokens is not None:
                    #     params["max_tokens"] = max_tokens
                        
                    response = self.client.responses.create(**params)
                    raw_response = response.output_text
                    response_content = raw_response
                    reasoning = None
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
                raw_response = response.choices[0].message.content.strip()
                response_content = raw_response
                reasoning = None
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        
        except Exception as e:
            raw_response = f"LLM调用失败: {str(e)}"
            response_content = raw_response
            reasoning = None
        
        # 记录交互结束时间
        end_time = datetime.datetime.now()
        
        # 记录完整的交互信息
        interaction_record = {
            "timestamp": start_time.isoformat(),
            "debug_label": debug_label,
            "duration_seconds": (end_time - start_time).total_seconds(),
            "model": self.model,
            "provider": self.provider,
            "input": {
                "messages": messages,
                "parameters": {
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            },
            "output": {
                # "raw_response": raw_response,
                "content": response_content,
                "reasoning": reasoning if reasoning else None,
                "structured_output_type": structured_output.__name__ if structured_output else None,
                "status": "success" if not response_content.startswith("LLM调用失败") else "error"
            }
        }
        
        # 添加到智能体的交互历史
        self.llm_interactions.append(interaction_record)
        
        return response_content

    def decide_contribution(self, round_number, r, num_players, all_history=None, mode="public"):
        """决定本轮的投入金额
        
        Args:
            round_number: 当前轮数
            r: 公共池倍数
            num_players: 玩家总数
            all_history: 所有玩家的历史记录
            mode: 信息模式 ("public" 或 "anonymous")
        """
        # 锚定智能体直接返回全部当前金额
        if self.is_anchor:
            return self.current_total_money

        # 构建提示信息
        base_prompt = f"""你是玩家"{self.name}"。

        游戏规则：
        - 当前第 {round_number} 轮
        - 你有 {self.current_total_money} 枚代币可投入公共池（包括初始禀赋和之前的收益）
        - 公共池总额 × {r} 后平分给 {num_players} 名玩家
        - 你的投入范围：0 到 {self.current_total_money}

        你的记忆："""

        # 添加策略记忆（仅在有策略时显示）
        if self.strategy_memory:
            latest_strategy = self.get_latest_strategy()
            base_prompt += f"\n当前策略：\n{latest_strategy}"

        # 根据模式添加历史信息
        if round_number > 1:
            base_prompt += f"\n\n历史投入记录："
            
            # 添加自己的历史投入
            base_prompt += f"\n你的历史投入："
            for r in range(1, round_number):
                if r <= len(self.history):
                    history_entry = self.history[r-1]
                    my_contrib = history_entry['contribution']
                    my_payoff = history_entry['payoff']
                    my_total_before = history_entry.get('total_money_before_round', my_contrib + my_payoff)
                    my_ratio = (my_contrib / my_total_before * 100) if my_total_before > 0 else 0
                    base_prompt += f"\n  第{r}轮: 投入{my_contrib}/{my_total_before} ({my_ratio:.1f}%), 收益{my_payoff:.1f}"
            
            # 根据模式添加其他玩家历史信息
            if all_history and mode == "public":
                # 公开模式：显示所有玩家所有轮次的贡献
                base_prompt += f"\n\n其他玩家历史投入："
                for player_id, player_data in all_history.items():
                    if player_id != self.id:
                        player_history = player_data.get('history', player_data)  # 兼容旧格式
                        base_prompt += f"\n玩家{player_id}: "
                        for r in range(1, round_number):
                            if r <= len(player_history):
                                history_entry = player_history[r-1]
                                contrib = history_entry['contribution']
                                # 尝试获取投入范围信息
                                if isinstance(history_entry, dict) and 'total_money_before_round' in history_entry:
                                    total_before = history_entry['total_money_before_round']
                                    ratio = (contrib / total_before * 100) if total_before > 0 else 0
                                    base_prompt += f"第{r}轮:{contrib}/{total_before}({ratio:.1f}%) "
                                else:
                                    base_prompt += f"第{r}轮:{contrib} "
            elif all_history and mode == "anonymous":
                # 匿名模式：只显示平均值和汇总信息
                base_prompt += f"\n\n其他玩家汇总信息："
                for r in range(1, round_number):
                    round_total = 0
                    round_count = 0
                    for player_id, player_data in all_history.items():
                        if player_id != self.id:
                            player_history = player_data.get('history', player_data)  # 兼容旧格式
                            if r <= len(player_history):
                                round_total += player_history[r-1]['contribution']
                                round_count += 1
                    if round_count > 0:
                        avg_contrib = round_total / round_count
                        base_prompt += f"\n  第{r}轮: 他人平均贡献{avg_contrib:.1f}, 他人总贡献{round_total}"
            
        base_prompt += f"\n\n请基于你的策略和信念，决定本轮投入金额。"
        
        # 添加结构化输出说明
        base_prompt += f"\n请输出决策理由和具体投入金额，必须在0–{self.current_total_money}之间。"
        
        # 使用当前的系统提示（可能已被信念记忆更新）
        current_system_prompt = self.get_current_system_prompt()
        
        messages = [
            {"role": "system", "content": current_system_prompt},
            {"role": "user", "content": base_prompt}
        ]
        
        # 创建用于结构化输出的动态模型
        class DynamicContributionDecision(BaseModel):
            reasoning: str = Field(
                ...,
                description="思考过程：说明你决策时考虑的边际收益、风险以及博弈策略"
            )
            output: int = Field(
                ...,
                ge=0,
                le=self.current_total_money,
                description=f"本轮投入金额，必须是 0–{self.current_total_money} 之间的整数"
            )
        
        # 调用LLM，使用结构化输出
        if self.provider == "openai":
            answer = self._call_llm(messages, debug_label="决策阶段", structured_output=DynamicContributionDecision)
        else:
            # 非OpenAI提供商，使用普通输出
            answer = self._call_llm(messages, debug_label="决策阶段")
            
        try:
            value = int(answer)
        except ValueError:
            value = 0
        return max(0, min(self.current_total_money, value))

    def get_current_system_prompt(self):
        """获取当前的系统提示（可能已被信念记忆更新）"""
        if self.is_anchor:
            return "你是锚定智能体，每轮自动全部投入，无需推理。"
        if self.belief_memory:
            latest_belief = self.belief_memory[-1]
            if 'new_system_prompt' in latest_belief:
                return latest_belief['new_system_prompt']
            elif 'updated_system_prompt' in latest_belief:
                return latest_belief['updated_system_prompt']
        # 兜底：如果system_prompt为None，返回neutral或默认提示
        base_prompt = self.system_prompt if self.system_prompt else PERSONALITY_PROMPTS.get("neutral", "你是一名玩家。")
        return f"{base_prompt}\n你正在参与公共品博弈。请根据你的性格特征和场景做出合理决策。"

    def get_latest_strategy(self):
        """获取最新的策略记忆"""
        if not self.strategy_memory:
            return None
        return f"策略总结: {self.strategy_memory[-1]['strategy']}"

    def get_latest_belief(self):
        """获取最新的信念记忆"""
        if not self.belief_memory:
            return None
        return f"当前身份状态: {self.belief_memory[-1]['updated_personality']}"

    def update_total_money(self, new_total):
        """更新当前总金额"""
        self.current_total_money = new_total

    def record_memory(self, round_number, event_type, content):
        """记录事件到记忆日志（已被新的记忆系统替代，保留兼容性）
        
        Args:
            round_number: 当前回合数
            event_type: 事件类型（'contribution', 'discussion', 'outcome'等）
            content: 事件内容
        """
        # 新的记忆系统不再使用此方法，但保留以确保向后兼容
        pass

    def record_round_data(self, round_num, contribution, group_total, payoff, total_money_before_round=None):
        """
        记录每轮的基本数据
        Args:
            round_num: 当前轮次
            contribution: 个人贡献
            group_total: 组总贡献
            payoff: 收益
            total_money_before_round: 本轮开始前的总金额（投入范围）
        """
        if self.is_anchor:
            # anchor只记录最基本数据
            round_data = {
                'round': round_num,
                'contribution': contribution,
                'group_total': group_total,
                'payoff': payoff,
                'total_money_before_round': total_money_before_round or self.current_total_money
            }
            self.history.append(round_data)
            return
        
        round_data = {
            'round': round_num,
            'contribution': contribution,
            'group_total': group_total,
            'payoff': payoff,
            'total_money_before_round': total_money_before_round or self.current_total_money
        }
        self.history.append(round_data)

    def set_debug_mode(self, debug=True):
        """设置是否输出调试信息（prompt内容）"""
        self.debug_prompts = debug

    def get_current_endowment(self):
        """获取当前总金额（已包含所有收益）"""
        return self.current_total_money

    def update_memory(self, round_number, own_contribution, payoff, reveal_mode, all_history=None):
        """更新智能体的记忆系统（仅非anchor智能体）
        
        Args:
            round_number: 当前回合数
            own_contribution: 自己的贡献
            payoff: 本轮收益
            reveal_mode: 信息公开模式 ("public" 或 "anonymous")
            all_history: 所有玩家的历史记录
        """
        if self.is_anchor:
            return  # anchor不更新记忆
        
        # 更新总金额（取整数）
        self.current_total_money = int(round(payoff))
        
        # 注意：策略和信念更新现在由游戏控制器统一管理，不在这里进行

    def _update_strategy_memory(self, round_number, reveal_mode, all_history):
        """更新策略记忆：每2轮总结投入策略"""
        if self.is_anchor:
            return  # anchor不更新策略，不调LLM
        
        # 确保有足够的历史数据（至少2轮）
        if len(self.history) < 2:
            return
            
        # 获取最近2轮的历史数据
        recent_history = self.history[-2:]
        
        # 构建策略分析提示
        prompt = f"""作为玩家 {self.name}，近两轮各玩家的投入情况如下：
        {self._format_recent_rounds_info(round_number, reveal_mode, all_history)}

        你当前的策略是：{self.get_latest_strategy() if self.strategy_memory else ""}

        请基于以上信息，简要思考（1–2句），重点描述整体资源投入趋势及潜在风险或机会。"""

        messages = [
            {"role": "system", "content": self.get_current_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        # 调用LLM，使用结构化输出
        if self.provider == "openai":
            strategy = self._call_llm(messages, debug_label="策略记忆更新", structured_output=StrategyUpdate)
        else:
            strategy = self._call_llm(messages, debug_label="策略记忆更新")
        
        # 记录到策略记忆
        strategy_record = {
            "rounds": [r['round'] for r in recent_history],
            "end_round": round_number,
            "timestamp": datetime.datetime.now().isoformat(),
            "strategy": strategy,
            "contributions_analyzed": [r['contribution'] for r in recent_history]
        }
        self.strategy_memory.append(strategy_record)

    def _update_belief_memory(self, round_number, reveal_mode, all_history):
        """更新信念记忆：每4轮更新对合作的信念，同时更新系统提示"""
        if self.is_anchor:
            return  # anchor不更新信念
        # 确保有策略记录才进行信念更新
        if not self.strategy_memory:
            return
            
        # 获取最近的策略记忆作为参考
        recent_strategies = []
        if len(self.strategy_memory) >= 2:
            recent_strategies = [mem['strategy'] for mem in self.strategy_memory[-2:]]
        elif len(self.strategy_memory) == 1:
            recent_strategies = [self.strategy_memory[-1]['strategy']]
        
        recent_strategy_text = " ".join(recent_strategies) if recent_strategies else "暂无策略记录"
        
        # 构建信念更新提示
        prompt = f"""作为玩家 {self.name}，近期你的投入策略如下：
        {recent_strategy_text}

        请基于近期的策略，重新审视并更新你的身份描述，使其更准确地反映你在公共品博弈中的倾向以及当前对资源分配的看法。

        要求：
        - 保持"你是一个...玩家"的句式开头
        - 描述你在公共品博弈中的行为特征
        - 反映你对合作与竞争的态度
        - 保持2-3句话的简洁描述

        请直接输出更新后的身份描述，不要包含其他解释。"""

        # 获取system_prompt，避免None
        system_prompt = self.system_prompt if self.system_prompt else PERSONALITY_PROMPTS.get("neutral", "你是一名玩家。")
        messages = [
            {"role": "system", "content": system_prompt + "\n请更新你的身份认知，这将成为你新的行为指导原则。"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用LLM，使用结构化输出
        if self.provider == "openai":
            updated_personality = self._call_llm(messages, debug_label="信念记忆更新", structured_output=BeliefUpdate)
        else:
            updated_personality = self._call_llm(messages, debug_label="信念记忆更新")

        print(updated_personality)
        
        # 构建新的系统提示，保持原有格式
        new_system_prompt = f"{updated_personality}\n你正在参与公共品博弈。请根据你的性格特征和场景做出合理决策。"
        
        # 记录到信念记忆
        belief_record = {
            "end_round": round_number,
            "timestamp": datetime.datetime.now().isoformat(),
            "original_system_prompt": self.system_prompt,
            "updated_personality": updated_personality,
            "new_system_prompt": new_system_prompt,
            "strategy_context": recent_strategy_text
        }
        self.belief_memory.append(belief_record)
        
        # 更新系统提示
        self.system_prompt = new_system_prompt

    def make_final_decision(self, initial_endowment, r, num_players):
        """游戏结束后的一次性PGG决策
        
        Args:
            initial_endowment: 初始禀赋（用于最后的一次性游戏）
            r: 公共池倍数
            num_players: 玩家数量
            
        Returns:
            int: 投入金额（0到initial_endowment）
        """
        if self.is_anchor:
            return initial_endowment

        prompt = f"""现在你面临一个全新的一次性公共品博弈：

        游戏规则：
        - 当前是一轮独立的新游戏，你与 {num_players-1} 名陌生玩家进行一次性博弈
        - 你有 {initial_endowment} 枚代币可投入公共池（包括初始禀赋和之前的收益）
        - 公共池总额 × {r} 后平分给{num_players} 名玩家
        - 你的投入范围：0 到 {initial_endowment}

        请基于你在之前游戏中形成的策略和信念，决定在这个一次性博弈中的投入。"""

        messages = [
            {"role": "system", "content": self.get_current_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        # 创建用于结构化输出的动态模型
        class FinalDecision(BaseModel):
            reasoning: str = Field(
                ...,
                description="思考过程：解释在最终一次性决策中考虑的因素"
            )
            output: int = Field(
                ...,
                ge=0,
                le=initial_endowment,
                description=f"投入金额，必须是0–{initial_endowment}之间的整数"
            )
        
        # 调用LLM，使用结构化输出
        if self.provider == "openai":
            answer = self._call_llm(messages, debug_label="最终一次性决策", structured_output=FinalDecision)
        else:
            answer = self._call_llm(messages, debug_label="最终一次性决策")
            
        try:
            value = int(answer)
        except ValueError:
            value = 0
        return max(0, min(initial_endowment, value))

    def _format_recent_rounds_info(self, round_number, reveal_mode, all_history):
        """格式化最近2轮的各玩家投入信息"""
        info_text = ""
        start_round = max(1, round_number - 1)  # 最近2轮
        
        # 包括当前轮次在内的最近2轮
        for r in range(start_round, round_number + 1):
            info_text += f"\n第{r}轮投入情况："
            
            # 添加自己的投入
            if r <= len(self.history):
                history_entry = self.history[r-1]
                my_contrib = history_entry['contribution']
                my_total_before = history_entry.get('total_money_before_round', my_contrib)
                my_ratio = (my_contrib / my_total_before * 100) if my_total_before > 0 else 0
                info_text += f"\n  你: {my_contrib}/{my_total_before}({my_ratio:.1f}%)"
            
            # 根据模式添加其他玩家信息
            if all_history and reveal_mode == "public":
                for player_id, player_data in all_history.items():
                    if player_id != self.id:
                        # 兼容新旧数据格式
                        player_history = player_data.get('history', player_data) if isinstance(player_data, dict) else player_data
                        if r <= len(player_history):
                            history_entry = player_history[r-1]
                            contrib = history_entry['contribution']
                            # 尝试获取投入范围信息
                            if isinstance(history_entry, dict) and 'total_money_before_round' in history_entry:
                                total_before = history_entry['total_money_before_round']
                                ratio = (contrib / total_before * 100) if total_before > 0 else 0
                                info_text += f"\n  玩家{player_id}: {contrib}/{total_before}({ratio:.1f}%)"
                            else:
                                # 如果没有total_money_before_round信息，只显示投入金额
                                info_text += f"\n  玩家{player_id}: {contrib}"
            elif all_history:
                # 匿名模式：计算其他玩家平均值
                other_contribs = []
                other_totals = []
                for player_id, player_data in all_history.items():
                    if player_id != self.id:
                        # 兼容新旧数据格式
                        player_history = player_data.get('history', player_data) if isinstance(player_data, dict) else player_data
                        if r <= len(player_history):
                            history_entry = player_history[r-1]
                            other_contribs.append(history_entry['contribution'])
                            if isinstance(history_entry, dict) and 'total_money_before_round' in history_entry:
                                other_totals.append(history_entry['total_money_before_round'])
                
                if other_contribs:
                    avg_contrib = sum(other_contribs) / len(other_contribs)
                    if other_totals and len(other_totals) == len(other_contribs):
                        avg_total = sum(other_totals) / len(other_totals)
                        avg_ratio = (avg_contrib / avg_total * 100) if avg_total > 0 else 0
                        info_text += f"\n  其他玩家平均: {avg_contrib:.1f}/{avg_total:.1f}({avg_ratio:.1f}%)"
                    else:
                        info_text += f"\n  其他玩家平均: {avg_contrib:.1f}"
        
        return info_text.strip() if info_text else "暂无历史记录"
