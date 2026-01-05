"""Agent configuration models for CLI.

This module re-exports the agent configuration models from the AI Model service.
DO NOT recreate these models - always import from ai_model.domain.agent_config.

For CLI usage, we add a TypeAdapter for deserializing the discriminated union.
"""

import sys
from pathlib import Path

# Add the ai-model service to the path for imports
# This allows the CLI to use the same models as the service
ai_model_path = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / "services"
    / "ai-model"
    / "src"
)
if str(ai_model_path) not in sys.path:
    sys.path.insert(0, str(ai_model_path))

# Re-export all agent config models from ai_model service
from ai_model.domain.agent_config import (  # noqa: E402
    AgentConfig,
    AgentConfigBase,
    AgentConfigMetadata,
    AgentConfigStatus,
    AgentType,
    ConversationalConfig,
    ErrorHandlingConfig,
    ExplorerConfig,
    ExtractorConfig,
    GeneratorConfig,
    InputConfig,
    LLMConfig,
    MCPSourceConfig,
    OutputConfig,
    RAGConfig,
    StateConfig,
    TieredVisionConfig,
    TieredVisionLLMConfig,
    TieredVisionRoutingConfig,
)
from pydantic import TypeAdapter  # noqa: E402

# TypeAdapter for deserializing the discriminated union
agent_config_adapter: TypeAdapter[AgentConfig] = TypeAdapter(AgentConfig)

__all__ = [
    # Enums
    "AgentType",
    "AgentConfigStatus",
    # Base and shared models
    "AgentConfigBase",
    "AgentConfigMetadata",
    "LLMConfig",
    "RAGConfig",
    "InputConfig",
    "OutputConfig",
    "MCPSourceConfig",
    "ErrorHandlingConfig",
    "StateConfig",
    # Tiered-vision specific
    "TieredVisionLLMConfig",
    "TieredVisionRoutingConfig",
    # Agent type configs
    "ExtractorConfig",
    "ExplorerConfig",
    "GeneratorConfig",
    "ConversationalConfig",
    "TieredVisionConfig",
    # Discriminated union
    "AgentConfig",
    # TypeAdapter
    "agent_config_adapter",
]
