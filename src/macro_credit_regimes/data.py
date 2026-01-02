import time
import urllib.error
import urllib.request
import os
import pandas as pd


class FREDDownloadError(RuntimeError):
    pass


def _read_csv_with_retries(url, retries=3, backoff_seconds=1.0, timeout_seconds=15):
    '''Download a CSV from a URL with retries & exponential backoff.'''
    last_err = None

    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout_seconds) as resp:
                return pd.read_csv(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff_seconds * (2 ** (attempt - 1)))
            else:
                break

    raise FREDDownloadError(f"Failed to download after {retries} retries. url={url}. err={last_err}")


def _fred_series(code, start, retries=3, backoff_seconds=1.0, timeout_seconds=15):
    '''Fetch one FRED series as a numeric Series indexed by DATE.'''
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}"
    df = _read_csv_with_retries(
        url,
        retries=retries,
        backoff_seconds=backoff_seconds,
        timeout_seconds=timeout_seconds,
    )
    # Normalize FRED CSV schema to a stable ['DATE', 'VALUE'] layout
    df.columns = ['DATE', 'VALUE']
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    s = df.set_index("DATE")["VALUE"]
    s = pd.to_numeric(s, errors="coerce")
    s = s.loc[s.index >= pd.to_datetime(start)]
    s.name = code
    return s


def load_macro_series(start="2005-01-01", series_map=None, retries=3, backoff_seconds=1.0, timeout_seconds=15, allow_partial=True):
    '''Load multiple macro/credit series from FRED and align them into a single DataFrame.'''
    if series_map is None:
        series_map = {
            "DGS10": "ust_10y",         # 10Y Treasury yield (long-term expectation)
            "DGS2": "ust_2y",           # 2Y Treasury yield (near-term expectation)
            "BAA10Y": "baa_10y_spread", # BAA corporate credit spread (credit risk premium)
            "VIXCLS": "vix",            # VIX index level (volatility index)
        }

    data = {}
    failures = {}

    for fred_code, col_name in series_map.items():
        try:
            s = _fred_series(fred_code, start, retries, backoff_seconds, timeout_seconds).rename(col_name)
            data[col_name] = s
        except Exception as e:
            failures[fred_code] = str(e)
            if not allow_partial:
                raise
            print(f"[WARN] Failed to load {fred_code}: {e}")

    if not data:
        raise FREDDownloadError(f"All FRED series failed. Details: {failures}")

    df = pd.concat(data.values(), axis=1).sort_index()
    df = df.dropna(how="all")
    df = df[~df.index.duplicated(keep="last")]

    # Save raw data
    os.makedirs("data/raw", exist_ok=True)
    df.to_csv("data/raw/macro_fred_raw.csv")

    return df


def preview_macro_series(start="2005-01-01", n=5):
    '''Sanity-check FRED retrieval (head/tail/missingness/date range).'''
    df = load_macro_series(start=start)

    print("\n[INFO] Head:")
    print(df.head(n))

    print("\n[INFO] Tail:")
    print(df.tail(n))

    print("\n[INFO] Missingness (%):")
    print((df.isna().mean() * 100).round(2))

    print("\n[INFO] Date range:", df.index.min().date(), "→", df.index.max().date())
    print("[INFO] Rows:", len(df), "Cols:", df.shape[1])

    return df
