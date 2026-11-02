# -*- coding: utf-8 -*-
"""
Agent 评测对照实验报告生成器
根据 experiment_results.json 动态生成报告
"""
import json
import os


def classify_failure(result):
    """
    自动分类失败原因
    返回：(原因分类, 详细说明)
    """
    output = result["model_output"]
    detail = result["detail"]

    # B组常见：JSON截断 / 解析错误
    if "Unterminated string" in output or "Expecting" in output or "JSON" in output:
        return "token限制导致JSON参数截断", "模型生成的工具调用参数被截断，JSON不完整，解析失败，工具未执行"

    # 模型输出被截断，没说完
    if len(output) < 20 and "FAIL" not in output and "错误" not in output:
        return "token限制导致输出被截断", f"模型只输出了'{output}'，明显未完成，输出空间不足"

    # C组常见：文件不存在
    if "不存在" in detail or "does not exist" in detail or "文件找不到" in detail:
        return "文件路径错误（执行层环境配置）", "模型正确调用了工具，但工作目录中文件不存在，执行失败"

    # API调用失败
    if "API调用失败" in output:
        return "API调用失败", output[:100]

    # 其他
    return "其他原因", detail[:100]


def main():
    with open("results/experiment_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []

    lines.append("# Agent 评测对照实验报告\n")

    # ========== 一、实验设计 ==========
    lines.append("## 一、实验设计\n")
    lines.append("| 组别 | 配置 | 改了什么 |")
    lines.append("|:---|:---|:---|")
    lines.append("| A组（正常） | max_tokens=2048, 正确路径 | 基线 |")
    lines.append("| B组（掐token） | max_tokens=40, 正确路径 | 仅改token限制 |")
    lines.append("| C组（错路径） | max_tokens=2048, 错误路径 | 仅改文件路径 |")
    lines.append("")
    lines.append("实验遵循控制变量法：每组仅修改一个执行层配置，模型、任务、评分标准完全一致。\n")

    # ========== 二、实验结果 ==========
    lines.append("## 二、实验结果\n")
    lines.append("| 题目 | A组（正常） | B组（掐token） | C组（错路径） |")
    lines.append("|:---|:---|:---|:---|")

    task_ids = [r["task_id"] for r in data["A_normal"]]
    task_titles = {r["task_id"]: r["task_title"] for r in data["A_normal"]}

    for tid in task_ids:
        row = f"| {tid} {task_titles.get(tid, '')} |"
        for exp_key in ["A_normal", "B_token_limit", "C_wrong_path"]:
            r = next(x for x in data[exp_key] if x["task_id"] == tid)
            row += f" {'✅通过' if r['passed'] else '❌失败'} |"
        lines.append(row)

    # 通过率汇总
    lines.append("\n| 组别 | 通过率 | 通过题数 |")
    lines.append("|:---|:---|:---|")
    pass_rates = {}
    for exp_key, label in [("A_normal", "A组"), ("B_token_limit", "B组"), ("C_wrong_path", "C组")]:
        passed = sum(1 for r in data[exp_key] if r["passed"])
        total = len(data[exp_key])
        rate = passed / total * 100
        pass_rates[exp_key] = (passed, total, rate)
        lines.append(f"| {label} | {rate:.0f}% | {passed}/{total} |")

    # ========== 三、失败案例分析 ==========
    lines.append("\n## 三、失败案例分析\n")

    for exp_key, label in [("B_token_limit", "B组"), ("C_wrong_path", "C组")]:
        lines.append(f"### {label}失败案例\n")
        failures = [r for r in data[exp_key] if not r["passed"]]

        if not failures:
            lines.append("本组全部通过，无失败案例。\n")
            continue

        # 统计失败原因分类
        failure_types = {}
        for r in failures:
            ftype, fdetail = classify_failure(r)
            if ftype not in failure_types:
                failure_types[ftype] = []
            failure_types[ftype].append(r)

        for ftype, fr_list in failure_types.items():
            lines.append(f"**失败类型：{ftype}**（{len(fr_list)}道题）")
            for r in fr_list:
                lines.append(f"- {r['task_id']}: {r['detail'][:80]}")
                lines.append(f"  模型输出前80字: {r['model_output'][:80]}")
            lines.append("")

    # ========== 四、归因结论 ==========
    lines.append("## 四、归因结论\n")

    a_rate = pass_rates["A_normal"][2]
    b_rate = pass_rates["B_token_limit"][2]
    c_rate = pass_rates["C_wrong_path"][2]

    lines.append(f"1. **整体结论**")
    lines.append(f"   - 基线（A组）通过率：{a_rate:.0f}%")
    lines.append(f"   - 仅限制token（B组）通过率：{b_rate:.0f}%，下降 {a_rate - b_rate:.0f} 个百分点")
    lines.append(f"   - 仅改变工作目录（C组）通过率：{c_rate:.0f}%，下降 {a_rate - c_rate:.0f} 个百分点")
    lines.append(f"   - 仅改变执行层的一个配置，通过率即可显著下降，验证了'Agent分数混叠'问题\n")

    # B组归因
    b_failures = [r for r in data["B_token_limit"] if not r["passed"]]
    b_json_fail = sum(1 for r in b_failures if "Unterminated" in r["model_output"] or "Expecting" in r["model_output"])
    b_truncated = sum(1 for r in b_failures if len(r["model_output"]) < 30 and "错误" not in r["model_output"])

    lines.append(f"2. **B组（token限制）失败归因**")
    lines.append(f"   - 共 {len(b_failures)} 道题失败")
    if b_json_fail > 0:
        lines.append(f"   - 其中 {b_json_fail} 道题是工具调用JSON参数被截断（Unterminated string / JSON解析错误）")
        lines.append(f"     → 模型知道该调什么工具、传什么参数，但输出空间不够，参数写了一半被截断")
        lines.append(f"     → 工具根本没被执行，任务直接失败。这是执行层配置问题，不是模型推理能力问题")
    if b_truncated > 0:
        lines.append(f"   - 其中 {b_truncated} 道题是模型直接回答时输出被截断")
        lines.append(f"     → 模型选择了不调工具直接回答，但回答没说完就被截断了")
    lines.append(f"   - 值得注意：B组通过的题目中，部分是模型'猜对'的（无需调用工具或直接给出答案），并非真正完成了工具调用\n")

    # C组归因
    c_failures = [r for r in data["C_wrong_path"] if not r["passed"]]
    c_path_fail = sum(1 for r in c_failures if "不存在" in r["detail"] or "does not exist" in r["detail"])

    lines.append(f"3. **C组（错误路径）失败归因**")
    lines.append(f"   - 共 {len(c_failures)} 道题失败")
    if c_path_fail > 0:
        lines.append(f"   - 其中 {c_path_fail} 道题是文件不存在导致的执行失败")
        lines.append(f"     → 模型正确调用了工具（read_file/extract_zip），参数也正确")
        lines.append(f"     → 但工作目录指向不存在的路径，文件找不到")
        lines.append(f"     → 模型的行为完全正确，是执行层环境配置错误")
    c_passes = [r for r in data["C_wrong_path"] if r["passed"]]
    if c_passes:
        passed_tasks = ", ".join(r["task_id"] for r in c_passes)
        lines.append(f"   - C组通过的题目（{passed_tasks}）包括：")
        lines.append(f"     → 纯推理题（无需文件操作）：路径错误不影响")
        lines.append(f"     → 写入类任务：write_file 会自动创建目录，所以不受路径不存在的影响")
        lines.append(f"     → 这说明不同类型的任务对执行层配置的敏感度不同，评测需分类分析\n")

    lines.append(f"4. **核心发现**")
    lines.append(f"   - 同一个模型、同一套题、同一个评分标准，仅改执行层配置，通过率可差 {a_rate - min(b_rate, c_rate):.0f} 个百分点")
    lines.append(f"   - 分数低 ≠ 模型能力差，可能是执行层配置的问题")
    lines.append(f"   - Agent 评测必须拆分模型层和执行层，否则分数没有意义")
    lines.append(f"   - 不同任务类型对执行层配置的敏感度不同，需要分类归因\n")

    # ========== 五、实验局限 ==========
    lines.append("## 五、实验局限与后续方向\n")
    lines.append("- 任务数量较少（4题），统计意义有限，后续可扩充至20-30题")
    lines.append("- 仅测试了两个执行层维度（token限制/路径错误），真实Agent框架涉及更多维度（沙箱、权限、压缩等）")
    lines.append("- 单模型测试，未做跨模型验证；后续可加入更多模型对比")
    lines.append("- 任务以文件操作为主，未能覆盖Agent的更多能力维度")
    lines.append("- 未来方向：接入真实Agent框架（如DeepSeek Harness），在更复杂的环境中验证归因方法\n")

    # 写文件
    with open("report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("报告已生成到 report.md")


if __name__ == "__main__":
    main()
