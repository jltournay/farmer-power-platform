"""AI Model service layer.

Story 0.75.4: Cache services for agent configs and prompts (ADR-013).
Story 0.75.10b: Document extraction service and workflow.
Story 0.75.10d: Semantic chunking service and workflow.
Story 0.75.12: Embedding service using Pinecone Inference API.
"""

from ai_model.services.agent_config_cache import AgentConfigCache
from ai_model.services.chunking_workflow import (
    ChunkingError,
    ChunkingWorkflow,
    TooManyChunksError,
)
from ai_model.services.document_extractor import (
    CorruptedFileError,
    DocumentExtractor,
    ExtractionError,
    ExtractionResult,
    PasswordProtectedError,
)
from ai_model.services.embedding_service import (
    EmbeddingBatchError,
    EmbeddingService,
    EmbeddingServiceError,
    PineconeNotConfiguredError,
)
from ai_model.services.extraction_workflow import (
    DocumentNotFoundError,
    ExtractionWorkflow,
    ExtractionWorkflowError,
    NoSourceFileError,
)
from ai_model.services.prompt_cache import PromptCache
from ai_model.services.semantic_chunker import ChunkResult, SemanticChunker

__all__ = [
    "AgentConfigCache",
    "ChunkResult",
    "ChunkingError",
    "ChunkingWorkflow",
    "CorruptedFileError",
    "DocumentExtractor",
    "DocumentNotFoundError",
    "EmbeddingBatchError",
    "EmbeddingService",
    "EmbeddingServiceError",
    "ExtractionError",
    "ExtractionResult",
    "ExtractionWorkflow",
    "ExtractionWorkflowError",
    "NoSourceFileError",
    "PasswordProtectedError",
    "PineconeNotConfiguredError",
    "PromptCache",
    "SemanticChunker",
    "TooManyChunksError",
]
