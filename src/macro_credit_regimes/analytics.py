import numpy as np
import pandas as pd
import os


REGIME_ORDER = [
    "Risk-off / crisis",
    "Policy pivot",
    "Late-cycle",
    "Risk-on / expansion",
    "Transition",
]

SIGNAL_DISPLAY_NAMES = {
    "curve_10y2y": "10Y–2Y Curve",
    "credit_level": "BAA–10Y Spread",
    "credit_chg_1m": "Credit Δ 1M",
    "vix_level": "VIX",
    "vix_chg_1m": "VIX Δ 1M",
    "ust_2y_chg_1m": "2Y Yield Δ 1M",
    "ust_10y_chg_1m": "10Y Yield Δ 1M",
    "risk_off_score": "Risk-off Score",
}

def _normalize_regime(regimes):
    """Ensure regimes is a clean Series aligned to a DatetimeIndex."""
    if regimes is None:
        raise ValueError("regimes is None")

    reg = regimes.copy()
    if not isinstance(reg, pd.Series):
        reg = pd.Series(reg)

    if not isinstance(reg.index, pd.DatetimeIndex):
        raise ValueError("regimes index must be a pandas DatetimeIndex")

    # Standardize missing values and enforce a default regime label
    reg = reg.astype("object")
    reg = reg.replace({None: np.nan})
    reg = reg.fillna("Transition")
    return reg


def _ordered_regime_index(idx):
    """Return an ordered CategoricalIndex for stable table ordering."""
    cats = [r for r in REGIME_ORDER if r in set(idx)]
    ordered = cats
    return pd.CategoricalIndex(idx, categories=ordered, ordered=True)


def _align_features_and_regimes(features, regimes):
    """Align features and regimes on a common index."""
    reg = _normalize_regime(regimes)

    if features is None or not isinstance(features, pd.DataFrame):
        raise ValueError("features must be a pandas DataFrame")

    if not isinstance(features.index, pd.DatetimeIndex):
        raise ValueError("features index must be a pandas DatetimeIndex")

    idx = features.index.intersection(reg.index)
    if idx.empty:
        raise ValueError("No overlapping dates between features and regimes")

    x = features.loc[idx].copy()
    r = reg.loc[idx].copy()
    return x, r


def regime_distribution(regimes, include_total=True):
    """
    Regime distribution table (days and share %).
    
    Parameters
    ----------
    regimes : Series
        Daily regime labels indexed by date.
    include_total : bool
        If True, attach total sample length as metadata.
    """
    reg = _normalize_regime(regimes)

    counts = reg.value_counts(dropna=False)
    out = pd.DataFrame({"Days": counts})
    out["Share (%)"] = (out["Days"] / out["Days"].sum() * 100).round(2)
    out.index = _ordered_regime_index(out.index.tolist())
    out = out.sort_index()
    out.index.name = "Regime"

    if include_total:
        out.attrs["total_days"] = int(out["Days"].sum())

    # Save regime distrubution
    os.makedirs("reports/table", exist_ok=True)
    out.to_csv("reports/table/regime_distribution.csv")

    return out


def key_signal_medians_by_regime(features, regimes, cols=None):
    """
    Compute median levels of selected macro signals within each regime.

    Parameters
    ----------
    features : DataFrame
        Feature matrix indexed by date.
    regimes : Series
        Daily regime labels aligned to features.
    cols : list[str] or None
        Feature columns to include; defaults to a core signal set.

    """
    x, r = _align_features_and_regimes(features, regimes)

    if cols is None:
        preferred = [
            "curve_10y2y",
            "credit_level",
            "credit_chg_1m",
            "vix_level",
            "vix_chg_1m",
            "ust_2y_chg_1m",
            "ust_10y_chg_1m",
            "risk_off_score",
        ]
        cols = [c for c in preferred if c in x.columns]

    if not cols:
        raise ValueError("No key-signal columns found/provided in features")

    df = x[cols].copy()
    df["Regime"] = r.values 

    out = df.groupby("Regime")[cols].median(numeric_only=True)
    out.index.name = "Regime"
    out.index = _ordered_regime_index(out.index.tolist())
    out = out.sort_index()
    out = out.rename(columns={k: SIGNAL_DISPLAY_NAMES[k] for k in out.columns if k in SIGNAL_DISPLAY_NAMES})

    # Save key signal medians
    os.makedirs("reports/table", exist_ok=True)
    out.to_csv("reports/table/key_signal_medians.csv")

    return out


def feature_summary_by_regime(features, regimes, cols=None, stats=None, quantiles=None):
    """
    Produce a statistical summary of features by regime.

    Parameters
    ----------
    features : DataFrame
        Feature matrix indexed by date.
    regimes : Series
        Daily regime labels aligned to features.
    cols : list[str] or None
        Feature columns to summarize.
    stats : list[str] or None
        Summary statistics to compute (e.g. mean, std).
    quantiles : list[float] or None
        Optional quantiles in [0, 1] (e.g. [0.1, 0.5, 0.9]).
    """
    x, r = _align_features_and_regimes(features, regimes)

    if cols is None:
        core = [
            # Rates
            "curve_10y2y",
            "ust_2y_chg_1m",
            # Credit
            "credit_level",
            "credit_chg_1m",
            # Volatility
            "vix_level",
            "vix_chg_1m",
            # Composite
            "risk_off_score",
        ]
        cols = [c for c in core if c in x.columns]
    if not cols:
        raise ValueError("No numeric feature columns available for summary")
    if stats is None:
        stats = ["mean", "std"]

    stats = list(stats)
    df = x[cols].copy()
    df["regime"] = r.values
    g = df.groupby("regime")
    pieces = []

    agg_map = {}
    for s in stats:
        if s in ("mean", "std", "min", "max", "median"):
            agg_map[s] = s

    if agg_map:
        base = g[cols].agg(list(agg_map.values()))
        pieces.append(base)

    # Optional quantiles computation
    if quantiles:
        q = list(quantiles)
        q_rows = []
        for name, sub in g:
            row = {}
            for c in cols:
                vals = sub[c].to_numpy(dtype=float)
                if np.all(np.isnan(vals)):
                    qs = [np.nan] * len(q)
                else:
                    qs = list(np.nanquantile(vals, q))
                for qi, qv in zip(q, qs):
                    row[(c, f"p{int(round(qi * 100))}")] = qv
            q_rows.append((name, row))

        qdf = pd.DataFrame({k: v for k, v in q_rows}).T  
        qdf.index.name = "regime"
        qdf.columns = pd.MultiIndex.from_tuples(qdf.columns)
        pieces.append(qdf)

    if not pieces:
        raise ValueError("No summary outputs produced (check stats/quantiles)")

    out = pd.concat(pieces, axis=1)
    out.index = _ordered_regime_index(out.index.tolist())
    out = out.sort_index()
    # Apply display names to the feature level of MultiIndex columns
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = pd.MultiIndex.from_tuples(
            [(SIGNAL_DISPLAY_NAMES.get(c[0], c[0]), c[1],) for c in out.columns]
        )
    # Save feature summary statistics
    os.makedirs("reports/table", exist_ok=True)
    out.to_csv("reports/table/feature_summary_statics.csv")

    return out



def stress_window_scorecard(regimes, windows, target="Risk-off / crisis", risk_off_score=None, score_threshold=[2, 3]):
    """
    Evaluate regime behavior during predefined stress episodes.

    Parameters
    ----------
    regimes : Series
        Daily regime labels indexed by date.
    windows : DataFrame
        Stress episodes with columns [episode, start, end].
    target : str
        Regime label treated as crisis.
    risk_off_score : Series or None
        Optional composite stress score aligned to regimes.
    score_threshold : list[int]
        Thresholds used to compute stress-hit rates.
    """
    reg = _normalize_regime(regimes)

    if windows is None or not isinstance(windows, pd.DataFrame):
        raise ValueError("windows must be a DataFrame with columns ['episode','start','end']")

    required = {"episode", "start", "end"}
    if not required.issubset(set(windows.columns)):
        raise ValueError(f"windows must include columns {sorted(required)}")

    w = windows.copy()
    w["start"] = pd.to_datetime(w["start"])
    w["end"] = pd.to_datetime(w["end"])

    if risk_off_score is not None:
        ros = pd.Series(risk_off_score).copy()
        ros = ros.reindex(reg.index)
    else:
        ros = None

    rows = []

    for _, row in w.iterrows():
        ep = row["episode"]
        start = row["start"]
        end = row["end"]
        mask = (reg.index >= start) & (reg.index <= end)
        sub = reg.loc[mask]
        n_obs = int(sub.shape[0])
        if n_obs == 0:
            rows.append(
                {
                    "episode": ep,
                    "start": start,
                    "end": end,
                    "n_obs": 0,
                    "crisis_share": np.nan,
                    "first_crisis_date": pd.NaT,
                    "max_crisis_run_days": 0,
                    "max_crisis_run_start": pd.NaT,
                    "max_crisis_run_end": pd.NaT
                }
            )
            continue

        is_crisis = sub.eq(target)
        crisis_share = float(is_crisis.mean())

        # First crisis date
        if is_crisis.any():
            first_crisis_date = is_crisis.idxmax() 
        else:
            first_crisis_date = pd.NaT

        # Max consecutive crisis run within the window
        run_id = (is_crisis != is_crisis.shift(1)).cumsum()
        max_run_days = 0
        max_run_start = pd.NaT
        max_run_end = pd.NaT

        for rid, chunk in is_crisis.groupby(run_id):
            if not chunk.iloc[0]:
                continue
            days = int(chunk.sum())
            if days > max_run_days:
                max_run_days = days
                max_run_start = chunk.index[0]
                max_run_end = chunk.index[-1]

        out_row = {
            "episode": ep,
            "start": start,
            "end": end,
            "n_obs": n_obs,
            "crisis_share": crisis_share,
            "first_crisis_date": first_crisis_date,
            "max_crisis_run_days": max_run_days,
            "max_crisis_run_start": max_run_start,
            "max_crisis_run_end": max_run_end,
        }

        if ros is not None:
            sub_score = ros.loc[mask]
            for st in score_threshold:
                out_row[f"risk_off_score>={st}_share"] = float((sub_score >= st).mean())

        rows.append(out_row)

    out = pd.DataFrame(rows)

    # Format for report display
    rename_map = {
        "episode": "Episode",
        "start": "Start Date",
        "end": "End Date",
        "n_obs": "Observations (d)",
        "crisis_share": "Crisis Days (%)",
        "first_crisis_date": "First Crisis Date",
        "max_crisis_run_days": "Max Crisis Run (d)",
        "max_crisis_run_start": "Max Run Start",
        "max_crisis_run_end": "Max Run End",
        "risk_off_score>=2_share": "Score ≥ 2 (%)",
        "risk_off_score>=3_share": "Score ≥ 3 (%)",
    }
    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})
    for c in ["Crisis (%)", "Score≥2 (%)", "Score≥3 (%)"]:
        if c in out.columns:
            out[c] = out[c] * 100

    # Save full stress scorecard
    os.makedirs("reports/table", exist_ok=True)
    out.to_csv("reports/table/stress_window_scorecard.csv", index=False)

    keep = [
        "Episode",
        "Start Date",
        "End Date",
        "Observations (d)",
        "Crisis Days (%)",
        "First Crisis Date",
        "Max Crisis Run (d)",
        "Score ≥ 2 (%)",
        "Score ≥ 3 (%)",
    ]
    keep = [c for c in keep if c in out.columns]
    out = out[keep]

    return out
