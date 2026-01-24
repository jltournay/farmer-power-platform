"""Cost event factory for generating valid UnifiedCostEvent instances.

Story 0.8.6: Cost Event Demo Data Generator
AC #1: CostEventFactory generates valid UnifiedCostEvent instances
AC #2: Cost events are JSON-serializable
AC #7: Metadata is realistic per cost type
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

# Set up paths at module load time
_project_root = Path(__file__).parent.parent.parent.parent
_paths_to_add = [
    _project_root / "libs" / "fp-common",
    _project_root / "scripts" / "demo",
    _project_root / "services" / "platform-cost" / "src",
]
for _p in _paths_to_add:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from platform_cost.domain.cost_event import UnifiedCostEvent  # noqa: E402

from .base import BaseModelFactory  # noqa: E402
from .random_utils import seeded_choice, seeded_choices, seeded_randint, seeded_uniform  # noqa: E402

# Valid cost_type -> unit mappings
COST_TYPE_UNIT_MAP: dict[str, str] = {
    "llm": "tokens",
    "document": "pages",
    "embedding": "queries",
    "sms": "messages",
}

# Realistic pricing ranges per cost type (min_usd, max_usd)
COST_AMOUNT_RANGES: dict[str, tuple[float, float]] = {
    "llm": (0.001, 0.05),
    "document": (0.01, 0.10),
    "embedding": (0.0001, 0.001),
    "sms": (0.01, 0.05),
}

# Quantity ranges per cost type
COST_QUANTITY_RANGES: dict[str, tuple[int, int]] = {
    "llm": (100, 5000),
    "document": (1, 10),
    "embedding": (1, 50),
    "sms": (1, 5),
}

# Source services per cost type
SOURCE_SERVICES: dict[str, str] = {
    "llm": "ai-model",
    "document": "collection-model",
    "embedding": "knowledge-model",
    "sms": "notification-model",
}

# LLM models to rotate through
LLM_MODELS: list[str] = [
    "anthropic/claude-3-haiku",
    "anthropic/claude-3.5-sonnet",
    "google/gemini-2.0-flash-lite",
]

# Agent types for LLM events
AGENT_TYPES: list[str] = [
    "extractor",
    "explorer",
    "generator",
    "conversational",
    "tiered_vision",
]

# Knowledge domains for embedding events
KNOWLEDGE_DOMAINS: list[str] = [
    "tea-quality",
    "weather-impact",
    "disease-detection",
    "farming-best-practices",
]

# SMS message types
SMS_MESSAGE_TYPES: list[str] = [
    "quality_feedback",
    "weekly_action_plan",
    "welcome",
    "alert",
]

# Default cost type distribution weights
DEFAULT_DISTRIBUTION: dict[str, int] = {
    "llm": 60,
    "document": 20,
    "embedding": 10,
    "sms": 10,
}


class CostEventFactory(BaseModelFactory[UnifiedCostEvent]):
    """Factory for generating valid UnifiedCostEvent instances.

    Generates cost events with realistic pricing, metadata, and
    time distribution for demo data generation.

    No FK Dependencies (Level 0 in seed order).
    """

    __model__ = UnifiedCostEvent
    _entity_type: ClassVar[str] = "cost_events"
    _id_counter: ClassVar[int] = 0
    _id_prefix: ClassVar[str] = "COST-"

    @classmethod
    def id(cls) -> str:
        """Generate unique event ID."""
        return str(uuid.uuid4())

    @classmethod
    def cost_type(cls) -> str:
        """Generate cost type (defaults to random weighted selection)."""
        types = list(DEFAULT_DISTRIBUTION.keys())
        weights = list(DEFAULT_DISTRIBUTION.values())
        return seeded_choices(types, weights=weights, k=1)[0]

    @classmethod
    def _get_cost_type_for_build(cls, **kwargs) -> str:
        """Get cost_type from kwargs or generate one."""
        return kwargs.get("cost_type", cls.cost_type())

    @classmethod
    def amount_usd(cls) -> Decimal:
        """Generate realistic cost amount for the default cost type (llm)."""
        return Decimal(str(round(seeded_uniform(0.001, 0.05), 6)))

    @classmethod
    def quantity(cls) -> int:
        """Generate quantity for the default cost type."""
        return seeded_randint(100, 5000)

    @classmethod
    def unit(cls) -> str:
        """Generate unit (defaults to tokens for llm)."""
        return "tokens"

    @classmethod
    def timestamp(cls) -> datetime:
        """Generate a timestamp within last 30 days."""
        days_ago = seeded_randint(0, 30)
        hours = seeded_randint(0, 23)
        minutes = seeded_randint(0, 59)
        return datetime.now(UTC) - timedelta(days=days_ago, hours=hours, minutes=minutes)

    @classmethod
    def source_service(cls) -> str:
        """Generate source service."""
        return "ai-model"

    @classmethod
    def success(cls) -> bool:
        """Generate success flag (95% success rate)."""
        return seeded_uniform(0, 1) < 0.95

    @classmethod
    def metadata(cls) -> dict:
        """Generate metadata for LLM type (default)."""
        tokens_in = seeded_randint(100, 3000)
        tokens_out = seeded_randint(50, 2000)
        return {
            "model": seeded_choice(LLM_MODELS),
            "agent_type": seeded_choice(AGENT_TYPES),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    @classmethod
    def factory_id(cls) -> str | None:
        """Generate optional factory_id (30% have one)."""
        if seeded_uniform(0, 1) < 0.3:
            try:
                return cls.get_random_fk("factories")
            except ValueError:
                return None
        return None

    @classmethod
    def request_id(cls) -> str:
        """Generate unique request ID."""
        return str(uuid.uuid4())

    @classmethod
    def agent_type(cls) -> str | None:
        """Will be set based on cost_type in build()."""
        return None

    @classmethod
    def model(cls) -> str | None:
        """Will be set based on cost_type in build()."""
        return None

    @classmethod
    def knowledge_domain(cls) -> str | None:
        """Will be set based on cost_type in build()."""
        return None

    @classmethod
    def build(cls, **kwargs) -> UnifiedCostEvent:
        """Build a single CostEvent with consistent fields.

        Overrides the base build() to ensure cost_type/unit/metadata/
        amount/quantity are all consistent with each other.

        Args:
            **kwargs: Field overrides.

        Returns:
            Valid UnifiedCostEvent instance.
        """
        # Determine cost_type first (everything else depends on it)
        ct = kwargs.pop("cost_type", None)
        if ct is None:
            ct = cls.cost_type()

        # Derive unit from cost_type
        unit = COST_TYPE_UNIT_MAP[ct]

        # Derive amount from cost_type ranges
        amt_range = COST_AMOUNT_RANGES[ct]
        amount = Decimal(str(round(seeded_uniform(amt_range[0], amt_range[1]), 6)))

        # Derive quantity from cost_type ranges
        qty_range = COST_QUANTITY_RANGES[ct]
        qty = seeded_randint(qty_range[0], qty_range[1])

        # Derive source_service from cost_type
        source = SOURCE_SERVICES[ct]

        # Generate metadata per cost_type
        meta = cls._generate_metadata(ct)

        # Extract indexed fields from metadata
        agent_type_val = meta.get("agent_type") if ct == "llm" else None
        model_val = meta.get("model") if ct in ("llm", "embedding") else None
        knowledge_domain_val = meta.get("knowledge_domain") if ct == "embedding" else None

        # Build with consistent fields (kwargs override generated values)
        fields = {
            "id": str(uuid.uuid4()),
            "cost_type": ct,
            "amount_usd": amount,
            "quantity": qty,
            "unit": unit,
            "timestamp": cls.timestamp(),
            "source_service": source,
            "success": cls.success(),
            "metadata": meta,
            "factory_id": cls.factory_id(),
            "request_id": str(uuid.uuid4()),
            "agent_type": agent_type_val,
            "model": model_val,
            "knowledge_domain": knowledge_domain_val,
        }

        # Apply overrides
        fields.update(kwargs)

        return UnifiedCostEvent(**fields)

    @classmethod
    def _generate_metadata(cls, cost_type: str) -> dict:
        """Generate realistic metadata based on cost type.

        Args:
            cost_type: One of "llm", "document", "embedding", "sms".

        Returns:
            Metadata dict appropriate for the cost type.
        """
        if cost_type == "llm":
            tokens_in = seeded_randint(100, 3000)
            tokens_out = seeded_randint(50, 2000)
            return {
                "model": seeded_choice(LLM_MODELS),
                "agent_type": seeded_choice(AGENT_TYPES),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            }
        elif cost_type == "document":
            return {
                "model_id": "prebuilt-document",
                "page_count": seeded_randint(1, 10),
            }
        elif cost_type == "embedding":
            return {
                "model": "text-embedding-3-small",
                "knowledge_domain": seeded_choice(KNOWLEDGE_DOMAINS),
                "texts_count": seeded_randint(1, 50),
            }
        elif cost_type == "sms":
            return {
                "message_type": seeded_choice(SMS_MESSAGE_TYPES),
                "recipient_count": seeded_randint(1, 5),
            }
        return {}

    @classmethod
    def build_batch_for_period(
        cls,
        days_span: int = 30,
        daily_events: int | tuple[int, int] = 10,
        distribution: dict[str, int] | None = None,
        source_services: list[str] | None = None,
    ) -> list[UnifiedCostEvent]:
        """Generate cost events distributed across a time period.

        Args:
            days_span: Number of days to spread events across.
            daily_events: Fixed count or (min, max) range per day.
            distribution: Cost type weights (defaults to DEFAULT_DISTRIBUTION).
            source_services: Override source services list.

        Returns:
            List of UnifiedCostEvent instances spread across the period.
        """
        dist = distribution or DEFAULT_DISTRIBUTION
        events: list[UnifiedCostEvent] = []

        for day_offset in range(days_span):
            # Determine event count for this day
            if isinstance(daily_events, tuple):
                day_count = seeded_randint(daily_events[0], daily_events[1])
            else:
                day_count = daily_events

            for _ in range(day_count):
                # Select cost_type based on distribution weights
                types = list(dist.keys())
                weights = list(dist.values())
                ct = seeded_choices(types, weights=weights, k=1)[0]

                # Generate timestamp within this day
                base_time = datetime.now(UTC) - timedelta(days=days_span - day_offset)
                hours = seeded_randint(6, 22)  # Business hours
                minutes = seeded_randint(0, 59)
                seconds = seeded_randint(0, 59)
                ts = base_time.replace(hour=hours, minute=minutes, second=seconds, microsecond=0)

                # Build with optional source_service override
                kwargs: dict = {"cost_type": ct, "timestamp": ts}
                if source_services:
                    kwargs["source_service"] = seeded_choice(source_services)

                event = cls.build(**kwargs)
                events.append(event)

        return events
