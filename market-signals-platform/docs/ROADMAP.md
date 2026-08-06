# Roadmap

Build order is chosen so that each phase produces something usable on its own, and all early phases are **zero data cost** (Tier 1 sources only).

---

## Phase 0 — Skeleton

**Goal: a running pipeline with one source, end to end.**

- Repo scaffolding: Python project, Postgres via Docker Compose, migrations, config, CI (lint + tests).
- Entity foundation: load SEC's free `company_tickers.json` (CIK ↔ ticker ↔ name) into `companies`.
- First connector: **SEC EDGAR Form 4 (insider transactions)** — near-real-time, clean data, obviously useful.
- Minimal signal scoring: insider cluster-buy detection (≥2 insiders buying within 14 days).
- Output: a CLI/report listing today's cluster buys. No UI yet.

**Exit criteria:** connector runs on a schedule, is idempotent, survives restarts; provenance from signal → raw filing works.

## Phase 1 — Core free connectors

**Goal: enough independent signal families for convergence to mean something.**

Connectors, in priority order:
1. **USASpending.gov** — federal contract awards (+ SAM.gov pre-award opportunities).
2. **EDGAR 8-K** — executive changes (Item 5.02), material agreements (Item 1.01).
3. **USPTO PatentsView** — filings/grants per assignee, citation counts.
4. **FINRA short interest** + **SEC FTDs** + **Reg SHO daily short volume**.
5. **Job postings** — Greenhouse/Lever public JSON endpoints for a tracked universe; WARN notices; DOL H-1B disclosures.
6. **GitHub** — org activity via GH Archive/API for companies with known orgs.
7. **Macro liquidity composite** — FRED/NY Fed/Treasury (Fed balance sheet − TGA − RRP), HY credit spreads.

Alongside connectors:
- Alias table + fuzzy matching + human-review queue for entity resolution (USASpending recipient names and patent assignees will force this).
- Baseline scoring (z-scores vs. per-company history) for all families.

**Exit criteria:** ≥6 signal families live; ≥80% of events auto-resolve to a company; review queue functional.

## Phase 2 — Convergence engine + dashboard

**Goal: the actual product — convergence detection with a usable UI.**

- Convergence scoring over rolling windows (30/60/90 days) with cross-family weighting and directionality tags.
- FastAPI backend.
- Next.js dashboard: convergence feed, company timeline (signals overlaid on price), signal explorer, provenance drill-down.
- Watchlists + alert delivery (email/Telegram/Discord).
- Price data for overlay/evaluation: free tier of a market data API (e.g., yfinance for dev, Polygon free tier).

**Exit criteria:** daily convergence feed generated automatically; alert fires end-to-end; every alert explains itself.

## Phase 3 — Evaluation loop

**Goal: prove (or disprove) that convergence scores carry signal.**

- Log every alert at generation time (no lookahead).
- Forward-return tracking: 5/20/60-day returns after each alert vs. sector benchmark.
- Per-family diagnostics: which signal families contribute to alerts that worked? Reweight accordingly.
- Kill or fix families that add only noise.

**Exit criteria:** an honest hit-rate report the platform generates about itself.

## Phase 4 — Paid data & advanced signals (only what earned it)

Candidates, gated on Phase 3 evidence and interest:

- **Options positioning:** options chain feed (Tradier free-with-account or Polygon paid) → compute per-ticker GEX, dealer positioning estimates, unusual-activity flags.
- **Dark pool prints:** Quiver/Unusual Whales API for daily block-trade granularity (free FINRA ATS weekly data ships in Phase 1).
- **Index rebalance calendar:** scrapers for S&P/Russell/Nasdaq/MSCI announcements → pre-scheduled event signals.
- **Regulatory expansions:** openFDA + ClinicalTrials.gov (biotech), FCC ECFS (new device certifications).
- **Supply-chain graph:** curated ecosystems first (e.g., AI/semis: NVDA→TSMC→ASML→suppliers), then NLP extraction of customer-concentration language from 10-Ks; bills-of-lading data (ImportGenius) only if the graph proves useful.
- **OSINT depth:** Certificate Transparency monitoring, package-registry releases, domain registrations for tracked companies.
- **Named signal blends** (see [MULTI_DATASET_BLENDS.md](MULTI_DATASET_BLENDS.md)): LLM novelty scoring of patent claims to power the patents+GitHub "tech-adoption" blend; corporate jet tracking (OpenSky/adsb.fi + FAA registry entity resolution) paired with 8-K M&A labels; EIA grid-anomaly signals as the free half of the SAR+telemetry blend.

## Phase 5 — Scale & polish (as needed)

- Move scheduling to a proper queue; parallelize connectors.
- TimescaleDB/partitioning if signal volume demands it.
- ML-based ranking on top of rule-based scores, trained on Phase 3 outcome labels.
- Multi-user support if the platform is ever shared.

---

## Cost profile

| Phase | Data cost | Infra cost |
|---|---|---|
| 0–3 | $0 (all Tier 1/2 sources) | ~$10–20/mo (one small VPS + Postgres) |
| 4 | ~$30–100/mo (options feed, dark pool API) — only if justified | same |
| 5 | Scales with ambition | scales |

## Non-goals (explicitly out of scope)

- Automated trade execution.
- Intraday/HFT-latency anything — this is a daily/weekly research platform.
- Institutional-only data (CDS singles, prime broker flow, credit card panels) — documented as context, not built against.
- Making buy/sell recommendations — the product is *surfaced, sourced evidence*, not advice.
