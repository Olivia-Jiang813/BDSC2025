"""
批量实验运行脚本
用于系统化地运行公共品博弈实验，并收集和分析结果

使用说明：
1. 在下方设置要循环的变量列表
2. 不需要循环的变量会使用 config.py 中的默认值
3. 运行：python run_experiments.py
"""

import time
import glob
import os
from main import main
from config import GAME_CONFIG

# ============ 实验参数设置 ============
# 设置要循环的变量（用列表表示），不循环的变量注释掉或设为单个值

# 模型设置
models = ["deepseek-chat",'gemini-2.5-flash','gpt-4.1']  # 可选：["gpt-4.1", "gpt-4.1-mini", "glm-4-flash"] gemini-2.5-flash

# 游戏基础参数
rounds_list = [10]  # 游戏轮数
num_players_list = [10]  # 玩家数量

# 实验条件参数
anchor_ratios = [0, 0.1, 0.2]  # Anchor比例，可选：[0, 0.1, 0.2, 0.3]
reveal_modes = ['public','anonymous']  # 信息公开模式 ['public',"anonymous"]
instruction_types = ['certain','uncertain']  # 指导语类型 "uncertain"
personality_types = ["neutral"]  # 性格类型，可选：["selfish", "neutral", "altruistic"]

# anchor_ratios = [0]  # Anchor比例，可选：[0, 0.1, 0.2, 0.3]
# reveal_modes = ['anonymous']  # 信息公开模式 ['public',"anonymous"]
# instruction_types = ['certain',]  # 指导语类型 "uncertain"
# personality_types = ["neutral"]  # 性格类型，可选：["selfish", "neutral", "altruistic"]

# 重复次数
repeat = 3  # 每组参数重复实验的次数

# ============ 辅助函数 ============
def check_experiment_exists(model, rounds, num_players, anchor_ratio, reveal_mode, instruction_type, personality_type, required_count=3):
    """
    检查指定条件的实验是否已经完成足够次数
    
    Args:
        model: 模型名称
        rounds: 轮数
        num_players: 玩家数
        anchor_ratio: anchor比例
        reveal_mode: 信息公开模式
        instruction_type: 指导语类型
        personality_type: 性格类型
        required_count: 需要的完成次数（默认3次）
    
    Returns:
        bool: 如果已完成足够次数返回True，否则返回False
    """
    # 构建文件名模式（不包含时间戳）
    anchor_pct = int(anchor_ratio * 100)
    pattern = f"game_history/{model}_{personality_type}_{num_players}p_{rounds}r_{reveal_mode}_anchor{anchor_pct}pct_{instruction_type}_completed_*.json"
    
    # 查找匹配的文件
    matching_files = glob.glob(pattern)
    
    # 返回是否已完成足够次数
    existing_count = len(matching_files)
    if existing_count >= required_count:
        print(f"  ✓ 跳过：该条件已完成 {existing_count} 次实验")
        return True
    elif existing_count > 0:
        print(f"  → 继续：该条件已完成 {existing_count}/{required_count} 次，需要补充 {required_count - existing_count} 次")
    return False

# ============ 批量运行函数 ============
def run_batch():
    """批量运行实验"""
    total_experiments = (len(models) * len(rounds_list) * len(num_players_list) * 
                        len(anchor_ratios) * len(reveal_modes) * 
                        len(instruction_types) * len(personality_types) * repeat)
    
    print(f"\n{'='*60}")
    print(f"总共需要运行 {total_experiments} 个实验")
    print(f"{'='*60}\n")
    
    experiment_count = 0
    skipped_count = 0
    
    for model in models:
        for rounds in rounds_list:
            for num_players in num_players_list:
                for anchor_ratio in anchor_ratios:
                    for reveal_mode in reveal_modes:
                        for instruction_type in instruction_types:
                            for personality_type in personality_types:
                                # 检查该条件是否已完成足够次数
                                if check_experiment_exists(model, rounds, num_players, anchor_ratio, 
                                                         reveal_mode, instruction_type, personality_type, 
                                                         required_count=repeat):
                                    skipped_count += repeat
                                    continue
                                
                                # 如果未完成足够次数，运行实验
                                for i in range(repeat):
                                    experiment_count += 1
                                    print(f"\n{'='*60}")
                                    print(f"实验 {experiment_count}/{total_experiments - skipped_count}")
                                    print(f"参数: model={model}, rounds={rounds}, players={num_players}")
                                    print(f"      anchor_ratio={anchor_ratio}, reveal_mode={reveal_mode}")
                                    print(f"      instruction_type={instruction_type}, personality={personality_type}")
                                    print(f"      重复次数: {i+1}/{repeat}")
                                    print(f"{'='*60}")
                                    
                                    # 运行实验（启用debug模式打印prompt）
                                    main(
                                        model=model,  # 传递模型参数
                                        endowment=GAME_CONFIG.get("endowment", 10),
                                        rounds=rounds,
                                        r=GAME_CONFIG.get("r", 3),
                                        num_players=num_players,
                                        personality_type=personality_type,
                                        reveal_mode=reveal_mode,
                                        anchor_ratio=anchor_ratio,
                                        instruction_type=instruction_type,
                                        debug_prompts=True  # 启用prompt调试输出
                                    )
                                    
                                    # 实验间休息
                                    if experiment_count < total_experiments - skipped_count:
                                        time.sleep(2)
    
    print(f"\n{'='*60}")
    print(f"所有实验完成！")
    print(f"  - 实际运行: {experiment_count} 个实验")
    print(f"  - 跳过已完成: {skipped_count} 个实验")
    print(f"  - 总计: {total_experiments} 个实验")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_batch()