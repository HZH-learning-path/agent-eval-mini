# -*- coding: utf-8 -*-
"""
大模型 API 调用稳定性统计
对同一 API 发起 100 次调用，统计：
- 成功率
- 平均响应时间
- 错误类型分布
"""
import os
import time
import json
from openai import OpenAI

# ============ 配置 ============
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    raise RuntimeError("未找到 DEEPSEEK_API_KEY，请先在终端设置该环境变量")
API_BASE = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"
TOTAL_CALLS = 100        # 总共调用100次
TIMEOUT = 30              # 单次超时30秒
TEST_PROMPT = "请回答：1+1等于几？只回答数字。"  # 固定 prompt，减少变量

# ============ 初始化客户端 ============
client = OpenAI(api_key=API_KEY, base_url=API_BASE)


def single_call():
    """
    单次 API 调用
    返回：(是否成功, 耗时秒数, 错误类型或None, 模型回复或None)
    """
    try:
        start = time.time()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": TEST_PROMPT}],
            max_tokens=50,
            temperature=0,
            timeout=TIMEOUT,
        )
        elapsed = time.time() - start
        reply = response.choices[0].message.content.strip()
        return True, elapsed, None, reply

    except Exception as e:
        elapsed = time.time() - start
        # 分类错误类型
        error_str = str(e).lower()
        if "timeout" in error_str or "timed out" in error_str:
            error_type = "超时"
        elif "rate" in error_str and "limit" in error_str:
            error_type = "限流"
        elif "insufficient" in error_str or "balance" in error_str:
            error_type = "余额不足"
        elif "connection" in error_str:
            error_type = "连接错误"
        else:
            error_type = "其他错误"
        return False, elapsed, error_type, str(e)[:100]


def main():
    print("=" * 50)
    print("  API 调用稳定性统计")
    print(f"  总调用次数: {TOTAL_CALLS}")
    print(f"  测试 Prompt: {TEST_PROMPT}")
    print("=" * 50)

    results = []

    for i in range(1, TOTAL_CALLS + 1):
        # 每10次打印一次进度
        if i % 10 == 0 or i == 1:
            print(f"[进度] {i}/{TOTAL_CALLS} ...")

        success, elapsed, error_type, reply = single_call()

        results.append({
            "call_id": i,
            "success": success,
            "elapsed": round(elapsed, 3),
            "error_type": error_type,
            "reply": reply[:50] if reply else None
        })

        # 成功/失败标记
        status = "OK" if success else f"FAIL({error_type})"
        if i % 10 == 0 or not success:
            print(f"  第{i}次: {status} ({elapsed:.2f}s)")

        # 避免请求太快被限流
        time.sleep(0.5)

    # ============ 统计分析 ============
    print("\n" + "=" * 50)
    print("  统计结果")
    print("=" * 50)

    total = len(results)
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    # 1. 成功率
    success_rate = len(successes) / total * 100
    print(f"\n成功率: {len(successes)}/{total} ({success_rate:.1f}%)")

    # 2. 响应时间统计（只算成功的）
    if successes:
        times = [r["elapsed"] for r in successes]
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        print(f"\n响应时间（仅成功调用）:")
        print(f"  平均: {avg_time:.2f}s")
        print(f"  最快: {min_time:.2f}s")
        print(f"  最慢: {max_time:.2f}s")

    # 3. 错误类型分布
    if failures:
        print(f"\n错误类型分布:")
        error_counts = {}
        for f in failures:
            et = f["error_type"]
            error_counts[et] = error_counts.get(et, 0) + 1
        for et, count in error_counts.items():
            print(f"  {et}: {count}次 ({count/len(failures)*100:.0f}%)")
    else:
        print(f"\n无失败调用")

    # 4. 保存详细数据
    with open("stability_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total_calls": total,
                "success_count": len(successes),
                "fail_count": len(failures),
                "success_rate": f"{success_rate:.1f}%",
                "avg_response_time": f"{avg_time:.2f}s" if successes else "N/A",
                "min_response_time": f"{min_time:.2f}s" if successes else "N/A",
                "max_response_time": f"{max_time:.2f}s" if successes else "N/A",
            },
            "error_distribution": error_counts if failures else {},
            "details": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n详细数据已保存到: stability_results.json")


if __name__ == "__main__":
    main()
