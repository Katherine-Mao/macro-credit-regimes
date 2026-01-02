import pandas as pd
import os

def build_features(macro, lag_days=1, days_1m=21, days_1y=252, fill_days=5):
    """
    Build lagged, interpretable macro/credit features for regime analysis
    
    All features are lagged to avoid lookahead bias, then lightly forward-filled
    to bridge small gaps introduced by the lag.
    """
    # Rolling z-score for level normalization (used for state vs. momentum)
    def zscore_rolling(x, window, min_periods):
        mu = x.rolling(window=window, min_periods=min_periods).mean()
        sd = x.rolling(window=window, min_periods=min_periods).std()
        sd = sd.replace(0, float('nan')) 
        return (x - mu) / sd
    
    df = macro.copy()
    min_1y = int(days_1y * 0.8)

    # -----------------------------
    # 1) Lag raw inputs (avoid lookahead)
    # -----------------------------
    df = df.shift(lag_days)
    # Fill small gaps after lag; do not carry forward indefinitely
    df = df.ffill(limit=fill_days)  

    # -----------------------------
    # 2) Yield curve (state)
    # -----------------------------
    if {"ust_10y", "ust_2y"}.issubset(df.columns):
        df["curve_10y2y"] = df["ust_10y"] - df["ust_2y"]
        df["curve_z_1y"] = zscore_rolling(df["curve_10y2y"], days_1y, min_1y)

    # -----------------------------
    # 3) Rates momentum (policy shift)
    # -----------------------------
    for col in ["ust_10y", "ust_2y"]:
        if col in df.columns:
            df[f"{col}_chg_1m"] = df[col] - df[col].shift(days_1m)

    # -----------------------------
    # 4) Credit stress
    # -----------------------------
    if "baa_10y_spread" in df.columns:
        df["credit_level"] = df["baa_10y_spread"]
        df["credit_chg_1m"] = df["baa_10y_spread"] - df["baa_10y_spread"].shift(days_1m)
        df["credit_z_1y"] = zscore_rolling(df["baa_10y_spread"], days_1y, min_1y)

    # -----------------------------
    # 5) Volatility (risk sentiment)
    # -----------------------------
    if "vix" in df.columns:
        df["vix_level"] = df["vix"]
        df["vix_chg_1m"] = df["vix"] - df["vix"].shift(days_1m)
        df["vix_z_1y"] = zscore_rolling(df["vix"], days_1y, min_1y)

    # -----------------------------
    # 6) Simple risk-off signal count
    # -----------------------------
    signals = []

    # 1. Yield curve inversion: market pricing economic slowdown / recession risk
    if "curve_10y2y" in df.columns:
        signals.append((df["curve_10y2y"] < 0).astype("float"))
    # 2. Credit spread widening: tightening financial conditions
    if "credit_chg_1m" in df.columns:
        signals.append((df["credit_chg_1m"] > 0).astype("float"))
    # 3. VIX increase: increasing uncertainty and demand for protection
    if "vix_chg_1m" in df.columns:
        signals.append((df["vix_chg_1m"] > 0).astype("float"))

    # Aggregate risk-off signals into score (higher = more stress signals)
    if signals:
        sig = pd.concat(signals, axis=1)
        df["risk_off_score"] = sig.sum(axis=1, min_count=len(signals))

    # Save engineered features
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/macro_features.csv")

    return df
