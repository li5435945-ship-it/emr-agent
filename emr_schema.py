"""门诊电子病历 Pydantic 数据模型。"""

from pydantic import BaseModel, Field


class OutpatientEMR(BaseModel):
    visit_time: str = Field(description="就诊时间，如 2026-04-28 09:30")
    department: str = Field(description="就诊科室")
    patient_name: str = Field(description="患者姓名（脱敏，如 张**）")
    gender: str = Field(description="性别：男/女")
    age: int = Field(description="年龄")
    chief_complaint: str = Field(description="主诉：症状+持续时间")
    present_illness: str = Field(description="现病史：发病过程、诊疗经过")
    past_history: str = Field(description="既往史：既往疾病、过敏史")
    physical_exam: str = Field(description="体格检查：T/P/R/BP + 系统查体")
    auxiliary_exam: str = Field(description="辅助检查：实验室/影像学结果")
    diagnosis: str = Field(description="诊断：主诊断 + 鉴别诊断")
    treatment: str = Field(description="治疗意见：药物、随访建议")
    doctor_name: str = Field(description="医师签名")


# 科室池
DEPARTMENT_POOL: list[str] = [
    "内科", "呼吸内科", "消化内科", "心血管内科", "神经内科",
    "内分泌科", "肾内科", "外科", "骨科", "泌尿外科",
    "神经外科", "妇产科", "儿科", "眼科", "耳鼻喉科",
    "皮肤科", "急诊科", "全科",
]
