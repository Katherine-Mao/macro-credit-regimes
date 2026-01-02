import pandas as pd
import os


def rule_based_regime(features):
    """
    Rule-based macro regime classifier.

    Regimes represent high-level macro states inferred from:
    - rates (policy expectations),
    - curve shape (cycle position),
    - credit (risk appetite),
    - volatility (market stress).
    """
    df = features.copy()

    # Initialize regime: assigned only when conditions are clear
    regime = pd.Series(float('nan'), index=df.index, dtype="object")

    # -----------------------------
    # Thresholds 
    # -----------------------------
    rate_move = 0.10          # 10bp monthly move = meaningful policy repricing
    credit_widen = 0.10       # 10bp credit widening = rising stress
    credit_stable = 0.05      # ±5bp = broadly stable credit
    vix_low = 15              # calm risk environment
    vix_elevated = 20         # elevated uncertainty
    vix_spike = 5             # large 1m volatility shock

    # -----------------------------
    # Required inputs
    # -----------------------------
    required = [
        "ust_2y_chg_1m",      # front-end policy expectations
        "ust_10y_chg_1m",     # long-end growth / inflation expectations
        "curve_10y2y",        # cycle signal
        "credit_chg_1m",      # risk premium dynamics
        "vix_level",          # absolute uncertainty
        "vix_chg_1m",         # volatility shock
    ]

    # If core signals are missing, do not force classification
    if not all(c in df.columns for c in required):
        return regime.fillna("Transition")

    # -----------------------------
    # Primitive signals
    # -----------------------------

    # Rates direction
    rates_rising = (
        (df["ust_2y_chg_1m"] > rate_move) &
        (df["ust_10y_chg_1m"] > rate_move)
    )
    rates_falling = (
        (df["ust_2y_chg_1m"] < -rate_move) |
        (df["ust_2y_chg_1m"] < -0.5 * df["ust_2y_chg_1m"].rolling(12).std())
    )


    # Curve shape
    curve_inverted = df["curve_10y2y"] < 0
    curve_flat_or_down = df["ust_10y_chg_1m"] <= 0

    # Credit behavior
    credit_widening = ((df["credit_chg_1m"] > credit_widen) & (df["credit_z_1y"] > 1.0))
    credit_tightening = df["credit_chg_1m"] < -credit_stable
    credit_stable_cond = df["credit_chg_1m"].abs() < credit_stable

    # Volatility state
    vix_low_cond = df["vix_level"] < vix_low
    vix_elev = df["vix_level"] >= vix_elevated
    vix_spiking = df["vix_chg_1m"] > vix_spike

    # -----------------------------
    # Regime definitions
    # -----------------------------

    # 1) Risk-off / crisis:
    # coordinated stress across rates, credit, and volatility
    crisis = (
        credit_widening &
        vix_spiking &
        ((df["risk_off_score"] >= 2) | (df["credit_z_1y"] > 1.5))
    )

    # 2) Policy pivot:
    # front-end rates falling (expected easing),
    # long-end not rising,
    # volatility elevated or unstable
    pivot = (
        (df["ust_2y_chg_1m"] < -rate_move) &
        curve_flat_or_down &
        vix_elev &
        (~vix_spiking)
    )


    # 3) Late-cycle:
    # curve inversion with calm risk conditions
    late_cycle = (
        curve_inverted &
        credit_stable_cond &
        vix_low_cond
    )

    # 4) Risk-on / expansion:
    # growth / inflation repricing,
    # improving credit,
    # low volatility
    expansion = rates_rising & credit_tightening & vix_low_cond

    # -----------------------------
    # Assign regimes 
    # -----------------------------
    # Higher-conviction regimes override weaker ones
    regime.loc[expansion] = "Risk-on / expansion"
    regime.loc[late_cycle] = "Late-cycle"
    regime.loc[pivot] = "Policy pivot"
    regime.loc[crisis] = "Risk-off / crisis"

    # -----------------------------
    # Risk-off score override
    # -----------------------------
    # If multiple independent stress signals align,
    # force classification as crisis
    if "risk_off_score" in df.columns:
        regime.loc[df["risk_off_score"] >= 3] = "Risk-off / crisis"

    # Crisis persistence: once in crisis, stay until credit AND vol normalize
    crisis_active = regime.eq("Risk-off / crisis")
    exit_crisis = ((df["credit_z_1y"] < 0.5) & (df["vix_level"] < vix_elevated))
    regime.loc[crisis_active.shift(1, fill_value=False) & ~exit_crisis] = "Risk-off / crisis"

    # -----------------------------
    # Final fill & rename
    # -----------------------------
    # Remaining NA = ambiguous / mixed signals
    regime = regime.fillna("Transition")
    regime.name = "Regime"

    # Save processed regimes
    os.makedirs("data/processed", exist_ok=True)
    regime.to_csv("data/processed/macro_regime.csv")

    return regime
