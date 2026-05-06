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
├── main.py              FastAPI 入口 + SSE 流式接口
├── config.py            LLM 配置模型
├── state.py             LangGraph 状态定义
├── graph.py             状态图构建（节点 + 条件边）
├── nodes.py             节点实现（init/search/generate/validate/next）
├── tools.py             Web 搜索工具（ddgs, 偏重中文医疗网站，失败自动降级）
├── emr_schema.py        病历 Pydantic 数据模型 + 科室池
├── excel_writer.py      Excel 导出（格式化, 警告高亮）
├── prompts/
│   ├── emr_system.txt   病历生成提示词
│   └── validate_system.txt  校验提示词（6维度）
├── static/
│   └── index.html       前端单页（SSE 实时进度）
└── requirements.txt     依赖清单
```

## 电子病历字段

每份生成的病历包含：就诊时间、科室、患者姓名（脱敏）、性别、年龄、主诉、现病史、既往史、体格检查、辅助检查、诊断、治疗意见、医师签名。

科室从 18 个科室池中完全随机抽取：内科、呼吸内科、消化内科、心血管内科、神经内科、内分泌科、肾内科、外科、骨科、泌尿外科、神经外科、妇产科、儿科、眼科、耳鼻喉科、皮肤科、急诊科、全科。

## 依赖

```
fastapi, uvicorn, langgraph, langchain, langchain-openai,
langchain-community, openai, ddgs, duckduckgo-search, openpyxl, pydantic
```

完整列表见 `requirements.txt`。
