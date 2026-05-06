"""FastAPI 入口 —— SSE 流式生成 + 静态文件 + Excel 下载。"""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import LLMConfig
from graph import build_graph
from excel_writer import write_emr_excel
from emr_schema import DEPARTMENT_POOL

app = FastAPI(title="门诊电子病历生成智能体")

_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

_output_dir = Path(__file__).parent / "output"
_output_dir.mkdir(parents=True, exist_ok=True)

_excel_store: dict[str, str] = {}


@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = _static_dir / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return HTMLResponse("<h1>index.html not found</h1>", status_code=404)


@app.post("/api/generate")
async def generate_emr(request: Request):
    """SSE 流式接口 —— 运行 LangGraph，实时推送进度，完成后写 Excel。"""
    data = await request.json()
    num_records = data.get("num_records", 1)
    enable_search = data.get("enable_search", False)
    model_config = data.get("model_config", {})

    if not model_config.get("api_key") or not model_config.get("base_url"):
        return StreamingResponse(
            _single_error("请先配置 LLM API 参数（Base URL + API Key）"),
            media_type="text/event-stream",
        )

    async def event_stream():
        from config import LangSmithSettings

        ls_settings = LangSmithSettings()
        trace_ctx = None
        if ls_settings.enabled and ls_settings.api_key:
            from langsmith import trace
            trace_ctx = trace(
                name="emr-generation-request",
                project_name=ls_settings.project,
                tags=[f"records:{num_records}", f"search:{enable_search}"],
                metadata={
                    "model": model_config.get("model", "unknown"),
                    "num_records": num_records,
                },
            )
            trace_ctx.__enter__()

        graph = build_graph()
        initial_state = {
            "num_records": num_records,
            "enable_search": enable_search,
            "model_config": model_config,
            "department_pool": list(DEPARTMENT_POOL),
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

        prev_log_len = 0
        final_state = None

        try:
            async for chunk in graph.astream(initial_state, stream_mode="values"):
                final_state = chunk
                new_logs = chunk.get("status_log", [])
                # 推送新增的日志条目
                for log in new_logs[prev_log_len:]:
                    yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
                prev_log_len = len(new_logs)

            # 图执行完毕，写 Excel
            if final_state:
                records = final_state.get("emr_records", [])
                warnings = final_state.get("warnings", [])
                if records:
                    excel_path = write_emr_excel(records, warnings, str(_output_dir))
                    task_id = uuid.uuid4().hex[:8]
                    _excel_store[task_id] = excel_path
                    yield f"data: {json.dumps({'type': 'done', 'task_id': task_id, 'total': len(records), 'warnings': len(warnings)}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': '未生成任何病历'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            if trace_ctx is not None:
                trace_ctx.__exit__(None, None, None)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _single_error(message: str):
    """生成单条错误 SSE。"""
    yield f"data: {json.dumps({'type': 'error', 'message': message}, ensure_ascii=False)}\n\n"


@app.get("/api/download/{task_id}")
async def download_excel(task_id: str):
    """下载生成的 Excel 文件。"""
    filepath = _excel_store.get(task_id)
    if not filepath or not Path(filepath).exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期，请重新生成")
    filename = Path(filepath).name
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )


@app.get("/api/config/defaults")
async def get_default_config():
    return LLMConfig().model_dump()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
