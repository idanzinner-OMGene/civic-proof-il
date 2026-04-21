---
name: standalone-report
description: Generate standalone multi-page HTML reports with interactive Plotly plots and embedded tables. Each plot/table/figure gets its own page with navigation. Reports are self-contained, zipped, and stored under reports/. Use when creating analysis reports, finishing a notebook section, exporting visualizations, or generating shareable HTML deliverables.
---

# Standalone HTML Report Generator

Produce self-contained, multi-page HTML reports with interactive Plotly figures and embedded tables. Each report lives in its own `reports/<report-name>/` directory and is zipped for distribution.

## Directory Layout

```
reports/
  <report-name>/
    index.html            # Landing page with TOC, summary stats, key findings
    pages/
      01_<slug>.html      # One page per plot, table, or figure
      02_<slug>.html
      ...
    plotly.min.js          # Local Plotly (offline support)
    generate_report.py     # Regeneration script (reads data, writes HTML)
  <report-name>.zip        # Zip of the entire directory (standalone)
```

## Workflow

1. **Collect artifacts** — gather all Plotly `fig` objects, DataFrames, and standalone figures produced in the notebook/section.
2. **Create report directory** — `reports/<meaningful-name>/` and `reports/<meaningful-name>/pages/`.
3. **Write generator script** — `generate_report.py` that reads source data and produces all HTML files.
4. **Generate pages** — one HTML file per artifact (plot, table, figure).
5. **Generate index** — landing page linking to all pages with summary.
6. **Copy Plotly.js** — ensure `plotly.min.js` is in the report directory for offline use.
7. **Zip** — create `reports/<report-name>.zip` containing the full directory.
8. **Register** — add report to `docs/PROJECT_STATUS.md` data assets table.

## Page Template

Every page (index and sub-pages) uses this HTML skeleton:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title} — {report_title}</title>
<style>
  /* Paste REPORT_CSS (see below) */
</style>
</head>
<body>
<div class="report-nav">
  <a href="index.html">{report_title}</a>
  <span class="nav-sep">›</span>
  <span>{page_title}</span>
</div>
<div class="container">
  <div class="page-nav">
    <div>{prev_link}</div>
    <div>Page {n} of {total}</div>
    <div>{next_link}</div>
  </div>

  <h1>{page_title}</h1>
  <p class="subtitle">{page_subtitle}</p>

  <div class="card">
    <!-- Plotly div OR table HTML -->
    <div id="figure-{n}"></div>
  </div>

  <!-- Optional detail/stats card below the figure -->

  <div class="page-nav">
    <div>{prev_link}</div>
    <div><a href="index.html">Back to Index</a></div>
    <div>{next_link}</div>
  </div>
</div>
<script src="../plotly.min.js"></script>
<script>
  var fig = {fig_json};
  Plotly.newPlot('figure-{n}', fig.data, fig.layout, {responsive: true, displayModeBar: true});
</script>
</body>
</html>
```

## REPORT_CSS

Shared CSS block — paste into every generated HTML `<style>` tag:

```css
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#f8f9fa;color:#333;line-height:1.6}
.report-nav{background:#1a1a2e;color:#fff;padding:10px 24px;font-size:.88rem;display:flex;align-items:center;gap:8px;position:sticky;top:0;z-index:100}
.report-nav a{color:#a8b4ff;text-decoration:none}
.report-nav a:hover{text-decoration:underline}
.nav-sep{color:#666}
.container{max-width:1200px;margin:0 auto;padding:24px}
h1{font-size:1.8rem;margin-bottom:6px;color:#1a1a2e}
.subtitle{color:#666;font-size:.95rem;margin-bottom:24px}
.card{background:#fff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08);padding:24px;margin-bottom:28px}
.card h2{font-size:1.2rem;margin-bottom:16px;color:#16213e;border-bottom:2px solid #e8e8e8;padding-bottom:8px}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:24px}
.stat-box{text-align:center;padding:16px 12px;background:#f0f4ff;border-radius:8px;border:1px solid #dce3f0}
.stat-box .number{font-size:1.6rem;font-weight:700;color:#1a1a2e;display:block}
.stat-box .label{font-size:.82rem;color:#666;margin-top:4px;display:block}
.param-table{width:100%;border-collapse:collapse;font-size:.85rem}
.param-table th{background:#f0f0f0;padding:8px 10px;text-align:left;border-bottom:2px solid #ddd;position:sticky;top:0}
.param-table td{padding:6px 10px;border-bottom:1px solid #eee}
.param-table tr:hover td{background:#f5f8ff}
.table-wrap{max-height:600px;overflow:auto;border:1px solid #e0e0e0;border-radius:6px}
.page-nav{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;padding:10px 0}
.page-nav a{padding:6px 14px;border-radius:6px;background:#f0f4ff;border:1px solid #dce3f0;font-size:.9rem;color:#4361ee;text-decoration:none}
.page-nav a:hover{background:#dce3f0}
.toc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-top:16px}
.toc-link{padding:10px 14px;border-radius:6px;border:1px solid #e0e0e0;display:flex;justify-content:space-between;align-items:center;font-size:.9rem;color:#333;text-decoration:none;transition:background .15s}
.toc-link:hover{background:#f0f4ff}
.toc-link .badge{display:inline-block;padding:3px 10px;border-radius:4px;font-size:.78rem;font-weight:600}
.badge-plot{background:#e0f0ff;color:#1a5276}
.badge-table{background:#e8f5e9;color:#2e7d32}
.badge-figure{background:#f3e5f5;color:#6a1b9a}
.method-note{font-size:.88rem;color:#555;margin-bottom:16px;padding:12px 16px;background:#f8f8f8;border-radius:6px;border-left:3px solid #636EFA}
.footer{text-align:center;color:#999;font-size:.8rem;margin-top:32px;padding-top:16px;border-top:1px solid #e0e0e0}
a{color:#4361ee;text-decoration:none}a:hover{text-decoration:underline}
@media(max-width:800px){.container{padding:16px}}
@media print{.report-nav{display:none}.page-nav{display:none}}
```

## Generator Script Pattern

Each report has a `generate_report.py` that can regenerate the HTML from source data:

```python
#!/usr/bin/env python3
"""Generate <report-name> report.

Creates:
  index.html          — landing page with TOC and summary
  pages/NN_slug.html  — one page per artifact
"""
import json, shutil, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_DIR = Path(__file__).resolve().parent
PAGES_DIR = REPORT_DIR / "pages"

REPORT_CSS = """..."""  # paste REPORT_CSS block above

def ensure_plotly_js():
    local = REPORT_DIR / "plotly.min.js"
    if local.exists():
        return
    for candidate in ROOT.glob("reports/*/plotly.min.js"):
        shutil.copy2(candidate, local)
        return
    raise FileNotFoundError("No plotly.min.js found; download from cdn.plot.ly")

def write_page(filename, title, subtitle, body_html, page_num, total,
               prev_file=None, next_file=None, fig_json=None):
    """Write a single report page."""
    prev_link = f'<a href="{prev_file}">← Previous</a>' if prev_file else '<span></span>'
    next_link = f'<a href="{next_file}">Next →</a>' if next_file else '<span></span>'
    plotly_script = ""
    if fig_json:
        plotly_script = f"""
<script src="../plotly.min.js"></script>
<script>
var fig = {fig_json};
Plotly.newPlot('figure-{page_num}', fig.data, fig.layout,
               {{responsive:true, displayModeBar:true}});
</script>"""
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>{REPORT_CSS}</style>
</head><body>
<div class="report-nav">
  <a href="../index.html">Report Name</a>
  <span class="nav-sep">›</span><span>{title}</span>
</div>
<div class="container">
  <div class="page-nav"><div>{prev_link}</div>
    <div>Page {page_num} of {total}</div><div>{next_link}</div></div>
  <h1>{title}</h1><p class="subtitle">{subtitle}</p>
  <div class="card">{body_html}</div>
  <div class="page-nav"><div>{prev_link}</div>
    <div><a href="../index.html">Back to Index</a></div>
    <div>{next_link}</div></div>
</div>{plotly_script}</body></html>"""
    (PAGES_DIR / filename).write_text(html, encoding="utf-8")

def zip_report():
    zip_path = REPORT_DIR.parent / f"{REPORT_DIR.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(REPORT_DIR.rglob("*")):
            if f.is_file():
                zf.write(f, f"{REPORT_DIR.name}/{f.relative_to(REPORT_DIR)}")
    print(f"Zipped → {zip_path} ({zip_path.stat().st_size/1024:.0f} KB)")

def main():
    PAGES_DIR.mkdir(exist_ok=True)
    ensure_plotly_js()
    # ... collect artifacts, call write_page per artifact, write index.html ...
    zip_report()

if __name__ == "__main__":
    main()
```

## Embedding Patterns

### Plotly Figure → Page

```python
fig = go.Figure(...)
fig.update_layout(height=600, template="plotly_white")
fig_json = fig.to_json()
write_page(
    "01_distribution.html", "Feature Distribution", "N=453 users",
    '<div id="figure-1" style="min-height:550px;"></div>',
    page_num=1, total=10, next_file="02_correlation.html",
    fig_json=fig_json,
)
```

### DataFrame → Page

Convert DataFrame to styled HTML table:

```python
table_html = df.to_html(index=False, classes="param-table", border=0)
body = f'<div class="table-wrap">{table_html}</div>'
write_page("05_parameters.html", "Parameter Table", "All fitted params",
           body, page_num=5, total=10,
           prev_file="04_foo.html", next_file="06_bar.html")
```

### Matplotlib/PIL Figure → Page

For non-Plotly figures, base64-encode:

```python
import base64, io
buf = io.BytesIO()
mpl_fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
b64 = base64.b64encode(buf.getvalue()).decode()
body = f'<img src="data:image/png;base64,{b64}" style="max-width:100%;border-radius:8px;">'
write_page("03_static.html", "Static Figure", "...", body, page_num=3, total=10, ...)
```

## Index Page

The index page includes:

1. **Report title and subtitle** with date and data source info
2. **Summary stat boxes** (key metrics in `.stat-grid`)
3. **Key findings** (bullet list or method-note box)
4. **Table of contents** (`.toc-grid` linking to each page, with badges: plot/table/figure)
5. **Footer** with generation metadata

TOC entry pattern:

```html
<a class="toc-link" href="pages/01_distribution.html">
  <span>Feature Distribution</span>
  <span class="badge badge-plot">Plot</span>
</a>
```

## Naming Convention

- Report directory: `snake_case` descriptive name (e.g. `scoring_analysis`, `pipeline_distributions`, `embedding_evaluation`)
- Page files: `NN_slug.html` with zero-padded index and short slug
- Generator: always `generate_report.py`

## Zipping

Always produce a zip at `reports/<report-name>.zip`:

```python
import zipfile
zip_path = REPORT_DIR.parent / f"{REPORT_DIR.name}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(REPORT_DIR.rglob("*")):
        if f.is_file():
            zf.write(f, f"{REPORT_DIR.name}/{f.relative_to(REPORT_DIR)}")
```

## Checklist

- [ ] Report directory created under `reports/`
- [ ] `pages/` subdirectory with one HTML per artifact
- [ ] Each page has prev/next navigation and back-to-index link
- [ ] `index.html` with TOC, summary stats, key findings
- [ ] Interactive Plotly figures embedded with local `plotly.min.js`
- [ ] DataFrames rendered as styled HTML tables
- [ ] `generate_report.py` can reproduce the report from source data
- [ ] `plotly.min.js` copied locally for offline use
- [ ] Zip created at `reports/<report-name>.zip`
- [ ] Report registered in `docs/PROJECT_STATUS.md`
