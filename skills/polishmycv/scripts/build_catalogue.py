#!/usr/bin/env python3
"""Rebuild docs/portfolio-catalogue.json and docs/portfolio-catalogue.md.

Inputs
  --catalogue  the current curated catalogue (base; may not exist on first run)
  --raw        fetch_portfolio.py output — facts from the site (always win for fact fields)
  --curated    optional JSON list of curated entries written by Claude for new/changed
               projects: [{"id": "project-39", "summary": …, "themes": […], …}]
               An entry may also carry "title", "notes", "also_published_as", "links"
               (extra curated links) or "drop": true (exclude this page, e.g. a duplicate).
  --profile    optional JSON object with curated profile fields to override
               (positioning, education, credentials, core_stack, …)

Fact fields taken from the site every time: site_title, date, url, client, site_tags,
image, source_text, sidebar links, and the profile counters / testimonials / links.
Curated fields (summary, themes, industries, domains, skills, role, outcomes,
cv_bullet, notes, title) are kept from the catalogue unless --curated overrides them.

Exit code 2 if a live project has no curated entry (unless --allow-uncurated), so a
refresh can never silently publish an empty catalogue entry.

Usage:
  python3 build_catalogue.py --catalogue docs/portfolio-catalogue.json --raw raw.json \
      [--curated refresh-curated.json] [--profile profile-override.json] \
      --out-json docs/portfolio-catalogue.json --out-md docs/portfolio-catalogue.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import OrderedDict

CATALOGUE_VERSION = "1.1"
CURATED_FIELDS = ("summary", "themes", "industries", "domains", "skills", "role", "outcomes", "cv_bullet")
FIELD_ORDER = ("id", "title", "site_title", "date", "url", "client", "listed", "summary", "themes",
               "industries", "domains", "skills", "site_tags", "role", "outcomes", "cv_bullet", "links",
               "notes", "image", "source_text", "also_published_as", "needs_curation")
STACK_LABELS = {"languages": "Languages", "ai": "AI", "ml": "ML", "interfaces": "Interfaces",
                "serving": "Serving", "infra": "Infra", "marketing": "Marketing"}


def num_of(pid: str) -> int:
    try:
        return int(pid.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def plus(n) -> str:
    return f"{int(n):,}+" if isinstance(n, (int, float)) else str(n)


def merge_links(site_links: list[dict], existing: list[dict], curated: list[dict] | None) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for src in (site_links, curated or [], existing):
        for l in src:
            u = (l.get("url") or "").strip()
            if not u or u.rstrip("/") in seen:
                continue
            seen.add(u.rstrip("/"))
            out.append({"label": l.get("label") or "Referenced", "url": u})
    return out


def build_profile(existing: dict, site: dict | None, override: dict | None) -> dict:
    prof = dict(existing or {})
    if site:
        counters = {k.upper(): v for k, v in (site.get("counters") or {}).items()}
        if "FINISHED PROJECTS" in counters:
            prof["projects_delivered"] = plus(counters["FINISHED PROJECTS"])
        if "LONG-TERM CLIENTS" in counters:
            prof["long_term_clients"] = plus(counters["LONG-TERM CLIENTS"])
        if "HOURS WORKED" in counters:
            prof["hours_worked"] = plus(counters["HOURS WORKED"])
        ld = site.get("json_ld") or {}
        graph = ld.get("@graph", [ld]) if isinstance(ld, dict) else []
        for node in graph:
            if isinstance(node, dict) and node.get("@type") == "Person":
                if node.get("jobTitle"):
                    prof["headline"] = node["jobTitle"].replace(" & ", " and ")
                if node.get("knowsAbout"):
                    prof["knows_about"] = node["knowsAbout"]
        if site.get("about_text"):
            prof["about_text"] = site["about_text"]
        if site.get("services"):
            # the site's service cards are the source of truth; keep curated extras that are not
            # just a re-spelling of one of them (e.g. "Machine learning" vs "Machine Learning")
            def key(x: str) -> str:
                return "".join(ch for ch in x.lower() if ch.isalnum())
            merged = list(site["services"])
            for s in prof.get("services") or []:
                if not any(key(s) in key(m) or key(m) in key(s) for m in merged):
                    merged.append(s)
            prof["services"] = merged
        if site.get("skills_pct"):
            prof["self_rated_skills_pct"] = site["skills_pct"]
        if site.get("testimonials"):
            prof["testimonials"] = site["testimonials"]
            prof["named_clients_and_references"] = [
                f"{t['name']} — {t['role']}" if t.get("role") else t["name"] for t in site["testimonials"]]
        links = dict(prof.get("links") or {})
        for k, v in (site.get("links") or {}).items():
            if v:
                links[k] = v.split("?")[0] if k == "book_a_call" else v
        prof["links"] = links
    if override:
        prof.update(override)
    prof.setdefault("name", "David Gadyan")
    return prof


def build_indexes(projects: list[dict]) -> tuple[list[str], dict, dict, dict, dict]:
    def index(field: str) -> dict:
        idx: dict[str, list[str]] = {}
        for p in projects:
            for v in p.get(field) or []:
                idx.setdefault(v, []).append(p["id"])
        return OrderedDict(sorted(idx.items(), key=lambda kv: (-len(kv[1]), kv[0])))

    themes = sorted({t for p in projects for t in (p.get("themes") or [])})
    return themes, index("themes"), index("industries"), index("domains"), index("skills")


# --------------------------------------------------------------------------- #
# Markdown rendering (format mirrors the hand-written v1.0 catalogue)
# --------------------------------------------------------------------------- #
def render_md(cat: dict) -> str:
    prof = cat["profile"]
    by_id = {p["id"]: p for p in cat["projects"]}
    L: list[str] = []
    L.append(f"# {prof.get('name', 'David Gadyan')} — Portfolio Project Catalogue\n")
    L.append(f"Source: {cat['source'].split(' ')[0]}  ")
    L.append(f"Generated: {cat['generated']} · {cat['counts']['projects']} projects · "
             f"Companion machine-readable file: `portfolio-catalogue.json`\n")
    L.append("**How to use this for CV tailoring.** Read the job post, pick the matching themes and industries "
             "from the index below, then pull those projects. Each entry has a `cv_bullet` written ready to drop "
             "into a CV, plus the outcomes and the public link to attach.\n")
    L.append("---\n")
    L.append("## Profile\n")
    L.append(f"**{prof.get('name')}** — {prof.get('headline', '')}\n")
    if prof.get("positioning"):
        L.append(prof["positioning"] + "\n")
    exp = f"- Experience: {prof.get('experience_years', '?')} years, {prof.get('projects_delivered', '?')} projects delivered, " \
          f"{prof.get('long_term_clients', '?')} long-term clients"
    if prof.get("hours_worked"):
        exp += f", {prof['hours_worked']} hours worked"
    L.append(exp)
    if prof.get("location"):
        L.append(f"- Location: {prof['location']}")
    for e in prof.get("education") or []:
        L.append(f"- Education: {e}")
    if prof.get("previously"):
        L.append(f"- Previously: {prof['previously']}")
    for c in prof.get("credentials") or []:
        L.append(f"- Credential: {c}")
    L.append("")
    if prof.get("services"):
        L.append("**Services offered:** " + "; ".join(prof["services"]) + "\n")
    if prof.get("core_stack"):
        L.append("**Core stack**\n")
        for k, v in prof["core_stack"].items():
            L.append(f"- *{STACK_LABELS.get(k, k.title())}:* " + ", ".join(v))
        L.append("")
    if prof.get("named_clients_and_references"):
        L.append("**Named clients and references**\n")
        for n in prof["named_clients_and_references"]:
            L.append(f"- {n}")
        L.append("")
    if prof.get("links"):
        parts = [f"[{k.replace('_', ' ').title()}]({v})" for k, v in prof["links"].items()]
        L.append("**Links:** " + " · ".join(parts) + "\n")
    L.append("---\n")

    def titles(ids: list[str]) -> str:
        return ", ".join(by_id[i]["title"] for i in ids if i in by_id)

    L.append("## Index by theme\n")
    L.append("Use this first: pick the themes the job post asks for.\n")
    for k, ids in cat["index_by_theme"].items():
        L.append(f"- **{k}** ({len(ids)}) — {titles(ids)}")
    L.append("")
    L.append("## Index by industry\n")
    for k, ids in cat["index_by_industry"].items():
        L.append(f"- **{k}** ({len(ids)}) — {titles(ids)}")
    L.append("")
    L.append("## Index by skill / technology\n")
    L.append("Only skills appearing in more than one project are listed here; the full per-skill index is in the JSON.\n")
    for k, ids in cat["index_by_skill"].items():
        if len(ids) > 1:
            L.append(f"- **{k}** ({len(ids)}) — {titles(ids)}")
    L.append("")
    L.append("---\n")
    L.append("## Projects\n")
    L.append("Newest first.\n")
    for p in cat["projects"]:
        L.append(f"### {p['title']}")
        meta = f"`{p['id']}` · {p.get('date') or 'undated'}"
        if p.get("client"):
            meta += f" · Client: {p['client']}"
        if p.get("listed") is False:
            meta += " · *(unlisted page)*"
        L.append(meta + "\n")
        if p.get("needs_curation"):
            L.append("*(NEEDS CURATION — summary, themes, outcomes and CV bullet not written yet)*\n")
        if p.get("site_title") and p["site_title"] != p["title"]:
            L.append(f"*(the site's heading reads “{p['site_title']}”)*\n")
        for n in p.get("notes") or []:
            L.append(f"*({n})*\n")
        if p.get("summary"):
            L.append(p["summary"] + "\n")
        L.append(f"- **Themes:** {', '.join(p.get('themes') or [])}")
        L.append(f"- **Industry:** {', '.join(p.get('industries') or [])}")
        L.append(f"- **Role:** {p.get('role') or ''}")
        L.append(f"- **Skills / tech:** {', '.join(p.get('skills') or [])}")
        L.append(f"- **Site tags:** {', '.join(p.get('site_tags') or [])}")
        L.append("- **Outcomes:**")
        for o in p.get("outcomes") or []:
            L.append(f"  - {o}")
        L.append(f"- **CV bullet (ready to use):** {p.get('cv_bullet') or ''}")
        L.append("- **Links:**")
        L.append(f"  - Portfolio page: {p['url']}")
        for l in p.get("links") or []:
            L.append(f"  - {l['label']}: {l['url']}")
        for u in p.get("also_published_as") or []:
            L.append(f"  - Also published at: {u}")
        L.append("")
    return "\n".join(L).rstrip() + "\n"


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalogue", required=True)
    ap.add_argument("--raw")
    ap.add_argument("--curated")
    ap.add_argument("--profile")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--keep-removed", action="store_true", help="keep catalogue entries no longer on the site")
    ap.add_argument("--allow-uncurated", action="store_true")
    args = ap.parse_args()

    try:
        cat = json.load(open(args.catalogue, encoding="utf-8"))
    except FileNotFoundError:
        cat = {"profile": {}, "projects": []}
    raw = json.load(open(args.raw, encoding="utf-8")) if args.raw else None
    curated_list = json.load(open(args.curated, encoding="utf-8")) if args.curated else []
    curated = {c["id"]: c for c in curated_list}
    override = json.load(open(args.profile, encoding="utf-8")) if args.profile else None

    existing = {p["id"]: p for p in cat.get("projects", [])}
    covered: dict[str, str] = {}
    for p in existing.values():
        for u in p.get("also_published_as") or []:
            covered[u.rstrip("/").lower()] = p["id"]
    for c in curated_list:
        for u in c.get("also_published_as") or []:
            covered[u.rstrip("/").lower()] = c["id"]

    projects: dict[str, dict] = {}
    uncurated: list[str] = []
    if raw:
        for r in raw["projects"]:
            pid = r["id"]
            if r["url"].rstrip("/").lower() in covered and covered[r["url"].rstrip("/").lower()] != pid:
                continue  # folded into another entry
            cur = curated.get(pid, {})
            if cur.get("drop"):
                continue
            base = dict(existing.get(pid, {}))
            p = {k: base.get(k) for k in FIELD_ORDER}
            p["id"] = pid
            p["site_title"] = r["title"]
            p["title"] = cur.get("title") or base.get("title") or r["title"]
            p["date"] = r.get("date") or base.get("date")
            p["url"] = r["url"]
            p["client"] = r.get("client")
            p["listed"] = r.get("listed", True)
            p["site_tags"] = r.get("site_tags") or []
            p["image"] = r.get("image")
            p["source_text"] = r.get("body_markdown") or base.get("source_text") or ""
            p["links"] = merge_links(r.get("links") or [], base.get("links") or [], cur.get("links"))
            for f in CURATED_FIELDS:
                if f in cur:
                    p[f] = cur[f]
            p["notes"] = list(cur.get("notes", base.get("notes") or []))
            # odd sidebar fields (e.g. "New Item: SecondSight has all rights…") — keep as notes,
            # unless the value is a bare URL, in which case it belongs with the links
            for label, value in (r.get("sidebar_other") or {}).items():
                if value.startswith("http"):
                    p["links"] = merge_links(p["links"], [{"label": label, "url": value}], None)
                elif f"{label}: {value}" not in p["notes"]:
                    p["notes"].append(f"{label}: {value}")
            p["also_published_as"] = cur.get("also_published_as", base.get("also_published_as") or [])
            if not p.get("cv_bullet") or not p.get("themes"):
                uncurated.append(pid)
                p["needs_curation"] = True
                p.setdefault("summary", r.get("rss_description") or r.get("meta_description") or "")
            else:
                p.pop("needs_curation", None)
            projects[pid] = p
        if args.keep_removed:
            for pid, p in existing.items():
                if pid not in projects and pid not in covered.values():
                    projects.setdefault(pid, p)
        else:
            for pid in existing:
                if pid not in projects and pid not in covered.values():
                    print(f"  - dropped {pid} (no longer on the site)", file=sys.stderr)
    else:
        projects = {pid: dict(p) for pid, p in existing.items()}
        for pid, cur in curated.items():
            if cur.get("drop"):
                projects.pop(pid, None)
                continue
            p = projects.setdefault(pid, {"id": pid})
            for k, v in cur.items():
                if k != "id":
                    p[k] = v

    if uncurated and not args.allow_uncurated:
        print("ERROR: these projects have no curated entry (summary/themes/cv_bullet). "
              "Write them to a --curated file and rerun, or pass --allow-uncurated:", file=sys.stderr)
        for pid in uncurated:
            print(f"  {pid}: {projects[pid]['title']}  {projects[pid]['url']}", file=sys.stderr)
        return 2

    ordered = sorted(projects.values(), key=lambda p: (p.get("date") or "0000-00-00", num_of(p["id"])), reverse=True)
    ordered = [{k: p.get(k) for k in FIELD_ORDER if k in p and (k != "needs_curation" or p.get(k))} for p in ordered]
    themes, by_theme, by_ind, by_dom, by_skill = build_indexes(ordered)
    profile = build_profile(cat.get("profile") or {}, raw.get("site_profile") if raw else None, override)

    out = OrderedDict()
    out["catalogue_version"] = CATALOGUE_VERSION
    out["generated"] = dt.date.today().isoformat()
    out["source"] = (raw or cat).get("source") or cat.get("source") or ""
    if not out["source"].startswith("http"):
        out["source"] = "https://davidgadyan.com/"
    out["source"] = out["source"].split(" ")[0] + " (site content extracted from the published pages)"
    out["purpose"] = cat.get("purpose") or ("Reference catalogue for tailoring David's CV to a job post and picking "
                                             "the most relevant portfolio projects to attach.")
    out["profile"] = profile
    out["counts"] = {"projects": len(ordered), "needs_curation": len(uncurated)}
    out["themes"] = themes
    out["index_by_theme"] = by_theme
    out["index_by_industry"] = by_ind
    out["index_by_domain"] = by_dom
    out["index_by_skill"] = by_skill
    out["projects"] = ordered

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(render_md(out))
    print(f"wrote {args.out_json} and {args.out_md}: {len(ordered)} projects, "
          f"{len(themes)} themes, {len(by_skill)} skills"
          + (f", {len(uncurated)} NEED CURATION" if uncurated else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
