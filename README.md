# Macro–Credit Regimes Dashboard

An end-to-end macroeconomic regime analysis pipeline that:
- retrieves macro and credit data from FRED,
- engineers interpretable macro features,
- classifies macro regimes using transparent rule-based logic,
- visualizes regime dynamics in a professional dashboard,
- and generates a publication-ready PDF report.

This project is designed to prioritize **economic interpretability**, **reproducibility**, and **clear regime narratives**, rather than black-box modeling.

---

## Overview

The pipeline produces a **macro–credit regime framework** grounded in:
- yield curve dynamics,
- interest rate repricing,
- credit spread behavior,
- market volatility,
- and composite stress signals.

The output is a single PDF report containing:
- a multi-panel macro dashboard with regime shading,
- a regime timeline,
- regime distribution statistics,
- key signal summaries by regime,
- and stress-test scorecards across historical episodes.

---

## Project Structure

```text
MACRO-CREDIT-REGIMES/
├── configs/
│   └── report_config.py        # Report metadata, descriptions, stress windows
│
├── data/
│   ├── raw/                    # Raw FRED downloads
│   └── processed/              # Engineered features and regime labels
│
├── reports/
│   ├── figures/                # Generated dashboard images
│   ├── table/                  # CSV tables used in the report
│   └── macro_credit_report.pdf # Final PDF output
│
├── src/macro_credit_regimes/
│   ├── data.py                 # FRED ingestion with retries and persistence
│   ├── features.py             # Lagged, interpretable feature engineering
│   ├── regimes.py              # Rule-based regime classification
│   ├── plots.py                # Dashboard and regime timeline visualization
│   ├── analytics.py            # Regime statistics and stress analysis
│   └── pdf_builder.py          # ReportLab PDF assembly
│
├── run_report.py               # Orchestrates the full pipeline
├── requirements.txt
└── README.md
```

---

## Regime Definitions

The framework classifies each day into one of five macro regimes:

* **Risk-off / crisis**  
  Credit widening, volatility shocks, and multiple aligned stress signals.

* **Policy pivot**  
  Front-end rates falling, elevated uncertainty, shifting policy expectations.

* **Late-cycle**  
  Inverted yield curve with stable credit and subdued volatility.

* **Risk-on / expansion**  
  Rising rates, tightening credit, low volatility.

* **Transition**  
  Mixed or ambiguous macro signals.

Regime assignment is **rule-based and explainable**, with persistence logic to avoid excessive regime churn.

---

## Data Sources

All macro data is sourced from **FRED (Federal Reserve Bank of St. Louis)**:

* U.S. Treasury yields (2Y, 10Y)
* BAA corporate credit spreads
* VIX volatility index

Data retrieval includes retries and partial-failure tolerance to ensure robustness.

---

## How to Run

### 1. Set up environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate the report

```bash
python run_report.py
```

This will:

* download and persist macro data,
* engineer features and regimes,
* generate dashboard figures,
* compute analytical tables,
* and output the final PDF to:

```text
reports/macro_credit_report.pdf
```

---

## Outputs

* **Dashboard figure**  
  Multi-panel macro signals with regime shading and a timeline band.

* **Tables (CSV + PDF)**
  * Regime distribution
  * Key signal medians by regime
  * Feature summary statistics
  * Stress window scorecards

All intermediate artifacts are saved for auditability and reuse.

---

## Design Philosophy

* **Interpretability first**  
  Every feature and threshold has a macroeconomic rationale.

* **No look-ahead bias**  
  All inputs are lagged before regime classification.

* **Separation of concerns**  
  Data, features, regimes, analytics, visualization, and reporting are cleanly modularized.

* **Production-minded**  
  Deterministic outputs, stable formatting, and report-ready visuals.

---

## Possible Extensions

* Probabilistic regime scoring
* Parquet-based storage
* International macro extensions
* Machine-learning regime overlays
* Interactive dashboards (Plotly / web)

---

## License

This project is intended for research, educational, and portfolio use.