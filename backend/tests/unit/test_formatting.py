"""Cross-language number presentation fixtures."""

import json
from pathlib import Path

import pytest

from stocgain.analytics.formatting import format_number

CASES = json.loads(
    (Path(__file__).parents[1] / "fixtures/format_cases.json").read_text()
)


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES)
def test_shared_format(case):
    assert format_number(case["kind"], case["value"]) == case["expected"]
