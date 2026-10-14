"""Independent finite-sum oracle for optimized scalar count distributions."""

import math

import numpy as np
import pytest
from scipy import stats

from stocgain.analytics.distributions import expected_shortage, prob_exceeds


@pytest.mark.parametrize(
    "mean,std",
    [
        (0.01, 0.1),
        (0.5, 2),
        (3, math.sqrt(3)),
        (3, 5),
        (19.99, 20),
        (19.99, math.sqrt(19.99)),
    ],
)
def test_count_primitives_match_scipy_finite_sum(mean, std):
    distribution = (
        stats.nbinom(mean**2 / (std**2 - mean), mean / std**2)
        if std**2 > mean
        else stats.poisson(mean)
    )
    cap = int(distribution.ppf(1 - 1e-9))
    for supply in sorted({0, 1, 2, 5, 20, cap - 1, cap, cap + 1, cap + 2}):
        values = np.arange(supply)
        shortage = max(
            0.0,
            float(mean - supply + np.sum((supply - values) * distribution.pmf(values))),
        )
        expected_p = float(distribution.sf(supply))
        if supply > cap:
            shortage = expected_p = 0.0
        assert prob_exceeds(mean, std, supply) == pytest.approx(expected_p, abs=1e-13)
        assert expected_shortage(mean, std, supply) == pytest.approx(
            shortage, abs=1e-10
        )
