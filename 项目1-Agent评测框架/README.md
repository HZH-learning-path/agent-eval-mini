# Agent 评测对照实验

## 项目简介

自建迷你 Agent 评测框架，通过对照实验验证"Agent 分数低不等于模型差"。

## 实验设计

三组对照实验，每组只改一个变量：

| 组别 | 配置 | 改了什么 |
|:---|:---|:---|
| A组（正常） | max_tokens=2048, 正确路径 | 基线 |
| B组（掐token） | max_tokens=40, 正确路径 | 仅改token限制 |
| C组（错路径） | max_tokens=2048, 错误路径 | 仅改文件路径 |

## 核心发现

同一模型，仅改变执行层配置，通过率可下降50%+。
说明 Agent 评测必须拆分模型层和执行层。

## 技术栈

- Python + OpenAI SDK（调用 DeepSeek API）
- 自建任务定义格式（JSON）+ 自动评分系统

## 运行方法

```bash
# 设置 API Key
# Windows PowerShell:
$env:DEEPSEEK_API_KEY="your_key"
# Linux/Mac:
export DEEPSEEK_API_KEY="your_key"

# 安装依赖
pip install openai

# 运行实验
python runner.py

# 生成报告
python analyze.py > report.md
```

## 文件结构

```
agent-eval-mini/
├── tasks/              # 任务定义（JSON格式）
│   ├── task1.json      # 读取JSON文件
│   ├── task2.json      # 写入文件
│   ├── task3.json      # 解压并读取
│   └── task4.json      # 解析JSON数据
├── config.py           # 实验配置（对照组定义）
├── runner.py           # 评测框架核心
├── analyze.py          # 分析与报告生成
├── results/            # 实验结果（自动生成）
├── README.md
└── report.md           # 实验报告（自动生成）
```
