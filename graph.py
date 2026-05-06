"""LangGraph 状态图构建 —— 节点 + 条件边编译。"""

from langgraph.graph import StateGraph, END

from state import EMRState
from nodes import (
    init_node,
    search_web_node,
    generate_emr_node,
    validate_emr_node,
    next_record_node,
)


def _after_init(state: EMRState) -> str:
    """init 之后的路线：搜索或直接生成。"""
    if state.get("enable_search", False):
        return "search_web"
    return "generate_emr"


def _after_validate(state: EMRState) -> str:
    """校验之后的路线：通过→下一份，不通过且未超→重试。"""
    if state.get("retry_count", 0) > 0:
        return "generate_emr"
    return "next_record"


def _after_next(state: EMRState) -> str:
    """判断是否还有病历需要生成。"""
    if state["current_index"] < state["num_records"]:
        return "generate_emr"
    return END


def build_graph():
    """构建并编译 LangGraph 状态图。"""
    from config import LangSmithSettings

    workflow = StateGraph(EMRState)

    workflow.add_node("init", init_node)
    workflow.add_node("search_web", search_web_node)
    workflow.add_node("generate_emr", generate_emr_node)
    workflow.add_node("validate_emr", validate_emr_node)
    workflow.add_node("next_record", next_record_node)

    workflow.set_entry_point("init")

    workflow.add_conditional_edges(
        "init", _after_init,
        {"search_web": "search_web", "generate_emr": "generate_emr"},
    )
    workflow.add_edge("search_web", "generate_emr")
    workflow.add_edge("generate_emr", "validate_emr")
    workflow.add_conditional_edges(
        "validate_emr", _after_validate,
        {"generate_emr": "generate_emr", "next_record": "next_record"},
    )
    workflow.add_conditional_edges(
        "next_record", _after_next,
        {"generate_emr": "generate_emr", END: END},
    )

    compiled = workflow.compile()

    langsmith_settings = LangSmithSettings()
    if langsmith_settings.enabled and langsmith_settings.api_key:
        from langsmith import traceable
        compiled = traceable(
            compiled,
            name="EMR-Generation-Agent",
            metadata={"graph_version": "1.0"},
        )

    return compiled
