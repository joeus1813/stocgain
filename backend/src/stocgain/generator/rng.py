"""Independent seeded NumPy streams for deterministic synthetic data (docs/06 §4)."""

import numpy as np

STREAMS = {
    "catalog": 1,
    "suppliers": 2,
    "lanes": 3,
    "promotions": 4,
    "demand": 5,
    "fulfillment": 6,
    "adjustments": 7,
    "policy": 8,
    "events": 9,
}


def stream(seed: int, name: str) -> np.random.Generator:
    """Return a reproducible independent stream for one generator component."""
    return np.random.default_rng(np.random.SeedSequence([seed, STREAMS[name]]))
