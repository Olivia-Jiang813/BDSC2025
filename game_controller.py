# game_controller.py
import random
import signal
import sys
from agents import Agent
from config import GAME_CONFIG
from rooms import ContributeRoom, DiscussionRoom, InterventionRoom
from game_recorder import GameRecorder

class GameController:
    def __init__(self, agents, endowment=None, r=None, rounds=None):
        """初始化游戏控制器
        
        Args:
            agents: Agent列表
            endowment: 每轮初始禀赋
            r: 公共池倍数
            rounds: 游戏轮数
        """
        self.agents = agents
        self.base_endowment = endowment or GAME_CONFIG["endowment"]
        self.r = r or GAME_CONFIG["r"]
        self.rounds = rounds or GAME_CONFIG["rounds"]
        
        # 初始化每个玩家的当前禀赋
        self.current_endowments = {ag.name: self.base_endowment for ag in agents}
        
        # 随机确定一个固定的贡献顺序
        self.contribution_order = list(self.agents)
        random.shuffle(self.contribution_order)
        print("本局游戏的贡献顺序：", " -> ".join([agent.name for agent in self.contribution_order]))
        
        # 验证玩家数量
        actual_count = len(agents)
        expected_count = GAME_CONFIG["num_players"]
        if actual_count != expected_count:
            raise ValueError(f"玩家数量不匹配：当前 {actual_count} 人，需要 {expected_count} 人")
        
        # 初始化游戏记录器
        self.recorder = GameRecorder()
        
        # 记录当前回合数
        self.current_round = 0
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """处理程序意外退出的情况"""
        print("\n\n检测到程序退出信号，正在保存当前进度...")
        self.save_game_state()
        sys.exit(0)

    def save_game_state(self):
        """保存当前游戏状态"""
        if self.current_round > 0:  # 只在游戏已经开始后保存
            game_config = {
                "endowment": self.base_endowment,
                "r": self.r,
                "rounds": self.rounds,
                "num_players": len(self.agents),
                "completed_rounds": self.current_round
            }
            self.recorder.save_game_history(game_config, self.agents, interrupted=True)
            print(f"已保存到第 {self.current_round} 回合的游戏记录")

    def calculate_payoffs(self, contributions):
        """计算一轮游戏中每个玩家的收益
        每轮public pool独立计算，不累积，但玩家的endowment会累积
        """
        # 计算本轮public pool相关的值
        total_contribution = sum(contributions.values())
        public_pool = total_contribution * self.r
        share_per_player = public_pool / len(self.agents)
        
        # 计算每个玩家的收益：现有禀赋 - 投入 + 分成
        payoffs = {}
        for agent in self.agents:
            contribution = contributions.get(agent.name, 0)
            # 保留现有禀赋，减去投入，加上本轮分成
            remaining = self.current_endowments[agent.name] - contribution
            payoff = remaining + share_per_player
            payoffs[agent.name] = payoff
        
        return payoffs, {
            "total_contribution": total_contribution,
            "public_pool": public_pool,
            "share_per_player": share_per_player
        }

    def play(self):
        """运行游戏主循环"""
        try:
            num_players = len(self.agents)
            rooms = {
                "ContributeRoom": ContributeRoom(self.base_endowment, self.r, num_players),
                "DiscussionRoom": DiscussionRoom(),
                "InterventionRoom": InterventionRoom(),
            }
            last_payoffs = {ag.name: None for ag in self.agents}

            for t in range(1, self.rounds + 1):
                self.current_round = t  # 更新当前回合数
                # 显示每个玩家的当前禀赋
                print("\n当前禀赋:")
                for ag in self.agents:
                    print(f"{ag.name}: {self.current_endowments[ag.name]:.2f}")
                print("")
                
                # 讨论阶段：所有玩家同时决定是否参与讨论
                discussion_participants = []
                discussion_decisions = {}
                
                # 所有玩家同时决定是否参与讨论
                for ag in self.agents:
                    should_join = rooms["DiscussionRoom"].should_enter_discussion(
                        ag,
                        {
                            "round": t,
                            "last_payoff": last_payoffs[ag.name],
                            "current_endowment": self.current_endowments[ag.name],
                            "prev_round_contributions": getattr(self, 'prev_round_contributions', {}),
                            "base_endowment": self.base_endowment
                        }
                    )
                    discussion_decisions[ag.name] = should_join
                    if should_join:
                        discussion_participants.append(ag)
                
                # 如果有人参与讨论，进行讨论
                discussion_summary = None
                if discussion_participants:
                    print(f"\n=== 第 {t} 轮讨论阶段 ===")
                    print(f"参与讨论的玩家：{', '.join([ag.name for ag in discussion_participants])}")
                    
                    # 所有参与者同时进行讨论
                    for ag in discussion_participants:
                        others = [
                            {"name": o.name,
                             "payoff": last_payoffs[o.name],
                             "current_endowment": self.current_endowments[o.name]}
                            for o in self.agents if o.name != ag.name
                        ]
                        rooms["DiscussionRoom"].handle(ag, t, {
                            "last_payoff": last_payoffs[ag.name],
                            "current_endowment": self.current_endowments[ag.name],
                            "others": others,
                            "participated": True
                        })
                    
                    # 记录非参与者
                    for ag in self.agents:
                        if ag not in discussion_participants:
                            rooms["DiscussionRoom"].record_non_participant(ag, t)
                    
                    # 获取讨论总结
                    discussion_summary = rooms["DiscussionRoom"].get_discussion_summary()
                
                # 按固定顺序进行贡献
                contributions = {}
                print(f"\n=== 第 {t} 轮贡献阶段 ===")
                for ag in self.contribution_order:
                    rooms["ContributeRoom"].endowment = self.current_endowments[ag.name]
                    c = rooms["ContributeRoom"].handle(
                        ag, t, last_payoffs[ag.name], 
                        discussion_summary=discussion_summary
                    )
                    c = min(c, self.current_endowments[ag.name])
                    contributions[ag.name] = c
                
                # 保存本轮贡献记录，供下一轮使用
                self.prev_round_contributions = contributions.copy()

                # 计算本轮收益
                payoffs, stats = self.calculate_payoffs(contributions)
                
                # 准备本轮的玩家数据
                agents_data = []
                for ag in self.agents:
                    contribution = contributions.get(ag.name, 0)
                    payoff = payoffs[ag.name]
                    last_payoffs[ag.name] = payoff
                    
                    agent_data = {
                        "name": ag.name,
                        "initial_endowment": self.current_endowments[ag.name],
                        "contribution": contribution,
                        "payoff": payoff
                    }
                    agents_data.append(agent_data)
                    
                    # 更新历史记录
                    ag.history.append(agent_data)
                    
                    # 更新下一轮的禀赋
                    self.current_endowments[ag.name] = payoff
                
                # 记录并显示本轮摘要
                self.recorder.record_round(t, stats, agents_data)
                print(self.recorder.format_round_summary(t, stats, agents_data))

                # 每回合结束后都保存一次进度
                if t % 5 == 0:  # 每5轮保存一次
                    self.save_game_state()

            # 游戏正常结束，保存完整记录
            game_config = {
                "endowment": self.base_endowment,
                "r": self.r,
                "rounds": self.rounds,
                "num_players": len(self.agents),
                "completed_rounds": self.rounds
            }
            self.recorder.save_game_history(game_config, self.agents, interrupted=False)
            
        except Exception as e:
            print(f"\n游戏过程中发生错误: {str(e)}")
            self.save_game_state()  # 保存当前进度
            raise  # 重新抛出异常
