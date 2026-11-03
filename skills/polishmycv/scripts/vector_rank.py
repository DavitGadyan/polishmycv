#!/usr/bin/env python3
"""Semantic ranking of portfolio projects against a job description.

Each project (title + description + page text, chunked) and each JD requirement line is embedded
with a local sentence-embedding model (default BAAI/bge-small-en-v1.5, loaded from the
HuggingFace cache). A project's score is, for every JD requirement, the best cosine similarity
over the project's chunks, averaged over requirements (coverage), blended with the single best
requirement match (peak). The table also shows which requirement each project matches best.

The model is English-only: for a non-English JD, pass an English rendering of the
requirements (one requirement per line), e.g. jd_en.txt.

Input projects: either the catalogue JSON ({"projects": [...]}) or a list of scraped site pages
([{"slug","url","title","description","date","text"}]).

  python3 vector_rank.py --index $H/docs/site-index --jd jd_en.txt --top 20 --json ranking_vector.json
  python3 vector_rank.py --projects site_projects.json --jd jd_en.txt   # no index: embed on the fly
"""
import argparse, json, re, sys

import numpy as np

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def load_projects(path):
    data = json.load(open(path))
    items = data["projects"] if isinstance(data, dict) else data
    out = []
    for p in items:
        text = p.get("text") or "\n".join(
            str(x) for x in [p.get("summary"), "; ".join(p.get("outcomes") or []),
                             ", ".join(p.get("skills") or []), p.get("source_text")] if x)
        out.append({"id": p.get("slug") or p.get("id"), "url": p.get("url"), "title": p.get("title", ""),
                    "date": (p.get("date") or "")[:10], "description": p.get("description") or p.get("summary") or "",
                    "text": text})
    return out


def chunks(p, size=120, stride=90):
    head = f"{p['title']}. {p['description']}"
    words = re.sub(r"\s+", " ", p["text"]).split()
    parts = [head]
    for i in range(0, max(len(words) - 20, 1), stride):
        parts.append(f"{p['title']}: " + " ".join(words[i:i + size]))
    return parts


def embed(texts, model_name, batch=32, query=False):
    import torch
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).eval()
    if query and "bge" in model_name and "en" in model_name:
        texts = ["Represent this sentence for searching relevant passages: " + t for t in texts]
    vecs = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            enc = tok(texts[i:i + batch], padding=True, truncation=True, max_length=512, return_tensors="pt")
            out = model(**enc).last_hidden_state[:, 0]          # CLS pooling (BGE convention)
            vecs.append(torch.nn.functional.normalize(out, dim=-1).numpy())
    return np.vstack(vecs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--index", help="prebuilt index dir from site_index.py (docs/site-index) — preferred")
    src.add_argument("--projects", help="catalogue JSON or scraped pages JSON (embeds them on the fly)")
    ap.add_argument("--jd", required=True, help="text file, one requirement per line (English)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--peak-weight", type=float, default=0.4)
    ap.add_argument("--json")
    a = ap.parse_args()

    if a.index:
        import os
        meta = json.load(open(os.path.join(a.index, "meta.json")))
        a.model = meta["model"]
        projects = load_projects(os.path.join(a.index, "projects.json"))
        pairs = json.load(open(os.path.join(a.index, "chunks.json")))
        C = np.load(os.path.join(a.index, "embeddings.npy"))
        all_chunks, owner = [c for _, c in pairs], np.array([i for i, _ in pairs])
        print(f"index built {meta['built']} from {meta['site']} ({meta['count']} projects)")
    else:
        projects = load_projects(a.projects)
    reqs = [l.strip(" -•\t") for l in open(a.jd, encoding="utf-8") if len(l.strip()) > 15]
    if not reqs:
        sys.exit("no requirement lines in --jd")

    if not a.index:
        all_chunks, owner = [], []
        for i, p in enumerate(projects):
            for c in chunks(p):
                all_chunks.append(c); owner.append(i)
        owner = np.array(owner)
        C = embed(all_chunks, a.model)
    Q = embed(reqs, a.model, query=True)
    sim = Q @ C.T                                               # reqs x chunks

    rows = []
    for i, p in enumerate(projects):
        s = sim[:, owner == i].max(axis=1)                        # best chunk per requirement
        cov, peak = float(s.mean()), float(s.max())
        score = (1 - a.peak_weight) * cov + a.peak_weight * peak
        best = [int(j) for j in np.argsort(-s)[:2]]
        rows.append({**{k: p[k] for k in ("id", "title", "url", "date")}, "score": round(score, 4),
                     "coverage": round(cov, 4), "peak": round(peak, 4),
                     "per_requirement": [round(float(x), 4) for x in s],
                     "best_requirements": [reqs[j][:90] for j in best]})
    rows.sort(key=lambda r: -r["score"])

    print(f"{len(projects)} projects, {len(all_chunks)} chunks, {len(reqs)} requirements, model {a.model}\n")
    print(f"{'rank':>4} {'score':>6} {'cov':>6} {'peak':>6}  {'date':10}  title  →  best-matched requirement")
    for n, r in enumerate(rows[:a.top], 1):
        print(f"{n:>4} {r['score']:.3f} {r['coverage']:.3f} {r['peak']:.3f}  {r['date']:10}  {r['title'][:55]}  →  {r['best_requirements'][0][:70]}")
    print("\nBest project per requirement:")
    for j, q in enumerate(reqs):
        b = max(rows, key=lambda r: r["per_requirement"][j])
        print(f"  {b['per_requirement'][j]:.3f}  {q[:70]:70}  ← {b['title'][:45]}")
    if a.json:
        json.dump({"model": a.model, "requirements": reqs, "ranking": rows}, open(a.json, "w"), indent=1, ensure_ascii=False)
        print(f"\nfull ranking → {a.json}")


if __name__ == "__main__":
    main()
