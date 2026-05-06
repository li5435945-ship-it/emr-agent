"""LangGraph 节点实现 —— 搜索、生成、校验、汇总。"""

import json
import re
from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from emr_schema import DEPARTMENT_POOL, OutpatientEMR
from tools import web_search

# 加载提示词
_PROMPTS_DIR = Path(__file__).parent / "prompts"
EMR_SYSTEM_PROMPT = (_PROMPTS_DIR / "emr_system.txt").read_text(encoding="utf-8")
VALIDATE_SYSTEM_PROMPT = (_PROMPTS_DIR / "validate_system.txt").read_text(encoding="utf-8")


def _build_llm(model_config: dict) -> ChatOpenAI:
    """根据配置构建 ChatOpenAI 实例。"""
    return ChatOpenAI(
        base_url=model_config["base_url"],
        api_key=model_config["api_key"],
        model=model_config["model"],
        temperature=model_config.get("temperature", 0.7),
        max_tokens=model_config.get("max_tokens", 4096),
    )


def _make_status(index: int, department: str, stage: str, message: str,
                 retry_count: int = 0, force_pass: bool = False) -> dict:
    """生成统一的状态日志条目。"""
    return {
        "index": index,
        "department": department,
        "stage": stage,  # generating | validating | passed | retrying | force_passed
        "message": message,
        "retry_count": retry_count,
        "force_pass": force_pass,
        "time": datetime.now().strftime("%H:%M:%S"),
    }


def init_node(state: dict) -> dict:
    """初始化节点：设置默认值，随机打乱科室池。"""
    import random
    pool = list(DEPARTMENT_POOL)
    random.shuffle(pool)
    return {
        "department_pool": pool,
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


def search_web_node(state: dict) -> dict:
    """搜索节点：检索中文医疗网站的电子病历书写规范与诊疗指南。"""
    queries = [
        "门诊电子病历书写规范 SOAP格式",
        "病历书写基本规范 国家卫健委",
        "临床诊疗指南 常见病诊断标准",
    ]
    all_results = []
    for q in queries:
        result = web_search(q)
        all_results.append(result)

    combined = "\n\n---\n\n".join(all_results)

    # 推送状态日志——搜索不绑定特定病历，index=-1 表示全局
    log_entry = {
        "index": -1,
        "department": "全局",
        "stage": "search_done",
        "message": f"已完成 {len(queries)} 个医疗规范搜索",
        "retry_count": 0,
        "force_pass": False,
        "time": datetime.now().strftime("%H:%M:%S"),
    }
    return {
        "search_results": combined[:6000],  # 截断，控制 token
        "status_log": [log_entry],
    }


def generate_emr_node(state: dict) -> dict:
    """生成节点：调用 LLM 生成单份电子病历 JSON。"""
    llm = _build_llm(state["model_config"])
    llm = llm.bind(response_format={"type": "json_object"})

    # 随机选取科室
    idx = state["current_index"]
    pool = state["department_pool"]
    department = pool[idx % len(pool)]

    # 构建用户消息
    user_parts = [
        f"请生成一份**{department}**的门诊电子病历。",
        f"患者就诊时间设定为 {datetime.now().strftime('%Y-%m-%d %H:%M')} 前后。",
    ]

    if state["search_results"]:
        user_parts.append(
            "参考以下病历书写规范和诊疗指南：\n"
            f"{state['search_results'][:2000]}"
        )

    if state["validation_feedback"]:
        user_parts.append(
            "⚠️ 上一版病历未通过质量审查，请根据以下反馈修正：\n"
            f"{state['validation_feedback']}\n"
            "务必修正上述所有问题，确保病历质量达标。"
        )

    user_parts.append("请直接输出 JSON，不要包含任何额外文本。")

    messages = [
        SystemMessage(content=EMR_SYSTEM_PROMPT),
        HumanMessage(content="\n\n".join(user_parts)),
    ]

    # 推送"生成中"状态
    is_retry = state["retry_count"] > 0
    stage = "retrying" if is_retry else "generating"
    msg = f"第{idx+1}份：{department}{'（重试' + str(state['retry_count']) + '）' if is_retry else ''} — 生成中..."

    status = _make_status(idx, department, stage, msg, state["retry_count"])

    # 调用 LLM
    response = llm.invoke(messages)
    raw = response.content

    # 解析 JSON
    try:
        # 尝试提取 JSON 块
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            emr_data = json.loads(json_match.group())
        else:
            emr_data = json.loads(raw)
    except json.JSONDecodeError:
        # LLM 输出格式错误，返回占位并标记
        emr_data = {
            "visit_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "department": department,
            "patient_name": "解析失败",
            "gender": "未知",
            "age": 0,
            "chief_complaint": f"LLM JSON 解析错误，原始输出: {raw[:200]}",
            "present_illness": "",
            "past_history": "",
            "physical_exam": "",
            "auxiliary_exam": "",
            "diagnosis": "",
            "treatment": "",
            "doctor_name": "",
        }

    # 确保 department 字段一致
    emr_data["department"] = department

    return {
        "current_emr": emr_data,
        "status_log": [status],
    }


def validate_emr_node(state: dict) -> dict:
    """校验节点：LLM 审查病历质量，输出 pass/fail + 反馈。"""
    llm = _build_llm(state["model_config"])
    llm = llm.bind(response_format={"type": "json_object"})

    emr = state["current_emr"]
    idx = state["current_index"]
    dept = emr.get("department", "未知")

    # 快速前置检查：JSON 解析是否成功
    if emr.get("patient_name") == "解析失败":
        return {
            "validation_feedback": "LLM 输出格式错误，无法解析为 JSON",
            "retry_count": state["retry_count"] + 1,
            "status_log": [_make_status(idx, dept, "retrying",
                                        f"第{idx+1}份：JSON 解析失败，准备重试",
                                        state["retry_count"] + 1)],
        }

    messages = [
        SystemMessage(content=VALIDATE_SYSTEM_PROMPT),
        HumanMessage(content=f"请审查以下门诊电子病历：\n\n{json.dumps(emr, ensure_ascii=False, indent=2)}"),
    ]

    response = llm.invoke(messages)
    raw = response.content

    # 解析校验结果
    try:
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"pass": False, "score": 0, "issues": [f"校验器输出解析失败: {raw[:200]}"], "suggestion": "重新生成"}

    passed = result.get("pass", False)
    retry_count = state["retry_count"]
    max_retries = state["max_retries"]

    if passed:
        # 通过：追加到 emr_records
        return {
            "emr_records": [emr],
            "validation_feedback": "",
            "retry_count": 0,
            "status_log": [_make_status(idx, dept, "passed",
                                        f"第{idx+1}份：校验通过（评分: {result.get('score', '?')}）")],
        }

    # 不通过
    retry_count += 1
    if retry_count >= max_retries:
        # 超过最大重试，强制通过
        warning = f"第{idx+1}份（{dept}）：{max_retries}次重试未通过，强制接受。问题: {'; '.join(result.get('issues', []))}"
        return {
            "emr_records": [emr],
            "warnings": [warning],
            "validation_feedback": "",
            "retry_count": 0,
            "status_log": [_make_status(idx, dept, "force_passed", warning, retry_count, force_pass=True)],
        }

    # 需要重试
    feedback = f"问题: {'; '.join(result.get('issues', []))}\n修正建议: {result.get('suggestion', '请修正上述问题')}"
    return {
        "validation_feedback": feedback,
        "retry_count": retry_count,
        "status_log": [_make_status(idx, dept, "retrying",
                                    f"第{idx+1}份：校验不通过（{retry_count}/{max_retries}），重试中... 问题: {'; '.join(result.get('issues', []))}",
                                    retry_count)],
    }


def next_record_node(state: dict) -> dict:
    """路由判断节点：递增索引，清空当前病历状态。"""
    return {
        "current_index": state["current_index"] + 1,
        "current_emr": None,
        "retry_count": 0,
        "validation_feedback": "",
    }


