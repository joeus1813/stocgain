"""Shared strict response models and documented numeric units (docs/08 §1)."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

Count = Annotated[int, Field(json_schema_extra={"x-unit": "count"})]
Units = Annotated[
    float,
    Field(json_schema_extra={"x-unit": "units"}),
    PlainSerializer(lambda v: round(v, 2)),
]
USD = Annotated[
    float,
    Field(json_schema_extra={"x-unit": "usd"}),
    PlainSerializer(lambda v: round(v, 2)),
]
Ratio = Annotated[
    float,
    Field(json_schema_extra={"x-unit": "ratio"}),
    PlainSerializer(lambda v: round(v, 4)),
]
Days = Annotated[
    float,
    Field(json_schema_extra={"x-unit": "days"}),
    PlainSerializer(lambda v: round(v, 1)),
]
Rate = Annotated[
    float,
    Field(json_schema_extra={"x-unit": "units_per_day"}),
    PlainSerializer(lambda v: round(v, 2)),
]


class StrictModel(BaseModel):
    """Reject accidental response fields and nonfinite computation results."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


LeadDays = Annotated[
    float,
    Field(json_schema_extra={"x-unit": "days"}),
    PlainSerializer(lambda v: round(v, 2)),
]
