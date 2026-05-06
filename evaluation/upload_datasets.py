"""将评估数据集上传到 LangSmith。

Usage:
    python evaluation/upload_datasets.py          # 上传全部数据集
    python evaluation/upload_datasets.py --dry-run  # 仅预览
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from langsmith import Client

from evaluation.datasets import ALL_SCENARIOS


def upload_dataset(client, name: str, examples: list, dry_run: bool = False):
    """上传（或覆盖）一个数据集。"""
    if dry_run:
        print(f"[DRY RUN] 将上传 {len(examples)} 条示例到数据集 '{name}'")
        for ex in examples:
            dept = ex["input"].get("target_department") or "随机"
            records = ex["input"].get("num_records", 1)
            print(f"  - {dept} ({records} 条记录)")
        return

    # 如果已存在则删除后重建
    try:
        existing = client.read_dataset(dataset_name=name)
        client.delete_dataset(dataset_id=existing.id)
        print(f"已删除旧数据集 '{name}'")
    except Exception:
        pass

    dataset = client.create_dataset(
        dataset_name=name,
        description=f"门诊电子病历生成评估 — {name}",
    )

    for i, example in enumerate(examples):
        client.create_example(
            inputs={"input_params": example["input"]},
            outputs={"quality_criteria": example["expected"]},
            dataset_id=dataset.id,
        )
        dept = example["input"].get("target_department") or "随机"
        print(f"  [{i+1}/{len(examples)}] {dept}")

    print(f"已上传 {len(examples)} 条示例到数据集 '{name}'")


def main():
    parser = argparse.ArgumentParser(description="上传评估数据集到 LangSmith")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际上传",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="仅上传指定数据集（默认全部）",
    )
    args = parser.parse_args()

    api_key = os.getenv("LANGSMITH_API_KEY", "")
    if not api_key and not args.dry_run:
        print("错误: 请在 .env 中设置 LANGSMITH_API_KEY")
        sys.exit(1)

    client = Client() if not args.dry_run else None

    datasets_to_upload = (
        {args.dataset: ALL_SCENARIOS[args.dataset]}
        if args.dataset
        else ALL_SCENARIOS
    )

    for name, examples in datasets_to_upload.items():
        upload_dataset(client, name, examples, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
