"""Seed isolation is the base of reproducible synthetic generation."""

import pytest

from stocgain.generator.rng import STREAMS, stream

pytestmark = pytest.mark.unit


def test_stream_reproducible_and_component_isolated() -> None:
    assert len(STREAMS) == len(set(STREAMS.values()))
    assert (
        stream(42, "demand").integers(0, 2**31, size=100).tolist()
        == stream(42, "demand").integers(0, 2**31, size=100).tolist()
    )
    assert (
        stream(42, "demand").integers(0, 2**31, size=100).tolist()
        != stream(42, "adjustments").integers(0, 2**31, size=100).tolist()
    )
    assert (
        stream(42, "demand").integers(0, 2**31, size=100).tolist()
        != stream(43, "demand").integers(0, 2**31, size=100).tolist()
    )
