# 公共品博弈游戏

## 快速开始

### 环境配置
确保已安装依赖包并配置了API密钥：
```bash
pip install -r requirements.txt
```

在项目根目录创建`.env`文件，添加API密钥：
```
OPENAI_API_KEY=your_openai_key
ZHIPUAI_API_KEY=your_zhipuai_key
```

### 运行游戏

**1. 单次游戏运行：**
```bash
python main.py
```

**2. 快速测试（少量实验）：**
```bash
python run_experiments.py quick
```

**3. 完整参数扫描：**
```bash
python run_experiments.py sweep
```

**4. 针对性实验：**
```bash
python run_experiments.py targeted
```

### 参数配置

所有游戏参数统一在`config.py`文件中管理：

- **GAME_CONFIG**: 单次游戏的默认参数（禀赋、轮数、玩家数等）
- **EXPERIMENT_CONFIG**: 批量实验的参数范围和特定实验配置

要修改实验参数，请编辑`config.py`中的相应部分。

---

# 项目文件说明

## main.py

* **作用：** 加载并验证配置，初始化agent配置。
* **主要流程：**
  1. 调用 `config.validate_config()` 检查环境变量与参数格式
  2. 从 `profiles.py` 中读取并采样agent的profile
  3. 实例化 `GameController` 并执行 `play()` 方法，开始PGG任务

## config.py

* **作用：** 管理项目全局配置，包括任务参数与模型参数。
* **主要内容：**
  * 通过 `python-dotenv` 加载 `.env` 中的 API Key
  * 定义 `GAME_CONFIG`（初始资金、倍增因子 r、回合数、玩家数）
  * 定义 `MODEL_CONFIG`（LLM提供商、模型名称等）
  * 提供 `validate_config()` 函数，确保环境变量与参数合法

## agents.py

* **作用：** 定义 `Agent` 类，封装agent的profile与决策逻辑。
* **主要功能：**
  * 根据个人档案（性别、年龄、性格得分）生成贡献决策
  * 处理讨论摘要，调整决策理由与数值

## game_controller.py

* **作用：** 核心的任务流程管理器。
* **主要功能：**
  1. **讨论阶段：** 组织agent讨论，生成摘要
  2. **决策阶段：** 收集贡献决策，计算公共池总额
  3. **收益计算：** 倍增并均分公共池
  4. **状态保存：** 定期保存游戏状态，支持中断恢复

## game_recorder.py

* **作用：** 记录任务过程数据。
* **主要功能：**
  * 保存经济数据（贡献、收益、累积得分）
  * 保存对话历史
  * 使用时间戳命名，避免覆盖历史记录

## rooms.py

* **作用：** 实现不同功能的交互空间。
* **主要类：**
  1. **ContributeRoom：** 处理贡献计算逻辑
  2. **DiscussionRoom：** 管理群体讨论过程
