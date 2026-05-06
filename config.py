"""LLM 配置管理 + LangSmith 设置（从 .env 加载）。"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 从项目根目录加载 .env
load_dotenv(Path(__file__).parent / ".env")

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI 兼容 API 的 Base URL",
    )
    api_key: str = Field(
        default="sk-xxxxxxxxxxxxx",
        description="API Key",
    )
    model: str = Field(
        default="gpt-4o",
        description="模型名称",
    )
    temperature: float = Field(default=0.7, description="生成温度")
    max_tokens: int = Field(default=4096, description="最大输出 tokens")


# 默认配置实例
default_config = LLMConfig()


# ---------------------------------------------------------------------------
# LangSmith 配置（从 .env 加载）
# ---------------------------------------------------------------------------

class LangSmithSettings(BaseModel):
    enabled: bool = Field(
        default_factory=lambda: os.getenv("LANGSMITH_TRACING", "false").lower()
        == "true"
    )
    endpoint: str = Field(
        default_factory=lambda: os.getenv(
            "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
        )
    )
    api_key: str = Field(
        default_factory=lambda: os.getenv("LANGSMITH_API_KEY", "")
    )
    project: str = Field(
        default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "emr-agent")
    )


def _is_langsmith_ready() -> bool:
    """LangSmith tracing 是否可用：已开启 且 已配置 API key。"""
    settings = LangSmithSettings()
    return settings.enabled and bool(settings.api_key)


def _apply_langsmith_env():
    """当 tracing 启用时将 LangSmith 配置注入 os.environ。

    LangGraph / LangChain 在导入时会自动检测这些环境变量，
    因此必须在 graph 构建之前调用。
    """
    settings = LangSmithSettings()
    if _is_langsmith_ready():
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_ENDPOINT"] = settings.endpoint
        os.environ["LANGSMITH_API_KEY"] = settings.api_key
        os.environ["LANGSMITH_PROJECT"] = settings.project


# 在模块加载时注入（其他模块 import config 之后即生效）
_apply_langsmith_env()
