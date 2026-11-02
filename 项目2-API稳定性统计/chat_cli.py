# -*- coding: utf-8 -*-
"""
大模型 API 多轮对话 CLI 工具
功能：调用 DeepSeek API 实现多轮对话，支持上下文记忆、错误重试、超时处理
"""
import os
import time
from openai import OpenAI

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    raise RuntimeError("未找到 DEEPSEEK_API_KEY，请先在终端设置该环境变量")
API_BASE = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"
MAX_RETRY = 3
TIMEOUT = 30
MAX_HISTORY = 20

client = OpenAI(api_key=API_KEY, base_url=API_BASE)


def call_api_with_retry(messages):
    for attempt in range(1, MAX_RETRY + 1):
        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=2048,
                temperature=0.7,
                timeout=TIMEOUT,
            )
            elapsed = time.time() - start_time
            reply = response.choices[0].message.content
            return True, reply, elapsed
        except Exception as e:
            error_msg = str(e)
            print(f"  [第{attempt}次尝试失败] {error_msg[:80]}")
            if attempt < MAX_RETRY:
                print(f"  等待2秒后重试...")
                time.sleep(2)
            else:
                return False, error_msg, 0
    return False, "未知错误", 0


def main():
    print("=" * 50)
    print("  大模型多轮对话工具")
    print("  输入 quit 退出，输入 clear 清空对话历史")
    print("=" * 50)

    history = [{"role": "system", "content": "你是一个友好的AI助手，请简洁地回答问题。"}]
    round_count = 0

    while True:
        user_input = input("\n你: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break
        if user_input.lower() == "clear":
            history = [{"role": "system", "content": "你是一个友好的AI助手，请简洁地回答问题。"}]
            round_count = 0
            print("对话历史已清空。")
            continue

        history.append({"role": "user", "content": user_input})
        if len(history) > MAX_HISTORY * 2 + 1:
            history = [history[0]] + history[-(MAX_HISTORY * 2):]

        success, reply, elapsed = call_api_with_retry(history)
        if success:
            history.append({"role": "assistant", "content": reply})
            round_count += 1
            print(f"\nAI: {reply}")
            print(f"  [耗时 {elapsed:.1f}s | 第{round_count}轮对话]")
        else:
            print(f"\n[错误] API调用失败: {reply[:100]}")
            history.pop()


if __name__ == "__main__":
    main()
