# Meridian Health Technologies — Senior Machine Learning Engineer (LLM / Agents)  (2026-09-20)

JD source: pasted (sample job description used to validate the `/polishmycv polish` workflow)

## Requirement → evidence

| Requirement (JD wording) | Evidence on the CV | Status |
|---|---|---|
| 5+ yrs ML/DS, 2+ yrs shipping LLM apps in production | Scope bullet (8 years, 180+ projects); Virgil.ai 2026, RAG 2024, LangGraph agent 2024, Mistral service 2024 | strong |
| Python, FastAPI, LangChain or LangGraph | Every project bullet names FastAPI/LangChain; LangGraph bullet | strong |
| Vector databases (Pinecone/pgvector) | Regulatory RAG assistant (Pinecone, sub-second retrieval) | strong on Pinecone; **pgvector not evidenced** |
| RAG, agents, structured extraction from documents (insurance cards, IDs) | RAG assistant; LangGraph document review; Document OCR (driver licences + insurance cards, Textract, ~10 s → <5 s) | strong — near-exact match |
| Fine-tune and serve open-source models | Mistral 7B fine-tune served via FastAPI on rented GPUs | strong |
| HIPAA / PHI | Virgil.ai built under HIPAA controls; "HIPAA-controlled data handling" in skills | strong |
| Docker, Kubernetes, AWS | Virgil.ai (Docker/Kubernetes on AWS); Data & infra line | strong |
| Strong SQL (PostgreSQL), data pipelines | Skills line (PostgreSQL, MySQL, BigQuery, ETL pipelines) — project-level SQL evidence (lead scoring, real-estate ETL) was cut for space | partial |
| Retrieval quality evals, monitoring, cost control | "retrieval QA" in skills only; no project text describes formal evals or monitoring | gap |
| Healthcare/insurance domain | Virgil.ai (health insurance, underwriting, broker partner); Document OCR (healthcare booking platform) | strong |
| Communicate trade-offs with product, clinicians, brokers | Replication packages / documentation (LangGraph, Mistral), broker partner on Virgil.ai | partial |

## Projects used (with links)

1. [Virgil.ai — AI health care](https://davitgadyan.github.io/portfolio_app/portfolio/project-34/) — the domain match plus agents, MCP, K8s/AWS, HIPAA; carries the "days → minutes" number.
2. [Document OCR & data extraction](https://davitgadyan.github.io/portfolio_app/portfolio/project-14/) — the JD literally asks for extraction from insurance cards and IDs; latency number ~10 s → <5 s.
3. [Crypto Blockchain Analysis RAG](https://davitgadyan.github.io/portfolio_app/portfolio/project-31/) — Pinecone RAG with OCR ingestion, sub-second retrieval, Docker.
4. [Gemini LangGraph LLM Agent](https://davitgadyan.github.io/portfolio_app/portfolio/project-28/) — LangGraph multi-agent workflow, external API validation, documentation/replication package.
5. [Multilingual AI Text Generation System](https://davitgadyan.github.io/portfolio_app/portfolio/project-22/) — fine-tuned Mistral 7B served via FastAPI on GPUs; 3 contracts.

Considered and dropped: [AI Lead Scoring — S1mple.ai](https://davitgadyan.github.io/portfolio_app/portfolio/project-35/) (PostgreSQL/MySQL + Kubernetes evidence) — six project bullets forced 9.5pt; removing it brought the page back to 10pt. Swap it in for the Mistral bullet if the SQL requirement matters more than open-source model serving.

## Changes vs base CV

- Headline → JD title first: "Senior Machine Learning Engineer | LLM & Agentic Systems | MLOps on AWS/Kubernetes".
- Added a 3-line summary with the platform stats and the HIPAA underwriting proof point.
- Upwork bullets: replaced the four generic ones with one scope bullet (numbers consolidated: 8 yrs, 180+ projects, 100+ clients, 50+ long-term, top 1%, $500k+, 8,700+ hrs) + five linked project bullets.
- EY compressed to one line; kept for the Big-4 signal and a gap-free timeline.
- Skills regrouped into JD categories (LLM & agents / Documents & vision / Data & infra / ML & compliance); "HIPPA" spelling corrected to HIPAA; "SOC20" left out pending confirmation.
- Personal projects (crypto trading strategy, ImprovTalk) dropped — unrelated to the role; Expert-Vetted/Toptal line kept.

## Gaps to prepare for

- pgvector: only Pinecone is evidenced. Be ready to say how the RAG stack would move to Postgres/pgvector.
- Formal LLM evaluation and monitoring: no project describes eval harnesses or observability — prepare an example (e.g. how retrieval quality was checked on the regulation RAG).
- SOC 2 (the base CV lists "SOC20"): confirm what this refers to before putting it back.
- The Virgil.ai underwriting metric is "days to minutes" as stated on the portfolio page; have the actual before/after ready if asked.

## Render

`David_Gadyan_CV_Meridian.pdf` — 1 page, 10pt, line-height 1.22, page fill 95%, 9 clickable links (4 contact + 5 projects). Four render passes: 9.5pt with six projects → dropped lead scoring → 10pt → headline shortened to one line → orphan lines tightened.
