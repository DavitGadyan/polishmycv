#!/usr/bin/env python3
"""Rank catalogue projects against a job description — a shortlist for Claude to choose from.

  python3 select_projects.py --jd jd.txt --catalogue docs/portfolio-catalogue.json [--top 12] [--json out.json]

Scoring is deliberately simple and transparent (keyword overlap with field weights, a small
recency bonus and a bonus for projects that already carry numbers). It exists to make sure
no relevant project is overlooked among ~40, not to make the final call: read the matched
terms it prints, then pick 3–6 projects by judgement (relevance to the must-haves first,
then measurable outcomes, then recency, then breadth of evidence across the requirements).

The JD text can be a file path or '-' for stdin.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were will with
you your our we they their he she his her them i me my not no yes but if then than so such via per into onto out over
under up down off about across after before during between within without also both each either more most other some
any all very can could should would may might must shall do does did done doing being been am own same too only just
who whom whose which what when where why how here there now new well work working works experience experienced strong
ability able team teams role roles job jobs candidate candidates ideal preferred required requirement requirements
responsibilities responsibility skills skill knowledge years year plus etc including include includes e g eg ie
company companies business businesses product products customer customers client clients solution solutions
build building develop developing development design designing deliver delivering deliver support supporting
understanding good great excellent proven track record environment fast paced""".split())

# JD wording → catalogue wording. Left side is matched as a phrase in the JD; right side terms are added.
ALIASES = {
    "llm": ["llm", "gpt", "openai", "langchain", "generative ai"],
    "llms": ["llm", "gpt", "openai", "langchain", "generative ai"],
    "large language model": ["llm", "gpt", "openai", "langchain"],
    "large language models": ["llm", "gpt", "openai", "langchain"],
    "genai": ["generative ai", "llm"],
    "generative ai": ["generative ai", "llm", "stable diffusion"],
    "agentic": ["agentic", "agent", "langgraph", "mcp"],
    "agents": ["agentic", "agent", "langgraph", "mcp"],
    "ai agent": ["agentic", "agent", "langgraph", "mcp"],
    "rag": ["rag", "retrieval", "pinecone", "vector"],
    "retrieval augmented generation": ["rag", "retrieval", "pinecone", "vector"],
    "vector database": ["pinecone", "vector", "rag"],
    "embeddings": ["embedding", "vector", "rag"],
    "fine-tuning": ["fine-tun", "huggingface", "mistral"],
    "fine tuning": ["fine-tun", "huggingface", "mistral"],
    "finetuning": ["fine-tun", "huggingface", "mistral"],
    "ml": ["machine learning", "xgboost", "scikit"],
    "machine learning": ["machine learning", "xgboost", "scikit", "classifier"],
    "deep learning": ["deep learning", "bert", "lstm", "u-net", "yolo", "neural"],
    "nlp": ["nlp", "text", "bert", "topic model", "sentiment"],
    "natural language processing": ["nlp", "text", "bert", "sentiment"],
    "computer vision": ["computer vision", "yolo", "u-net", "opencv", "image", "ocr"],
    "cv": ["computer vision", "yolo", "u-net", "opencv", "image"],
    "ocr": ["ocr", "textract", "document"],
    "forecasting": ["forecast", "time-series", "time series", "lstm"],
    "time series": ["time-series", "time series", "forecast"],
    "recommendation": ["recommender", "collaborative filtering"],
    "recommender": ["recommender", "collaborative filtering"],
    "recommendation systems": ["recommender", "collaborative filtering"],
    "mlops": ["mlops", "docker", "kubernetes", "deployment", "ci/cd", "fastapi"],
    "llmops": ["llmops", "mlops", "deployment", "fastapi"],
    "kubernetes": ["kubernetes", "k8s"],
    "k8s": ["kubernetes", "k8s"],
    "docker": ["docker", "container"],
    "aws": ["aws", "ec2", "s3", "textract", "sagemaker"],
    "gcp": ["gcp", "google cloud", "bigquery", "vertex"],
    "google cloud": ["gcp", "google cloud", "bigquery"],
    "azure": ["azure"],
    "sql": ["sql", "postgres", "mysql", "bigquery"],
    "postgres": ["postgres", "postgresql"],
    "postgresql": ["postgres", "postgresql"],
    "data pipeline": ["pipeline", "etl", "scrapy", "bigquery"],
    "data pipelines": ["pipeline", "etl", "scrapy", "bigquery"],
    "etl": ["etl", "pipeline", "sqlalchemy"],
    "data engineering": ["etl", "pipeline", "scrapy", "bigquery", "sqlalchemy"],
    "web scraping": ["scrap", "crawler", "selenium", "playwright"],
    "scraping": ["scrap", "crawler", "selenium"],
    "dashboard": ["dashboard", "dash", "plotly", "d3", "streamlit", "visualis"],
    "dashboards": ["dashboard", "dash", "plotly", "d3", "streamlit", "visualis"],
    "data visualization": ["visualis", "plotly", "d3", "dashboard"],
    "data visualisation": ["visualis", "plotly", "d3", "dashboard"],
    "bi": ["dashboard", "kpi", "plotly"],
    "react": ["react", "next.js"],
    "next.js": ["next.js", "react"],
    "nextjs": ["next.js", "react"],
    "frontend": ["react", "next.js", "d3", "dash", "web app"],
    "full stack": ["react", "fastapi", "flask", "web app", "next.js"],
    "full-stack": ["react", "fastapi", "flask", "web app", "next.js"],
    "backend": ["fastapi", "flask", "rest api", "api"],
    "rest api": ["rest api", "fastapi", "flask", "api"],
    "apis": ["api", "rest", "fastapi"],
    "fastapi": ["fastapi"],
    "python": ["python"],
    "r ": ["r plotly", " r,", " r ", "rest api in r"],
    "statistics": ["statistic", "hypothesis", "pca", "regression"],
    "statistical": ["statistic", "hypothesis", "pca", "regression"],
    "a/b testing": ["hypothesis", "experiment", "statistic"],
    "experimentation": ["hypothesis", "experiment", "statistic"],
    "quant": ["quant", "bloomberg", "trading", "pca", "yield"],
    "quantitative": ["quant", "bloomberg", "trading", "pca", "statistic"],
    "trading": ["trading", "binance", "tradingview", "quant"],
    "finance": ["finance", "financial", "trading", "stock", "yield", "bloomberg"],
    "financial": ["finance", "financial", "trading", "stock", "yield"],
    "fintech": ["finance", "trading", "crypto", "stock"],
    "crypto": ["crypto", "blockchain", "binance"],
    "blockchain": ["crypto", "blockchain"],
    "healthcare": ["health", "hipaa", "medical", "insurance"],
    "health": ["health", "hipaa", "medical"],
    "hipaa": ["hipaa", "health"],
    "insurance": ["insurance", "underwriting", "health"],
    "legal": ["legal", "law firm", "due diligence", "regulation", "compliance"],
    "compliance": ["compliance", "regulation", "hipaa", "gdpr"],
    "real estate": ["real estate", "property", "valuation", "mls"],
    "proptech": ["real estate", "property", "valuation"],
    "e-commerce": ["e-commerce", "retail", "product", "apparel"],
    "ecommerce": ["e-commerce", "retail", "product", "apparel"],
    "retail": ["retail", "e-commerce", "apparel", "product"],
    "marketing": ["marketing", "ga4", "google ads", "meta ads", "conversion", "campaign", "seo"],
    "growth": ["marketing", "conversion", "lead", "ga4", "seo"],
    "analytics": ["analytics", "ga4", "kpi", "dashboard", "tracking"],
    "google analytics": ["ga4", "google analytics", "tag manager"],
    "ga4": ["ga4", "google analytics"],
    "seo": ["seo", "geo", "schema.org", "indexable"],
    "attribution": ["attribution", "click-id", "conversion", "ga4"],
    "lead scoring": ["lead scoring", "lead-scoring", "churn", "hubspot"],
    "crm": ["hubspot", "zoho", "monday", "crm", "lead"],
    "hubspot": ["hubspot", "crm"],
    "churn": ["churn", "lead scoring", "retention"],
    "automation": ["automation", "n8n", "workflow", "agent"],
    "workflow automation": ["n8n", "workflow", "automation"],
    "n8n": ["n8n", "workflow"],
    "chatbot": ["chatbot", "assistant", "rag", "agent"],
    "conversational ai": ["chatbot", "assistant", "rag", "agent"],
    "clustering": ["cluster", "dbscan", "kmeans", "pca"],
    "segmentation": ["cluster", "segment", "dbscan", "kmeans", "u-net"],
    "classification": ["classif", "xgboost", "bert", "random forest"],
    "xgboost": ["xgboost", "gradient boost"],
    "gradient boosting": ["xgboost", "gradient boost"],
    "pytorch": ["pytorch", "torch", "deep learning", "fine-tun"],
    "tensorflow": ["tensorflow", "keras", "deep learning", "u-net", "lstm"],
    "huggingface": ["huggingface", "transformers", "bert", "fine-tun"],
    "hugging face": ["huggingface", "transformers", "bert", "fine-tun"],
    "transformers": ["bert", "huggingface", "transformers"],
    "stable diffusion": ["stable diffusion", "controlnet", "image generation"],
    "image generation": ["stable diffusion", "image generation", "controlnet"],
    "video generation": ["video", "higgsfield", "kling", "seedance"],
    "edge": ["edge", "raspberry", "jetson", "onnx", "iot"],
    "iot": ["iot", "raspberry", "jetson", "edge"],
    "embedded": ["raspberry", "jetson", "onnx", "edge"],
    "entity resolution": ["entity resolution", "dedupe", "deduplic", "matching"],
    "deduplication": ["dedupe", "deduplic", "entity resolution"],
    "record linkage": ["dedupe", "entity resolution", "fuzzy"],
    "geospatial": ["geospatial", "location", "mls"],
    "consulting": ["consult", "mentor", "lead", "advis", "technical lead"],
    "mentoring": ["mentor", "lead", "code review"],
    "leadership": ["lead", "mentor", "technical lead", "team"],
    "stakeholder": ["stakeholder", "client", "handover", "documentation"],
    "communication": ["stakeholder", "client", "documentation", "report"],
    "mcp": ["mcp", "model context protocol"],
    "model context protocol": ["mcp"],
    "openai": ["openai", "gpt"],
    "gemini": ["gemini", "google"],
    "claude": ["claude", "anthropic"],
    "anthropic": ["claude", "anthropic"],
    "prompt engineering": ["prompt", "few-shot", "llm"],
    "evaluation": ["evaluat", "benchmark", "qa", "accuracy"],
    "evals": ["evaluat", "benchmark", "qa", "accuracy"],
    "streamlit": ["streamlit"],
    "gradio": ["streamlit", "dash", "web app"],
    "spark": ["spark", "bigquery", "large-scale", "millions"],
    "big data": ["bigquery", "spark", "millions", "large-scale"],
    "large-scale": ["millions", "large-scale", "scale"],
    "startup": ["mvp", "product", "founder", "saas"],
    "saas": ["saas", "platform", "product"],
    "mvp": ["mvp", "prototype", "product"],
}


def tokens(text: str) -> list[str]:
    text = text.lower().replace("’", "'")
    words = re.findall(r"[a-z0-9][a-z0-9+#./-]*", text)
    return [w.strip("./-") for w in words if w.strip("./-") and w.strip("./-") not in STOP and len(w) > 1]


def jd_terms(jd: str) -> dict[str, float]:
    """Weighted search terms from the JD: aliases (weight 2), bigrams (1.5), unigrams (1)."""
    low = jd.lower()
    terms: dict[str, float] = {}
    for phrase, expansions in ALIASES.items():
        if re.search(r"(?<![a-z])" + re.escape(phrase.strip()) + r"(?![a-z])", low):
            for t in expansions:
                terms[t] = max(terms.get(t, 0), 2.0)
    toks = tokens(jd)
    for a, b in zip(toks, toks[1:]):
        bg = f"{a} {b}"
        if len(bg) > 6:
            terms.setdefault(bg, 1.5)
    counts = Counter(toks)
    for t, n in counts.items():
        if len(t) >= 3 and not t.isdigit():
            terms.setdefault(t, 1.0 + min(n, 3) * 0.1)  # repeated terms matter a little more
    return terms


def project_fields(p: dict) -> dict[str, str]:
    return {
        "skills": " | ".join(p.get("skills") or []).lower(),
        "themes": " | ".join((p.get("themes") or []) + (p.get("domains") or []) + (p.get("site_tags") or [])).lower(),
        "industries": " | ".join(p.get("industries") or []).lower(),
        "headline": " ".join([p.get("title") or "", p.get("summary") or "", p.get("cv_bullet") or ""]).lower(),
        "outcomes": " ".join(p.get("outcomes") or []).lower(),
        "body": (p.get("source_text") or "").lower(),
    }


FIELD_WEIGHT = {"skills": 3.0, "themes": 2.5, "industries": 2.0, "headline": 2.0, "outcomes": 1.5, "body": 0.6}


def score_project(p: dict, terms: dict[str, float], idf: dict[str, float]) -> tuple[float, list[str]]:
    fields = project_fields(p)
    matched: dict[str, float] = {}
    for term, w in terms.items():
        best = 0.0
        for f, text in fields.items():
            if term in text:
                best = max(best, FIELD_WEIGHT[f])
        if best:
            matched[term] = w * best * idf.get(term, 1.0)
    score = sum(matched.values())
    year = int((p.get("date") or "2000")[:4])
    if year >= 2025:
        score *= 1.15
    elif year >= 2023:
        score *= 1.08
    if re.search(r"\d", " ".join(p.get("outcomes") or [])):
        score *= 1.1  # already quantified — easier to make a strong bullet
    top = sorted(matched.items(), key=lambda kv: -kv[1])
    return round(score, 1), [t for t, _ in top[:10]]


#: Work David has asked never to be shown (unfinished): dropped even if a
#: stale catalogue still lists it, so no CV can pick it up again.
WITHHELD = ("s1mple", "s1mpleai")


def withheld(project) -> bool:
    import json as _json

    return any(term in _json.dumps(project, ensure_ascii=False).lower() for term in WITHHELD)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jd", required=True, help="job description text file, or '-' for stdin")
    ap.add_argument("--catalogue", default=None, help="default: <home>/docs/portfolio-catalogue.json (see home.py)")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--json", help="write the full ranking here")
    args = ap.parse_args()

    jd = sys.stdin.read() if args.jd == "-" else open(args.jd, encoding="utf-8").read()
    if args.catalogue is None:
        from home import resolve  # sibling script
        args.catalogue = str(resolve() / "docs" / "portfolio-catalogue.json")
    cat = json.load(open(args.catalogue, encoding="utf-8"))
    projects = [p for p in cat["projects"] if not withheld(p)]
    if len(projects) != len(cat["projects"]):
        print(f"{len(cat['projects']) - len(projects)} withheld project(s) excluded — unfinished work is never shown.")
    terms = jd_terms(jd)

    # idf-ish: a term that appears in every project tells us nothing
    n = len(projects)
    df = Counter()
    for p in projects:
        blob = " ".join(project_fields(p).values())
        for t in terms:
            if t in blob:
                df[t] += 1
    idf = {t: (1.0 + (n / (1 + df[t])) ** 0.35) / 2 for t in terms}

    ranked = []
    for p in projects:
        s, matched = score_project(p, terms, idf)
        ranked.append({"id": p["id"], "title": p["title"], "date": p.get("date"), "score": s,
                       "matched": matched, "themes": p.get("themes"), "industries": p.get("industries"),
                       "has_numbers": bool(re.search(r"\d", " ".join(p.get("outcomes") or []))),
                       "url": p.get("url"), "cv_bullet": p.get("cv_bullet")})
    ranked.sort(key=lambda r: -r["score"])

    recognised = sorted([t for t in terms if df[t] > 0], key=lambda t: -terms[t])
    unmatched = sorted([t for t in terms if df[t] == 0 and " " not in t and len(t) >= 4])
    print(f"JD terms recognised in the catalogue ({len(recognised)}): " + ", ".join(recognised[:40]))
    if unmatched:
        print(f"JD terms with NO project evidence (do not claim these): " + ", ".join(unmatched[:30]))
    print()
    print(f"{'rank':>4}  {'score':>6}  {'id':<11} {'date':<10} {'#':1}  title  —  matched terms")
    for i, r in enumerate(ranked[:args.top], 1):
        num = "#" if r["has_numbers"] else " "
        print(f"{i:>4}  {r['score']:>6}  {r['id']:<11} {r['date'] or '':<10} {num}  {r['title'][:48]}  —  "
              + ", ".join(r["matched"][:6]))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"terms": terms, "recognised": recognised, "unmatched": unmatched, "ranking": ranked},
                      f, ensure_ascii=False, indent=2)
        print(f"\nfull ranking → {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
