import os

# ============ API 配置 ============
# Key 从环境变量读取，不要写死在代码里
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    raise RuntimeError("未找到 DEEPSEEK_API_KEY，请先在终端设置该环境变量")
API_BASE = "https://api.deepseek.com"
MODEL_NAME = "deepseek-flash"

# ============ 三组对照实验配置 ============
# 每组只改一个变量，其他保持一致
EXPERIMENTS = {
    "A_normal": {
        "label": "A组：正常配置",
        "max_tokens": 2048,
        "work_dir": "./workspace",
        "description": "基线组，所有配置正常"
    },
    "B_token_limit": {
        "label": "B组：限制输出token",
        "max_tokens": 40,
        "work_dir": "./workspace",
        "description": "模拟Harness中token限制过小的问题"
    },
    "C_wrong_path": {
        "label": "C组：错误文件路径",
        "max_tokens": 2048,
        "work_dir": "./wrong_workspace",
        "description": "模拟Harness中文件操作路径错误的问题"
    }
}
