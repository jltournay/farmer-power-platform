"""LLM Gateway module for AI Model service.

This module provides the unified LLM gateway with:
- OpenRouter integration via LangChain-compatible ChatOpenRouter
- LLMGateway wrapper for retry, fallback, and cost tracking
- Token bucket rate limiting for RPM and TPM
- Cost event tracking and budget monitoring

Story 0.75.5: OpenRouter LLM Gateway with Cost Observability
"""

from ai_model.llm.budget_monitor import BudgetMonitor
from ai_model.llm.chat_openrouter import ChatOpenRouter
from ai_model.llm.exceptions import (
    AllModelsUnavailableError,
    LLMError,
    ModelUnavailableError,
    RateLimitExceededError,
    TransientError,
)
from ai_model.llm.gateway import LLMGateway
from ai_model.llm.rate_limiter import RateLimiter

__all__ = [
    "AllModelsUnavailableError",
    "BudgetMonitor",
    "ChatOpenRouter",
    "LLMError",
    "LLMGateway",
    "ModelUnavailableError",
    "RateLimitExceededError",
    "RateLimiter",
    "TransientError",
]
