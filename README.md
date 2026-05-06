# 门诊电子病历智能生成系统

基于 **LangGraph** 构建的智能体，调用大模型 API 生成符合真实诊疗逻辑的门诊电子病历，内置多轮校验-修正闭环，前端实时展示进度，结果通过 Excel 导出。

## 快速开始

### 1. 环境准备

```bash
# 激活 conda 环境（依赖已安装，无需再次 pip install）
conda activate F:\ProgramData\anaconda3\envs\emr
```

### 2. 启动服务

```bash
cd /d F:\ProgramData\anaconda3\envs\emr
python main.py
```

### 3. 打开浏览器

访问 **http://localhost:8000**，配置 LLM API 参数后开始生成。

## 配置说明

所有 LLM 配置在前端页面完成，无需修改配置文件：

| 参数 | 说明 | 示例 |
|------|------|------|
| API Base URL | OpenAI 兼容接口地址 | `https://api.deepseek.com/v1` |
| API Key | 你的密钥 | `sk-xxxxx` |
| 模型名 | 模型标识 | `deepseek-chat`（DeepSeek V4） |
| 温度 | 控制随机性 0-2 | `0.7` |
| 生成数量 | 需要几份病历 | `5` |
| 搜索规范 | 是否检索医疗网站 | 勾选 |

## 工作流程

```
用户设置参数 → [搜索中文医疗规范] → 逐份生成病历
                                       ↓
           校验诊疗逻辑 ←────────────────┘
           ↓ 不通过(≤3次)
           自动重试修正
           ↓ 通过
           下一份 / 导出 Excel
```

### 质量保障（6 维校验）

每份病历生成后由 LLM 自动审查：

1. **主诉-诊断一致性** — 症状是否导向诊断结论
2. **诊断-治疗匹配** — 用药是否对应诊断疾病
3. **年龄合理性** — 诊断是否符合年龄段特征
4. **体格检查合理性** — T/P/R/BP 是否在医学合理范围
5. **病历格式完整性** — 是否符合 SOAP 格式要求
6. **药物剂量合理性** — 用法用量是否规范

校验不通过自动携带反馈重试生成，最多 3 次；超限则强制通过并在 Excel 中标黄警告。

## 项目结构

```
emr code/
├── main.py                 FastAPI 入口 + SSE 流式接口
├── config.py               LLM 配置 + LangSmith 设置
├── state.py                LangGraph 状态定义
├── graph.py                状态图构建（节点 + 条件边）+ traceable 包装
├── nodes.py                节点实现（init/search/generate/validate/next）
├── tools.py                Web 搜索工具（ddgs, 偏重中文医疗网站，失败自动降级）
├── emr_schema.py           病历 Pydantic 数据模型 + 科室池
├── excel_writer.py         Excel 导出（格式化, 警告高亮）
├── .env.example            LangSmith + LLM 配置模板（可提交）
├── .env                    实际配置（含 API Key，gitignore）
├── prompts/
│   ├── emr_system.txt      病历生成提示词
│   └── validate_system.txt 校验提示词（6维度）
├── evaluation/             LangSmith 评估模块
│   ├── datasets.py         评估数据集定义（18 科室 + 批量）
│   ├── upload_datasets.py  数据集上传脚本
│   ├── evaluators.py       7 个确定性评估器 + LLM-as-judge 工厂
│   └── run_eval.py         离线评估 CLI
├── static/
│   └── index.html          前端单页（SSE 实时进度）
└── requirements.txt        依赖清单
```

## 电子病历字段

每份生成的病历包含：就诊时间、科室、患者姓名（脱敏）、性别、年龄、主诉、现病史、既往史、体格检查、辅助检查、诊断、治疗意见、医师签名。

科室从 18 个科室池中完全随机抽取：内科、呼吸内科、消化内科、心血管内科、神经内科、内分泌科、肾内科、外科、骨科、泌尿外科、神经外科、妇产科、儿科、眼科、耳鼻喉科、皮肤科、急诊科、全科。

## LangSmith 评估体系

项目集成了 **LangSmith** 用于智能体的可观测性追踪与离线质量评估。

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    LangSmith 评估流程                      │
│                                                           │
│  数据集（18科室 + 2批量场景）                                │
│       │                                                   │
│       ▼                                                   │
│  target_factory() ──► 构建初始状态 → 运行 LangGraph 图      │
│       │                    │                              │
│       │              init → search? → generate → validate │
│       │                    │                              │
│       ▼                    ▼                              │
│  最终状态（emr_records）   LangSmith 自动追踪每个节点        │
│       │                                                   │
│       ▼                                                   │
│  7 个确定性评估器 ← 逐条评分                                 │
│       │                                                   │
│       ▼                                                   │
│  LangSmith Experiments → 汇总统计，可视化对比                │
└─────────────────────────────────────────────────────────┘
```

### 评估器详解（7 个确定性评估器）

所有评估器接收 LangSmith 的 `Run`（图运行结果）和 `Example`（数据集预期值），返回 `{key, score, comment}` 评分三元组。

#### 1. `emr_fields_present` — 字段完整性

| 项目 | 内容 |
|------|------|
| **原理** | 检查 13 个必要 SOAP 字段（visit_time, department, patient_name, gender, age, chief_complaint, present_illness, past_history, physical_exam, auxiliary_exam, diagnosis, treatment, doctor_name）是否全部存在且非空 |
| **评分** | `1.0 - 缺失字段数 / 13`，满分 1.0 表示全部齐全 |
| **类型** | 纯字符串判断，零 token 消耗 |

#### 2. `vitals_in_range` — 生命体征合理范围

| 项目 | 内容 |
|------|------|
| **原理** | 用正则从体格检查文本中提取 T（体温）、P（脉搏）、R（呼吸）、BP（血压），与医学合理范围比对 |
| **范围** | T: 35.0–42.0°C，P: 30–250 次/分，R: 8–60 次/分，收缩压: 60–260mmHg，舒张压: 30–160mmHg，且收缩压 > 舒张压 |
| **评分** | 全部通过 = 1.0，任一越界 = 0.0 |
| **类型** | 正则提取 + 数值比较，零 token 消耗 |

#### 3. `age_diagnosis_plausibility` — 年龄-诊断流行病学合理性

| 项目 | 内容 |
|------|------|
| **原理** | 基于医学流行病学常识的启发式规则：儿科科室年龄应 ≤ 14；老年疾病（如前列腺增生、骨质疏松、帕金森）不应出现在 < 18 岁患者；儿童专属疾病（如手足口病、幼儿急疹）不应出现在 > 18 岁患者 |
| **评分** | 无违规 = 1.0，有违规 = 0.0 |
| **类型** | 规则引擎，零 token 消耗 |

#### 4. `medication_dosage_reasonable` — 药物剂量合理性

| 项目 | 内容 |
|------|------|
| **原理** | 正则提取治疗方案中的剂量模式，检查：口服药单次不超过 50 片/粒、单次 mg 剂量不超过 5000mg、儿童患者不应标注"成人"用量 |
| **评分** | 无异常 = 1.0，有异常 = 0.5 |
| **类型** | 正则提取 + 规则判断，零 token 消耗 |

#### 5. `duplicate_detection` — 主诉/诊断多样性

| 项目 | 内容 |
|------|------|
| **原理** | 对批量生成（≥2 条记录），用 `SequenceMatcher` 计算任意两条主诉之间和诊断之间的文本相似度。相似度 > 0.8（主诉）或 > 0.9（诊断）视为高度重复 |
| **评分** | 无重复 = 1.0，有重复 = 0.2 |
| **类型** | 文本相似度算法（difflib），零 token 消耗 |

#### 6. `chief_complaint_diagnosis_consistency` — 主诉-诊断一致性

| 项目 | 内容 |
|------|------|
| **原理** | 复用智能体内置的 6 维校验结果。如果某条记录被 force-pass 且警告信息中含"主诉"或"一致性"关键词，说明内置校验器判定该记录存在主诉-诊断不一致 |
| **评分** | 无警告 = 1.0，有相关警告 = 0.2 |
| **类型** | 读取已有校验结果，零额外 token 消耗 |

#### 7. `diagnosis_department_match` — 诊断-科室匹配

| 项目 | 内容 |
|------|------|
| **原理** | 将生成病历的诊断文本与数据集中该科室的典型诊断关键词池做包含匹配（如"心血管内科"的典型诊断含"高血压""冠心病"等） |
| **评分** | 命中 = 1.0，未命中 = 0.3 |
| **类型** | 关键词匹配，零 token 消耗 |
| **注意** | 当前智能体的 init_node 会随机打乱科室池，生成科室不可控，因此该评估器命中率仅 ~6%（1/18），仅作为参考 |

### 评估器设计原则

1. **确定性优先** — 全部 7 个评估器都是确定性的（规则/正则/相似度），不消耗额外 LLM token，评分结果可复现
2. **互补覆盖** — 覆盖格式、数值、逻辑、多样性四个维度的质量检查，与内置的 LLM 校验形成互补
3. **轻量级** — 评估器无需调用 LLM，执行耗时可忽略不计

> 可选扩展：`evaluation/evaluators.py` 中额外提供了 `llm_as_judge_evaluator()` 工厂函数，可创建基于 LLM-as-Judge 的评估器（如 `diagnosis_treatment_match`、`format_completeness`），在 `run_eval.py` 中通过 `--llm-judge` 参数启用。

### 评估数据集

| 数据集 | 示例数 | 说明 |
|--------|--------|------|
| `emr-targeted-scenarios` | 18 条 | 覆盖全部 18 个科室，每条含典型主诉和诊断关键词池 |
| `emr-multi-record-scenarios` | 2 条 | 3 条和 5 条批量生成场景 |

### 使用方式

```bash
# 1. 配置 .env（从模板复制并填入真实 key）
cp .env.example .env

# 2. 上传数据集到 LangSmith（首次）
python evaluation/upload_datasets.py

# 3. 跑本地烟雾测试（1 条记录，不上传）
python evaluation/run_eval.py --smoke

# 4. 跑完整评估（确定性评估器）
python evaluation/run_eval.py --dataset emr-targeted-scenarios --prefix my-experiment

# 5. 跑完整评估（含 LLM-as-judge）
python evaluation/run_eval.py --dataset emr-targeted-scenarios --llm-judge
```

### Tracing（可观测性追踪）

LangSmith Tracing **默认关闭**，通过 `.env` 中的 `LANGSMITH_TRACING` 控制：

```
LANGSMITH_TRACING=true   # 开启：每次 Web UI 生成都会在 LangSmith 中产生 trace
LANGSMITH_TRACING=false  # 关闭：无额外开销，生产环境推荐
```

开启后，LangGraph 会自动为每个节点（init → search_web → generate_emr → validate_emr → next_record）创建 span，在 LangSmith UI 中可查看每次运行的完整调用链、输入输出和耗时。

### LangSmith 评估 vs 内置 6 维校验

| 维度 | 内置 6 维校验 | LangSmith 评估 |
|------|--------------|---------------|
| **执行时机** | 每次生成后实时运行 | 离线批量运行 |
| **执行方式** | LLM 评审（消耗 token） | 确定性规则（零 token） |
| **用途** | 生产质量控制，触发重试修正 | 开发阶段质量回归检测 |
| **可复现性** | LLM 有随机性 | 确定性的，每次结果一致 |

## 依赖

```
fastapi, uvicorn, langgraph, langchain, langchain-openai,
langchain-community, openai, ddgs, duckduckgo-search, openpyxl, pydantic,
langsmith, python-dotenv
```

完整列表见 `requirements.txt`。
