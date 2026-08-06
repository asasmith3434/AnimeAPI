# Architecture

## Overview

The platform is a pipeline: **ingest → resolve entities → score signals → detect convergence → alert**. Every stage writes to durable storage so any alert can be traced back to raw source documents.

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER                          │
│  One connector per source, on its own schedule                  │
│  (EDGAR, USASpending, USPTO, FINRA, GitHub, FRED, WARN, ...)    │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RAW EVENT STORE                             │
│  Immutable, append-only. Original documents + parsed JSON.      │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ENTITY RESOLUTION                            │
│  Map every event to: company → ticker → CIK → sector →          │
│  supply-chain relationships                                     │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNAL SCORING                               │
│  Per (company, signal_type, date): abnormality score vs.        │
│  that company's own baseline (z-scores, percentile ranks)       │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 CONVERGENCE DETECTION                           │
│  Rolling window: how many independent signal families are       │
│  abnormal for this company right now? Weighted composite.       │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              ALERTS + DASHBOARD + API                           │
│  Watchlists, convergence feed, per-company signal timeline,     │
│  full provenance drill-down                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Ingestion layer (`ingest/`)

One connector per data source, each implementing a common interface:

```python
class Connector(Protocol):
    source_id: str          # "usaspending", "edgar_form4", ...
    schedule: str           # cron expression
    def fetch(self, since: datetime) -> Iterator[RawEvent]: ...
```

- Connectors are **idempotent** (safe to re-run; dedupe on source-native IDs).
- Each run records a watermark (last successful fetch time / cursor) so backfills and incremental pulls use the same code path.
- Scheduling: start with cron-style scheduling in a single worker; move to a queue (e.g., Celery/Temporal) only when connector count demands it.

### 2. Raw event store

Append-only table (Postgres + object storage for large documents):

```sql
raw_events(
  id, source_id, source_native_id, fetched_at, event_time,
  payload JSONB, document_url, document_blob_ref
)
```

Never mutated. Reprocessing (better parsers, new entity resolution) always re-reads from here.

### 3. Entity resolution (`entities/`)

The hardest and most valuable piece. Every dataset names companies differently ("NVIDIA Corp", "Nvidia Corporation", a subsidiary, a GitHub org).

Canonical entity model:

```sql
companies(company_id, name, ticker, cik, lei, sector, industry)
company_aliases(company_id, alias, alias_type)   -- names, subsidiaries, GH orgs, domains
company_relationships(from_id, to_id, rel_type)  -- supplier, customer, competitor
```

Resolution strategy, in order:
1. **Exact identifier joins** — CIK (SEC), ticker, LEI where available.
2. **SEC company tickers file** — EDGAR publishes CIK↔ticker↔name mappings (free).
3. **Alias table** — curated + learned mappings (e.g., USASpending recipient names, GitHub orgs, patent assignees). GLEIF LEI data and SEC EX-21 subsidiary lists seed this.
4. **Fuzzy match with review queue** — anything below a confidence threshold lands in a human-review queue rather than auto-linking.

### 4. Signal scoring (`signals/`)

Convert raw events into normalized, comparable signals:

```sql
signals(
  company_id, signal_family, signal_type, event_date,
  value, baseline_mean, baseline_std, zscore, percentile,
  raw_event_ids[]   -- provenance
)
```

- **Signal families** group related types so convergence counts *independent* evidence: `procurement`, `insider`, `patents`, `labor`, `short_interest`, `osint`, `options`, `macro`, `regulatory`, `flows`.
- Scoring is **baseline-relative per company**: rolling 1–2 year mean/std for that company's own history (e.g., job postings/week, patent filings/quarter, contract dollars/quarter).
- Sparse-event types (e.g., a company's first-ever defense contract) get rule-based scores instead of z-scores.

### 5. Convergence detection (`correlation/`)

The differentiating layer. For each company, over a rolling window (e.g., 30/60/90 days):

```
convergence_score(company, window) =
    Σ over signal families f:  weight(f) × max_abnormality(f, window)
    × novelty_multiplier      # first-time signals count extra
    × cross-family bonus      # 4 families firing ≫ 1 family firing 4×
```

Design decisions:
- **Cross-family requirement:** an alert needs ≥2–3 distinct families abnormal. This is the "weak signals converging" thesis, encoded.
- **Directionality tagging:** each signal type is tagged bullish/bearish/ambiguous (e.g., insider cluster buying = bullish; borrow rate spiking = squeeze setup; WARN notices = bearish) so the composite has a sign, not just a magnitude.
- Keep v1 **transparent and rule-based** — weighted scoring, no ML. Every score must be explainable in the UI. ML ranking can come later once labeled outcomes accumulate.

### 6. Alerts, API, dashboard (`api/`, `web/`)

- **API:** FastAPI. Endpoints for company timeline, convergence leaderboard, watchlists, signal drill-down.
- **Dashboard:** Next.js/React.
  - *Convergence feed* — today's highest-scoring companies with the signal breakdown.
  - *Company page* — timeline of all signals overlaid on price history.
  - *Signal explorer* — browse any single dataset (e.g., all new defense contracts this week).
  - *Provenance drill-down* — every signal links to the source document.
- **Alert delivery:** email/Telegram/Discord webhook when a watchlist company or any company crosses a convergence threshold.

## Tech Stack (proposed)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | Best ecosystem for data ingestion/parsing; every source has Python examples |
| Database | PostgreSQL (+ TimescaleDB extension if time-series volume grows) | One database for entities, events, signals; JSONB for raw payloads |
| Object storage | S3-compatible (or local dir in dev) | Raw filings/documents |
| Scheduling | cron via APScheduler in v1 | Simplest thing that works |
| API | FastAPI | |
| Frontend | Next.js + Tailwind + a charting lib (e.g., Recharts/ECharts) | |
| Deployment | Single VPS or Fly.io/Railway in v1; Docker Compose | Total v1 infra cost ≈ $10–20/mo |

## Key Risks

- **Entity resolution quality** caps the value of everything downstream. Budget real effort here; keep the human-review queue from day one.
- **Scraping fragility** (Tier-2 sources): isolate each scraper, monitor for schema drift, alert on connector failures.
- **Terms-of-service:** prefer official APIs and bulk files; document ToS status per connector in `DATA_SOURCES.md`.
- **Signal decay / data snooping:** log every alert with a timestamp *when generated* so backtests are honest (no lookahead).
- **Not investment advice:** frame all output as research signals with provenance.
