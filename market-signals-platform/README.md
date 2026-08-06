# Market Signals Platform

A platform that aggregates and correlates unconventional market data sources to surface investment opportunities before they become common knowledge.

## The Core Thesis

The most durable investing edge comes from **connecting weak signals across many datasets**. Individually, a spike in hiring or a burst of GitHub activity may not mean much. Together — especially when they align with procurement wins, unusual options activity, and supplier momentum — they can provide a much stronger indication that something meaningful is developing.

This platform ingests many independent signal streams, resolves them to a common company/ticker entity graph, scores each signal, and detects **convergence**: multiple weak signals aligning on the same company within a time window.

## What It Does

1. **Ingests** data from public and commercial sources (government contracts, patents, job postings, SEC filings, options positioning, short interest, GitHub activity, regulatory filings, and more).
2. **Normalizes** everything to a shared entity model — every signal maps to a company, ticker, sector, and supply-chain relationships.
3. **Scores** each signal for surprise/abnormality relative to that company's baseline.
4. **Correlates** signals across datasets and detects convergence events.
5. **Alerts** the user when convergence crosses a threshold, with full provenance (every underlying data point linked to its source).

## Repository Layout

```
market-signals-platform/
├── README.md                  # This file
├── docs/
│   ├── DATA_SOURCES.md        # All 20 signal areas mapped to concrete sources, cost, and feasibility
│   ├── ARCHITECTURE.md        # System design: ingestion, entity graph, scoring, correlation, alerting
│   └── ROADMAP.md             # Phased build plan, starting with free data sources
├── msp/                       # Python package (Phase 0)
│   ├── config.py              # Env-driven settings (DB URL, SEC user agent)
│   ├── db.py                  # SQLAlchemy models: companies, raw_events, insider_transactions, signals
│   ├── entities.py            # Company loader (SEC CIK<->ticker mapping)
│   ├── ingest/
│   │   ├── edgar.py           # Rate-limited EDGAR HTTP client
│   │   └── form4.py           # Form 4 (insider transactions) connector
│   ├── signals/
│   │   └── insider_cluster.py # Cluster-buy detection
│   └── cli.py                 # Command-line interface
└── tests/
```

## Quick Start (Phase 0)

```bash
cd market-signals-platform
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m msp.cli init-db
python -m msp.cli load-companies          # ~10k companies from SEC's free mapping
python -m msp.cli ingest-form4 --days-back 7   # pull a week of insider filings
python -m msp.cli detect-clusters              # store cluster-buy signals
python -m msp.cli report                       # print current cluster buys
```

Run tests with `pip install pytest && python -m pytest tests/ -v`.

## Guiding Principles

- **Free and public data first.** A surprising amount of the edge described here is available at zero cost (SEC EDGAR, USASpending.gov, USPTO, FINRA, GitHub). Prove the correlation engine works before paying for commercial feeds.
- **Provenance always.** Every alert must trace back to raw source documents. No black boxes.
- **Signals, not predictions.** The platform surfaces "something is happening here — look closer." It does not make buy/sell calls.
- **Baseline-relative scoring.** A signal only matters if it's abnormal *for that company*. 50 new job postings is noise for Amazon and a five-alarm signal for a 200-person company.

## Start Here

- [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) — what data exists, where to get it, and what it costs
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how the system fits together
- [docs/ROADMAP.md](docs/ROADMAP.md) — build order and milestones
- [docs/MULTI_DATASET_BLENDS.md](docs/MULTI_DATASET_BLENDS.md) — institutional signal-blend playbooks (SAR+IoT, patents+GitHub, jet tracking+flows) mapped to our tiers
