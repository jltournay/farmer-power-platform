"""BFF transformer layer.

Transformers convert domain models to API schemas per ADR-012.
They handle tier computation, trend mapping, and other presentation logic.
"""

from bff.transformers.farmer_transformer import FarmerTransformer

__all__ = ["FarmerTransformer"]
