#!/usr/bin/env python3
"""Render a cv.json into a one-page PDF (plus HTML and a PNG preview) and report whether it fits.

  python3 render_cv.py --cv output/<job>/cv.json --out output/<job>/David_Gadyan_CV_<Company>.pdf
                       [--fit] [--min-font 9] [--max-pages 1] [--png] [--template …] [--photo …]

What it does
  1. Jinja2-renders assets/cv-template.html with the cv.json content (inline **bold**,
     *italic* and [text](url) are converted; everything else is HTML-escaped).
  2. Prints it to PDF with headless Google Chrome (falls back to Python Playwright).
     Chrome keeps <a href> as clickable link annotations, which is why the project
     titles in the CV can link to the portfolio pages.
  3. Counts pages. With --fit it steps the font size down (0.25pt at a time, never below
     --min-font) and tightens line-height until the CV fits on --max-pages. If it still
     does not fit, exit code 2: the content must be cut, not squeezed.
  4. Measures how much of the last page is used (fill ratio) from a low-res raster, so the
     caller knows whether there is room to add a bullet or a need to trim.
  5. --png writes <out>.preview.png for a visual check.

Exit codes: 0 fits · 2 does not fit · 1 error.  A JSON summary is printed on stdout.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

HERE = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = HERE.parent / "assets" / "cv-template.html"
DEFAULT_STYLE = {"font_size_pt": 10.0, "line_height": 1.25, "margin_in": 0.5,
                 "section_gap_pt": 9.0, "entry_gap_pt": 5.0, "bullet_char": "●"}
CHROME_CANDIDATES = [
    os.environ.get("CHROME_BIN", ""),
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
]


# --------------------------------------------------------------------------- #
# inline markdown → HTML (tiny on purpose: bold, italic, links)
# --------------------------------------------------------------------------- #
def md(text) -> Markup:
    if text is None:
        return Markup("")
    s = html.escape(str(text), quote=False)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|mailto:[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", s)
    s = s.replace("\n", "<br>")
    return Markup(s)


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def render_html(cv: dict, style: dict, template_path: Path, photo: Path | None) -> str:
    env = Environment(loader=FileSystemLoader(str(template_path.parent)),
                      autoescape=select_autoescape(["html"]))
    env.filters["md"] = md
    tpl = env.get_template(template_path.name)
    return tpl.render(cv=cv, style=style, photo_data_uri=data_uri(photo) if photo else None)


# --------------------------------------------------------------------------- #
# HTML → PDF
# --------------------------------------------------------------------------- #
def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        if not c:
            continue
        if os.path.isabs(c) and os.path.exists(c):
            return c
        if shutil.which(c):
            return shutil.which(c)
    return None


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = find_chrome()
    if chrome:
        if pdf_path.exists():
            pdf_path.unlink()
        with tempfile.TemporaryDirectory() as prof:
            # a throwaway profile keeps this independent of the user's Chrome session; the
            # updater/default-browser flags stop background helpers from keeping the process alive
            cmd = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                   "--disable-component-update", "--disable-extensions", "--disable-background-networking",
                   f"--user-data-dir={prof}", "--no-pdf-header-footer",
                   f"--print-to-pdf={pdf_path}", html_path.as_uri()]
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            deadline = time.time() + 90
            stable_since = None
            last_size = -1
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                if pdf_path.exists():
                    size = pdf_path.stat().st_size
                    if size > 0 and size == last_size:
                        if stable_since and time.time() - stable_since > 1.5:
                            break  # file written and stable; Chrome is just lingering
                        stable_since = stable_since or time.time()
                    else:
                        stable_since = None
                    last_size = size
                time.sleep(0.25)
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            err = proc.stderr.read() if proc.stderr else ""
        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return
        sys.stderr.write(err[-800:] + "\n")
        raise RuntimeError("Chrome did not produce a PDF")
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as e:
        raise RuntimeError("No Chrome/Chromium found and Playwright is not installed. "
                           "Install Google Chrome or `pip install playwright && playwright install chromium`.") from e
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(html_path.as_uri())
        page.pdf(path=str(pdf_path), format="Letter", print_background=True, prefer_css_page_size=True)
        b.close()


def page_count(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader  # type: ignore
        return len(PdfReader(str(pdf_path)).pages)
    except ImportError:
        out = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True).stdout
        m = re.search(r"Pages:\s+(\d+)", out)
        return int(m.group(1)) if m else -1


def link_count(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader  # type: ignore
        n = 0
        for pg in PdfReader(str(pdf_path)).pages:
            for a in pg.get("/Annots") or []:
                if a.get_object().get("/Subtype") == "/Link":
                    n += 1
        return n
    except Exception:
        return -1


def fill_ratio(pdf_path: Path, page: int) -> float | None:
    """Fraction of the page height used by content (last non-white row / height), from a 40-dpi
    greyscale raster of the given page. Needs poppler's pdftoppm; returns None if unavailable."""
    if not shutil.which("pdftoppm"):
        return None
    with tempfile.TemporaryDirectory() as d:
        base = Path(d) / "pg"
        subprocess.run(["pdftoppm", "-gray", "-r", "40", "-f", str(page), "-l", str(page), str(pdf_path), str(base)],
                       capture_output=True)
        files = sorted(Path(d).glob("pg*.pgm"))
        if not files:
            return None
        data = files[0].read_bytes()
        # PGM: P5 <w> <h> <max>\n<bytes>
        header = re.match(rb"P5\s+(\d+)\s+(\d+)\s+(\d+)\s", data)
        if not header:
            return None
        w, h = int(header.group(1)), int(header.group(2))
        px = data[header.end():]
        last = 0
        for y in range(h):
            row = px[y * w:(y + 1) * w]
            if any(b < 200 for b in row):
                last = y
        return round((last + 1) / h, 3)


def render_preview(pdf_path: Path) -> Path | None:
    if not shutil.which("pdftoppm"):
        return None
    for old in pdf_path.parent.glob(pdf_path.stem + ".preview*.png"):
        old.unlink()  # never leave a stale preview behind — it would be mistaken for the new one
    base = pdf_path.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-r", "70", str(pdf_path), str(base) + ".preview"], capture_output=True)
    cands = sorted(pdf_path.parent.glob(pdf_path.stem + ".preview*.png"))
    if not cands:
        return None
    final = pdf_path.with_suffix(".preview.png")
    if len(cands) == 1:
        cands[0].rename(final)
        return final
    return cands[0]  # multi-page: numbered files stay, return the first


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cv", required=True, help="cv.json")
    ap.add_argument("--out", required=True, help="output PDF path")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--photo", help="override the photo path in cv.json ('' to omit)")
    ap.add_argument("--fit", action="store_true", help="shrink type within limits until it fits --max-pages")
    ap.add_argument("--max-pages", type=int, default=1)
    ap.add_argument("--min-font", type=float, default=9.0)
    ap.add_argument("--png", action="store_true", help="also write a PNG preview next to the PDF")
    ap.add_argument("--html", help="where to write the intermediate HTML (default: next to the PDF)")
    args = ap.parse_args()

    cv_path = Path(args.cv).resolve()
    cv = json.loads(cv_path.read_text(encoding="utf-8"))
    style = {**DEFAULT_STYLE, **(cv.get("style") or {})}
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    html_path = Path(args.html).resolve() if args.html else out.with_suffix(".html")

    photo: Path | None = None
    photo_setting = args.photo if args.photo is not None else cv.get("photo")
    if photo_setting:
        p = Path(photo_setting)
        sys.path.insert(0, str(HERE))
        from home import resolve  # sibling script
        for cand in (p, cv_path.parent / p, Path.cwd() / p, resolve() / p, HERE.parent / "assets" / p.name):
            if cand.exists():
                photo = cand.resolve()
                break
        if photo is None:
            print(f"warning: photo not found: {photo_setting}", file=sys.stderr)

    attempts = []
    font = float(style["font_size_pt"])
    lh = float(style["line_height"])
    while True:
        style_now = {**style, "font_size_pt": round(font, 2), "line_height": round(lh, 3)}
        html_path.write_text(render_html(cv, style_now, Path(args.template), photo), encoding="utf-8")
        html_to_pdf(html_path, out)
        pages = page_count(out)
        attempts.append({"font_size_pt": style_now["font_size_pt"], "line_height": style_now["line_height"], "pages": pages})
        if pages <= args.max_pages or not args.fit:
            break
        # shrink: alternate between line-height and font size so the page keeps its rhythm
        if lh > 1.15:
            lh = max(1.15, lh - 0.03)
        elif font - 0.25 >= args.min_font:
            font -= 0.25
            lh = float(style["line_height"]) if float(style["line_height"]) <= 1.22 else 1.2
        else:
            break

    fits = pages <= args.max_pages
    summary = {
        "pdf": str(out), "html": str(html_path), "pages": pages, "fits": fits,
        "font_size_pt": attempts[-1]["font_size_pt"], "line_height": attempts[-1]["line_height"],
        "links_in_pdf": link_count(out),
        "last_page_fill": fill_ratio(out, pages if pages > 0 else 1),
        "attempts": attempts,
    }
    if args.png:
        prev = render_preview(out)
        summary["preview_png"] = str(prev) if prev else None
    print(json.dumps(summary, indent=2))
    if not fits:
        print(f"\nDOES NOT FIT: {pages} pages at {attempts[-1]['font_size_pt']}pt. "
              f"Cut or shorten bullets (see last_page_fill) rather than shrinking further.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
