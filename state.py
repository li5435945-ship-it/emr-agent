"""LangGraph State 定义。"""

import operator
from typing import Annotated, TypedDict


class EMRState(TypedDict):
    # 输入参数
    num_records: int
    enable_search: bool
    model_config: dict  # {base_url, api_key, model, temperature, max_tokens}

    # 共享资源
    department_pool: list[str]
    search_results: str

    # 当前病历生成状态
    current_index: int
    current_emr: dict | None
    retry_count: int
    max_retries: int
    validation_feedback: str

    # 质量追踪（用于 SSE 推送），operator.add 实现追加式更新
    status_log: Annotated[list[dict], operator.add]

    # 最终结果
    emr_records: Annotated[list[dict], operator.add]
    warnings: Annotated[list[str], operator.add]
    excel_path: str
