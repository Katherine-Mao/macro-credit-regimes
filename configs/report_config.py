# report_config.py

REPORT_META = {
    "output_path": "reports/macro_credit_report.pdf",
    "title": "Macro–Credit Regimes Report",
    "subtitle": (
        "Rule-based macro-credit regime identification using yield-curve dynamics, "
        "corporate credit spreads, and market volatility to characterize shifts in "
        "the economic and risk environment."
    ),
}

FEATURE_SUMMARY_GROUPS = {
    "Feature Summary by Regime": {
        "Rates": ["10Y–2Y Curve", "2Y Yield Δ 1M", "10Y Yield Δ 1M"],
        "Credit": ["BAA–10Y Spread", "Credit Δ 1M"],
        "Volatility": ["VIX", "VIX Δ 1M"],
        "Composite": ["Risk-off Score"],
    }
}

STRESS_WINDOWS = [
    {"episode": "GFC 2007–09", "start": "2007-07-01", "end": "2009-06-30"},
    {"episode": "Eurozone / US downgrade 2011", "start": "2011-07-01", "end": "2011-12-31"},
    {"episode": "Volmageddon + Q4 2018", "start": "2018-01-15", "end": "2018-12-31"},
    {"episode": "COVID 2020", "start": "2020-02-01", "end": "2020-06-30"},
    {"episode": "Rates shock / 2022", "start": "2022-01-01", "end": "2022-12-31"},
]

STRESS_SCORE_THRESHOLDS = [2, 3]

DATA_SOURCES = [
    (
        "Federal Reserve Economic Data (FRED), Federal Reserve Bank of St. Louis",
        "https://fred.stlouisfed.org/",
    )
]

SERIES_EXPLANATIONS = {
    "UST 10Y yield": "Long-term risk-free rate reflecting growth and inflation expectations.",
    "UST 2Y yield": "Short-term policy-sensitive rate reflecting near-term monetary stance.",
    "10Y–2Y curve": "Yield curve slope; inversions historically signal late-cycle or recession risk.",
    "BAA–10Y credit spread": "Corporate credit risk premium over Treasuries.",
    "VIX index": "Implied equity volatility; proxy for market stress and risk aversion.",
}

REGIME_DESCRIPTIONS = {
    "Risk-off / crisis": "Stress regime; credit spreads widen, volatility spikes, and investors reduce risk as liquidity and capital preservation dominate.",
    "Policy pivot": "Transition around central-bank shifts; front-end rates typically fall as markets price policy easing amid elevated uncertainty.",
    "Late-cycle": "Late stage of the economic cycle; yield curves flatten or invert and the risk of economic slowdown begins to increase.",
    "Risk-on / expansion": "Supportive growth environment; risk appetite is healthy, credit conditions are stable, and volatility remains contained.",
    "Transition": "Mixed signals or regime handoff; indicators are not decisive enough to define a single dominant state.",
}
