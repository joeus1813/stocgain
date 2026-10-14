"""Bounded run-keyed cache of full-precision model inputs for counterfactuals."""

from collections import OrderedDict
from threading import RLock

from stocgain.analytics.config import AnalyticsConfig
from stocgain.analytics.pipeline import compute, extract_inputs
from stocgain.analytics.types import ModelInputs, ModelOutputs
from stocgain.api.dependencies import Context

_CACHE: OrderedDict[tuple[str, int], tuple[ModelInputs, ModelOutputs]] = OrderedDict()
_LOCK = RLock()


def get_baseline(ctx: Context) -> tuple[ModelInputs, ModelOutputs]:
    """Replay only operational as-of inputs; never calculate from rounded snapshots."""
    key = (str(ctx.connection.engine.url), int(ctx.run["run_id"]))
    with _LOCK:
        if key not in _CACHE:
            config = AnalyticsConfig(**ctx.run["config"])
            inputs = extract_inputs(ctx.connection, ctx.run["as_of_date"], config)
            _CACHE[key] = (inputs, compute(inputs))
            while len(_CACHE) > 2:
                _CACHE.popitem(last=False)
        _CACHE.move_to_end(key)
        return _CACHE[key]
