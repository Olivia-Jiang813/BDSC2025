# game_controller.py
import random
import signal
import sys
from agents import Agent
from config import GAME_CONFIG, MODEL_CONFIG
from game_recorder import GameRecorder

class GameController:
    def __init__(self, config):
        """Initialize the game controller
        
        Args:
            config: Game configuration dictionary
        """
        self.config = config
        print(f"[game_controller.py] 初始化时 config: {self.config}")
        self.agents = []
        self.current_round = 0
        self.reveal_mode = config["reveal_mode"]
        # 移除讨论相关功能
        # self.allow_discussion = config["allow_discussion"]

        # 初始化游戏记录器
        self.recorder = GameRecorder()

    def set_debug_mode(self, debug=True):
        """设置所有智能体的调试模式"""
        for agent in self.agents:
            agent.set_debug_mode(debug)

    def setup_game(self):
        """初始化游戏，创建智能体"""
        num_agents = self.config["num_players"]
        anchor_ratio = self.config.get("anchor_ratio", 0)
        num_anchors = int(num_agents * anchor_ratio)
        if anchor_ratio > 0 and num_anchors == 0:
            num_anchors = 1  # 至少1个anchor
        # 随机选取anchor的位置
        anchor_indices = set(random.sample(range(num_agents), num_anchors))
        for i in range(num_agents):
            if i in anchor_indices:
                agent = Agent(
                    agent_id=str(i),
                    personality_type="anchor",
                    is_anchor=True,
                    model=self.config.get("model"),
                    provider=self.config.get("provider")
                )
            else:
                agent = Agent(
                    agent_id=str(i),
                    personality_type=self.config["personality_type"],
                    model=self.config.get("model"),
                    provider=self.config.get("provider")
                )
            self.agents.append(agent)

    def signal_handler(self, signum, frame):
        """处理程序意外退出的情况"""
        print("\n\n检测到程序退出信号，正在保存当前进度...")
        self.save_game_state(interrupted=True)
        sys.exit(0)

    def conduct_final_decision(self):
        """进行游戏结束后的最终一次性PGG决策"""
        final_decisions = {}
        print("\n各玩家进行最终一次性PGG决策:")
        
        for agent in self.agents:
            final_contribution = agent.make_final_decision(
                initial_endowment=self.config["endowment"],
                r=self.config["r"],
                num_players=len(self.agents)
            )
            final_decisions[agent.id] = final_contribution
            print(f"玩家 {agent.id}: 最终一次性投入 {final_contribution}")
            
        return final_decisions

    def save_game_state(self, interrupted=True, final_decisions=None):
        """保存当前游戏状态"""
        if self.current_round > 0:  # 只在游戏已经开始后保存
            game_config = {
                "model": self.config["model"],  # ✅ 使用实际传入的model
                "provider": self.config.get("provider", "openai"),  # ✅ 添加provider
                "personality_type": self.config["personality_type"],
                "endowment": self.config["endowment"],
                "r": self.config["r"],
                "rounds": self.config["rounds"],
                "num_players": len(self.agents),
                "reveal_mode": self.config["reveal_mode"],
                "completed_rounds": self.current_round,
                "final_decisions": final_decisions,  # 添加最终决策数据
                "anchor_ratio": self.config.get("anchor_ratio", None),  # 确保anchor_ratio写入
                "instruction_type": self.config.get("instruction_type", "certain")  # 确保instruction_type写入
            }
            self.recorder.save_game_history(game_config, self.agents, interrupted=interrupted)
            if interrupted:
                print(f"已保存到第 {self.current_round} 回合的游戏记录")
            else:
                print(f"游戏完成，已保存完整游戏记录（包含最终决策）")

    def reveal_contributions(self, contributions):
        """根据不同的揭示模式返回贡献信息"""
        if self.reveal_mode == "public":
            return {agent.id: contrib for agent, contrib in contributions.items()}
        else:  # anonymous
            return {"总贡献": sum(contributions.values())}

    def calculate_payoffs(self, contributions):
        """计算一轮游戏中每个玩家的收益
        每轮public pool独立计算，不累积，但玩家的total_money会累积
        """
        # 计算本轮public pool相关的值
        total_contribution = sum(contributions.values())
        public_pool = total_contribution * self.config["r"]
        share_per_player = public_pool / len(self.agents)
        
        # 计算每个玩家的收益：现有总金额 - 投入 + 分成
        payoffs = {}
        for agent in self.agents:
            contribution = contributions.get(agent.id, 0)
            # 保留现有总金额，减去投入，加上本轮分成
            remaining = agent.current_total_money - contribution
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
                print("\n当前总金额:")
                for agent in self.agents:
                    print(f"{agent.id}: {agent.current_total_money:.2f}")
                    
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
                
            # 游戏正常结束后，进行最终一次性PGG决策
            print("\n=== 最终一次性PGG决策 ===")
            final_decisions = self.conduct_final_decision()
            
            # 游戏正常结束时的处理
            print("\n=== 游戏正常结束 ===")
            self.save_game_state(interrupted=False, final_decisions=final_decisions)  # 保存完成状态的游戏记录
            
        except Exception as e:
            print(f"\n游戏过程中发生错误: {str(e)}")
            self.save_game_state(interrupted=True)  # 发生错误时保存当前进度
            raise

    def play_round(self):
        """执行一轮游戏的具体流程"""
        round_data = {
            'round': self.current_round,
            'contributions': {},
            'stats': {}
        }
        
        # 收集所有智能体的历史记录用于决策
        all_history = {}
        initial_total_money = {}  # 记录本轮开始前每个玩家的总金额
        for agent in self.agents:
            all_history[agent.id] = agent.history
            initial_total_money[agent.id] = agent.current_total_money  # 记录本轮开始前的总金额
        
        # 将当前轮的总金额信息添加到all_history中，供其他玩家参考
        all_history_with_current_money = {}
        for agent_id, history in all_history.items():
            all_history_with_current_money[agent_id] = {
                'history': history,
                'current_total_money': initial_total_money[agent_id]
            }
        
        # 计算上一轮平均贡献比例（仅anonymous模式下）
        avg_contrib_ratio = None
        if self.reveal_mode == 'anonymous' and self.current_round > 1:
            prev_agents_data = self.recorder.round_records[-1]["agents"]
            ratios = []
            for a in prev_agents_data:
                initial_money = a.get('total_money_before_round', a.get('initial_total_money', a.get('initial_endowment', 10)))
                ratio = a['contribution'] / initial_money if initial_money else 0
                ratios.append(ratio)
            avg_contrib_ratio = sum(ratios) / len(ratios) if ratios else 0
        # 1. 收集贡献决策
        print("\n=== 各玩家本轮决策 ===")
        for agent in self.agents:
            contribution = agent.decide_contribution(
                self.current_round,
                self.config["r"],
                len(self.agents),
                all_history_with_current_money,
                self.reveal_mode,
                avg_contrib_ratio=avg_contrib_ratio
            )
            contribution = min(contribution, agent.current_total_money)  # 确保不超过当前总金额
            round_data['contributions'][agent.id] = contribution
            print(f"\n玩家 {agent.id}{'（锚定智能体）' if agent.is_anchor else ''}:")
            print(f"- 当前总金额: {agent.current_total_money:.2f}")
            print(f"- 决定投入: {contribution:.2f}")
            
        # 2. 计算本轮收益
        payoffs, stats = self.calculate_payoffs(round_data['contributions'])
        round_data['payoffs'] = payoffs
        round_data['stats'] = stats
        
        # 3. 更新记忆，并收集每个agent本轮数据
        agents_data = []
        for agent in self.agents:
            # 先记录本轮的基础游戏数据到agent.history，并获取本轮数据
            agent_round_data = agent.record_round_data(
                round_num=self.current_round,
                contribution=round_data['contributions'][agent.id],
                group_total=round_data['stats']['total_contribution'],
                payoff=round_data['payoffs'][agent.id],
                total_money_before_round=initial_total_money[agent.id]
            )
            agents_data.append(agent_round_data)
            # 然后更新智能体的记忆（此时history已包含当前轮数据）
            agent.update_memory(
                round_number=self.current_round,
                own_contribution=round_data['contributions'][agent.id],
                payoff=round_data['payoffs'][agent.id],
                reveal_mode=self.reveal_mode,
                all_history=all_history
            )
        round_data['agents_data'] = agents_data
        # 信念每轮都更新
        self._update_agents_memory(all_history)
        return round_data
    
    def _update_agents_memory(self, all_history):
        """统一更新所有智能体的信念记忆（每轮都更新）"""
        print("\n=== 信念记忆更新 ===")
        for agent in self.agents:
            agent._update_belief_memory(self.current_round, self.reveal_mode, all_history)
            if agent.belief_memory:
                print(f"\n玩家 {agent.id} 的信念记忆更新：\n{agent.belief_memory[-1]['updated_personality']}")


