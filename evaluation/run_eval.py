"""离线评估 CLI —— 运行 LangSmith evaluation。

Usage:
    python evaluation/run_eval.py --smoke                # 本地烟雾测试
    python evaluation/run_eval.py                        # 默认数据集评估
    python evaluation/run_eval.py --dataset emr-targeted-scenarios
    python evaluation/run_eval.py --dataset emr-targeted-scenarios --llm-judge
    python evaluation/run_eval.py --prefix my-experiment --records 5
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from langsmith import Client, evaluate

from graph import build_graph
from emr_schema import DEPARTMENT_POOL
from evaluation.evaluators import DETERMINISTIC_EVALUATORS, LLM_JUDGE_EVALUATORS


def target_factory(inputs: dict) -> dict:
    """LangSmith evaluate 的目标函数。

    接收来自数据集的 input_params，构建初始状态，
    同步运行图，返回最终状态。
    """
    input_params = inputs.get("input_params", inputs)

    num_records = input_params.get("num_records", 1)
    enable_search = input_params.get("enable_search", False)
    target_department = input_params.get("target_department")

    # 使用环境变量中的 LLM 配置（与 Web UI 解耦）
    model_config = {
        "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "model": os.getenv("LLM_MODEL", "gpt-4o"),
        "temperature": 0.0,
        "max_tokens": 4096,
    }

    # 如果指定了目标科室，将其置入科室池首项
    # （init_node 会打乱，但单记录时大概率选中）
    department_pool = list(DEPARTMENT_POOL)
    if target_department and target_department in department_pool:
        department_pool.remove(target_department)
        department_pool.insert(0, target_department)

    initial_state = {
        "num_records": num_records,
        "enable_search": enable_search,
        "model_config": model_config,
        "department_pool": department_pool,
        "search_results": "",
        "current_index": 0,
        "current_emr": None,
        "retry_count": 0,
        "max_retries": 3,
        "validation_feedback": "",
        "status_log": [],
        "emr_records": [],
        "warnings": [],
        "excel_path": "",
    }

    graph = build_graph()
    final_state = None
    for chunk in graph.stream(initial_state, stream_mode="values"):
        final_state = chunk

    return final_state


def run_evaluation(
    dataset_name: str,
    experiment_prefix: str,
    use_llm_judge: bool = False,
    max_concurrency: int = 1,
):
    """执行 LangSmith 评估实验。"""
    client = Client()

    evaluators = list(DETERMINISTIC_EVALUATORS)
    if use_llm_judge:
        evaluators.extend(LLM_JUDGE_EVALUATORS)
        print(f"[INFO] 使用 {len(evaluators)} 个评估器（含 LLM judge）")
    else:
        print(f"[INFO] 使用 {len(evaluators)} 个确定性评估器")

    results = evaluate(
        target_factory,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        max_concurrency=max_concurrency,
        metadata={
            "model": os.getenv("LLM_MODEL", "gpt-4o"),
            "evaluator_type": "llm_judge" if use_llm_judge else "deterministic",
        },
    )

    print(f"[DONE] 实验结果: {results}")
    return results


def run_smoke_test():
    """本地烟雾测试 —— 跑 1 条记录，输出概要。"""
    print("=" * 50)
    print("  LangSmith 评估 — 烟雾测试")
    print("=" * 50)

    api_key = os.getenv("LANGSMITH_API_KEY", "")
    if api_key:
        print(f"[INFO] LangSmith API Key: {api_key[:8]}...{api_key[-4:]}")
    else:
        print("[WARN] 未设置 LANGSMITH_API_KEY，测试仅在本地方运行")

    model = os.getenv("LLM_MODEL", "gpt-4o")
    print(f"[INFO] 模型: {model}")

    test_input = {"num_records": 1, "enable_search": False}
    print("[INFO] 运行中（1 条记录，无搜索）...")

    try:
        final = target_factory(test_input)
    except Exception as e:
        print(f"[FAIL] 图运行失败: {e}")
        return None

    records = final.get("emr_records", [])
    warnings = final.get("warnings", [])

    print(f"\n[OK] 生成 {len(records)} 条记录，{len(warnings)} 条警告")
    if records:
        r = records[0]
        print(f"  科室:     {r.get('department')}")
        print(f"  年龄/性别: {r.get('age')} / {r.get('gender')}")
        print(f"  主诉:     {r.get('chief_complaint', '')[:80]}")
        print(f"  诊断:     {r.get('diagnosis', '')[:80]}")
        print(f"  治疗:     {r.get('treatment', '')[:80]}")
        filled = len([k for k, v in r.items() if v])
        print(f"  字段完整度: {filled}/13")

    if warnings:
        print(f"\n  警告列表:")
        for w in warnings:
            print(f"    - {w[:120]}")

    print("\n[OK] 烟雾测试完成")
    return final


def main():
    parser = argparse.ArgumentParser(
        description="LangSmith 评估 CLI — 门诊电子病历智能体"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="emr-targeted-scenarios",
        help="LangSmith 数据集名称（默认 emr-targeted-scenarios）",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default="emr-eval",
        help="实验名称前缀（默认 emr-eval）",
    )
    parser.add_argument(
        "--llm-judge",
        action="store_true",
        help="包含 LLM-as-judge 评估器（需要额外 API 调用）",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="运行本地烟雾测试（不上传 LangSmith）",
    )

    args = parser.parse_args()

    if args.smoke:
        run_smoke_test()
    else:
        api_key = os.getenv("LANGSMITH_API_KEY", "")
        if not api_key:
            print("错误: 请在 .env 中设置 LANGSMITH_API_KEY")
            sys.exit(1)
        run_evaluation(
            dataset_name=args.dataset,
            experiment_prefix=args.prefix,
            use_llm_judge=args.llm_judge,
        )


if __name__ == "__main__":
    main()
