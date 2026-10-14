"""Window demand and distribution primitives, docs/05 §5.2–5.3."""

import math
from collections.abc import Sequence
from typing import Any

import numpy as np
from scipy import special, stats  # type: ignore[import-untyped]


def cumulative_forecast(daily: Sequence[float], days: float) -> float:
    """Expected units through fractional days, extending the last week (§3.8)."""
    if days < 0 or not daily:
        raise ValueError("A nonnegative window and nonempty forecast are required")
    values = np.asarray(daily, dtype=float)
    whole = math.floor(days)
    extension = float(np.mean(values[-7:]))
    total = float(values[:whole].sum()) + max(0, whole - len(values)) * extension
    next_value = float(values[whole]) if whole < len(values) else extension
    return total + (days - whole) * next_value


def window_demand(
    daily: Sequence[float], days: float, window_std: float, daily_std: float
) -> tuple[float, float]:
    """Return window mean and standard deviation in units; docs/05 §5.2."""
    mean = cumulative_forecast(daily, days)
    if days == 0:
        return 0.0, 0.0
    return mean, math.sqrt(days * daily_std**2 + (mean / days) ** 2 * window_std**2)


def select_family(mean: float, std: float, normal_min_mean: float = 20.0) -> str:
    """Select the specified count/continuous family; docs/05 §5.3."""
    if mean <= 0 or std <= 1e-9:
        return "degenerate"
    if mean >= normal_min_mean:
        return "normal"
    return "negative_binomial" if std**2 > mean else "poisson"


def prob_exceeds(
    mean: float, std: float, supply: int, normal_min_mean: float = 20.0
) -> float:
    """Probability demand exceeds integer available supply, docs/05 §5.3."""
    family = select_family(mean, std, normal_min_mean)
    if family == "degenerate":
        return float(max(0.0, mean) > supply)
    if family == "normal":
        return float(special.ndtr((mean - supply) / std))
    tail = _count_tail(mean, std, supply)
    # For integer S, S > ppf(q) iff CDF(S - 1) >= q. Keep the
    # canonical 1e-9 tail cutoff without a repeated inverse-CDF search.
    return 0.0 if _count_tail(mean, std, supply - 1) <= 1e-9 else tail


def _count_tail(mean: float, std: float, supply: int, shifted: bool = False) -> float:
    """P[X > supply] via public SciPy special functions for count families."""
    if supply < 0:
        return 1.0
    if std**2 <= mean:
        return float(special.gammainc(supply + 1, mean))
    n, p = mean**2 / (std**2 - mean), mean / std**2
    return float(special.betainc(supply + 1, n + int(shifted), 1 - p))


def quantile(
    mean: float, std: float, alpha: float, normal_min_mean: float = 20.0
) -> float:
    """Demand quantile in units, docs/05 §5.3."""
    family = select_family(mean, std, normal_min_mean)
    if family == "degenerate":
        return max(0.0, mean)
    if family == "normal":
        return float(mean + special.ndtri(alpha) * std)
    if family == "poisson":
        return float(stats.poisson.ppf(alpha, mean))
    return float(stats.nbinom.ppf(alpha, mean**2 / (std**2 - mean), mean / std**2))


def expected_shortage(
    mean: float, std: float, supply: int, normal_min_mean: float = 20.0
) -> float:
    """Expected unserved units without multiplying by probability; docs/05 §5.3."""
    family = select_family(mean, std, normal_min_mean)
    if family == "degenerate":
        return max(0.0, mean - supply)
    if family == "normal":
        z = (supply - mean) / std
        density = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
        return max(0.0, float(std * (density - z * special.ndtr(-z))))
    if 0 < std**2 - mean < 1e-10 * mean:
        # Preserve the reference finite-sum behavior at the numerically singular
        # NB/Poisson boundary (huge NB shape). Do not change the family rule.
        n, p = mean**2 / (std**2 - mean), mean / std**2
        if supply > stats.nbinom.ppf(1 - 1e-9, n, p):
            return 0.0
        values = np.arange(supply, dtype=float)
        return max(
            0.0,
            float(
                mean
                - supply
                + np.sum((supply - values) * stats.nbinom.pmf(values, n, p))
            ),
        )
    if _count_tail(mean, std, supply - 1) <= 1e-9:
        return 0.0
    # Exact truncated first-moment identity for the specified finite sum:
    # E[(X-S)+] = mu * P[X' > S-1] - S * P[X > S]. For NB,
    # X' has shape n+1 and the same p; Poisson keeps the same mean.
    return max(
        0.0,
        mean * _count_tail(mean, std, supply - 1, shifted=True)
        - supply * _count_tail(mean, std, supply),
    )


def evaluate_batch(
    means: Sequence[float],
    stds: Sequence[float],
    supplies: Sequence[int],
    normal_min_mean: float = 20.0,
) -> tuple[
    np.ndarray[Any, np.dtype[np.float64]], np.ndarray[Any, np.dtype[np.float64]]
]:
    """Vectorize probabilities and expected shortage across positions (§5.3).

    Count shortage uses the algebraically equivalent truncated first moment,
    avoiding a potentially large position-by-count probability matrix.
    """
    mean = np.asarray(means, dtype=np.float64)
    std = np.asarray(stds, dtype=np.float64)
    supply = np.asarray(supplies, dtype=np.float64)
    if mean.shape != std.shape or mean.shape != supply.shape:
        raise ValueError("Mean, standard deviation and supply shapes must agree")
    degenerate = (mean <= 0) | (std <= 1e-9)
    normal = ~degenerate & (mean >= normal_min_mean)
    count = ~degenerate & ~normal
    poisson = count & (std**2 <= mean)
    negative_binomial = count & ~poisson
    probabilities = np.zeros_like(mean)
    shortages = np.zeros_like(mean)
    probabilities[degenerate] = np.maximum(0, mean[degenerate]) > supply[degenerate]
    shortages[degenerate] = np.maximum(0, mean[degenerate] - supply[degenerate])
    z = (supply[normal] - mean[normal]) / std[normal]
    probabilities[normal] = stats.norm.sf(z)
    shortages[normal] = std[normal] * (stats.norm.pdf(z) - z * stats.norm.sf(z))
    mu = mean[poisson]
    stock = supply[poisson]
    tail = stats.poisson.sf(stock, mu)
    cap = stock > stats.poisson.ppf(1 - 1e-9, mu)
    probabilities[poisson] = np.where(cap, 0, tail)
    shortages[poisson] = np.where(
        cap, 0, mu * stats.poisson.sf(stock - 1, mu) - stock * tail
    )
    mu = mean[negative_binomial]
    variance = std[negative_binomial] ** 2
    stock = supply[negative_binomial]
    n = mu**2 / (variance - mu)
    p = mu / variance
    tail = stats.nbinom.sf(stock, n, p)
    cap = stock > stats.nbinom.ppf(1 - 1e-9, n, p)
    probabilities[negative_binomial] = np.where(cap, 0, tail)
    shortages[negative_binomial] = np.where(
        cap, 0, mu * stats.nbinom.sf(stock - 1, n + 1, p) - stock * tail
    )
    return np.clip(probabilities, 0, 1), np.maximum(shortages, 0)
