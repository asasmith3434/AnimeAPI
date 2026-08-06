# Multi-Dataset Blends: Next-Generation Signal Combinations

Traditional alternative data relies on a single source (e.g., a standard credit card panel). Next-generation datasets derive their edge by **cross-referencing disparate physical, digital, and structural signals** to catch informational mismatches weeks before they materialize in financial statements.

This document captures three institutional-grade blend patterns, the evidence behind them, and — most importantly — how each maps onto this platform's tiers and roadmap. The blends are the strongest available validation of the platform's core thesis: convergence across independent signal families beats any single indicator.

## Comparative Overview

| Blend | Primary Target Sector | Typical Lead Time vs. Consensus | Baseline Evidence |
|---|---|---|---|
| 1. InSAR radar + industrial IoT telemetry | Energy, commodities, heavy industrials | 2–4 weeks | Ursa Space Systems & SpaceKnow benchmarks: SAR-based oil inventory/crude storage tracking; adding grid/telemetry data reportedly cuts false-positive "shadow" signals from satellite noise by over 35% |
| 2. GenAI patent scoring + developer code activity | Technology, micro/mid-cap biotech | 1–3 months | Sparkline Capital thematic studies: NLP/ML patent analysis; pairing patent breadth with GitHub forks and package downloads forecast enterprise SaaS revenue inflections ~90 days out |
| 3. Corporate jet telemetry + blockchain ledgers | Financials (M&A), multi-sector large cap | 3–10 days | Oxford University corporate jet study: anomalous corporate flight logs to key hubs (Teterboro, Luton) showed statistically significant predictive power for impending M&A announcements |

---

## Test Case 1: InSAR & Satellite Intelligence

**The problem.** Early quant models relied purely on optical satellite imagery (counting factory parking-lot cars, measuring oil-tank shadow lengths). Prolonged cloud cover over key hubs (US Gulf Coast, North Sea) produced "data blackout" periods lasting weeks.

**The evidence.** Providers like SpaceKnow and Ursa Space Systems adopted Synthetic Aperture Radar (SAR), which penetrates clouds and darkness. Radar imagery detects millimeter-level structural changes and inventory build-ups in real time.

**The alpha result.** Funds blending SAR with local IoT power-grid telemetry (factory heat and electricity surge anomalies) map commodity supply curves weeks before the EIA or traditional agencies publish official metrics.

**Platform mapping:**

| Component | Source | Tier |
|---|---|---|
| SAR imagery / InSAR analytics | Ursa Space, SpaceKnow, ICEYE | 4 — institutional; document, don't build |
| Electricity demand & grid telemetry | EIA hourly grid monitor API | **1 — free, already in DATA_SOURCES §18** |
| Official inventory baselines | EIA weekly petroleum/gas reports | **1 — free** |

*Realistic v1 play:* we can't afford SAR, but the **free half of this blend** (EIA hourly electricity demand + weekly inventories) still leads official monthly narratives and earnings commentary. Regional grid-demand anomalies also double as a datacenter-buildout proxy for tech/utilities.

## Test Case 2: Corporate Jet Tracking & M&A Arbitrage

**The problem.** M&A generates explosive alpha, but predicting deals via news/sentiment lands traders in rumor-mill gray areas.

**The evidence.** Academic and institutional work — most notably the widely cited Oxford flight-path study — tracked tail numbers and ADS-B transponder pings of corporate aircraft. Anomalous private-jet flights to remote corporate headquarters correlated significantly with subsequent M&A disclosures.

**Modern integration.** Institutions overlay ledger/flow tracking: acquirer's jet near a target's campus *plus* unusual institutional liquidity reallocation triggers a position change 3–10 days before a press release.

**Platform mapping:**

| Component | Source | Tier |
|---|---|---|
| ADS-B flight data | OpenSky Network (free for research), ADS-B Exchange (unfiltered; paid API), adsb.fi | 2–3 |
| Tail number → owner | FAA aircraft registry (free bulk download) | 1 |
| Owner LLC → public company | Entity resolution (our alias table) + curated mapping | 2 — our own work |
| M&A confirmation / labels | SEC 8-K (Item 1.01) and DEFM14A filings | 1 — already planned |

*Caveats to encode:* many corporate tails opt into FAA LADD blocking and PIA (rotating anonymous transponder codes), so coverage is partial and biased toward less-sophisticated operators — treat as a **supporting** signal, never standalone. Aircraft are often owned through trustee LLCs (e.g., bank trustees in Delaware/Utah), so the tail→ticker mapping is a genuine entity-resolution project — the same alias-table machinery we're already building for contract recipients and patent assignees.

## Test Case 3: AI Patent Scoring + Open-Source Developer Activity

**The problem.** Corporate PR inflates "AI capabilities" during earnings calls, tricking naive sentiment models ("tech-washing").

**The evidence.** In Sparkline Capital-style thematic studies, LLMs algorithmically score patent filings for genuine technical novelty and defensive strength rather than generic keywords.

**The alpha result.** A high-scoring patent filing *plus* a simultaneous spike in the company's open-source footprint (GitHub forks, package downloads, active contributors) signals genuine adoption. The blend filters out tech-washing and isolates true technological leaders months before backward-looking fundamentals catch up.

**Platform mapping:**

| Component | Source | Tier |
|---|---|---|
| Patent filings, claims text, citations | USPTO PatentsView | **1 — already in roadmap (Phase 1)** |
| LLM novelty scoring of claims | Our own pipeline on top of PatentsView text | 2 — compute cost only |
| GitHub org activity | GH Archive / GitHub API | **1 — already in roadmap (Phase 1)** |
| Package downloads | npm/PyPI/crates.io APIs | **1 — already in DATA_SOURCES §20** |

*This is the highest-priority blend for us:* every ingredient is free and both connectors are already scheduled in Phase 1. The blend itself is exactly what the Phase 2 convergence engine computes (patents family × OSINT family firing together). LLM-based novelty scoring is a natural Phase 4 enhancement on top of raw filing counts.

---

## How Blends Fit the Architecture

Blends are **not** a new subsystem. They are convergence rules over signal families we already produce:

1. Each blend component is an ordinary connector emitting scored signals (`patents`, `osint`, `flows`, `movement`).
2. A blend is a *named convergence pattern*: specific families, co-firing window, and directionality (e.g., `patent_novelty↑ + github_activity↑ within 60d → bullish tech-adoption`).
3. Blend hits get boosted weight in the convergence score and a labeled explanation in the UI ("Tech-adoption blend fired: high-novelty patent 2026-07-14 + 3.2σ GitHub activity spike").

This keeps the correlation engine generic while letting us encode institutional playbooks explicitly.

## Build Priority

1. **Now (validates Phase 1–2 as planned):** patents + GitHub/package blend — all free, both connectors already scheduled.
2. **Phase 4 candidate:** corporate jet tracking — OpenSky/adsb.fi feed + FAA registry entity resolution; pairs with 8-K M&A labels we'll already have. Moderate effort, partial coverage, high novelty.
3. **Free-half only:** EIA grid/inventory anomalies (the accessible half of the InSAR blend) — cheap addition to the `flows` family.
4. **Documented, not built:** SAR imagery, blockchain institutional-flow overlays — institutional pricing or weak public-data analogs; revisit only if the platform earns a data budget.
