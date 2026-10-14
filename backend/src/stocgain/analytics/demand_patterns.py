"""Descriptive demand patterns on uncensored observations (docs/05 §3.9)."""

import numpy as np
from numpy.typing import NDArray


def classify(adi: float | None, cv_squared: float) -> str:
    """Classify dimensionless ADI and squared nonzero-demand CV, §3.9."""
    if adi is None:
        return "no_demand"
    if adi <= 1.32:
        return "smooth" if cv_squared < 0.49 else "erratic"
    return "intermittent" if cv_squared < 0.49 else "lumpy"


def pattern_statistics(
    units: NDArray[np.float64], clean: NDArray[np.bool_]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return per-position ADI (NaN for none) and sample CV², docs/05 §3.9."""
    positive = clean & (units > 0)
    count = positive.sum(axis=1)
    total = np.where(positive, units, 0).sum(axis=1)
    mean = np.divide(total, count, out=np.zeros_like(total), where=count > 0)
    squares = np.where(positive, (units - mean[:, None]) ** 2, 0).sum(axis=1)
    variance = np.divide(
        squares, count - 1, out=np.zeros_like(squares), where=count > 1
    )
    cv2 = np.divide(variance, mean**2, out=np.zeros_like(mean), where=mean > 0)
    adi = np.divide(
        clean.sum(axis=1), count, out=np.full_like(mean, np.nan), where=count > 0
    )
    return adi, cv2
