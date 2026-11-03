#!/usr/bin/env python3
"""Keep a vector index of every project on https://davidgadyan.com/ and rebuild it when the site changes.

Run before every `/polishmycv polish`:

  python3 site_index.py ensure            # check, reindex only if the portfolio changed
  python3 site_index.py check             # just report (exit 0 = up to date, 10 = changed)
  python3 site_index.py ensure --force    # reindex regardless

Change detection (cheap, two requests):
  1. the total count on the home page's #portfolio section ("These 40 projects …")
  2. the set of English project slugs in the sitemap (/portfolio/<slug>/)
If either differs from the stored index, every project page is re-scraped, chunked and embedded
again, and the new / removed projects are reported.

Index location: $H/docs/site-index/ (H = the polishmycv data home, see home.py)
  meta.json      count, slugs, built date, model, per-project title/date/updated
  projects.json  scraped pages: slug, url, title, description, date, updated, text
  chunks.json    [[project_index, chunk_text], ...]
  embeddings.npy float32 (n_chunks x dim), L2-normalised

vector_rank.py --index $H/docs/site-index reads this instead of re-embedding the projects.
"""
import argparse, datetime as dt, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_rank import chunks as make_chunks, embed, DEFAULT_MODEL  # noqa: E402

SITE = "https://davidgadyan.com/"
UA = {"User-Agent": "polishmycv-site-index/1.0"}


def data_home():
    import subprocess
    return Path(subprocess.run([sys.executable, str(Path(__file__).with_name("home.py"))],
                               capture_output=True, text=True, check=True).stdout.strip())


def live_state(site):
    home = BeautifulSoup(requests.get(site, headers=UA, timeout=30).text, "lxml")
    sec = home.find(id="portfolio")
    m = re.search(r"(\d+)\s+projects", sec.get_text(" ", strip=True) if sec else "")
    count = int(m.group(1)) if m else None
    sm = requests.get(site + "sitemap.xml", headers=UA, timeout=30).text
    pat = re.compile(re.escape(site) + r"portfolio/([^/]+)/$")
    slugs = sorted({pat.match(u).group(1) for u in re.findall(r"<loc>([^<]+)</loc>", sm) if pat.match(u)})
    return count, slugs


def scrape(site, slugs):
    def get(slug):
        url = f"{site}portfolio/{slug}/"
        s = BeautifulSoup(requests.get(url, headers=UA, timeout=30).text, "lxml")
        meta = lambda **k: (s.find("meta", attrs=k) or {}).get("content", "")
        art = s.find("article") or s.find("main")
        text = art.get_text("\n", strip=True).split("\nRelated projects")[0] if art else ""
        return {"slug": slug, "url": url, "title": meta(property="og:title"),
                "description": meta(name="description"), "date": meta(property="article:published_time"),
                "updated": meta(property="article:modified_time"), "text": text}
    with ThreadPoolExecutor(8) as ex:
        return list(ex.map(get, slugs))


def load_meta(idx):
    f = idx / "meta.json"
    return json.load(open(f)) if f.exists() else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["check", "ensure"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--site", default=SITE)
    ap.add_argument("--index", help="index dir (default $H/docs/site-index)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()

    idx = Path(a.index) if a.index else data_home() / "docs" / "site-index"
    meta = load_meta(idx)
    count, slugs = live_state(a.site)
    if count is None:
        print("WARNING: could not read the project count from #portfolio; relying on the sitemap")
    if count is not None and count != len(slugs):
        print(f"WARNING: home page says {count} projects but the sitemap lists {len(slugs)}")

    old_slugs = set(meta["slugs"]) if meta else set()
    new, removed = sorted(set(slugs) - old_slugs), sorted(old_slugs - set(slugs))
    changed = (meta is None or meta.get("count") != count or new or removed
               or meta.get("model") != a.model)
    print(f"site: {count} projects on #portfolio, {len(slugs)} in sitemap")
    print(f"index: {meta['count'] if meta else 'none'} projects, built {meta['built'] if meta else '-'}")
    if new: print("NEW:", ", ".join(new))
    if removed: print("REMOVED:", ", ".join(removed))

    if a.cmd == "check":
        print("CHANGED → run `site_index.py ensure`" if changed else "up to date")
        sys.exit(10 if changed else 0)
    if not changed and not a.force:
        print("up to date: no reindex needed")
        return

    print(f"reindexing {len(slugs)} projects …")
    projects = sorted(scrape(a.site, slugs), key=lambda p: p["date"], reverse=True)
    empty = [p["slug"] for p in projects if len(p["text"]) < 200]
    if empty:
        print("WARNING: little or no text scraped for:", ", ".join(empty))
    pairs = []
    for i, p in enumerate(projects):
        for c in make_chunks(p):
            pairs.append([i, c])
    import numpy as np
    E = embed([c for _, c in pairs], a.model).astype("float32")

    idx.mkdir(parents=True, exist_ok=True)
    json.dump(projects, open(idx / "projects.json", "w"), indent=1, ensure_ascii=False)
    json.dump(pairs, open(idx / "chunks.json", "w"), ensure_ascii=False)
    np.save(idx / "embeddings.npy", E)
    old_updated = {p["slug"]: p.get("updated") for p in (meta or {}).get("projects", [])}
    edited = [p["slug"] for p in projects if p["slug"] in old_updated and old_updated[p["slug"]] != p["updated"]]
    json.dump({"site": a.site, "count": count, "slugs": slugs, "built": dt.datetime.now().isoformat(timespec="seconds"),
               "model": a.model, "n_chunks": len(pairs),
               "projects": [{k: p[k] for k in ("slug", "title", "date", "updated")} for p in projects]},
              open(idx / "meta.json", "w"), indent=1, ensure_ascii=False)
    print(f"index written → {idx}  ({len(projects)} projects, {len(pairs)} chunks)")
    if edited: print("pages updated since last index:", ", ".join(edited))


if __name__ == "__main__":
    main()
