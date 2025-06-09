## main.py

* **作用：** 加载并验证配置，初始化agent配置。
* **主要流程：**

  1. 调用 `config.validate_config()` 检查环境变量与参数格式。
  2. 从 `profiles.py` 中读取并采样agent的profile。
  3. 实例化 `GameController` 并执行 `play()` 方法，开始PGG任务。

---

## config.py

* **作用：** 管理项目全局配置，包括任务参数（如奖励系数/每组人数等）与模型参数。
* **主要内容：**

  * 通过 `python-dotenv` 加载 `.env` 中的 API Key（如 `OPENAI_API_KEY`、`ZHIPUAI_API_KEY`）。
  * 定义 `GAME_CONFIG`（初始资金、倍增因子 r、回合数、玩家数）和 `MODEL_CONFIG`（LLM 提供商、模型名称等）。
  * 提供 `validate_config()` 函数，确保关键环境变量已设置且参数合法。

---

## agents.py

* **作用：** 定义 `Agent` 类，封装agent的profile与决策逻辑。
* **主要功能：**

  * 根据个人档案（性别、年龄、性格得分）和游戏状态，调用 LLM 接口生成贡献决策（贡献多少到公共池）。
  * 可接收可选的讨论摘要，调整决策理由与数值。

---

## profiles.py

* **作用：** 读取并管理agent信息数据。
* **主要功能：**

  * 从 `beijing_agent_profile.json` 中加载样本档案。
  * 提供随机采样接口，根据 `GAME_CONFIG` 中的玩家数，返回指定数量的agent信息列表。

---

## game\_controller.py

* **作用：** 核心的任务流程管理，负责协调各阶段执行顺序。
* **主要功能：**

  1. **讨论阶段（DiscussionRoom）：** 组织agent进入讨论房间，收集消息并生成讨论摘要。
  2. **决策阶段（ContributeRoom）：** 调用每个agent的决策方法，计算其对公共池的贡献。
  3. **收益计算：** 按比例倍增公共池后均分，记录每位agent的收益。
  4. **中断与状态保存：** 每隔固定回合或中断时，将当前游戏状态写入history，方便恢复与分析。

---

## game\_recorder.py

* **作用：** 负责记录并存储任务过程中金额数据与对话历史，便于后续分析。
* **主要功能：**

  * 将每个回合的经济数据（贡献量、收益、累积得分）和文本对话记录保存为 JSON 文件，默认保存在 `game_history/` 目录。
  * 文件命名包含时间戳与回合信息，确保不覆盖历史记录。

---

## rooms.py

* **作用：** 实现不同功能的“房间”类，封装交互逻辑。
* **主要类：**

  1. **ContributeRoom：** 处理贡献计算，接收各agent的贡献数并返回公共池总额。
  2. **DiscussionRoom：** 管理agent之间的对话，调用 LLM 生成讨论摘要，用于影响后续决策。
  3. **InterventionRoom：** 可拓展外部干预机制（如政府补贴、突发事件），目前仅提供空方法以供后续自定义。【还未实现】
