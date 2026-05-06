"""LLM 配置管理。运行时可被前端参数覆盖。"""

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
