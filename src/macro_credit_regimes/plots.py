import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path


def apply_report_style():
    """Apply global matplotlib style for the PDF report."""
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 12,
            "axes.titlesize": 16,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 11,
            "legend.fontsize": 10,
            "figure.dpi": 220,
            "savefig.dpi": 220,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )

def _regime_palette():
    """Return the fixed color palette used for regime shading."""
    return {
        "Risk-on / expansion": "#6B8F71",
        "Late-cycle": "#6C7A89",
        "Policy pivot": "#5B7C99",
        "Risk-off / crisis": "#8B3A3A",
        "Transition": "#D0D0D0",
    }


def _signal_labels():
    """Map feature column names to display labels used in charts."""
    return {
        "ust_2y": "US 2Y Treasury Yield (%)",
        "curve_10y2y": "US 10Y–2Y Yield Curve (pp)",
        "credit_level": "BAA–10Y Credit Spread (pp)",
        "vix_level": "VIX Index (level)",
    }


def _align_regimes(df_index, reg, palette):
    """Align regime labels to a target index and restrict to allowed regime names."""
    if reg is None or reg.empty or not isinstance(reg.index, pd.DatetimeIndex):
        return None
    r = reg.reindex(df_index).fillna("Transition")
    allowed = set(palette.keys())
    return r.where(r.isin(allowed), "Transition")


def _shade(ax, series, palette, alpha):
    """Shade contiguous regime blocks behind an axis."""
    if series is None or series.empty:
        return
    start = series.index[0]
    cur = series.iloc[0]
    for t, v in series.iloc[1:].items():
        if v != cur:
            ax.axvspan(start, t, color=palette.get(cur, "#BBBBBB"), alpha=alpha, linewidth=0, zorder=-1)
            start, cur = t, v
    ax.axvspan(start, series.index[-1], color=palette.get(cur, "#BBBBBB"), alpha=alpha, linewidth=0, zorder=-1)


def _draw_signal_panels(fig, gs, df, r, cols, title, palette, labels, alpha_all, alpha_crisis, lw, row_h):
    """Draw stacked signal panels with regime shading."""
    n = len(cols)
    axes = []
    for i, col in enumerate(cols):
        ax = fig.add_subplot(gs[i, 0], sharex=axes[0] if axes else None)
        axes.append(ax)

        ax.plot(df.index, df[col], linewidth=lw, zorder=3)

        if r is not None:
            _shade(ax, r, palette, alpha_all)
            _shade(ax, r.where(r.eq("Risk-off / crisis"), "Transition"), palette, alpha_crisis)

        ax.set_title(labels.get(col, col.replace("_", " ").title()), loc="left", pad=6)
        ax.grid(True, alpha=0.15)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if i < n - 1:
            ax.tick_params(labelbottom=False)

    # Use a figure-level title so it doesn't collide with axes
    fig.suptitle(title, x=0.01, ha="left", y=0.985, fontsize=22)
    return axes


def _draw_regime_timeline(ax, df_index, r, title, palette, band_height=(0.22, 0.78), lw_sep=0.0, show_legend=True):
    """Draw a regime timeline band (colored spans) over the full history."""
    # Build contiguous regime blocks for shading
    blocks = []
    start = r.index[0]
    cur = r.iloc[0]
    for t, v in r.iloc[1:].items():
        if v != cur:
            blocks.append((start, t, cur))
            start, cur = t, v
    blocks.append((start, r.index[-1], cur))

    ymin, ymax = band_height
    for a, b, lab in blocks:
        ax.axvspan(
            a,
            b + pd.Timedelta(days=1),
            ymin=ymin,
            ymax=ymax,
            color=palette.get(lab, "#BBBBBB"),
            linewidth=lw_sep,
        )

    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_title(title, loc="left", pad=12)

    years = pd.date_range(df_index.min().normalize(), df_index.max().normalize(), freq="YS")
    if len(years) > 10:
        step = max(1, len(years) // 10)
        years = years[::step]
    ax.set_xticks(years)
    ax.set_xticklabels([d.strftime("%Y") for d in years])

    for sp in ax.spines.values():
        sp.set_visible(False)

    if show_legend:
        order = ["Risk-on / expansion", "Late-cycle", "Policy pivot", "Risk-off / crisis", "Transition"]
        handles = [plt.Line2D([0], [0], color=palette[k], lw=6) for k in order]
        ax.legend(
            handles,
            order,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.98),  
            ncol=5,
            frameon=False,
            handlelength=1.8,
            columnspacing=1.3,
            borderaxespad=0.0,
        )


def make_report_plots(df, reg, out_dir="reports/figures",
                      cols=None, title="Macro–Credit Dashboard",
                      alpha_all=0.05, alpha_crisis=0.12, lw=1.2, row_h=2.0,
                      timeline_title="Regime Timeline"):
    """
    Create a combined dashboard figure for the PDF report.

    Parameters
    ----------
    df : DataFrame
        Feature data indexed by date.
    reg : Series
        Regime labels indexed by date.
    out_dir : str
        Output directory for saved figures.
    cols : list[str] or None
        Signal columns to plot (defaults to a core set).
    title : str
        Figure title.
    timeline_title : str
        Title for the regime timeline band.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("df must be indexed by a DatetimeIndex.")

    apply_report_style()

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    palette = _regime_palette()
    labels = _signal_labels()

    if cols is None:
        cols = ["ust_2y", "curve_10y2y", "credit_level", "vix_level"]
    cols = [c for c in cols if c in df.columns]
    if not cols:
        raise ValueError("None of the requested cols exist in df.")

    r = _align_regimes(df.index, reg, palette)
    if r is None:
        raise ValueError("reg must be a non-empty Series with a DatetimeIndex.")

    n = len(cols)

    # Figure height scales with the number of signal rows
    fig_h = max(6.0, row_h * n + 2.2)
    fig, _ = plt.subplots(figsize=(20, fig_h), dpi=220)
    fig.clf()

    gs = fig.add_gridspec(
        nrows=n + 2,
        ncols=1,
        height_ratios=[1.0] * n + [0.25, 0.55], 
        hspace=0.35,
    )

    axes = _draw_signal_panels(
        fig=fig,
        gs=gs,
        df=df,
        r=r,
        cols=cols,
        title=title,
        palette=palette,
        labels=labels,
        alpha_all=alpha_all,
        alpha_crisis=alpha_crisis,
        lw=lw,
        row_h=row_h,
    )

     # Timeline band at the bottom (share x-axis with signal panels)
    ax_tl = fig.add_subplot(gs[n + 1, 0], sharex=axes[0])
    _draw_regime_timeline(
        ax=ax_tl,
        df_index=df.index,
        r=r,
        title=timeline_title,
        palette=palette,
        band_height=(0.22, 0.78),
        lw_sep=0.0,
        show_legend=True,
    )

    ax_tl.set_xlabel("Date")
    fig.subplots_adjust(top=0.88, bottom=0.08, left=0.05, right=0.995)

    out_path = out_dir / "macro_credit_dashboard.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path
