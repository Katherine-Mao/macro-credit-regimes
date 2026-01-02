import os
from datetime import datetime
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def build_pdf_report(
    output_path,
    title,
    subtitle=None,
    figures=None,
    tables=None,
    table_column_groups=None, 
    notes=None,
    data_sources=None,
    series_explanations=None,
    regime_descriptions=None,
    page_size=landscape(LETTER),
    author=None,
    add_timestamp_footer=True,
):
    """
    Build the PDF report.

    Parameters
    ----------
    output_path : str
        Output PDF path.
    title : str
        Report title.
    subtitle : str or None
        Optional subtitle under the title.
    figures : list[tuple[str, str]] or None
        (section_title, image_path) pairs.
    tables : list[tuple[str, DataFrame]] or None
        (section_title, table_df) pairs.
    table_column_groups : dict or None
        Optional mapping from table title to grouped column definitions.
    notes : list[tuple[str, str]] or None
        Summary bullets rendered on the cover page.
    data_sources : list or None
        Optional list of (label, url) pairs or plain strings.
    series_explanations : dict or None
        Optional mapping of series name to short description.
    regime_descriptions : dict or None
        Optional mapping of regime name to short description.
    page_size : tuple
        ReportLab page size (default landscape LETTER).
    author : str or None
        Optional author metadata.
    add_timestamp_footer : bool
        If True, render timestamp + page number footer.
    """
    figures = figures or []
    tables = tables or []
    notes = notes or []

    _ensure_parent_dir(output_path)
    _register_fonts_safely()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=page_size,
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=title,
        author=author or "",
    )

    styles = _make_styles()
    story = []

    # --- Title page / header block ---
    story.extend(_build_title_block(title, subtitle, notes, styles, 
                                    data_sources=data_sources, 
                                    series_explanations=series_explanations,
                                    regime_descriptions=regime_descriptions))
    story.append(PageBreak())

    # --- Figures section ---
    if figures:
        story.append(Paragraph("Regime Visualizations", styles["h1"]))
        story.append(Spacer(1, 0.12 * inch))

        for sec_title, img_path in figures:
            story.extend(_add_figure_section(sec_title, img_path, styles))
        story.append(PageBreak())

    # --- Tables section ---
    if tables:
        story.append(Paragraph("Tables", styles["h1"]))
        story.append(Spacer(1, 0.12 * inch))

        for sec_title, df in tables:
            groups = None
            if table_column_groups and sec_title in table_column_groups:
                groups = table_column_groups[sec_title]
            story.extend(_add_table_section(sec_title, df, styles, column_groups=groups))

    # --- Footer section ---
    if add_timestamp_footer:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        on_page = lambda canvas, doc_: _draw_footer(canvas, doc_, ts)
    else:
        on_page = None

    doc.build(
        story,
        onFirstPage=on_page,
        onLaterPages=on_page,
    )

    return output_path


# -------------------------------------------------------------------
# Title block
# -------------------------------------------------------------------

def _build_title_block(title, subtitle, notes, styles, data_sources=None, series_explanations=None, regime_descriptions=None):
    """Build the title and contextual header block for the report."""
    blocks = []

    # Title 
    blocks.append(Paragraph(title, styles["title"]))
    if subtitle:
        blocks.append(Spacer(1, 0.04 * inch))       
        blocks.append(Paragraph(subtitle, styles["subtitle"]))

    # Summary
    if notes:
        blocks.append(Spacer(1, 0.06 * inch))         
        blocks.append(Paragraph("Summary", styles["h1"]))
        blocks.append(Spacer(1, 0.015 * inch))      

        for k, v in notes:
            if str(k).strip().lower() in {"regime", "regimes"} and isinstance(regime_descriptions, dict) and regime_descriptions:
                # Special handling: expand regime bullets into labeled descriptions
                blocks.append(Paragraph(f"• {_escape(k)}:", styles["note"]))
                blocks.append(Spacer(1, 0.004 * inch)) 
                for name, desc in regime_descriptions.items():
                    line = f"&nbsp;&nbsp;&nbsp;&nbsp;- <b>{_escape(name)}</b>: {_escape(desc)}"
                    blocks.append(Paragraph(line, styles["note"]))
                    blocks.append(Spacer(1, 0.004 * inch))  
            else:
                line = f"• {_escape(k)}: {_escape(v)}"
                blocks.append(Paragraph(line, styles["note"]))
                blocks.append(Spacer(1, 0.006 * inch))      

        blocks.append(Spacer(1, 0.08 * inch))               

    # Data Sources
    if data_sources:
        blocks.append(Paragraph("Data Sources", styles["h1"]))
        blocks.append(Spacer(1, 0.015 * inch))             
        for src in data_sources:
            if isinstance(src, (list, tuple)) and len(src) == 2:
                label, url = src
                line = (
                    f"• {_escape(label)} "
                    f"(<link href='{_escape(url)}' color='#1F4FD8'>{_escape(url)}</link>)"
                )
            else:
                line = f"• {_escape(src)}"
            blocks.append(Paragraph(line, styles["note"]))
            blocks.append(Spacer(1, 0.006 * inch))      

        blocks.append(Spacer(1, 0.08 * inch))          

    # Series Overview
    if series_explanations:
        blocks.append(Paragraph("Series Overview", styles["h1"]))
        blocks.append(Spacer(1, 0.015 * inch))             
        for name, desc in series_explanations.items():
            line = f"<b>• {_escape(name)}</b> — {_escape(desc)}"
            blocks.append(Paragraph(line, styles["note"]))
            blocks.append(Spacer(1, 0.006 * inch))         

    # Bottom padding
    blocks.append(Spacer(1, 0.12 * inch))                 
    return blocks


# -------------------------------------------------------------------
# Figure sections
# -------------------------------------------------------------------

def _add_figure_section(section_title, image_path, styles):
    """Insert a single figure image into the report with size normalization and spacing."""
    blocks = []

    if not image_path or not os.path.exists(image_path):
        blocks.append(Paragraph(f"<i>Missing image:</i> {_escape(str(image_path))}", styles["warn"]))
        blocks.append(Spacer(1, 0.18 * inch))
        return blocks

    img = Image(image_path)
    img.hAlign = "LEFT"
    max_width = 10.2 * inch
    w, h = img.imageWidth, img.imageHeight
    if w > 0 and h > 0:
        scale = min(1.0, max_width / float(w))
        img.drawWidth = w * scale
        img.drawHeight = h * scale

    blocks.append(img)
    blocks.append(Spacer(1, 0.25 * inch))
    return blocks

# -------------------------------------------------------------------
# Table sections
# -------------------------------------------------------------------

def _apply_numeric_alignment(style, chunk):
    """Auto-align table columns by inferring numeric versus text content."""
    header = chunk[0]
    for j, _ in enumerate(header):
        col_vals = [row[j] for row in chunk[1:] if row[j] != ""]
        if not col_vals:
            continue

        is_numeric = True
        for v in col_vals[:5]:
            try:
                float(str(v).replace(",", ""))
            except Exception:
                is_numeric = False
                break

        style.add("ALIGN", (j, 1), (j, -1), "RIGHT" if is_numeric else "LEFT")
    return style

def _add_table_section(section_title, df, styles, column_groups=None):
    """Render a DataFrame as a paginated report table with optional column grouping."""
    blocks = []

    blocks.append(Paragraph(_escape(section_title), styles["h2"]))
    blocks.append(Spacer(1, 0.10 * inch))

    if df is None:
        blocks.append(Paragraph("<i>No table provided.</i>", styles["warn"]))
        blocks.append(Spacer(1, 0.18 * inch))
        return blocks

    if not isinstance(df, pd.DataFrame):
        if isinstance(df, pd.Series):
            df = df.to_frame()
        else:
            blocks.append(Paragraph("<i>Unsupported table type.</i>", styles["warn"]))
            blocks.append(Spacer(1, 0.18 * inch))
            return blocks

    df_render = _flatten_df_for_report(df)

    # If groups provided, render multiple subtables
    if column_groups:
        blocks.extend(_add_grouped_tables(df_render, column_groups, styles))
        blocks.append(Spacer(1, 0.10 * inch))
        return blocks
    
    # Default to render whole table
    data = [df_render.columns.tolist()] + df_render.values.tolist()
    rows_per_page = _estimate_rows_per_page(n_cols=df_render.shape[1])
    chunks = _chunk_table_rows(data, rows_per_page=rows_per_page)

    for i, chunk in enumerate(chunks):
        tbl = Table(chunk, repeatRows=1)
        tbl.hAlign = "LEFT"
        style = _apply_numeric_alignment(_table_style(), chunk)
        tbl.setStyle(style)

        blocks.append(tbl)
        blocks.append(Spacer(1, 0.22 * inch))

        if i < len(chunks) - 1:
            blocks.append(PageBreak())
            blocks.append(Paragraph(_escape(section_title) + " (continued)", styles["h2"]))
            blocks.append(Spacer(1, 0.10 * inch))

    return blocks


def _add_grouped_tables(df_render, column_groups, styles):
    """Split a wide table into multiple subtables by column group."""
    blocks = []

    # Keep the first (label) column in every subtable for context
    first_col = df_render.columns[0] if df_render.columns.size else None

    for group_name, base_feats in column_groups.items():
        cols = _select_group_columns(df_render.columns.tolist(), base_feats, first_col=first_col)
        # Skip groups with no renderable data columns
        if len(cols) <= (1 if first_col else 0):
            continue

        sub = df_render[cols].copy()

        blocks.append(Paragraph(_escape(group_name), styles["h3"]))
        blocks.append(Spacer(1, 0.02 * inch))

        data = [sub.columns.tolist()] + sub.values.tolist()

        tbl = Table(data, repeatRows=1)
        tbl.hAlign = "LEFT"
        # Align numeric columns right; keep text columns left
        style = _apply_numeric_alignment(_table_style(), data)
        tbl.setStyle(style)
        blocks.append(tbl)
        blocks.append(Spacer(1, 0.05 * inch))  

        # Small gap between groups
        blocks.append(Spacer(1, 0.04 * inch))

    return blocks


def _select_group_columns(all_cols, base_feats, first_col=None):
    """Select columns matching a group definition while preserving order."""
    keep = []
    # Always retain the leading identifier column
    if first_col and first_col in all_cols:
        keep.append(first_col)

    # Preserve original column order
    for c in all_cols:
        if c == first_col:
            continue
        for feat in base_feats:
            feat = str(feat)
            if c == feat or c.startswith(feat + " |") or c.startswith(feat + " ("):
                keep.append(c)
                break

    # De-duplicate while preserving the original left-to-right column order
    seen = set()
    out = []
    for c in keep:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _flatten_df_for_report(df):
    """Format a DataFrame for ReportLab rendering (index, columns, rounding)."""
    x = df.copy()

    # Bring index into first column if it's not the default RangeIndex
    if not isinstance(x.index, pd.RangeIndex):
        idx_name = x.index.name or "Regime"
        x = x.reset_index().rename(columns={"index": idx_name})

    # Flatten MultiIndex columns like (feature, stat) -> "feature (stat)"
    if isinstance(x.columns, pd.MultiIndex):
        x.columns = [
            str(c[0]) if (c[1] is None or str(c[1]).strip() == "" or str(c[0]).lower() == "regime")
            else f"{c[0]} ({str(c[1])})"
            for c in x.columns.to_list()
        ]
    else:
        x.columns = [str(c) for c in x.columns]
    
    # Format datelike columns
    for c in x.columns:
        if _looks_like_datetime_series(x[c]):
            x[c] = pd.to_datetime(x[c], errors="coerce").dt.strftime("%Y-%m-%d")

    # Round numeric columns (keep tables readable)
    num_cols = x.select_dtypes(include=[np.number]).columns.tolist()
    for c in num_cols:
        if (c.lower() in {"days", "n_obs"} or c.lower().endswith("_days") or (x[c] % 1 == 0).all()):
            x[c] = x[c].map(lambda v: f"{int(v)}" if v != "" else "")
        elif "share" in c.lower() or c.endswith("%") or "(%)" in c:
            x[c] = x[c].map(lambda v: f"{v:.2f}" if v != "" else "")
        else:
            x[c] = x[c].map(lambda v: f"{v:.3f}" if v != "" else "")

    # Ensure strings for ReportLab
    x = x.replace({np.nan: ""})
    x = x.astype(object)

    # Convert all cells to strings to avoid ReportLab numeric formatting issues
    for c in x.columns:
        x[c] = x[c].map(lambda v: "" if v is None else str(v))
    return x


def _looks_like_datetime_series(s):
    """Determine whether a Series represents date-like values."""
    if s.dtype == "datetime64[ns]":
        return True
    if s.dtype == "object":
        sample = s.dropna().astype(str).head(5)
        if sample.empty:
            return False
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            parsed = pd.to_datetime(sample, format=fmt, errors="coerce")
            if parsed.notna().mean() >= 0.6:
                return True
        return False
    return False


def _estimate_rows_per_page(n_cols):
    """Estimate how many table rows fit on a page based on column count."""
    if n_cols <= 6:
        return 34
    if n_cols <= 10:
        return 28
    if n_cols <= 14:
        return 22
    return 18


def _chunk_table_rows(data, rows_per_page):
    """Split table data into page-sized chunks while repeating the header row."""
    header = data[0]
    body = data[1:]

    chunks = []
    for i in range(0, len(body), rows_per_page):
        chunk = [header] + body[i : i + rows_per_page]
        chunks.append(chunk)

    if not chunks:
        chunks = [[header]]

    return chunks


# -------------------------------------------------------------------
# Styles
# -------------------------------------------------------------------

def _make_styles():
    base = getSampleStyleSheet()

    try:
        serif = "Times-Roman"
    except:
        if "Times New Roman" in pdfmetrics.getRegisteredFontNames():
            serif = "Times New Roman"

    styles = {}

    styles["title"] = ParagraphStyle(
        "Title",
        parent=base["Title"],
        fontName=serif,
        fontSize=20,
        leading=24,
        spaceAfter=10,
    )

    styles["subtitle"] = ParagraphStyle(
        "Subtitle",
        parent=base["BodyText"],
        fontName=serif,
        fontSize=11,
        leading=22,
        spaceAfter=2,
        textColor=colors.HexColor("#333333"),
    )

    styles["h1"] = ParagraphStyle(
        "H1",
        parent=base["Heading1"],
        fontName=serif,
        fontSize=14,
        leading=18,
        spaceBefore=5,
        spaceAfter=2,
    )

    styles["h2"] = ParagraphStyle(
        "H2",
        parent=base["Heading2"],
        fontName=serif,
        fontSize=12.5,
        leading=16,
        spaceBefore=6,
        spaceAfter=6,
    )

    styles["h3"] = ParagraphStyle(
        "H3",
        parent=base["Heading3"],
        fontName=serif,
        fontSize=11,
        leading=14,
        spaceBefore=2,
        spaceAfter=2,
    )

    styles["note"] = ParagraphStyle(
        "Note",
        parent=base["BodyText"],
        fontName=serif,
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor("#111111"),
        boldFontName="Times New Roman Bold",
    )

    styles["warn"] = ParagraphStyle(
        "Warn",
        parent=base["BodyText"],
        fontName=serif,
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor("#8B0000"),
    )

    styles["link"] = ParagraphStyle(
        "Link",
        parent=styles["note"],
        textColor=colors.HexColor("#1F4FD8"), 
        underline=True,
    )
    return styles


def _table_style():
    return TableStyle(
        [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("FONTNAME", (0, 0), (-1, 0), "Times-Roman"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),

            # Body
            ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#111111")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBFBFB")]),
        ]
    )


# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------

def _draw_footer(canvas, doc, timestamp_str):
    """Simple footer: left timestamp, right page number."""
    canvas.saveState()
    canvas.setFont("Times-Roman", 9)

    y = 0.55 * inch
    canvas.setFillColor(colors.HexColor("#666666"))

    canvas.drawString(doc.leftMargin, y, f"Created: {timestamp_str}")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, y, f"Page {doc.page}")

    canvas.restoreState()


# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

def _ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _escape(x):
    # Minimal HTML escape for reportlab Paragraph
    if x is None:
        return ""
    s = str(x)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )


def _register_fonts_safely():
    """
    Register Times New Roman if available on the system.
    If not present, ReportLab will use Times-Roman.
    """
    candidates = [
        "/Library/Fonts/Times New Roman.ttf",              # MacOS
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "C:\\Windows\\Fonts\\times.ttf",                   # Windows
        "C:\\Windows\\Fonts\\timesbd.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",  # Linux 
        "/usr/share/fonts/truetype/msttcorefonts/times.ttf",
    ]

    for fp in candidates:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("Times New Roman", fp))
                pdfmetrics.registerFont(TTFont("Times New Roman Bold", fp.replace(".ttf", " Bold.ttf")))
                return
            except Exception:
                return
