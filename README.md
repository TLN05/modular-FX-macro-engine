# FX Fundamental Strength & Macro Bias Engine

Manual-input-first Streamlit application for transparent, rules-based macro scoring. It produces fundamental bias and evidence summaries; it does not provide trading signals.

## Run

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Provider architecture

`data_model.py` defines the provider-neutral `MetricRecord` schema and `DataProvider` interface. `providers/manual.py` implements the initial manual-entry source. The normalization and scoring modules depend only on standardized records, so another provider can replace manual ingestion without modifying those calculation layers or the dashboard.

## Project layout

- `app.py`: Streamlit application shell and tab composition
- `config.py`: assets, category weights, and standardized metric catalog
- `data_model.py`: canonical metric schema and provider interface
- `providers/manual.py`: manual input adapter
- `scoring_engine.py`: hierarchical aggregation, confidence, and relative matrix
- `utils/normalization.py`: explicit metric normalization and freshness rules
- `utils/validation.py`: value and date validation
- `components/`: dashboard, manual editor, detail view, and matrix UI

Blank values remain unavailable. The app uses session state; download entered records to retain a copy outside the current browser session.
