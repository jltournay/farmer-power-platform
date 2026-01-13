"""Domain models for the AI Model service.

This module exports all domain models for prompt, agent configuration, and RAG document storage.

Story 0.75.9: Added RagDocument, RagChunk, and related RAG models.
Story 0.75.12: Added Embedding domain models.
Story 0.75.13: Added Vector store domain models.
Story 0.75.13b: Added Vectorization pipeline domain models.
Story 13.7: Removed LlmCostEvent, EmbeddingCostEvent - cost tracking now via DAPR (ADR-016)
"""

from ai_model.domain.agent_config import (
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
from ai_model.domain.embedding import (
    EmbeddingInputType,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingUsage,
)
from ai_model.domain.prompt import (
    Prompt,
    PromptABTest,
    PromptContent,
    PromptMetadata,
    PromptStatus,
)
from ai_model.domain.rag_document import (
    ExtractionMethod,
    FileType,
    KnowledgeDomain,
    RagChunk,
    RagDocument,
    RAGDocumentMetadata,
    RagDocumentStatus,
    SourceFile,
)
from ai_model.domain.vector_store import (
    VECTOR_DIMENSIONS,
    IndexStats,
    NamespaceStats,
    QueryMatch,
    QueryResult,
    UpsertResult,
    VectorMetadata,
    VectorUpsertRequest,
)
from ai_model.domain.vectorization import (
    FailedChunk,
    VectorizationJob,
    VectorizationJobStatus,
    VectorizationProgress,
    VectorizationResult,
)

__all__ = [
    "VECTOR_DIMENSIONS",
    "AgentConfig",
    "AgentConfigBase",
    "AgentConfigMetadata",
    "AgentConfigStatus",
    "AgentType",
    "ConversationalConfig",
    "EmbeddingInputType",
    "EmbeddingRequest",
    "EmbeddingResult",
    "EmbeddingUsage",
    "ErrorHandlingConfig",
    "ExplorerConfig",
    "ExtractionMethod",
    "ExtractorConfig",
    "FailedChunk",
    "FileType",
    "GeneratorConfig",
    "IndexStats",
    "InputConfig",
    "KnowledgeDomain",
    "LLMConfig",
    "MCPSourceConfig",
    "NamespaceStats",
    "OutputConfig",
    "Prompt",
    "PromptABTest",
    "PromptContent",
    "PromptMetadata",
    "PromptStatus",
    "QueryMatch",
    "QueryResult",
    "RAGConfig",
    "RAGDocumentMetadata",
    "RagChunk",
    "RagDocument",
    "RagDocumentStatus",
    "SourceFile",
    "StateConfig",
    "TieredVisionConfig",
    "TieredVisionLLMConfig",
    "TieredVisionRoutingConfig",
    "UpsertResult",
    "VectorMetadata",
    "VectorUpsertRequest",
    "VectorizationJob",
    "VectorizationJobStatus",
    "VectorizationProgress",
    "VectorizationResult",
]
