"""
批量实验运行脚本
用于系统化地运行公共品博弈实验，并收集和分析结果
"""

import os
import time
from main import main
from config import GAME_CONFIG

# 你要的 anchor_ratio 和 reveal_mode 组合
anchor_ratios = [0.1, 0, 0.2]
reveal_modes = ["public", "anonymous"]

def run_batch():
    for anchor_ratio in anchor_ratios:
        for reveal_mode in reveal_modes:
            print(f"\n===== 运行 anchor_ratio={anchor_ratio}, reveal_mode={reveal_mode} =====")
            # 复制默认配置并设置参数
            params = dict(GAME_CONFIG)
            params["anchor_ratio"] = anchor_ratio
            params["reveal_mode"] = reveal_mode
            # 只传递 main 支持的参数
            main(
                endowment=params.get("endowment", 10),
                rounds=params.get("rounds", 10),
                r=params.get("r", 2),
                num_players=params.get("num_players", 10),
                personality_type=params.get("personality_type", "neutral"),
                reveal_mode=reveal_mode,
                anchor_ratio=anchor_ratio
            )
            time.sleep(2)

if __name__ == "__main__":
    run_batch()