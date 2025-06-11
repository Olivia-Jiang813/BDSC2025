# game_controller.py
import random
import signal
import sys
from agents import Agent
from config import GAME_CONFIG
from rooms import ContributeRoom, DiscussionRoom
from game_recorder import GameRecorder

class GameController:
    def __init__(self, config):
        """Initialize the game controller
        
        Args:
            config: Game configuration dictionary
        """
        self.config = config
        self.agents = []
        self.current_round = 0
        self.reveal_mode = config["reveal_mode"]
        self.allow_discussion = config["allow_discussion"]

        # 初始化游戏记录器
        self.recorder = GameRecorder()

    def setup_game(self):
        """初始化游戏，创建智能体"""
        # 创建普通智能体
        num_agents = self.config["num_players"]
        if self.config["use_anchor_agent"]:
            # 如果使用锚定智能体，则减少一个普通智能体
            num_normal_agents = num_agents - 1
        else:
            num_normal_agents = num_agents
            
        # 创建普通智能体
        for i in range(num_normal_agents):
            agent = Agent(
                agent_id=str(i),
                personality_type=self.config["personality_type"]
            )
            self.agents.append(agent)
            
        # 如果启用了锚定智能体，添加一个锚定智能体
        if self.config["use_anchor_agent"]:
            anchor_agent = Agent(
                agent_id=str(num_agents-1),
                personality_type="anchor",
                is_anchor=True
            )
            self.agents.append(anchor_agent)

    def signal_handler(self, signum, frame):
        """处理程序意外退出的情况"""
        print("\n\n检测到程序退出信号，正在保存当前进度...")
        self.save_game_state()
        sys.exit(0)

    def save_game_state(self):
        """保存当前游戏状态"""
        if self.current_round > 0:  # 只在游戏已经开始后保存
            game_config = {
                "endowment": self.config["endowment"],
                "r": self.config["r"],
                "rounds": self.config["rounds"],
                "num_players": len(self.agents),
                "completed_rounds": self.current_round
            }
            self.recorder.save_game_history(game_config, self.agents, interrupted=True)
            print(f"已保存到第 {self.current_round} 回合的游戏记录")

    def reveal_contributions(self, contributions):
        """根据不同的揭示模式返回贡献信息"""
        if self.reveal_mode == "public":
            return {agent.id: contrib for agent, contrib in contributions.items()}
        else:  # anonymous
            return {"总贡献": sum(contributions.values())}

    def run_discussion(self, agents):
        """根据讨论设置运行讨论阶段"""
        if not self.allow_discussion:
            return []

        discussion_log = []
        for agent in agents:
            # 获取记忆摘要
            memory_summary = agent.get_memory_summary(num_rounds=3)  # 最近3轮的记忆
            
            # 根据揭示模式准备上下文
            contribution_info = self.reveal_contributions(
                {a.id: a.history[-1]['contribution'] for a in agents if a.history}
            )
            
            # 准备讨论消息
            message = f"根据当前情况和历史记录：\n{memory_summary}\n"
            message += f"贡献信息：{contribution_info}\n"
            message += "请发表你对下一轮的看法。"
            
            # 记录讨论到智能体的记忆
            agent.record_memory(
                round_num=self.current_round,
                event_type='discussion',
                details=message
            )
            discussion_log.append({
                'agent_id': agent.id,
                'message': message
            })
            
        return discussion_log

    def calculate_payoffs(self, contributions):
        """计算一轮游戏中每个玩家的收益
        每轮public pool独立计算，不累积，但玩家的endowment会累积
        """
        # 计算本轮public pool相关的值
        total_contribution = sum(contributions.values())
        public_pool = total_contribution * self.config["r"]
        share_per_player = public_pool / len(self.agents)
        
        # 计算每个玩家的收益：现有禀赋 - 投入 + 分成
        payoffs = {}
        for agent in self.agents:
            contribution = contributions.get(agent.id, 0)
            # 保留现有禀赋，减去投入，加上本轮分成
            remaining = agent.get_current_endowment() - contribution
            payoff = remaining + share_per_player
            payoffs[agent.id] = payoff
        
        return payoffs, {
            "total_contribution": total_contribution,
            "public_pool": public_pool,
            "share_per_player": share_per_player
        }

    def play(self):
        """运行完整游戏流程"""
        try:
            # 初始化游戏状态
            self.last_payoffs = {ag.id: self.config["endowment"] for ag in self.agents}
            
            for round_num in range(1, self.config["rounds"] + 1):
                self.current_round = round_num
                print(f"\n{'='*20} 第 {round_num} 轮 {'='*20}")
                
                # 显示当前状态
                print("\n当前禀赋:")
                for agent in self.agents:
                    print(f"{agent.id}: {self.last_payoffs[agent.id]:.2f}")
                    
                # 执行一轮游戏
                round_data = self.play_round()
                
                # 更新游戏状态
                for agent_id, payoff in round_data['payoffs'].items():
                    self.last_payoffs[agent_id] = payoff
                    
                # 显示本轮摘要
                print(self.recorder.format_round_summary(
                    round_num,
                    round_data['stats'],
                    round_data['agents_data']
                ))
                
                # 记录本轮数据
                self.recorder.record_round(
                    round_num,
                    round_data['stats'],
                    round_data['agents_data']
                )
                
            # 游戏正常结束时的处理
            print("\n=== 游戏正常结束 ===")
            
        except Exception as e:
            print(f"\n游戏过程中发生错误: {str(e)}")
            self.save_game_state()  # 发生错误时保存当前进度
            raise

    def play_round(self):
        """执行一轮游戏的具体流程"""
        round_data = {
            'round': self.current_round,
            'contributions': {},
            'measurements': {},
            'discussion': [] if self.allow_discussion else None,
            'stats': {}
        }
        
        # 1. 收集贡献决策
        print("\n=== 各玩家本轮决策 ===")
        for agent in self.agents:
            contribution = agent.decide_contribution(
                self.current_round,
                self.config["endowment"],
                self.config["r"],  # multiplier是r
                len(self.agents)
            )
            contribution = min(contribution, agent.get_current_endowment())  # 确保不超过当前禀赋
            round_data['contributions'][agent.id] = contribution
            print(f"\n玩家 {agent.id}{'（锚定智能体）' if agent.is_anchor else ''}:")
            print(f"- 当前禀赋: {agent.get_current_endowment():.2f}")
            print(f"- 决定投入: {contribution:.2f}")
            
        # 2. 测量阶段
        for agent in self.agents:
            measurements = self._collect_measurements(agent)
            round_data['measurements'][agent.id] = measurements
        
        # 3. 计算本轮收益
        payoffs, stats = self.calculate_payoffs(round_data['contributions'])
        round_data['payoffs'] = payoffs
        round_data['stats'] = stats
        
        # 4. 讨论阶段（如果允许）
        if self.allow_discussion: 
            round_data['discussion'] = self._conduct_discussion(round_data)
            
        # 5. 更新记忆
        for agent in self.agents:
            # 根据reveal_mode准备其他人的贡献信息
            if self.reveal_mode == "public":
                others_contributions = {
                    a_id: contrib for a_id, contrib in round_data['contributions'].items()
                    if a_id != agent.id
                }
            else:
                others_contributions = None
                
            # 获取相关的讨论信息
            discussion_messages = None
            if self.allow_discussion and round_data['discussion']:
                discussion_messages = [
                    msg for msg in round_data['discussion']
                    if msg['agent_id'] != agent.id
                ]
                
            # 更新记忆
            agent.update_memory(
                round_number=self.current_round,
                own_contribution=round_data['contributions'][agent.id],
                own_measurement=round_data['measurements'][agent.id],
                reveal_mode=self.reveal_mode,
                public_pool_share=round_data['stats']['share_per_player'],
                others_contributions=others_contributions,
                discussion_messages=discussion_messages
            )
        
        # 6. 准备agent数据用于记录
        round_data['agents_data'] = [{
            "id": agent.id,
            "initial_endowment": agent.get_current_endowment(),
            "contribution": round_data['contributions'][agent.id],
            "payoff": round_data['payoffs'][agent.id],
            "memory": agent.memory_log[-1] if agent.memory_log else None  # 添加记忆内容
        } for agent in self.agents]
        
        # 每轮保存游戏状态
        self.save_game_state()
        
        # 打印每个智能体的记忆内容
        print("\n=== 智能体记忆 ===")
        for agent in self.agents:
            if agent.memory_log:
                print(f"\n玩家 {agent.id} 的记忆：\n{agent.memory_log[-1]['summary']}")
        
        return round_data
        
    def _collect_measurements(self, agent):
        """收集测量数据"""
        # 构建提示，要求智能体估计其他人的平均贡献
        other_agents_count = len(self.agents) - 1
        
        # 如果是第一轮，就不提供历史贡献信息
        if not agent.history:
            prompt = f"""请估计其他 {other_agents_count} 位玩家的平均投入会是多少？
            只需输出一个数字，范围 0-{self.config["endowment"]}。"""
        else:
            prompt = f"""本轮你投入了 {agent.history[-1]['contribution']} 代币。
            请估计其他 {other_agents_count} 位玩家的平均投入是多少？
            只需输出一个数字，范围 0-{self.config["endowment"]}。"""
        
        messages = [
            {"role": "system", "content": "你需要基于已知信息，估计其他玩家的平均投入。"},
            {"role": "user", "content": prompt}
        ]
        
        estimated_avg = agent._call_llm(messages)
        try:
            estimated_avg = float(estimated_avg)
        except ValueError:
            estimated_avg = self.config["endowment"] / 2  # 默认值
            
        return {
            'estimated_avg_contribution': estimated_avg
            # 可以添加更多测量
        }
        
    def _conduct_discussion(self, round_data):
        """执行讨论阶段"""
        discussion_log = []
        for agent in self.agents:
            # 获取当前轮的投入数据
            current_contribution = round_data['contributions'].get(agent.id)
            
            # 获取其他人的信息（包括当前轮的投入）
            others_info = self._get_others_info(agent, current_contributions=round_data['contributions'])
            
            # 根据是否是第一轮，提供不同的历史信息
            if not agent.history:
                message = agent.speak_in_discussion(
                    round_number=self.current_round,
                    last_contribution=current_contribution,  # 使用当前轮的投入
                    last_payoff=None,
                    others=others_info
                )
            else:
                message = agent.speak_in_discussion(
                    round_number=self.current_round,
                    last_contribution=current_contribution,  # 使用当前轮的投入
                    last_payoff=agent.history[-1]['payoff'],
                    others=others_info
                )
                
            # 只有当讨论有内容时才记录
            if message:
                discussion_log.append({
                    'agent_id': agent.id,
                    'message': message
                })
                # 打印讨论内容
                print(f"\n玩家 {agent.id}{'（锚定智能体）' if agent.is_anchor else ''} 的讨论：\n{message}")
            else:
                print(f"\n玩家 {agent.id}{'（锚定智能体）' if agent.is_anchor else ''} 没有参与讨论")
                
        return discussion_log if discussion_log else None  # 如果没有任何有效讨论，返回None
        
    def _get_others_info(self, agent, current_contributions=None):
        """获取其他玩家的信息，用于讨论
        
        Args:
            agent: 当前智能体
            current_contributions: 当前轮所有玩家的贡献，用于讨论阶段
        """
        if self.reveal_mode == "public":
            others = []
            for ag in self.agents:
                if ag != agent:
                    if current_contributions:
                        contribution = current_contributions.get(ag.id)
                    else:
                        contribution = ag.history[-1]['contribution'] if ag.history else None
                        
                    others.append({
                        "id": ag.id,
                        "last_contribution": contribution,
                        "last_payoff": ag.history[-1]['payoff'] if ag.history else None,
                        "current_endowment": ag.get_current_endowment()
                    })
            return others
        else:  # anonymous模式
            # 只返回总体信息
            total_contribution = 0
            total_agents = len(self.agents) - 1  # 不包括当前智能体
            
            if current_contributions:
                # 使用当前轮的贡献数据
                for ag_id, contrib in current_contributions.items():
                    if ag_id != agent.id:
                        total_contribution += contrib
            else:
                # 使用历史数据
                for ag in self.agents:
                    if ag != agent and ag.history:
                        total_contribution += ag.history[-1]['contribution']
                        
            return {
                "total_agents": total_agents,
                "total_contribution": total_contribution,
                "avg_contribution": total_contribution / total_agents if total_agents > 0 and total_contribution > 0 else None
            }


