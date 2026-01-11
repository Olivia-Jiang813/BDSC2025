# agents.py
from openai import OpenAI
from zhipuai import ZhipuAI
from pydantic import BaseModel, Field
from config import API_KEYS, GAME_CONFIG, MODEL_CONFIG
from personality_traits import PERSONALITY_PROMPTS
import datetime
import time
import json

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
from google import genai
from google.genai import types
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
        self.name = f"{int(agent_id) + 1}"  # 智能体名称，基于ID+1生成
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
        self.belief_memory = []   # 信念记忆：每轮更新，存储对自身身份/风格的宏观反思
        self.llm_interactions = []  # LLM交互记录：存储每次AI交互的完整输入输出
        self.reasoning = []  # 用于存储每轮reasoning等短期记忆，替代short_term_memory
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
        elif self.provider == "gemini":
            # 使用新的Google GenAI SDK
            self.client = genai.Client(api_key=API_KEYS["gemini"])
        elif self.provider == "deepseek":
            # DeepSeek使用OpenAI兼容的API
            self.client = OpenAI(
                api_key=API_KEYS["deepseek"],
                base_url="https://api.deepseek.com"
            )

    def _call_llm(self, messages, debug_label="", structured_output=None): 
        # 记录交互开始时间
        start_time = datetime.datetime.now()
        
        # 添加调试输出
        if self.debug_prompts:
            try:
                print(f"\n{'='*80}")
                print(f"【Agent {self.name} - {self.personality_type} - {self.provider}/{self.model}】{debug_label}")
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
            # LLM自动重试机制
            max_retry = 10
            retry_count = 0
            while True:
                try:
                    if self.provider == "openai":
                        if structured_output:
                            params = {
                                "model": self.model,
                                "input": messages,
                                "text_format": structured_output
                            }
                            response = self.client.responses.parse(**params)
                            parsed_response = response.output_parsed
                            if hasattr(parsed_response, "reasoning") and hasattr(parsed_response, "output"):
                                reasoning = parsed_response.reasoning
                                output = parsed_response.output
                                # 提取estimated_others_avg_ratio和output_ratio（如果存在）
                                estimated_others_avg_ratio = getattr(parsed_response, "estimated_others_avg_ratio", None)
                                output_ratio = getattr(parsed_response, "output_ratio", None)
                                if isinstance(output, (int, float)):
                                    response_content = str(output)
                                else:
                                    response_content = output
                            else:
                                reasoning = None
                                estimated_others_avg_ratio = None
                                output_ratio = None
                                response_content = str(parsed_response)
                        else:
                            params = {
                                "model": self.model,
                                "input": messages
                            }
                            response = self.client.responses.create(**params)
                            raw_response = response.output_text
                            response_content = raw_response
                            reasoning = None
                            estimated_others_avg_ratio = None
                            output_ratio = None
                    elif self.provider == "gemini":
                        # 使用新的Google GenAI SDK调用，支持system instruction
                        system_instruction = ""
                        user_content = ""
                        
                        for msg in messages:
                            if msg["role"] == "system":
                                system_instruction += msg["content"] + "\n\n"
                            elif msg["role"] == "user":
                                user_content += msg["content"] + "\n\n"
                            elif msg["role"] == "assistant":
                                user_content += f"[Previous response: {msg['content']}]\n\n"
                        
                        # 构建GenerateContentConfig
                        config_kwargs = {
                            "thinking_config": types.ThinkingConfig(thinking_budget=0)
                        }
                        
                        # 如果有system instruction，添加到config
                        if system_instruction.strip():
                            config_kwargs["system_instruction"] = system_instruction.strip()
                        
                        # 如果有structured_output要求，添加JSON schema
                        if structured_output:
                            config_kwargs["response_mime_type"] = "application/json"
                            config_kwargs["response_schema"] = structured_output
                        
                        # 创建config对象
                        config = types.GenerateContentConfig(**config_kwargs)
                        
                        # 调用Gemini API
                        response = self.client.models.generate_content(
                            model=self.model,
                            contents=user_content.strip(),
                            config=config
                        )
                        
                        # 处理响应
                        if structured_output:
                            # 使用结构化输出
                            parsed_response = response.parsed
                            if hasattr(parsed_response, "reasoning") and hasattr(parsed_response, "output"):
                                reasoning = parsed_response.reasoning
                                output = parsed_response.output
                                # 提取estimated_others_avg_ratio和output_ratio（如果存在）
                                estimated_others_avg_ratio = getattr(parsed_response, "estimated_others_avg_ratio", None)
                                output_ratio = getattr(parsed_response, "output_ratio", None)
                                if isinstance(output, (int, float)):
                                    response_content = str(output)
                                else:
                                    response_content = output
                            else:
                                reasoning = None
                                estimated_others_avg_ratio = None
                                output_ratio = None
                                response_content = str(parsed_response)
                        else:
                            # 非结构化输出
                            raw_response = response.text.strip()
                            response_content = raw_response
                            reasoning = None
                            estimated_others_avg_ratio = None
                            output_ratio = None
                    elif self.provider == "deepseek":
                        # DeepSeek使用OpenAI兼容API + JSON mode
                        if structured_output:
                            # DeepSeek需要在system prompt中说明JSON格式
                            # 添加JSON输出格式说明到system message
                            schema_instruction = f"\n\nPlease output your response in the following JSON format:\n{json.dumps(structured_output.model_json_schema(), indent=2)}\n\nIMPORTANT: Output ONLY valid JSON, no additional text."
                            
                            # 修改messages,将schema说明加入system prompt
                            modified_messages = messages.copy()
                            if modified_messages and modified_messages[0]["role"] == "system":
                                modified_messages[0] = {
                                    "role": "system",
                                    "content": modified_messages[0]["content"] + schema_instruction
                                }
                            else:
                                modified_messages.insert(0, {
                                    "role": "system", 
                                    "content": schema_instruction
                                })
                            
                            # 使用JSON mode (简化格式)
                            params = {
                                "model": self.model,
                                "messages": modified_messages,
                                "response_format": {
                                    "type": "json_object"  # DeepSeek使用简化的JSON mode
                                }
                            }
                            
                            response = self.client.chat.completions.create(**params)
                            raw_json = response.choices[0].message.content.strip()
                            
                            # 解析JSON为Pydantic对象 (json已在文件顶部导入)
                            parsed_data = json.loads(raw_json)
                            parsed_response = structured_output(**parsed_data)
                            
                            if hasattr(parsed_response, "reasoning") and hasattr(parsed_response, "output"):
                                reasoning = parsed_response.reasoning
                                output = parsed_response.output
                                estimated_others_avg_ratio = getattr(parsed_response, "estimated_others_avg_ratio", None)
                                output_ratio = getattr(parsed_response, "output_ratio", None)
                                if isinstance(output, (int, float)):
                                    response_content = str(output)
                                else:
                                    response_content = output
                            else:
                                reasoning = None
                                estimated_others_avg_ratio = None
                                output_ratio = None
                                response_content = str(parsed_response)
                        else:
                            # 非结构化输出
                            params = {
                                "model": self.model,
                                "messages": messages
                            }
                            response = self.client.chat.completions.create(**params)
                            raw_response = response.choices[0].message.content.strip()
                            response_content = raw_response
                            reasoning = None
                            estimated_others_avg_ratio = None
                            output_ratio = None
                    else:
                        raise ValueError(f"Unsupported provider: {self.provider}")
                    # 检查是否为连接失败
                    if isinstance(response_content, str) and response_content.startswith("LLM调用失败: Connection error"):
                        raise RuntimeError("LLM调用失败: Connection error")
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retry:
                        raise RuntimeError(f"LLM调用失败: Connection error, 已重试{max_retry}次仍未成功。最后错误: {e}")
                    time.sleep(1)
        except Exception as e:
            raw_response = f"LLM调用失败: {str(e)}"
            response_content = raw_response
            reasoning = None
            estimated_others_avg_ratio = None
            output_ratio = None
        
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
                "messages": messages
            },
            "output": {
                # "raw_response": raw_response,
                "content": response_content,
                "reasoning": reasoning if reasoning else None,
                "estimated_others_avg_ratio": estimated_others_avg_ratio if estimated_others_avg_ratio else None,
                "output_ratio": output_ratio if output_ratio else None,
                "structured_output_type": structured_output.__name__ if structured_output else None,
                "status": "success" if not response_content.startswith("LLM调用失败") else "error"
            }
        }
        
        # 添加到智能体的交互历史
        self.llm_interactions.append(interaction_record)
        # 自动写入reasoning记忆（只存字符串）
        if reasoning:
            self.reasoning.append(reasoning)
        
        # 添加调试输出：显示LLM返回结果
        if self.debug_prompts:
            try:
                print(f"\n{'🤖'*40}")
                print(f"【Agent {self.name} 的 LLM 返回结果】")
                print(f"{'🤖'*40}")
                print(f"模型: {self.provider}/{self.model}")
                print(f"耗时: {(end_time - start_time).total_seconds():.2f}秒")
                if structured_output:
                    print(f"\n📊 结构化输出:")
                    if estimated_others_avg_ratio is not None:
                        print(f"  • 估算他人平均投入比例: {estimated_others_avg_ratio}%")
                    if output_ratio is not None:
                        print(f"  • 自己投入比例: {output_ratio}%")
                    print(f"  • 投入金额: {response_content}")
                    if reasoning:
                        print(f"  • 推理过程: {reasoning[:200]}..." if len(reasoning) > 200 else f"  • 推理过程: {reasoning}")
                else:
                    print(f"\n📝 原始输出: {response_content}")
                print(f"{'🤖'*40}\n")
            except Exception as debug_error:
                print(f"调试输出错误: {debug_error}")
        
        return response_content

    def decide_contribution(self, round_number, r, num_players, all_history=None, mode="public", avg_contrib_ratio=None):
        """决定本轮的投入金额
        
        Args:
            round_number: 当前轮数
            r: 公共池倍数
            num_players: 玩家总数
            all_history: 所有玩家的历史记录
            mode: 信息模式 ("public" 或 "anonymous")
            avg_contrib_ratio: 匿名模式下上一轮的平均贡献比例
        """
        # 锚定智能体直接返回全部当前金额（100%投入）
        if self.is_anchor:
            return self.current_total_money

        # 构建提示信息
        # 根据指导语类型确定轮数描述
        instruction_type = GAME_CONFIG.get("instruction_type", "certain")
        total_rounds = GAME_CONFIG.get("rounds", 10)
        
        if instruction_type == "certain":
            round_info = f"当前第 {round_number} 轮，总共有 {total_rounds} 轮"
        else:  # uncertain
            round_info = f"当前第 {round_number} 轮，游戏将持续若干轮，可能在任意一轮结束"
        
        base_prompt = f"""你是玩家"{self.name}"。

        游戏规则：
        - {round_info}
        - 你有 {self.current_total_money} 枚代币可投入公共池（包括初始禀赋和之前的收益），你的投入范围：0 到 {self.current_total_money}
        - 本轮公共池由所有玩家的投入累积形成
        - 公共池总额 × {r} 后，将平均分配给所有玩家"""

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
            
            # 匿名模式下，加入上一轮平均贡献比例
            # if mode == "anonymous" and avg_contrib_ratio is not None:
            #     base_prompt += f"\n上一轮所有玩家平均贡献比例为: {avg_contrib_ratio:.1%}"
            
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
                # 匿名模式：显示每轮他人平均贡献比例
                base_prompt += f"\n\n其他玩家汇总信息："
                for r in range(1, round_number):
                    round_total = 0
                    round_init_total = 0
                    round_count = 0
                    for player_id, player_data in all_history.items():
                        if player_id != self.id:
                            player_history = player_data.get('history', player_data)  # 兼容旧格式
                            if r <= len(player_history):
                                contrib = player_history[r-1]['contribution']
                                # 优先用init_amount，没有则用total_money_before_round，再没有用endowment
                                init_amt = player_history[r-1].get('init_amount', None)
                                if init_amt is None:
                                    init_amt = player_history[r-1].get('total_money_before_round', None)
                                if init_amt is None and r == 1:
                                    init_amt = GAME_CONFIG.get('endowment', 10)
                                round_total += contrib
                                if init_amt is not None and init_amt > 0:
                                    round_init_total += init_amt
                                    round_count += 1
                    if round_count > 0 and round_init_total > 0:
                        avg_contrib_ratio = (round_total / round_init_total) * 100
                        base_prompt += f"\n  第{r}轮: 他人平均贡献比例{avg_contrib_ratio:.1f}%"
                    else:
                        base_prompt += f"\n  第{r}轮: 他人平均贡献比例--%"
        # 添加结构化输出说明
        base_prompt += f"\n\n请完成以下任务："
        base_prompt += f"\n1. 估计其他玩家本轮的平均投入比例（0-100%之间，基于历史表现和当前情况）"
        base_prompt += f"\n2. 决定你本轮的具体投入金额（必须在0–{self.current_total_money}之间的整数）"
        base_prompt += f"\n3. 说明你的完整决策理由（包括：你如何认知其他玩家的行为、你考虑的边际收益和风险、以及你的博弈策略）"
        
        # 使用当前的系统提示（可能已被信念记忆更新）
        current_system_prompt = self.get_current_system_prompt()
        
        messages = [
            {"role": "system", "content": current_system_prompt},
            {"role": "user", "content": base_prompt}
        ]
        
        # 创建用于结构化输出的动态模型
        class DynamicContributionDecision(BaseModel):
            estimated_others_avg_ratio: float = Field(
                ...,
                ge=0,
                le=100,
                description=f"估计其他玩家本轮的平均投入比例（0-100之间的百分比数值，例如50表示50%）"
            )
            output: int = Field(
                ...,
                ge=0,
                le=self.current_total_money,
                description=f"本轮投入金额，必须是 0–{self.current_total_money} 之间的整数"
            )
            output_ratio: float = Field(
                ...,
                ge=0,
                le=100,
                description=f"本轮投入比例（0-100之间的百分比数值，应该等于 output/{self.current_total_money}*100）"
            )
            reasoning: str = Field(
                ...,
                description="完整决策理由：先说明你如何认知其他玩家（为什么估计他们会这样投入），再解释你自己的决策逻辑（考虑边际收益、风险以及博弈策略）"
            )
        
        # 调用LLM，使用结构化输出
        if self.provider in ["openai", "gemini", "deepseek"]:
            # OpenAI, Gemini和DeepSeek都支持结构化输出
            answer = self._call_llm(messages, debug_label="决策阶段", structured_output=DynamicContributionDecision)
        else:
            # 其他模型使用非结构化输出
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
        return f"{base_prompt} 你正在参与公共品博弈。请根据你的性格特征和场景做出合理决策。"

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
        # 先记录本轮开始前的金额
        round_data = {
            'id': self.id,
            'round': round_num,
            'contribution': int(round(contribution)) if self.is_anchor else contribution,
            'group_total': group_total,
            'payoff': payoff,
            'total_money_before_round': int(round(total_money_before_round)) if self.is_anchor and total_money_before_round is not None else total_money_before_round if total_money_before_round is not None else self.current_total_money
        }
        self.history.append(round_data)
        # 再结算本轮后的金额
        if self.is_anchor:
            self.current_total_money = int(round((total_money_before_round if total_money_before_round is not None else self.current_total_money) - contribution + payoff))
        else:
            self.current_total_money = (total_money_before_round if total_money_before_round is not None else self.current_total_money) - contribution + payoff
        return round_data

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

    def _update_belief_memory(self, round_number, reveal_mode, all_history):
        """每轮更新信念记忆，输入为最近reasoning，输出为更宏观的自我反思"""
        if self.is_anchor:
            return  # anchor不更新信念
        # 收集所有 reasoning，全部为字符串
        recent_reasonings = "\n".join(self.reasoning[-3:])  # 取最近3轮，也可调整为全部
        
        # 构建system prompt
        current_system = self.get_current_system_prompt()
        system_prompt = f"""{current_system}

你当前需要根据最近几轮的思考摘要，对你的信念进行更新：
- 输出为一个简洁段落，不包含数字或轮次细节
- 段落中体现行为风格、价值观、自我认知
- 保持整体风格连贯"""
        
        # 构建user prompt
        user_prompt = f"""以下是最近几轮的思考摘要：
{recent_reasonings}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        # 调用 LLM，直接获取文本输出（不需要reasoning）
        updated_personality = self._call_llm(messages, debug_label="信念更新")
        
        # 记录信念记忆
        self.belief_memory.append({
            "round": round_number,
            "updated_personality": updated_personality,
            "prompt": user_prompt
        })
        # 信念更新后自动更新system_prompt，自动将“我”替换为“你”
        self.system_prompt = updated_personality.replace("我", "你")

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
        - 公共池总额 × {r} 后平分给所有玩家
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
        if self.provider in ["openai", "gemini", "deepseek"]:
            # OpenAI, Gemini和DeepSeek都支持结构化输出
            answer = self._call_llm(messages, debug_label="最终一次性决策", structured_output=FinalDecision)
        else:
            # 其他模型使用非结构化输出
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
                                info_text += f"\n  玩家{player_id}: {contrib}/{total_before}(投入比例：{ratio:.1f}%)"
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
