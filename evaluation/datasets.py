"""LangSmith 评估数据集定义。

三个类别：
- TARGETED_SCENARIOS: 定向科室单条记录（覆盖全部 18 个科室）
- MULTI_RECORD_SCENARIOS: 批量生成场景
"""

# ===========================================================================
# 定向科室场景（18 个科室，每个科室 1 条）
# ===========================================================================

TARGETED_SCENARIOS = [
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "呼吸内科",
        },
        "expected": {
            "department": "呼吸内科",
            "typical_chief_complaints": ["咳嗽", "咳痰", "发热", "胸闷", "气促", "胸痛"],
            "typical_diagnoses": [
                "急性支气管炎", "肺炎", "支气管哮喘", "慢性阻塞性肺疾病",
                "上呼吸道感染", "肺部感染",
            ],
            "key_checks": [
                "age_between_1_and_90",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "心血管内科",
        },
        "expected": {
            "department": "心血管内科",
            "typical_chief_complaints": ["胸痛", "胸闷", "心悸", "气短", "头晕", "水肿"],
            "typical_diagnoses": [
                "高血压", "冠心病", "心力衰竭", "心律失常",
                "心肌炎", "高脂血症",
            ],
            "key_checks": [
                "age_gte_35_for_chronic",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "神经内科",
        },
        "expected": {
            "department": "神经内科",
            "typical_chief_complaints": ["头痛", "头晕", "肢体麻木", "抽搐", "失眠", "记忆力减退"],
            "typical_diagnoses": [
                "偏头痛", "脑梗死", "脑供血不足", "面神经炎",
                "帕金森病", "癫痫",
            ],
            "key_checks": [
                "age_between_18_and_90",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "消化内科",
        },
        "expected": {
            "department": "消化内科",
            "typical_chief_complaints": ["腹痛", "腹胀", "恶心", "反酸", "腹泻", "便秘"],
            "typical_diagnoses": [
                "慢性胃炎", "胃食管反流病", "消化性溃疡", "功能性消化不良",
                "肠易激综合征", "急性胃肠炎",
            ],
            "key_checks": [
                "age_between_10_and_85",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "内分泌科",
        },
        "expected": {
            "department": "内分泌科",
            "typical_chief_complaints": ["多饮", "多尿", "体重下降", "乏力", "心悸", "怕热多汗"],
            "typical_diagnoses": [
                "2型糖尿病", "甲状腺功能亢进", "甲状腺功能减退",
                "高尿酸血症", "代谢综合征",
            ],
            "key_checks": [
                "age_between_18_and_80",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "肾内科",
        },
        "expected": {
            "department": "肾内科",
            "typical_chief_complaints": ["水肿", "腰痛", "尿频", "尿痛", "血尿", "泡沫尿"],
            "typical_diagnoses": [
                "慢性肾小球肾炎", "尿路感染", "肾病综合征",
                "慢性肾功能不全", "肾结石",
            ],
            "key_checks": [
                "age_between_10_and_85",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "内科",
        },
        "expected": {
            "department": "内科",
            "typical_chief_complaints": ["发热", "乏力", "头晕", "纳差", "全身不适"],
            "typical_diagnoses": [
                "急性上呼吸道感染", "贫血", "发热待查", "高血压",
            ],
            "key_checks": [
                "age_between_1_and_90",
                "vitals_in_range",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "外科",
        },
        "expected": {
            "department": "外科",
            "typical_chief_complaints": ["腹痛", "腹部包块", "颈部肿块", "乳房肿块"],
            "typical_diagnoses": [
                "急性阑尾炎", "胆囊结石", "腹股沟疝", "甲状腺结节",
            ],
            "key_checks": [
                "age_between_10_and_85",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "骨科",
        },
        "expected": {
            "department": "骨科",
            "typical_chief_complaints": ["关节疼痛", "腰腿痛", "活动受限", "外伤后疼痛", "颈肩痛"],
            "typical_diagnoses": [
                "腰椎间盘突出", "颈椎病", "膝关节骨性关节炎",
                "肩周炎", "骨折",
            ],
            "key_checks": [
                "age_between_12_and_90",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "泌尿外科",
        },
        "expected": {
            "department": "泌尿外科",
            "typical_chief_complaints": ["排尿困难", "尿频", "尿痛", "腰痛", "血尿"],
            "typical_diagnoses": [
                "前列腺增生", "泌尿系结石", "膀胱炎", "肾囊肿",
            ],
            "key_checks": [
                "age_between_18_and_90",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "神经外科",
        },
        "expected": {
            "department": "神经外科",
            "typical_chief_complaints": ["剧烈头痛", "肢体无力", "言语不清", "意识障碍", "癫痫发作"],
            "typical_diagnoses": [
                "脑出血", "颅内肿瘤", "颅脑损伤", "脑动脉瘤",
            ],
            "key_checks": [
                "age_between_18_and_85",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "妇产科",
        },
        "expected": {
            "department": "妇产科",
            "typical_chief_complaints": ["下腹痛", "月经不调", "阴道出血", "白带异常", "停经"],
            "typical_diagnoses": [
                "盆腔炎", "子宫肌瘤", "卵巢囊肿", "月经不调",
                "早孕", "阴道炎",
            ],
            "key_checks": [
                "patient_gender_female",
                "age_between_14_and_65",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "儿科",
        },
        "expected": {
            "department": "儿科",
            "typical_chief_complaints": ["发热", "咳嗽", "腹泻", "呕吐", "皮疹", "食欲不振"],
            "typical_diagnoses": [
                "急性上呼吸道感染", "小儿腹泻", "手足口病",
                "支气管肺炎", "幼儿急疹",
            ],
            "key_checks": [
                "age_between_0_and_14",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "眼科",
        },
        "expected": {
            "department": "眼科",
            "typical_chief_complaints": ["视力下降", "眼痛", "眼红", "异物感", "视物模糊", "流泪"],
            "typical_diagnoses": [
                "结膜炎", "白内障", "青光眼", "屈光不正", "干眼症",
            ],
            "key_checks": [
                "age_between_3_and_90",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "耳鼻喉科",
        },
        "expected": {
            "department": "耳鼻喉科",
            "typical_chief_complaints": ["鼻塞", "流涕", "咽痛", "耳痛", "耳鸣", "听力下降"],
            "typical_diagnoses": [
                "过敏性鼻炎", "慢性鼻窦炎", "急性扁桃体炎",
                "中耳炎", "声带息肉",
            ],
            "key_checks": [
                "age_between_2_and_85",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "皮肤科",
        },
        "expected": {
            "department": "皮肤科",
            "typical_chief_complaints": ["皮疹", "瘙痒", "红斑", "脱屑", "色素沉着", "水疱"],
            "typical_diagnoses": [
                "湿疹", "荨麻疹", "银屑病", "接触性皮炎",
                "带状疱疹", "痤疮",
            ],
            "key_checks": [
                "age_between_1_and_90",
                "vitals_in_range",
                "diagnosis_matches_department",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "急诊科",
        },
        "expected": {
            "department": "急诊科",
            "typical_chief_complaints": ["突发胸痛", "腹痛", "头晕伴意识模糊", "外伤", "呼吸困难"],
            "typical_diagnoses": [
                "急性心肌梗死", "急性胰腺炎", "脑卒中",
                "过敏性休克", "急性创伤",
            ],
            "key_checks": [
                "age_between_1_and_90",
                "vitals_in_range",
                "soap_format_complete",
            ],
        },
    },
    {
        "input": {
            "num_records": 1,
            "enable_search": False,
            "target_department": "全科",
        },
        "expected": {
            "department": "全科",
            "typical_chief_complaints": ["头晕", "乏力", "发热", "体重下降", "全身酸痛"],
            "typical_diagnoses": [
                "高血压", "上呼吸道感染", "2型糖尿病",
                "缺铁性贫血", "高脂血症",
            ],
            "key_checks": [
                "age_between_18_and_85",
                "vitals_in_range",
                "soap_format_complete",
            ],
        },
    },
]

# ===========================================================================
# 批量记录场景
# ===========================================================================

MULTI_RECORD_SCENARIOS = [
    {
        "input": {
            "num_records": 3,
            "enable_search": True,
            "target_department": None,
        },
        "expected": {
            "quality_checks": [
                "all_soap_format_complete",
                "no_duplicate_chief_complaints",
                "diverse_departments",
                "all_vitals_in_range",
            ],
        },
    },
    {
        "input": {
            "num_records": 5,
            "enable_search": False,
            "target_department": None,
        },
        "expected": {
            "quality_checks": [
                "all_soap_format_complete",
                "no_duplicate_chief_complaints",
                "diverse_departments",
                "all_vitals_in_range",
                "min_pass_rate_80_percent",
            ],
        },
    },
]

# ===========================================================================
# 聚合导出
# ===========================================================================

ALL_SCENARIOS = {
    "emr-targeted-scenarios": TARGETED_SCENARIOS,
    "emr-multi-record-scenarios": MULTI_RECORD_SCENARIOS,
}
