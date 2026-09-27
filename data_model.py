"""Provider-neutral schema used by every ingestion source and the scoring engine."""

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


@dataclass
class MetricRecord:
    metric_name: str
    asset: str
    category: str
    value: float | str | None
    previous_value: float | str | None = None
    forecast: float | str | None = None
    unit: str = ""
    date: str | None = None
    source: str = ""
    frequency: str = ""
    raw_score: float | None = None
    weight: float | None = None
    contribution: float | None = None
    confidence: float = 1.0
    notes: str = ""
    metric_id: str = ""
    group: str = ""
    polarity: int = 0
    scale: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DataProvider:
    """Interface for ingestion providers. Implement fetch_records() for new sources."""

    def fetch_records(self) -> list[MetricRecord]:
        raise NotImplementedError


def records_to_frame(records: list[MetricRecord]):
    import pandas as pd
    return pd.DataFrame([record.to_dict() for record in records])
