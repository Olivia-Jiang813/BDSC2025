"""
批量实验运行脚本
用于系统化地运行公共品博弈实验，并收集和分析结果
"""

import os
import time
import json
import itertools
from datetime import datetime
from typing import Dict, List, Any, Tuple
import pandas as pd
from main import main
from config import GAME_CONFIG, EXPERIMENT_CONFIG

class ExperimentRunner:
    """实验运行器，负责批量运行实验并收集结果"""
    
    def __init__(self, results_dir: str = "experiment_results"):
        self.results_dir = results_dir
        self.history_dir = "game_history"
        self.ensure_dirs()
        
    def ensure_dirs(self):
        """确保结果目录存在"""
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    def run_single_experiment(self, **kwargs) -> Dict[str, Any]:
        """运行单个实验"""
        start_time = datetime.now()
        
        try:
            print(f"\n{'='*60}")
            print(f"开始实验: {kwargs}")
            print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            # 运行游戏
            main(**kwargs)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 获取最新的游戏历史文件
            history_file, text_file = self.get_latest_history_files()
            
            result = {
                "experiment_params": kwargs,
                "start_time": start_time.isoformat(),
                "history_files": {
                    "json": history_file,
                    "text": text_file
                },
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "history_file": history_file,
                "status": "completed"
            }
            
            print(f"实验完成，耗时: {duration:.2f}秒")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "experiment_params": kwargs,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e),
                "status": "failed"
            }
            
            print(f"实验失败: {e}")
            return result
    
    def get_latest_history_file(self) -> str:
        """获取最新的游戏历史文件"""
        if not os.path.exists(self.history_dir):
            return None
            
        files = [f for f in os.listdir(self.history_dir) if f.endswith('.json')]
        if not files:
            return None
            
        # 按修改时间排序，获取最新的文件
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.history_dir, x)), reverse=True)
        return files[0]
    
    def get_latest_history_files(self) -> Tuple[str, str]:
        """获取最新的游戏历史文件（JSON和文本格式）"""
        files = os.listdir(self.history_dir)
        json_files = [f for f in files if f.endswith('.json')]
        
        if not json_files:
            return None, None
            
        # 按文件修改时间排序
        latest_json = max(json_files, key=lambda x: os.path.getmtime(os.path.join(self.history_dir, x)))
        latest_text = latest_json.rsplit('.', 1)[0] + '.txt'
        
        json_path = os.path.join(self.history_dir, latest_json)
        text_path = os.path.join(self.history_dir, latest_text)
        
        return json_path, text_path if os.path.exists(text_path) else None
    
    def run_parameter_sweep(self, 
                           endowment_values: List[int] = None,
                           rounds_values: List[int] = None,
                           num_players_values: List[int] = None,
                           r_values: List[float] = None,
                           personality_types: List[str] = None,
                           reveal_modes: List[str] = None) -> List[Dict[str, Any]]:
        """运行参数扫描实验"""
        
        # 使用默认值或配置文件中的值
        endowment_values = endowment_values or EXPERIMENT_CONFIG["endowment_values"]
        rounds_values = rounds_values or EXPERIMENT_CONFIG["rounds_values"]
        num_players_values = num_players_values or EXPERIMENT_CONFIG["num_players_values"]
        r_values = r_values or EXPERIMENT_CONFIG["r_values"]
        personality_types = personality_types or EXPERIMENT_CONFIG["personality_types"]
        reveal_modes = reveal_modes or EXPERIMENT_CONFIG["reveal_modes"]
        
        # 生成所有参数组合
        param_combinations = list(itertools.product(
            endowment_values,
            rounds_values,
            num_players_values,
            r_values,
            personality_types,
            reveal_modes
        ))
        
        total_experiments = len(param_combinations)
        print(f"计划运行 {total_experiments} 个实验")
        
        results = []
        
        for i, (endowment, rounds, num_players, r, personality_type, reveal_mode) in enumerate(param_combinations, 1):
            print(f"\n进度: {i}/{total_experiments}")
            
            experiment_params = {
                "endowment": endowment,
                "rounds": rounds,
                "num_players": num_players,
                "r": r,
                "personality_type": personality_type,
                "reveal_mode": reveal_mode
            }
            
            result = self.run_single_experiment(**experiment_params)
            results.append(result)
            
            # 保存中间结果
            self.save_results(results, f"sweep_progress_{i}_{total_experiments}")
            
            # 短暂休息，避免API过载
            time.sleep(2)
        
        return results
    
    def run_targeted_experiments(self) -> List[Dict[str, Any]]:
        """运行针对性实验，测试特定假设"""
        
        experiments = EXPERIMENT_CONFIG["targeted_experiments"]
        
        results = []
        total_experiments = len(experiments)
        
        for i, experiment_params in enumerate(experiments, 1):
            print(f"\n针对性实验进度: {i}/{total_experiments}")
            result = self.run_single_experiment(**experiment_params)
            results.append(result)
            
            # 保存中间结果
            self.save_results(results, f"targeted_progress_{i}_{total_experiments}")
            
            time.sleep(2)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], filename: str = None):
        """保存实验结果"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"experiment_results_{timestamp}"
        
        filepath = os.path.join(self.results_dir, f"{filename}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存到: {filepath}")
    
    def generate_summary_report(self, results: List[Dict[str, Any]]) -> str:
        """生成实验总结报告"""
        total_experiments = len(results)
        completed_experiments = len([r for r in results if r.get("status") == "completed"])
        failed_experiments = total_experiments - completed_experiments
        
        total_duration = sum(r.get("duration_seconds", 0) for r in results)
        avg_duration = total_duration / total_experiments if total_experiments > 0 else 0
        
        report = f"""
        实验总结报告
        {'='*50}
        总实验数: {total_experiments}
        成功完成: {completed_experiments}
        失败实验: {failed_experiments}
        成功率: {completed_experiments/total_experiments*100:.1f}%

        总耗时: {total_duration:.1f}秒 ({total_duration/60:.1f}分钟)
        平均耗时: {avg_duration:.1f}秒

        实验参数统计:
        """
        
        if completed_experiments > 0:
            # 分析成功实验的参数分布
            successful_results = [r for r in results if r.get("status") == "completed"]
            
            params_summary = {}
            for result in successful_results:
                params = result.get("experiment_params", {})
                for key, value in params.items():
                    if key not in params_summary:
                        params_summary[key] = {}
                    if value not in params_summary[key]:
                        params_summary[key][value] = 0
                    params_summary[key][value] += 1
            
            for param_name, param_values in params_summary.items():
                report += f"\n{param_name}:\n"
                for value, count in param_values.items():
                    report += f"  {value}: {count} 次\n"
        
        if failed_experiments > 0:
            report += "\n失败实验:\n"
            failed_results = [r for r in results if r.get("status") == "failed"]
            for i, result in enumerate(failed_results, 1):
                error = result.get("error", "未知错误")
                params = result.get("experiment_params", {})
                report += f"{i}. 错误: {error}\n   参数: {params}\n"
        
        return report


def run_quick_test():
    """运行快速测试"""
    runner = ExperimentRunner()
    
    # 使用配置文件中的快速测试参数
    quick_config = EXPERIMENT_CONFIG["quick_test"]
    results = runner.run_parameter_sweep(
        endowment_values=quick_config["endowment_values"],
        rounds_values=quick_config["rounds_values"],
        num_players_values=quick_config["num_players_values"],
        r_values=quick_config["r_values"],
        personality_types=quick_config["personality_types"],
        reveal_modes=quick_config["reveal_modes"]
    )
    
    runner.save_results(results, "quick_test")
    print(runner.generate_summary_report(results))


def run_comprehensive_sweep():
    """运行全面的参数扫描"""
    runner = ExperimentRunner()
    
    # 限制参数范围以避免过多实验
    results = runner.run_parameter_sweep(
        endowment_values=[10, 20],
        rounds_values=[10, 20],
        num_players_values=[5, 10],
        r_values=[1.5, 2.0],
        personality_types=["selfish", "altruistic"],
        reveal_modes=["public"]
    )
    
    runner.save_results(results, "comprehensive_sweep")
    print(runner.generate_summary_report(results))


def run_targeted_analysis():
    """运行针对性分析实验"""
    runner = ExperimentRunner()
    results = runner.run_targeted_experiments()
    
    runner.save_results(results, "targeted_analysis")
    print(runner.generate_summary_report(results))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        experiment_type = sys.argv[1]
        
        if experiment_type == "quick":
            run_quick_test()
        elif experiment_type == "sweep":
            run_comprehensive_sweep()
        elif experiment_type == "targeted":
            run_targeted_analysis()
        else:
            print("使用方法: python run_experiments.py [quick|sweep|targeted]")
    else:
        # 默认运行快速测试
        print("运行默认快速测试...")
        run_quick_test()