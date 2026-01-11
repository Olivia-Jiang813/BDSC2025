# 公共品博弈（PGG）实验框架

一个基于大型语言模型（LLM）的公共品博弈模拟平台，用于研究AI智能体在合作场景中的行为、策略演化和博弈动态。

## 项目概述

本项目通过集成多种大型语言模型（OpenAI、Zhipuai、Google Gemini、DeepSeek），模拟多个AI智能体参与公共品博弈。每个智能体基于LLM的推理能力做出投资决策，系统记录详细的游戏数据用于分析。

### 核心特性

- 🤖 **多模型支持**：支持 GPT-4、Gemini、DeepSeek、GLM 等多个LLM
- 🎮 **公共品博弈模拟**：完整的博弈逻辑（多轮、多玩家、动态收益）
- 🎭 **个性化智能体**：支持不同性格特征的智能体模拟
- ⚓ **锚点智能体**：特殊的Anchor智能体可引导或影响其他智能体行为
- 📊 **完整数据记录**：记录每轮游戏的详细决策、推理过程和收益数据
- 🔄 **灵活的实验模式**：支持单次游戏、参数扫描、快速测试、针对性实验等多种运行模式

---

## 快速开始

### 1. 环境设置

克隆项目后，安装依赖：
```bash
pip install -r requirements.txt
```

在项目根目录创建 `.env` 文件，添加您的API密钥：
```
OPENAI_API_KEY=your_openai_api_key
ZHIPUAI_API_KEY=your_zhipuai_api_key
GEMINI_API_KEY=your_google_gemini_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```

### 2. 运行游戏

**游戏运行：**
```bash
python main.py
```

可添加参数自定义游戏配置：
```bash
python main.py \
  --model gemini-2.5-flash \
  --rounds 10 \
  --num-players 10 \
  --endowment 10 \
  --r 3 \
  --anchor-ratio 0.2 \
  --reveal-mode anonymous \
  --instruction-type certain
```

---

## 参数配置详解

所有游戏参数统一在 `config.py` 中管理。主要参数说明：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `model` | 使用的LLM模型 | `"gemini-2.5-flash"` |
| `endowment` | 每轮初始代币数 | `10` |
| `r` | 公共池倍数 | `3` |
| `rounds` | 游戏总轮数 | `10` |
| `num_players` | 游戏玩家数量 | `10` |
| `anchor_ratio` | Anchor智能体比例（0~1） | `0.2` |
| `reveal_mode` | 信息公开模式（`public` 或 `anonymous`） | `"anonymous"` |
| `instruction_type` | 指导语类型（`certain` 或 `uncertain`） | `"certain"` |

---

## 项目文件说明

### `main.py`
**游戏启动入口**
- 解析命令行参数
- 创建游戏配置副本并根据参数更新
- 初始化并运行 `GameController`
- 支持调试输出选项

### `config.py`
**全局配置管理**
- 通过 `python-dotenv` 加载 `.env` 中的 API Key
- 定义 `API_KEYS` 配置（支持 OpenAI、Zhipuai、Gemini、DeepSeek）
- 定义 `MODEL_CONFIG` 和 `GAME_CONFIG`
- 提供配置验证函数

### `agents.py`
**智能体定义和决策逻辑**
- `Agent` 类：封装单个AI智能体的行为
- 支持调用不同LLM提供商的API
- 定义Pydantic模型约束LLM输出结构
- 生成贡献决策、策略更新、信念更新等

### `game_controller.py`
**游戏流程控制**
- 初始化智能体（包括普通和Anchor智能体）
- 管理游戏的多轮流程
- 计算投资决策和公共池收益
- 处理信息公开模式（public/anonymous）
- 集成 `GameRecorder` 记录游戏数据

### `game_recorder.py`
**游戏数据记录**
- 记录每轮游戏的统计数据（总投入、公共池、人均分配等）
- 保存智能体的决策和推理过程
- 生成JSON和TXT格式的游戏历史记录
- 使用时间戳命名避免数据覆盖

### `personality_traits.py`
**性格特征定义**
- 定义不同性格类型的Prompt模板
- 为智能体注入个性化的价值观和决策倾向

### `run_experiments.py`
**实验运行脚本**
- 支持多种实验模式（quick、sweep、targeted）
- 批量运行不同参数组合的游戏
- 用于系统化研究智能体行为

---

## 数据输出

游戏结果保存在 `game_history/` 目录下：

- **JSON文件**：完整的游戏数据（结构化格式，便于数据分析）
- **TXT文件**：可读的游戏日志（包含详细的决策过程和推理）

### 输出文件命名格式
```
{model}_{reveal_mode}_{num_players}p_{rounds}r_{anchor_info}_{instruction_type}_completed_{timestamp}.json
```

### 数据分析
项目包含 `game_history/DataAnalysis.ipynb` Jupyter notebook，用于：
- 可视化游戏数据
- 分析合作程度变化
- 比较不同模型/参数的表现

---

## 博弈论基础

### 公共品博弈（Public Goods Game）

每轮游戏流程：
1. **初始阶段**：每个玩家获得初始禀赋（如10个代币）
2. **决策阶段**：玩家决定投入多少到公共池
3. **收益计算**：公共池总额乘以倍数$r$，均分给所有玩家
4. **信息阶段**：根据 `reveal_mode` 选择是否公开每个玩家的投资额

### 博弈动态

- **社会困境**：理性追求个人收益可能导致集体福利降低
- **免费搭车问题**：有人少投入，让其他人补偿，仍能获得公共池分配
- **合作演化**：通过多轮重复博弈，可能形成合作或惩罚机制

---

## 实验示例

### 示例1：基础10人游戏
```bash
python main.py \
  --model gemini-2.5-flash \
  --rounds 10 \
  --num-players 10 \
  --endowment 10 \
  --r 3
```

### 示例2：对比不同模型
```bash
# GPT-4.1
python main.py --model gpt-4.1 --rounds 20

# DeepSeek
python main.py --model deepseek-chat --rounds 20

# GLM-4
python main.py --model glm-4-flash --rounds 20
```

### 示例3：研究Anchor智能体影响
```bash
# 无Anchor（baseline）
python main.py --anchor-ratio 0

# 20% Anchor智能体
python main.py --anchor-ratio 0.2

# 50% Anchor智能体
python main.py --anchor-ratio 0.5
```

### 示例4：研究信息公开模式
```bash
# 公开模式（玩家知道每个人的投资额）
python main.py --reveal-mode public

# 匿名模式（玩家只知道总投资额）
python main.py --reveal-mode anonymous
```

---

## 依赖项

- `openai` ≥ 1.0.0 - OpenAI API客户端
- `zhipuai` ≥ 2.0.0 - 智谱AI API客户端
- `google-genai` ≥ 0.1.0 - Google Gemini API客户端
- `python-dotenv` ≥ 0.19.0 - 环境变量管理

如有问题或建议，请联系项目维护者。
