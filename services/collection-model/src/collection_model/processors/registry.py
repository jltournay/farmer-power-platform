"""Processor registry for mapping processor_type to processor classes.

This module provides the ProcessorRegistry class which enables dynamic
processor lookup based on the ingestion.processor_type config value.
"""

from typing import ClassVar

from collection_model.processors.base import ContentProcessor, ProcessorNotFoundError


class ProcessorRegistry:
    """Maps ingestion.processor_type values to processor classes.

    This registry enables the Open/Closed Principle:
    - New processors are added by registering them here
    - Core pipeline code never needs to be modified

    Usage:
        # Registration (in __init__.py)
        ProcessorRegistry.register("json-extraction", JsonExtractionProcessor)

        # Lookup (in worker)
        processor = ProcessorRegistry.get_processor("json-extraction")
        result = await processor.process(job, source_config)
    """

    _processors: ClassVar[dict[str, type[ContentProcessor]]] = {}

    @classmethod
    def register(cls, processor_type: str, processor_class: type[ContentProcessor]) -> None:
        """Register a processor class for a processor_type.

        Args:
            processor_type: The ingestion.processor_type value from source config.
            processor_class: The ContentProcessor subclass to instantiate.
        """
        cls._processors[processor_type] = processor_class

    @classmethod
    def get_processor(cls, processor_type: str) -> ContentProcessor:
        """Get an instantiated processor for the given processor_type.

        Args:
            processor_type: The ingestion.processor_type value from source config.

        Returns:
            Instantiated ContentProcessor.

        Raises:
            ProcessorNotFoundError: If no processor is registered for processor_type.
        """
        if processor_type not in cls._processors:
            raise ProcessorNotFoundError(f"No processor registered for processor_type: {processor_type}")
        return cls._processors[processor_type]()

    @classmethod
    def list_registered(cls) -> list[str]:
        """List all registered processor_type names.

        Returns:
            List of registered processor_type strings.
        """
        return list(cls._processors.keys())

    @classmethod
    def is_registered(cls, processor_type: str) -> bool:
        """Check if a processor_type is registered.

        Args:
            processor_type: The processor_type to check.

        Returns:
            True if registered, False otherwise.
        """
        return processor_type in cls._processors

    @classmethod
    def clear(cls) -> None:
        """Clear all registered processors (for testing)."""
        cls._processors.clear()
