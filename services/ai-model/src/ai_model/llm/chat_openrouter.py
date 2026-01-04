"""OpenRouter LLM client compatible with LangChain/LangGraph.

This module provides ChatOpenRouter, a subclass of ChatOpenAI that routes
requests through OpenRouter's OpenAI-compatible API.

Benefits:
- Native LangChain/LangGraph compatibility for agent workflows
- Access to multiple LLM providers (OpenAI, Anthropic, Google, Meta, Mistral)
- Single API key and unified billing

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

import os
from typing import Annotated, Any

from langchain_openai import ChatOpenAI
from pydantic import Field, SecretStr
from pydantic.functional_validators import BeforeValidator

# OpenRouter API configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-3-5-sonnet"
DEFAULT_SITE_URL = "https://farmer-power.com"
DEFAULT_SITE_NAME = "Farmer Power Platform"


def _get_secret_from_env(v: Any) -> SecretStr | None:
    """Get secret from environment variable if not already set."""
    if v is not None:
        if isinstance(v, SecretStr):
            return v
        if isinstance(v, str):
            return SecretStr(v)
    env_value = os.environ.get("OPENROUTER_API_KEY")
    if env_value:
        return SecretStr(env_value)
    return None


class ChatOpenRouter(ChatOpenAI):
    """OpenRouter LLM client compatible with LangChain/LangGraph.

    Subclasses ChatOpenAI since OpenRouter uses OpenAI-compatible API.
    This allows seamless integration with LangChain chains, agents, and
    LangGraph workflows.

    Example:
        ```python
        from ai_model.llm import ChatOpenRouter

        # Simple usage
        llm = ChatOpenRouter(model="anthropic/claude-3-5-sonnet", temperature=0.3)
        response = await llm.ainvoke(messages)

        # With custom settings
        llm = ChatOpenRouter(
            model="openai/gpt-4o",
            openai_api_key="sk-or-...",
            max_tokens=2000,
        )
        ```
    """

    # Override api_key to use OPENROUTER_API_KEY env var
    openai_api_key: Annotated[SecretStr | None, BeforeValidator(_get_secret_from_env)] = Field(
        alias="api_key",
        default=None,
    )

    # Site identification for OpenRouter
    site_url: str = Field(
        default=DEFAULT_SITE_URL,
        description="Site URL for OpenRouter rankings",
    )
    site_name: str = Field(
        default=DEFAULT_SITE_NAME,
        description="Site name for OpenRouter rankings",
    )

    @property
    def lc_secrets(self) -> dict[str, str]:
        """Return the secrets mapping for LangChain serialization."""
        return {"openai_api_key": "OPENROUTER_API_KEY"}

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        openai_api_key: str | SecretStr | None = None,
        site_url: str = DEFAULT_SITE_URL,
        site_name: str = DEFAULT_SITE_NAME,
        **kwargs: Any,
    ) -> None:
        """Initialize the ChatOpenRouter client.

        Args:
            model: The model identifier (e.g., "anthropic/claude-3-5-sonnet").
            openai_api_key: OpenRouter API key. If not provided, uses
                           OPENROUTER_API_KEY environment variable.
            site_url: Site URL for OpenRouter rankings and identification.
            site_name: Site name for OpenRouter rankings.
            **kwargs: Additional arguments passed to ChatOpenAI (temperature,
                      max_tokens, etc.).
        """
        # Resolve API key
        api_key = openai_api_key
        if api_key is None:
            api_key = os.environ.get("OPENROUTER_API_KEY")

        if api_key is None:
            raise ValueError(
                "OpenRouter API key is required. "
                "Set OPENROUTER_API_KEY environment variable or pass openai_api_key parameter."
            )

        # Build default headers for OpenRouter
        default_headers = kwargs.pop("default_headers", {})
        default_headers.update(
            {
                "HTTP-Referer": site_url,
                "X-Title": site_name,
            }
        )

        # Initialize parent with OpenRouter base URL
        super().__init__(
            model=model,
            base_url=OPENROUTER_BASE_URL,
            openai_api_key=api_key,
            default_headers=default_headers,
            **kwargs,
        )

        self.site_url = site_url
        self.site_name = site_name

    @property
    def _llm_type(self) -> str:
        """Return the LLM type identifier."""
        return "openrouter"
