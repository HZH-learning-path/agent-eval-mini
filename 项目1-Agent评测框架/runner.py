# -*- coding: utf-8 -*-
"""
Agent 评测框架核心
通过 function calling 让模型真正能读写文件
Agent 工作流程：模型推理 → 调用工具 → 框架执行 → 结果回传 → 继续推理
"""
import json
import os
import zipfile
import shutil
from openai import OpenAI
from config import API_KEY, API_BASE, MODEL_NAME, EXPERIMENTS

client = OpenAI(api_key=API_KEY, base_url=API_BASE)

# ============ 工具定义（告诉模型有哪些工具可用）============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取指定路径的文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "把内容写入指定路径的文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                    "content": {"type": "string", "description": "要写入的内容"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_zip",
            "description": "解压zip文件并返回其中某个文件的内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "zip_path": {"type": "string", "description": "zip文件路径"},
                    "file_name": {"type": "string", "description": "要读取的文件名"}
                },
                "required": ["zip_path", "file_name"]
            }
        }
    }
]


def execute_tool(tool_name, args, work_dir):
    """执行模型调用的工具，返回结果给模型"""
    if tool_name == "read_file":
        path = os.path.join(work_dir, args.get("path", ""))
        if not os.path.exists(path):
            return f"错误：文件不存在 - {path}"
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    elif tool_name == "write_file":
        path = os.path.join(work_dir, args.get("path", ""))
        content = args.get("content", "")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"文件写入成功: {path}"

    elif tool_name == "extract_zip":
        zip_path = os.path.join(work_dir, args.get("zip_path", ""))
        file_name = args.get("file_name", "")
        if not os.path.exists(zip_path):
            return f"错误：zip文件不存在 - {zip_path}"
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                if file_name in zf.namelist():
                    return zf.read(file_name).decode("utf-8")
                return f"错误：文件 {file_name} 不在zip中"
        except Exception as e:
            return f"错误：解压失败 - {str(e)}"

    return f"错误：未知工具 {tool_name}"


def setup_task(task, work_dir):
    """根据任务定义创建初始文件"""
    os.makedirs(work_dir, exist_ok=True)
    files = task.get("setup", {}).get("files", {})
    for filepath, content in files.items():
        full_path = os.path.join(work_dir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        if content.startswith("zip:"):
            zip_info = content[4:]
            filename, file_content = zip_info.split("=", 1)
            with zipfile.ZipFile(full_path, "w") as zf:
                zf.writestr(filename, file_content)
        else:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)


def call_agent(task, max_tokens, work_dir):
    """
    完整的 Agent 调用流程：
    1. 发送任务给模型
    2. 模型可能调用工具（function calling）
    3. 执行工具，结果回传给模型
    4. 模型给出最终答案
    最多循环 5 轮，防止死循环
    """
    messages = [
        {"role": "system", "content": "你是一个文件操作助手。你可以使用工具来读写文件。请直接调用工具完成任务，不要给出代码让用户自己运行。"},
        {"role": "user", "content": task["prompt"]}
    ]

    all_tool_calls = []  # 记录模型调用了哪些工具

    for round_num in range(5):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0,
            tools=TOOLS,
        )

        msg = response.choices[0].message

        # 如果模型没有调用工具，说明它给出了最终答案
        if not msg.tool_calls:
            return msg.content, all_tool_calls

        # 模型调用了工具，先把模型的工具调用消息加入对话
        messages.append(msg)

        # 执行每个工具调用，把结果回传给模型
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            result = execute_tool(tool_name, tool_args, work_dir)
            all_tool_calls.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result[:200]  # 只记前200字符
            })
            # 把工具执行结果加入对话
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            })

    # 5轮还没结束，返回最后一轮的输出
    return "超过最大轮数，Agent未能完成任务", all_tool_calls


def check_result(task, model_output, work_dir, all_tool_calls):
    """自动评分"""
    check = task["check"]

    if check["type"] == "contains":
        passed = check["answer"].lower() in model_output.lower()
        return {
            "passed": passed,
            "detail": f"期望包含 '{check['answer']}'，实际输出: {model_output[:200]}"
        }

    elif check["type"] == "file_exists":
        file_path = os.path.join(work_dir, check["path"])
        if not os.path.exists(file_path):
            return {"passed": False, "detail": f"文件不存在: {check['path']}"}
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        passed = check["answer"] in content
        return {
            "passed": passed,
            "detail": f"文件内容: '{content[:100]}'，期望: '{check['answer']}'"
        }

    return {"passed": False, "detail": "未知的检查类型"}


def run_experiment(exp_name, exp_config, tasks):
    """跑一组实验"""
    print(f"\n{'='*50}")
    print(f"开始实验: {exp_config['label']}")
    print(f"说明: {exp_config['description']}")
    print(f"{'='*50}")

    work_dir = exp_config["work_dir"]
    max_tokens = exp_config["max_tokens"]

    # 清理工作目录
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    if work_dir == "./wrong_workspace":
        # C组：故意不创建目录
        pass
    else:
        os.makedirs(work_dir, exist_ok=True)

    results = []
    for task in tasks:
        print(f"\n--- {task['id']}: {task['title']} ---")

        # 1. 准备初始文件
        if work_dir != "./wrong_workspace":
            setup_task(task, work_dir)

        # 2. 调用 Agent（可能经过多轮工具调用）
        try:
            model_output, all_tool_calls = call_agent(task, max_tokens, work_dir)
        except Exception as e:
            model_output = f"[API调用失败] {str(e)}"
            all_tool_calls = []

        print(f"模型输出: {model_output[:120]}...")
        if all_tool_calls:
            print(f"工具调用: {len(all_tool_calls)} 次 - {[tc['tool'] for tc in all_tool_calls]}")

        # 3. 自动评分
        check = check_result(task, model_output, work_dir, all_tool_calls)

        result = {
            "task_id": task["id"],
            "task_title": task["title"],
            "experiment": exp_name,
            "max_tokens": max_tokens,
            "work_dir": work_dir,
            "model_output": model_output,
            "tool_calls": all_tool_calls,
            "passed": check["passed"],
            "detail": check["detail"]
        }
        results.append(result)
        print(f"结果: {'✅ 通过' if check['passed'] else '❌ 失败'} - {check['detail']}")

    return results


def main():
    # 加载所有任务
    tasks = []
    task_dir = "tasks"
    for i in range(1, 5):
        with open(os.path.join(task_dir, f"task{i}.json"), "r", encoding="utf-8") as f:
            tasks.append(json.load(f))

    # 跑三组实验
    all_results = {}
    for exp_name, exp_config in EXPERIMENTS.items():
        all_results[exp_name] = run_experiment(exp_name, exp_config, tasks)

    # 保存结果
    os.makedirs("results", exist_ok=True)
    result_file = os.path.join("results", "experiment_results.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 打印汇总
    print(f"\n{'='*50}")
    print("实验汇总")
    print(f"{'='*50}")
    for exp_name, results in all_results.items():
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        label = EXPERIMENTS[exp_name]["label"]
        print(f"{label}: {passed}/{total} 通过 ({passed/total*100:.0f}%)")

    print(f"\n详细结果已保存到: {result_file}")


if __name__ == "__main__":
    main()
