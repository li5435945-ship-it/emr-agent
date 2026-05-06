"""自定义评估器。

确定性评估器（不消耗 LLM token）：
  - emr_fields_present      13 个必要字段是否齐全
  - vitals_in_range         T/P/R/BP 数值在医学合理范围
  - age_diagnosis_plausibility  年龄-诊断流行病学合理性
  - medication_dosage_reasonable  药物剂量模式检查
  - duplicate_detection     主诉多样性检查
  - chief_complaint_diagnosis_consistency  主诉-诊断一致性

LLM-as-judge 评估器：
  - llm_as_judge_evaluator() 工厂函数
"""

import json
import re
from difflib import SequenceMatcher
from typing import Any


# ===========================================================================
# 辅助函数
# ===========================================================================


def _extract_emr(run) -> dict | None:
    """从 LangSmith Run 输出中提取单条 EMR dict。"""
    outputs = run.outputs
    if isinstance(outputs, dict):
        records = outputs.get("emr_records", [])
        if records:
            return records[0]
    return None


def _extract_records(run) -> list[dict]:
    """从 Run 输出中提取所有 EMR 记录。"""
    outputs = run.outputs
    if isinstance(outputs, dict):
        return outputs.get("emr_records", [])
    return []


REQUIRED_FIELDS = [
    "visit_time", "department", "patient_name", "gender", "age",
    "chief_complaint", "present_illness", "past_history",
    "physical_exam", "auxiliary_exam", "diagnosis", "treatment", "doctor_name",
]


# ===========================================================================
# 确定性评估器
# ===========================================================================


def emr_fields_present(run, example) -> dict:
    """检查 SOAP 格式所有必要字段是否完整。"""
    emr = _extract_emr(run)
    if not emr:
        return {"key": "fields_present", "score": 0.0, "comment": "No EMR found in run output"}

    missing = [f for f in REQUIRED_FIELDS if not emr.get(f)]
    score = 1.0 - (len(missing) / len(REQUIRED_FIELDS))
    return {
        "key": "fields_present",
        "score": round(score, 3),
        "comment": f"Missing: {missing}" if missing else "All 13 fields present",
    }


def vitals_in_range(run, example) -> dict:
    """验证 T/P/R/BP 生命体征在医学合理范围内。

    正常范围：
    - 体温: 35.0 – 42.0 °C
    - 脉搏: 30 – 250 次/分
    - 呼吸: 8 – 60 次/分
    - 收缩压: 60 – 260 mmHg
    - 舒张压: 30 – 160 mmHg
    - 收缩压 > 舒张压
    """
    emr = _extract_emr(run)
    if not emr:
        return {"key": "vitals_in_range", "score": 0.0, "comment": "No EMR"}

    physical_exam = emr.get("physical_exam", "")

    temp_match = re.search(r"T\s*(\d+\.?\d*)\s*[℃C]?", physical_exam)
    pulse_match = re.search(r"P\s*(\d+)\s*次", physical_exam)
    resp_match = re.search(r"R\s*(\d+)\s*次", physical_exam)
    bp_match = re.search(r"BP\s*(\d+)\s*/\s*(\d+)", physical_exam)

    issues = []

    if temp_match:
        t = float(temp_match.group(1))
        if t < 35 or t > 42:
            issues.append(f"体温 {t} 超出范围 [35,42]")

    if pulse_match:
        p = int(pulse_match.group(1))
        if p < 30 or p > 250:
            issues.append(f"脉搏 {p} 超出范围 [30,250]")

    if resp_match:
        r = int(resp_match.group(1))
        if r < 8 or r > 60:
            issues.append(f"呼吸 {r} 超出范围 [8,60]")

    if bp_match:
        sys_bp = int(bp_match.group(1))
        dia_bp = int(bp_match.group(2))
        if sys_bp < 60 or sys_bp > 260 or dia_bp < 30 or dia_bp > 160:
            issues.append(f"血压 {sys_bp}/{dia_bp} 超出范围")
        if sys_bp <= dia_bp:
            issues.append(f"收缩压 {sys_bp} <= 舒张压 {dia_bp}")

    score = 1.0 if not issues else 0.0
    return {
        "key": "vitals_in_range",
        "score": score,
        "comment": "; ".join(issues) if issues else "All vitals in plausible range",
    }


def age_diagnosis_plausibility(run, example) -> dict:
    """检查年龄与诊断的流行病学合理性。

    - 儿科患者年龄应 ≤ 14 岁
    - 老年病不应出现在未成年人
    - 儿童专属疾病不应出现在成年人
    """
    emr = _extract_emr(run)
    if not emr:
        return {"key": "age_diag_plausibility", "score": 0.0, "comment": "No EMR"}

    age = emr.get("age", 0)
    diagnosis = emr.get("diagnosis", "")
    dept = emr.get("department", "")

    issues = []

    if dept == "儿科" and age > 14:
        issues.append(f"儿科科室但年龄 {age} > 14")

    geriatric_conditions = [
        "前列腺增生", "骨质疏松", "老年性", "白内障",
        "帕金森", "阿尔茨海默",
    ]
    if age < 18:
        for cond in geriatric_conditions:
            if cond in diagnosis:
                issues.append(f"老年疾病 '{cond}' 出现在 {age} 岁患者")

    pediatric_only = ["手足口病", "幼儿急疹", "百日咳"]
    if age > 18:
        for cond in pediatric_only:
            if cond in diagnosis:
                issues.append(f"儿科疾病 '{cond}' 出现在 {age} 岁患者")

    score = 1.0 if not issues else 0.0
    return {
        "key": "age_diag_plausibility",
        "score": score,
        "comment": "; ".join(issues) if issues else "Age-diagnosis plausibly consistent",
    }


def medication_dosage_reasonable(run, example) -> dict:
    """检查治疗字段中的药物剂量模式是否合理。

    - 口服药单次剂量不应超过 50 片/粒
    - 单次 mg 剂量不应超过 5000mg
    - 儿童患者不应出现"成人"用量标注
    """
    emr = _extract_emr(run)
    if not emr:
        return {"key": "med_dosage", "score": 0.0, "comment": "No EMR"}

    treatment = emr.get("treatment", "")
    age = emr.get("age", 0)
    issues = []

    abnormal_dosage = re.findall(r"(\d{3,})\s*(片|粒|颗|支|瓶|袋)", treatment)
    for amount, unit in abnormal_dosage:
        if int(amount) > 50:
            issues.append(f"异常剂量: {amount}{unit}")

    mg_dosage = re.findall(r"(\d{4,})\s*mg", treatment)
    for amount in mg_dosage:
        if int(amount) > 5000:
            issues.append(f"异常 mg 剂量: {amount}mg")

    if age < 12:
        if "成人" in treatment:
            issues.append("儿童患者治疗方案中出现'成人'标注")

    score = 1.0 if not issues else 0.5
    return {
        "key": "med_dosage",
        "score": score,
        "comment": "; ".join(issues) if issues else "Dosage patterns appear reasonable",
    }


def duplicate_detection(run, example) -> dict:
    """检查批量生成的主诉/诊断是否有过高相似度。"""
    records = _extract_records(run)
    if len(records) < 2:
        return {
            "key": "duplicate_detection",
            "score": 1.0,
            "comment": "Single record, no duplication check needed",
        }

    complaints = [r.get("chief_complaint", "") for r in records]
    diagnoses = [r.get("diagnosis", "") for r in records]

    max_cc_sim = 0.0
    max_diag_sim = 0.0
    for i in range(len(complaints)):
        for j in range(i + 1, len(complaints)):
            cc_sim = SequenceMatcher(None, complaints[i], complaints[j]).ratio()
            diag_sim = SequenceMatcher(None, diagnoses[i], diagnoses[j]).ratio()
            max_cc_sim = max(max_cc_sim, cc_sim)
            max_diag_sim = max(max_diag_sim, diag_sim)

    issues = []
    if max_cc_sim > 0.8:
        issues.append(f"主诉高度相似 ({max_cc_sim:.2f})")
    if max_diag_sim > 0.9:
        issues.append(f"诊断高度重复 ({max_diag_sim:.2f})")

    score = 1.0 if not issues else 0.2
    return {
        "key": "duplicate_detection",
        "score": score,
        "comment": "; ".join(issues) if issues else f"Records sufficiently diverse (max cc sim: {max_cc_sim:.2f})",
    }


def chief_complaint_diagnosis_consistency(run, example) -> dict:
    """检查主诉-诊断一致性（利用内置校验结果）。"""
    outputs = run.outputs
    if not isinstance(outputs, dict):
        return {"key": "cc_diag_consistency", "score": 0.0, "comment": "No output state"}

    warnings = outputs.get("warnings", [])
    for w in warnings:
        if "主诉" in w or "一致性" in w:
            return {
                "key": "cc_diag_consistency",
                "score": 0.2,
                "comment": f"Force-passed with consistency issue: {w[:100]}",
            }

    return {
        "key": "cc_diag_consistency",
        "score": 1.0,
        "comment": "Built-in validator passed (no consistency warnings)",
    }


def diagnosis_department_match(run, example) -> dict:
    """检查诊断是否与指定科室基本匹配（关键词覆盖）。"""
    emr = _extract_emr(run)
    if not emr:
        return {"key": "diag_dept_match", "score": 0.0, "comment": "No EMR"}

    expected = (example.outputs or {}).get("quality_criteria", {})
    typical_diags = expected.get("typical_diagnoses", [])

    if not typical_diags:
        return {
            "key": "diag_dept_match",
            "score": None,
            "comment": "No reference diagnoses to compare",
        }

    diagnosis_text = emr.get("diagnosis", "")
    match = any(keyword in diagnosis_text for keyword in typical_diags)

    return {
        "key": "diag_dept_match",
        "score": 1.0 if match else 0.3,
        "comment": (
            f"Diagnosis '{diagnosis_text[:60]}' matches department pool"
            if match
            else f"Diagnosis '{diagnosis_text[:60]}' outside typical pool for this department"
        ),
    }


# ===========================================================================
# LLM-as-judge 评估器工厂
# ===========================================================================


def llm_as_judge_evaluator(dimension: str):
    """创建 LLM-as-judge 评估器。

    dimension:
      - "diagnosis_treatment_match": 诊断与治疗方案是否匹配
      - "format_completeness": SOAP 格式各部分是否详尽
    """
    JUDGE_PROMPTS = {
        "diagnosis_treatment_match": (
            "请评审以下门诊电子病历的「诊断」与「治疗方案」是否临床一致、逻辑匹配。"
            "输出 JSON: {\"score\": 0-100, \"explanation\": \"中文说明\", \"pass\": true/false}"
        ),
        "format_completeness": (
            "请评审以下门诊电子病历是否遵循 SOAP 格式，各部分是否详尽、描述充分。"
            "输出 JSON: {\"score\": 0-100, \"explanation\": \"中文说明\", \"pass\": true/false}"
        ),
    }

    def evaluator(run, example) -> dict:
        import os

        from langchain_openai import ChatOpenAI

        emr = _extract_emr(run)
        if not emr:
            return {"key": f"llm_judge_{dimension}", "score": 0.0, "comment": "No EMR"}

        llm = ChatOpenAI(
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            temperature=0.0,
            max_tokens=1024,
        )

        prompt = JUDGE_PROMPTS.get(
            dimension,
            f"Evaluate EMR quality for dimension: {dimension}. Output JSON with score (0-100).",
        )
        full_prompt = f"{prompt}\n\nEMR:\n{json.dumps(emr, ensure_ascii=False, indent=2)}"

        try:
            response = llm.invoke(full_prompt)
            result = json.loads(response.content)
            return {
                "key": f"llm_judge_{dimension}",
                "score": result.get("score", 0) / 100.0,
                "comment": result.get("explanation", ""),
            }
        except json.JSONDecodeError:
            raw = response.content if isinstance(response.content, str) else str(response.content)
            return {
                "key": f"llm_judge_{dimension}",
                "score": 0.0,
                "comment": f"Judge output parse error: {raw[:200]}",
            }

    return evaluator


# ===========================================================================
# 评估器汇总
# ===========================================================================

DETERMINISTIC_EVALUATORS = [
    emr_fields_present,
    vitals_in_range,
    age_diagnosis_plausibility,
    medication_dosage_reasonable,
    duplicate_detection,
    chief_complaint_diagnosis_consistency,
    diagnosis_department_match,
]

LLM_JUDGE_EVALUATORS = [
    llm_as_judge_evaluator("diagnosis_treatment_match"),
    llm_as_judge_evaluator("format_completeness"),
]

ALL_EVALUATORS = DETERMINISTIC_EVALUATORS + LLM_JUDGE_EVALUATORS
