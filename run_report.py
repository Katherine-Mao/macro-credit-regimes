import sys
import os
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
sys.path.append(os.path.join(os.path.dirname(__file__), "configs"))

from macro_credit_regimes.data import load_macro_series
from macro_credit_regimes.features import build_features
from macro_credit_regimes.regimes import rule_based_regime
from macro_credit_regimes.plots import make_report_plots
from macro_credit_regimes.analytics import (
    regime_distribution,
    key_signal_medians_by_regime,
    feature_summary_by_regime,
    stress_window_scorecard,
)
from macro_credit_regimes.pdf_builder import build_pdf_report
from configs.report_config import (
    REPORT_META,
    FEATURE_SUMMARY_GROUPS,
    STRESS_WINDOWS,
    STRESS_SCORE_THRESHOLDS,
    DATA_SOURCES,
    SERIES_EXPLANATIONS,
    REGIME_DESCRIPTIONS,
)



def main():
    macro = load_macro_series(start="2005-01-01")
    features = build_features(macro)
    regimes = rule_based_regime(features)

    dashboard_path = make_report_plots(features, regimes)

    dist = regime_distribution(regimes)
    medians = key_signal_medians_by_regime(features, regimes)
    feat_summary = feature_summary_by_regime(features, regimes, stats=["mean", "std"])

    windows = pd.DataFrame(STRESS_WINDOWS)

    stress = stress_window_scorecard(
        regimes,
        windows,
        risk_off_score=features.get("risk_off_score"),
        score_threshold=STRESS_SCORE_THRESHOLDS,
    )

    build_pdf_report(
        output_path=REPORT_META["output_path"],
        title=REPORT_META["title"],
        subtitle=REPORT_META["subtitle"],
        figures=[("Macro–Credit Dashboard", dashboard_path)],
        tables=[
            ("Regime Distribution", dist),
            ("Key Signal Medians by Regime", medians),
            ("Feature Summary by Regime", feat_summary),
            ("Stress Test Scorecard", stress),
        ],
        table_column_groups=FEATURE_SUMMARY_GROUPS,
        notes=[
            ("Data start", str(features.index.min().date())),
            ("Data end", str(features.index.max().date())),
            ("Regimes", ", ".join(REGIME_DESCRIPTIONS.keys())),
        ],
        data_sources=DATA_SOURCES,
        series_explanations=SERIES_EXPLANATIONS,
        regime_descriptions=REGIME_DESCRIPTIONS,
    )

if __name__ == "__main__":
    main()

