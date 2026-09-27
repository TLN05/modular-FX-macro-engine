"""Manual data-entry provider. It is the only ingestion source used in version 1."""

from __future__ import annotations

import pandas as pd

from config import metric_catalog
from data_model import DataProvider, MetricRecord


class ManualInputProvider(DataProvider):
    """Collects UI-edited rows and emits the canonical MetricRecord schema."""

    def __init__(self, rows: list[dict] | pd.DataFrame):
        self.rows = pd.DataFrame(rows)

    @staticmethod
    def blank_frame(asset: str) -> pd.DataFrame:
        catalog = metric_catalog(asset)
        frame = pd.DataFrame(catalog)
        frame["asset"] = asset
        for field, default in {
            "value": None, "previous_value": None, "forecast": None, "date": None,
            "source": "", "frequency": "", "confidence": 0.7, "notes": "",
        }.items():
            frame[field] = default
        return frame

    def fetch_records(self) -> list[MetricRecord]:
        out = []
        for row in self.rows.to_dict("records"):
            val = row.get("value")
            if pd.isna(val) or val == "":
                val = None
            else:
                try:
                    val = float(val)
                except (TypeError, ValueError):
                    val = str(val)
            def optional_number(key):
                x = row.get(key)
                if pd.isna(x) or x == "":
                    return None
                try:
                    return float(x)
                except (TypeError, ValueError):
                    return str(x)
            d = row.get("date")
            if pd.isna(d) or d == "":
                d = None
            elif hasattr(d, "strftime"):
                d = d.strftime("%Y-%m-%d")
            confidence = row.get("confidence", 0.7)
            if pd.isna(confidence):
                confidence = 0.7
            out.append(MetricRecord(
                metric_name=row["metric_name"], asset=row["asset"],
                category=row["category"], value=val,
                previous_value=optional_number("previous_value"),
                forecast=optional_number("forecast"), unit=row["unit"], date=d,
                source=str(row.get("source") or ""),
                frequency=str(row.get("frequency") or ""),
                confidence=float(confidence),
                notes=str(row.get("notes") or ""), metric_id=row["metric_id"],
                group=row["group"], polarity=int(row["polarity"]), scale=float(row["scale"]),
            ))
        return out
