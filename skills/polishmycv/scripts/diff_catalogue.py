#!/usr/bin/env python3
"""Compare a fresh site scrape (fetch_portfolio.py output) with docs/portfolio-catalogue.json.

Prints a human summary and writes a JSON delta with the *full raw records* of every
project that is new or changed, so the curation step only has to look at those.

Statuses:
  new        — live on the site, not in the catalogue (needs curation)
  changed    — in the catalogue, but the site's facts/body differ (re-curate the changed fields)
  unchanged  — nothing to do
  covered    — a duplicate page already folded into another entry via `also_published_as`
  removed    — in the catalogue, no longer on the site

Usage:
  python3 diff_catalogue.py --raw raw.json --catalogue docs/portfolio-catalogue.json \
                            --out refresh-diff.json
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys

# `title` is compared against the catalogue's `site_title` (the literal heading on the site)
# because the curated `title` may deliberately fix a typo in it.
FACT_FIELDS = ("date", "client", "site_tags", "image")


def norm(s: str | None) -> str:
    """Normalise body text so markup-only differences (bold, link syntax, blank lines) don't count."""
    s = html.unescape(s or "")
    s = re.sub(r"^\[embedded: [^\]]*\]\s*$", "", s, flags=re.M)  # iframe placeholders
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)                # images
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)                    # **bold** → bold
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"\1", s)            # *em* → em
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)            # [text](url) → text
    s = re.sub(r"https?://\S+", "", s)                          # bare URLs
    s = re.sub(r"^\s*\d+\.\s+", "- ", s, flags=re.M)            # 1. item → - item
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip().lower()


def norm_url(u: str | None) -> str:
    return html.unescape(u or "").strip().lower().rstrip("/")


def norm_val(v):
    if isinstance(v, str):
        return html.unescape(v).strip()
    if isinstance(v, list):
        return [norm_val(x) for x in v]
    return v


def links_of(rec: dict) -> set[tuple[str, str]]:
    return {(l.get("label", "").strip(), norm_url(l.get("url"))) for l in rec.get("links", [])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--catalogue", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--body-threshold", type=float, default=0.985,
                    help="difflib ratio below which the body counts as changed")
    args = ap.parse_args()

    raw = json.load(open(args.raw, encoding="utf-8"))
    try:
        cat = json.load(open(args.catalogue, encoding="utf-8"))
    except FileNotFoundError:
        cat = {"projects": []}
    cat_by_id = {p["id"]: p for p in cat.get("projects", [])}
    covered_urls: dict[str, str] = {}
    for p in cat.get("projects", []):
        for u in p.get("also_published_as") or []:
            covered_urls[norm_url(u)] = p["id"]

    new, changed, unchanged, covered = [], [], [], []
    seen_ids = set()
    for r in raw["projects"]:
        rid = r["id"]
        if rid in cat_by_id:
            seen_ids.add(rid)
            c = cat_by_id[rid]
            diffs = []
            if norm_val(r.get("title")) != norm_val(c.get("site_title") or c.get("title")):
                diffs.append("title")
            for f in FACT_FIELDS:
                if norm_val(r.get(f) or None) != norm_val(c.get(f) or None):
                    diffs.append(f)
            # the site's sidebar links must all be present; the catalogue may hold extra curated ones
            if not links_of(r) <= links_of(c):
                diffs.append("links")
            ratio = difflib.SequenceMatcher(None, norm(c.get("source_text")), norm(r.get("body_markdown"))).ratio()
            if ratio < args.body_threshold:
                diffs.append(f"body (similarity {ratio:.3f})")
            if diffs:
                changed.append({"id": rid, "title": r["title"], "fields": diffs, "raw": r,
                                "current": {k: c.get(k) for k in ("title", "date", "client", "summary", "themes",
                                                                    "industries", "domains", "skills", "role",
                                                                    "outcomes", "cv_bullet", "notes")}})
            else:
                unchanged.append(rid)
        elif norm_url(r["url"]) in covered_urls:
            covered.append({"id": rid, "covered_by": covered_urls[norm_url(r["url"])]})
            seen_ids.add(covered_urls[norm_url(r["url"])])
        else:
            # a brand-new page that duplicates another live page: still surface it, but say so
            new.append({"id": rid, "title": r["title"], "possible_duplicate_of": r.get("possible_duplicate_of", []),
                        "raw": r})
    removed = [{"id": pid, "title": p["title"]} for pid, p in cat_by_id.items() if pid not in seen_ids]

    out = {
        "raw_fetched": raw.get("fetched"),
        "catalogue_generated": cat.get("generated"),
        "summary": {"new": len(new), "changed": len(changed), "unchanged": len(unchanged),
                    "covered": len(covered), "removed": len(removed)},
        "new": new, "changed": changed, "removed": removed, "covered": covered, "unchanged": unchanged,
        "site_profile": raw.get("site_profile"),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    s = out["summary"]
    print(f"NEW {s['new']}  CHANGED {s['changed']}  UNCHANGED {s['unchanged']}  COVERED {s['covered']}  REMOVED {s['removed']}")
    for n in new:
        dup = f"  (possible duplicate of {', '.join(n['possible_duplicate_of'])})" if n["possible_duplicate_of"] else ""
        print(f"  + new      {n['id']}: {n['title']}{dup}")
    for c in changed:
        print(f"  ~ changed  {c['id']}: {c['title']} — {', '.join(c['fields'])}")
    for r in removed:
        print(f"  - removed  {r['id']}: {r['title']}")
    for c in covered:
        print(f"  = covered  {c['id']} → folded into {c['covered_by']}")
    print(f"delta written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
