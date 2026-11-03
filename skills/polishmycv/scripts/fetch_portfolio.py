#!/usr/bin/env python3
"""Fetch David's portfolio site (a Hugo static site) into one raw JSON file.

This is the deterministic half of `/polishmycv refresh`. It pulls facts only —
no summarising, no theme tagging. The curation happens afterwards in Claude,
on the *delta* reported by diff_catalogue.py.

Sources used, in order:
  1. portfolio/index.xml  — RSS feed: canonical list of published projects + dates
  2. sitemap.xml          — catches anything the feed missed
  3. probing project-N+1… — unlisted-but-live pages (project-38 was one of these)
  4. each project page    — title, hero image, body (as markdown), sidebar facts
  5. home page            — counters (data-count), JSON-LD, testimonials, services
  6. the CV PDF           — downloaded next to the output so refresh can spot changes

Usage:
  python3 fetch_portfolio.py --out raw.json [--base-url URL] [--cv-out path.pdf]
                             [--probe 5] [--quiet]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as htmlmod
import json
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_BASE = "https://davidgadyan.com/"
UA = {"User-Agent": "polishmycv-refresh/1.0 (+https://github.com/DavitGadyan)"}
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def log(msg: str, quiet: bool = False) -> None:
    if not quiet:
        print(msg, file=sys.stderr)


def get(url: str, retries: int = 3, timeout: int = 30) -> requests.Response | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except requests.RequestException as e:  # pragma: no cover - network
            if attempt == retries - 1:
                log(f"  ! failed {url}: {e}")
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


# --------------------------------------------------------------------------- #
# HTML → markdown (just enough for the body of a Hugo project page)
# --------------------------------------------------------------------------- #
def inline_md(node: Tag | NavigableString) -> str:
    if isinstance(node, NavigableString):
        return re.sub(r"\s+", " ", str(node))
    name = node.name.lower()
    inner = "".join(inline_md(c) for c in node.children)
    if name == "a":
        href = node.get("href", "").strip()
        text = inner.strip()
        if not href:
            return text
        if text == href or not text:
            return href
        return f"[{text}]({href})"
    if name in ("strong", "b"):
        return f"**{inner.strip()}**" if inner.strip() else ""
    if name in ("em", "i"):
        return f"*{inner.strip()}*" if inner.strip() else ""
    if name == "code":
        return f"`{inner.strip()}`"
    if name == "br":
        return "\n"
    if name == "img":
        alt = node.get("alt", "").strip()
        return f"![{alt}]({node.get('src', '')})"
    return inner


def block_md(node: Tag, depth: int = 0) -> list[str]:
    """Return a list of markdown paragraphs for a block-level node."""
    out: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString):
            t = re.sub(r"\s+", " ", str(child)).strip()
            if t:
                out.append(t)
            continue
        name = child.name.lower()
        if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(name[1])
            out.append("#" * level + " " + inline_md(child).strip())
        elif name == "p":
            t = inline_md(child).strip()
            if t:
                out.append(t)
        elif name in ("ul", "ol"):
            items = []
            for i, li in enumerate(child.find_all("li", recursive=False), 1):
                # nested lists inside li
                nested = [c for c in li.children if isinstance(c, Tag) and c.name in ("ul", "ol")]
                for n in nested:
                    n.extract()
                text = inline_md(li).strip()
                marker = f"{i}." if name == "ol" else "-"
                items.append(("  " * depth) + f"{marker} {text}")
                for n in nested:
                    items.extend(block_md(n, depth + 1))
            out.append("\n".join(items))
        elif name == "li":  # a bare li inside nested list handled by caller
            out.append(("  " * depth) + "- " + inline_md(child).strip())
        elif name in ("blockquote",):
            inner = block_md(child, depth)
            out.append("\n".join("> " + line for para in inner for line in para.split("\n")))
        elif name in ("pre",):
            out.append("```\n" + child.get_text() + "\n```")
        elif name in ("img",):
            out.append(inline_md(child))
        elif name in ("table",):
            rows = []
            for tr in child.find_all("tr"):
                cells = [inline_md(td).strip() for td in tr.find_all(["td", "th"])]
                rows.append("| " + " | ".join(cells) + " |")
            if rows:
                rows.insert(1, "|" + "---|" * (rows[0].count("|") - 1))
            out.append("\n".join(rows))
        elif name in ("div", "section", "article", "span", "figure", "center"):
            out.extend(block_md(child, depth))
        elif name in ("hr",):
            out.append("---")
        elif name in ("script", "style", "iframe", "noscript"):
            src = child.get("src") if name == "iframe" else None
            if src:
                out.append(f"[embedded: {src}]")
        else:
            t = inline_md(child).strip()
            if t:
                out.append(t)
    return out


def html_to_markdown(node: Tag) -> str:
    paras = [p for p in block_md(node) if p.strip()]
    return "\n\n".join(paras).strip()


# --------------------------------------------------------------------------- #
# Parsers
# --------------------------------------------------------------------------- #
def parse_rss(xml: str) -> list[dict]:
    soup = BeautifulSoup(xml, "xml")
    items = []
    for it in soup.find_all("item"):
        items.append({
            "title": (it.title.text if it.title else "").strip(),
            "url": (it.link.text if it.link else "").strip(),
            "pubDate": (it.pubDate.text if it.pubDate else "").strip(),
            "description": (it.description.text if it.description else "").strip(),
        })
    return items


def parse_sitemap(xml: str) -> list[str]:
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def lower_host(u: str | None) -> str | None:
    """GitHub Pages hosts are case-insensitive; the site links to itself as DavitGadyan.github.io."""
    if not u:
        return u
    m = re.match(r"^(https?://)([^/]+)(.*)$", u)
    return f"{m.group(1)}{m.group(2).lower()}{m.group(3)}" if m else u


def project_num(url: str) -> int | None:
    m = re.search(r"/portfolio/project-(\d+)/?", url)
    return int(m.group(1)) if m else None


def parse_sidebar_date(text: str) -> str | None:
    # "07 Jul, 2021"  or "29 Aug, 2026"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*,?\s+(\d{4})", text)
    if not m:
        return None
    d, mon, y = int(m.group(1)), MONTHS.get(m.group(2)[:3].title()), int(m.group(3))
    if not mon:
        return None
    return f"{y:04d}-{mon:02d}-{d:02d}"


def parse_rfc822(text: str) -> str | None:
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return dt.datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_project_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("div.col-lg-8") or soup.body
    h1 = main.find("h1") if main else None
    title = h1.get_text(" ", strip=True) if h1 else (soup.title.get_text(strip=True) if soup.title else "")
    title = re.sub(r"\s*\|\s*David Gadyan\s*$", "", title).strip()
    hero = main.find("img") if main else None
    image = hero.get("src") if hero else None
    content = main.select_one("div.content") if main else None
    body_links = []
    if content:
        for a in content.find_all("a", href=True):
            href = htmlmod.unescape(a["href"].strip())
            if href.startswith("http") and href not in [b["url"] for b in body_links]:
                body_links.append({"text": a.get_text(" ", strip=True), "url": href})
    body_md = html_to_markdown(content) if content else ""

    sidebar: dict[str, str] = {}
    links: list[dict] = []
    for li in soup.select("div.col-lg-4 li.media"):
        label_el = li.find("h4")
        value_el = li.select_one("div.content")
        if not label_el or not value_el:
            continue
        label = label_el.get_text(" ", strip=True)
        a = value_el.find("a")
        if a and a.get("href"):
            links.append({"label": label, "url": a["href"].strip(),
                          "text": a.get_text(" ", strip=True)})
        else:
            sidebar[label] = value_el.get_text(" ", strip=True)

    categories = [c.strip() for c in sidebar.get("Categories", "").split(",") if c.strip()]
    meta_desc = soup.find("meta", attrs={"name": "description"})
    return {
        "id": f"project-{project_num(url)}" if project_num(url) else url.rstrip("/").split("/")[-1],
        "num": project_num(url),
        "title": title,
        "url": lower_host(url),
        "date": parse_sidebar_date(sidebar.get("Date", "")),
        "client": sidebar.get("Client") or None,
        "site_tags": categories,
        "links": [{"label": l["label"], "url": htmlmod.unescape(l["url"]), "text": l["text"]} for l in links],
        "body_links": body_links,
        "image": lower_host(htmlmod.unescape(image)) if image else None,
        "meta_description": meta_desc.get("content", "").strip() if meta_desc else None,
        "body_markdown": body_md,
        "sidebar_other": {k: v for k, v in sidebar.items() if k not in ("Date", "Categories", "Client")},
    }


def parse_home(html: str, base: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    profile: dict = {"counters": {}, "json_ld": None, "testimonials": [], "skills_pct": {},
                     "services": [], "study_experience": [], "links": {}, "about_text": ""}

    # animated counters: <p class="fact-counter count" data-count="180">0</p> + a label nearby
    for p in soup.select("[data-count]"):
        label = None
        parent = p.parent
        for _ in range(3):
            if parent is None:
                break
            cand = parent.find(["h1", "h2", "h3", "h4", "h5", "h6", "p", "span"], string=True)
            for el in parent.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "span", "div"]):
                t = el.get_text(" ", strip=True)
                if t and el is not p and not re.fullmatch(r"[\d,\.+% ]*", t):
                    label = t
                    break
            if label:
                break
            parent = parent.parent
        try:
            profile["counters"][label or f"counter_{len(profile['counters'])}"] = int(p["data-count"])
        except ValueError:
            pass

    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            profile["json_ld"] = json.loads(s.string or "")
            break
        except Exception:
            continue

    # testimonials: name + role blocks. The theme renders them as h4/h5-ish pairs; be lenient.
    for block in soup.select(".single-testimonial, .testimonial-item, .testimonial, .testimonials-item"):
        name = block.find(["h3", "h4", "h5", "strong"])
        role = block.find(["p", "span", "h6"], class_=re.compile("(designation|position|title|role)", re.I))
        if role is None and name is not None:
            role = name.find_next_sibling("span")  # this theme: <h3>name</h3><span>role</span><p>quote</p>
        quote = block.find("p")
        if name:
            profile["testimonials"].append({
                "name": name.get_text(" ", strip=True),
                "role": re.sub(r"\s+", " ", role.get_text(" ", strip=True)) if role else None,
                "quote": quote.get_text(" ", strip=True) if quote else None,
            })

    # skills with percentages (progress bars)
    for bar in soup.select(".skill-item, .progress-item, .skill, .single-skill"):
        t = bar.get_text(" ", strip=True)
        m = re.match(r"(.+?)\s*(\d{1,3})\s*%$", t)
        if m and len(m.group(1).strip()) < 60:  # skip section containers that swallow every bar
            profile["skills_pct"][m.group(1).strip()] = int(m.group(2))

    # fallback: plain text scan for "Label\n95%" pairs and the study/experience timeline
    text = soup.get_text("\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, l in enumerate(lines[:-1]):
        if re.fullmatch(r"\d{1,3}%", lines[i + 1]) and not re.fullmatch(r"\d{1,3}%", l):
            profile["skills_pct"].setdefault(l, int(lines[i + 1][:-1]))
    # education/experience timeline (title, org, years, blurb)
    for i, l in enumerate(lines):
        if re.fullmatch(r"(19|20)\d{2}\s*-\s*((19|20)\d{2}|Present)", l) and i >= 2:
            profile["study_experience"].append({
                "title": lines[i - 2], "org": lines[i - 1], "years": l,
                "blurb": lines[i + 1] if i + 1 < len(lines) else None})
    if not profile["testimonials"]:
        # theme prints: Name / Role / Quote triplets after the TESTIMONIALS heading
        try:
            start = next(i for i, l in enumerate(lines) if l.upper() == "TESTIMONIALS")
            end = next(i for i, l in enumerate(lines) if i > start and re.fullmatch(r"0", l))
            seg = lines[start + 1:end]
            i = 0
            while i + 2 < len(seg):
                name, role, quote = seg[i], seg[i + 1], seg[i + 2]
                if len(quote) > len(role) and len(name) < 60:
                    profile["testimonials"].append({"name": name, "role": role, "quote": quote})
                    i += 3
                else:
                    i += 1
        except StopIteration:
            pass
    # services list
    try:
        s0 = next(i for i, l in enumerate(lines) if l.upper() == "SERVICES")
        for l in lines[s0 + 1:s0 + 25]:
            if l.upper().startswith("NEED A SERVICE") or l.upper() == "PORTFOLIO":
                break
            profile["services"].append(l)
    except StopIteration:
        pass
    # about text: the first paragraph of the About section
    about = soup.select_one("section.about-me div.content p, #about div.content p")
    if about:
        profile["about_text"] = about.get_text(" ", strip=True)
    # links
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if "linkedin.com" in h:
            profile["links"].setdefault("linkedin", h)
        elif "github.com" in h and "portfolio_app" not in h:
            profile["links"].setdefault("github", h)
        elif "calendly.com" in h:
            profile["links"].setdefault("book_a_call", h)
        elif h.lower().endswith(".pdf"):
            profile["links"].setdefault("cv_pdf", lower_host(urljoin(base, h)))
        elif "upwork.com" in h:
            profile["links"].setdefault("upwork", h)
    profile["links"].setdefault("portfolio", base)
    profile["links"].setdefault("all_projects", urljoin(base, "portfolio/"))
    return profile


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=DEFAULT_BASE)
    ap.add_argument("--out", required=True, help="where to write the raw JSON")
    ap.add_argument("--cv-out", help="also download the CV PDF linked from the site to this path")
    ap.add_argument("--probe", type=int, default=5, help="how many ids above the max listed one to probe")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    base = args.base_url if args.base_url.endswith("/") else args.base_url + "/"

    log(f"fetching {base}", args.quiet)
    home = get(base)
    if not home:
        print("could not fetch the home page", file=sys.stderr)
        return 1
    site_profile = parse_home(home.text, base)

    urls: dict[str, dict] = {}
    rss = get(urljoin(base, "portfolio/index.xml"))
    if rss:
        for it in parse_rss(rss.text):
            n = project_num(it["url"])
            if n is not None:
                urls[f"project-{n}"] = {"url": lower_host(it["url"]), "rss": it}
    sm = get(urljoin(base, "sitemap.xml"))
    if sm:
        for loc in parse_sitemap(sm.text):
            n = project_num(loc)
            if n is not None:
                urls.setdefault(f"project-{n}", {"url": lower_host(loc), "rss": None})
    max_n = max((project_num(v["url"]) or 0 for v in urls.values()), default=0)
    log(f"  {len(urls)} listed projects (max id {max_n}); probing {args.probe} ids above", args.quiet)
    for n in range(max_n + 1, max_n + 1 + args.probe):
        u = urljoin(base, f"portfolio/project-{n}/")
        r = get(u, retries=1)
        if r and r.status_code == 200 and "<h1" in r.text:
            urls[f"project-{n}"] = {"url": u, "rss": None, "unlisted": True, "_html": r.text}
            log(f"  + unlisted live page: {u}", args.quiet)

    projects = []
    for pid, info in sorted(urls.items(), key=lambda kv: -(project_num(kv[1]["url"]) or 0)):
        html = info.get("_html")
        if html is None:
            r = get(info["url"])
            if not r:
                log(f"  ! skipping {info['url']}", args.quiet)
                continue
            html = r.text
        rec = parse_project_page(html, info["url"])
        rec["listed"] = not info.get("unlisted", False)
        if info.get("rss"):
            rec["rss_description"] = info["rss"]["description"]
            rec["date"] = rec["date"] or parse_rfc822(info["rss"]["pubDate"])
        projects.append(rec)
        log(f"  ✓ {pid}: {rec['title']} ({rec['date']})", args.quiet)

    # duplicates: same hero image or same body → flag, do not decide
    by_img: dict[str, list[str]] = {}
    for p in projects:
        if p.get("image"):
            by_img.setdefault(p["image"], []).append(p["id"])
    for p in projects:
        dups = [x for x in by_img.get(p.get("image") or "", []) if x != p["id"]]
        p["possible_duplicate_of"] = dups

    out = {
        "fetched": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
        "source": base,
        "site_profile": site_profile,
        "counts": {"projects": len(projects), "listed": sum(p["listed"] for p in projects)},
        "projects": projects,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f"wrote {args.out} ({len(projects)} projects)", args.quiet)

    if args.cv_out:
        cv_url = site_profile["links"].get("cv_pdf") or urljoin(base, "David_Gadyan_Resume.pdf")
        r = get(cv_url)
        if r and r.content[:4] == b"%PDF":
            with open(args.cv_out, "wb") as f:
                f.write(r.content)
            log(f"downloaded CV {cv_url} → {args.cv_out}", args.quiet)
        else:
            log(f"  ! CV not downloaded from {cv_url}", args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
