"""Seeded random utilities for deterministic data generation.

This module provides random number generation utilities that can be seeded
for deterministic, reproducible output.

Story 0.8.4: Profile-Based Data Generation
AC #3: Deterministic generation with --seed flag
"""

from __future__ import annotations

import random
from typing import Any, TypeVar

T = TypeVar("T")


class SeededRandom:
    """Seeded random number generator for deterministic data generation.

    Wraps Python's random module to provide seeded, reproducible random
    number generation across the entire data generation pipeline.

    Example:
        rng = SeededRandom(seed=12345)

        # These will always produce the same results with the same seed
        farmer_name = rng.choice(["John", "Grace", "Daniel"])
        quality_score = rng.uniform(70.0, 95.0)
        batch_size = rng.randint(20, 60)
    """

    def __init__(self, seed: int | None = None) -> None:
        """Initialize with optional seed.

        Args:
            seed: Random seed for reproducibility. None uses random seed.
        """
        self._seed = seed
        self._rng = random.Random(seed)

    @property
    def seed(self) -> int | None:
        """Get the seed value used."""
        return self._seed

    def reseed(self, seed: int | None = None) -> None:
        """Reseed the random generator.

        Args:
            seed: New seed value. None uses random seed.
        """
        self._seed = seed
        self._rng = random.Random(seed)

    def random(self) -> float:
        """Return random float in [0.0, 1.0)."""
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        """Return random integer N such that a <= N <= b."""
        return self._rng.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """Return random float N such that a <= N <= b."""
        return self._rng.uniform(a, b)

    def choice(self, seq: list[T]) -> T:
        """Return random element from non-empty sequence."""
        return self._rng.choice(seq)

    def choices(self, population: list[T], weights: list[int | float] | None = None, k: int = 1) -> list[T]:
        """Return k sized list of elements chosen with replacement."""
        return self._rng.choices(population, weights=weights, k=k)

    def sample(self, population: list[T], k: int) -> list[T]:
        """Return k unique elements from population (no replacement)."""
        return self._rng.sample(population, k)

    def shuffle(self, x: list[Any]) -> None:
        """Shuffle list x in place."""
        self._rng.shuffle(x)

    def gauss(self, mu: float, sigma: float) -> float:
        """Return Gaussian distribution with mean mu and std deviation sigma."""
        return self._rng.gauss(mu, sigma)


# Global seeded random instance
_global_rng: SeededRandom | None = None


def get_seeded_random() -> SeededRandom:
    """Get the global seeded random instance.

    Returns:
        Global SeededRandom instance.
    """
    global _global_rng
    if _global_rng is None:
        _global_rng = SeededRandom()
    return _global_rng


def set_global_seed(seed: int | None) -> None:
    """Set the global random seed for deterministic generation.

    This affects all random operations using get_seeded_random() or
    the module-level random functions.

    Args:
        seed: Random seed. None uses random seed.
    """
    global _global_rng
    _global_rng = SeededRandom(seed)

    # Also seed the standard random module for compatibility
    random.seed(seed)


def get_global_seed() -> int | None:
    """Get the current global seed.

    Returns:
        The seed value or None if not set.
    """
    global _global_rng
    if _global_rng is None:
        return None
    return _global_rng.seed


# Module-level convenience functions using global seeded random
def seeded_randint(a: int, b: int) -> int:
    """Return random integer N such that a <= N <= b using seeded random."""
    return get_seeded_random().randint(a, b)


def seeded_uniform(a: float, b: float) -> float:
    """Return random float N such that a <= N <= b using seeded random."""
    return get_seeded_random().uniform(a, b)


def seeded_choice(seq: list[T]) -> T:  # noqa: UP047
    """Return random element from non-empty sequence using seeded random."""
    return get_seeded_random().choice(seq)


def seeded_choices(  # noqa: UP047
    population: list[T], weights: list[int | float] | None = None, k: int = 1
) -> list[T]:
    """Return k sized list of elements chosen with replacement using seeded random."""
    return get_seeded_random().choices(population, weights=weights, k=k)


def seeded_sample(population: list[T], k: int) -> list[T]:  # noqa: UP047
    """Return k unique elements from population using seeded random."""
    return get_seeded_random().sample(population, k)
