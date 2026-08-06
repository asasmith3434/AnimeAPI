# Data Sources

Every signal area from the original research note, mapped to concrete sources, access method, and cost. Sources are grouped into **feasibility tiers** so the build can start free and add paid feeds only where they prove their worth.

- **Tier 1 — Free & programmatic.** Public APIs or bulk downloads. Build these first.
- **Tier 2 — Free but requires scraping/parsing effort.** Public data without a clean API.
- **Tier 3 — Cheap commercial.** Retail-priced APIs (roughly $10–$300/mo).
- **Tier 4 — Institutional.** Expensive or access-restricted. Document, don't build initially.

---

## 1. Dealer Positioning & Market Microstructure

Market makers hedge the options they've sold; that hedging amplifies or suppresses price moves.

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Gamma Exposure (GEX), Vanna, Charm | Compute from options chain (OI × greeks per strike) | 3 | Needs an options chain feed: CBOE delayed data, Polygon.io, Tradier, or ORATS |
| Options chain + open interest | Polygon.io (~$30–200/mo), Tradier (free w/ brokerage), CBOE DataShop | 3 | OCC also publishes daily aggregate volume/OI for free |
| Dealer positioning estimates | SqueezeMetrics (GEX/DIX), SpotGamma, Menthor Q | 3–4 | Prebuilt if we don't want to compute ourselves |
| Order book imbalance | Polygon/Databento L2 feeds | 3–4 | High volume; defer until the platform needs intraday granularity |

**Build note:** GEX per ticker is computable from a daily options chain snapshot — a well-understood formula over open interest and strike-level gamma. This is a good Tier-3 candidate once the free tiers are live.

## 2. Treasury Market Plumbing

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Reverse Repo (RRP) balances | NY Fed API / FRED series `RRPONTSYD` | 1 | Daily, clean JSON |
| Treasury General Account (TGA) | Treasury FiscalData API (`/v1/accounting/dts`) | 1 | Daily Treasury Statement |
| SOFR | NY Fed API / FRED `SOFR` | 1 | |
| Treasury auction results | TreasuryDirect API (`treasurydirect.gov/TA_WS`) | 1 | Bid-to-cover, tails, dealer take-down |
| Fed balance sheet / QT-QE | FRED `WALCL` (H.4.1 release) | 1 | Weekly |
| Bank reserves | FRED `WRESBAL` | 1 | |

**Build note:** This whole section is Tier 1 — FRED + Treasury + NY Fed APIs are free and reliable. Combine into a single "net dollar liquidity" composite (Fed balance sheet − TGA − RRP), a widely watched macro backdrop signal.

## 3. Dollar Liquidity

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Dollar swap line usage | NY Fed central bank liquidity swaps data | 1 | Weekly |
| Cross-currency basis swaps | BIS data (quarterly), Bloomberg for live | 4 | Live basis data is institutional; BIS gives the slow-moving picture |
| DXY / dollar index | FRED `DTWEXBGS`, or any market data API | 1 | |
| Eurodollar/offshore dollar conditions | Proxy via SOFR-OIS spreads, FRA-OIS | 2–4 | Hard to get clean retail access; treat as macro context |

## 4. Prime Broker Data

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Hedge fund gross/net leverage | OFR Hedge Fund Monitor, Fed's SCOOS survey | 1 | Quarterly, lagged — directional context only |
| Hedge fund crowding | 13F filings via SEC EDGAR | 1 | Quarterly with 45-day lag; compute overlap/crowding ourselves |
| Broker margin debt | FINRA margin statistics (monthly) | 1 | |
| Real-time PB flow | Goldman/Morgan Stanley PB notes | 4 | Not accessible; the free proxies above are the realistic version |

## 5. Securities Lending

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Short interest | FINRA equity short interest (bi-monthly, free) | 1 | |
| Fails to Deliver (FTDs) | SEC FTD data (free bulk download, 2×/month) | 1 | |
| Borrow rate / utilization / shares available | Interactive Brokers FTP (free w/ account), iBorrowDesk, S3 Partners / Ortex | 2–3 | IBKR publishes borrowable shares + indicative rates for free |
| Daily short volume | FINRA Reg SHO daily files | 1 | Daily short volume ratio per ticker |

## 6. Dark Pools

| Signal | Source | Tier | Notes |
|---|---|---|---|
| ATS (dark pool) volume by ticker | FINRA OTC Transparency data | 1 | Free, weekly, per-venue per-ticker |
| Dark pool prints / block trades | Quiver Quant, Unusual Whales, Intrinio | 3 | For daily granularity |
| Dark pool sentiment (DIX) | SqueezeMetrics (free daily DIX/GEX csv) | 1 | |

## 7. ETF Creation & Redemption

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Fund flows | ETF.com, Farside (BTC ETFs), issuer sites | 2 | Scraping; ICI publishes weekly aggregate flows free |
| Shares outstanding changes | Issuer daily files (iShares/SPDR publish holdings + SO daily) | 2 | SO delta = creation/redemption activity |
| ETF holdings | Issuer daily holdings files, SEC N-PORT | 1–2 | Enables "which stocks feel ETF flow pressure" |

## 8. Index Rebalancing

| Signal | Source | Tier | Notes |
|---|---|---|---|
| S&P 500/400/600 changes | S&P press releases (RSS/scrape) | 2 | Announced ~5 days before effective |
| Russell reconstitution | FTSE Russell published calendar + preliminary lists | 2 | Annual June event, highly forecastable |
| Nasdaq-100 reconstitution | Nasdaq press releases | 2 | December |
| MSCI reviews | MSCI announcement calendar | 2 | Quarterly |

**Build note:** an event-calendar ingester + announcement scraper covers this whole area.

## 9. Corporate Bond Markets

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Credit spreads (IG/HY) | FRED: `BAMLH0A0HYM2` (HY OAS), `BAMLC0A0CM` (IG OAS) | 1 | Daily, free |
| Per-bond trades | FINRA TRACE (free with registration, bulk) | 2 | Company-level credit deterioration signals |
| New issuance | SEC EDGAR (424B prospectuses, FWP) | 1 | |

## 10. Credit Default Swaps

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Single-name CDS spreads | S&P/ICE/Bloomberg | 4 | Institutional only |
| CDS indices (CDX IG/HY) | Occasionally mirrored on FRED/news; otherwise T4 | 2–4 | Use HY OAS from FRED as the free proxy |

## 11. Supply Chain & Shipping Data

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Container import volume | Port of LA/Long Beach public stats (monthly + POLA "Signal" forward-looking) | 2 | |
| Freight rates | Freightos Baltic Index (weekly, free headline), Drewry WCI | 2 | |
| Rail shipments | AAR weekly rail traffic (free) | 2 | |
| Trucking | Cass Freight Index (monthly, free) | 2 | |
| Ship tracking / satellite | MarineTraffic, Spire, Planet | 4 | |
| US import bills of lading | ImportGenius, Panjiva | 3–4 | Company-specific import volumes — powerful but paid |

## 12. Alternative Data

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Web traffic | Similarweb (limited free), Cloudflare Radar (free) | 2–3 | |
| App downloads/rankings | App store top-chart scraping, Sensor Tower | 2–4 | |
| Credit card panels | Bloomberg Second Measure, Yodlee | 4 | Institutional |
| Job postings | See §19 — free | 1–2 | |
| Energy consumption | EIA API (free) | 1 | |

## 13. Government Procurement

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Federal contract awards | **USASpending.gov API** (free, comprehensive) | 1 | Award amount, agency, recipient, NAICS |
| Pre-award opportunities | **SAM.gov API** (free) | 1 | RFPs before award = earlier signal |
| Defense contracts | defense.gov daily contract announcements (scrape/RSS) | 2 | Daily, >$7.5M contracts |
| State RFPs | Per-state portals | 2 | Fragmented; defer |

**Build note:** USASpending + SAM.gov are among the highest-value free sources on this list. Entity resolution (recipient name → public company) is the main work.

## 14. Supply Chain Mapping

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Customer/supplier disclosures | 10-K filings ("customer concentration" language) via EDGAR full-text search | 1–2 | NLP extraction |
| Relationship datasets | FactSet Supply Chain, Bloomberg SPLC | 4 | |
| Bills of lading | ImportGenius/Panjiva | 3–4 | Empirical shipper→consignee links |

**Build note:** start with a manually curated graph for a few high-interest ecosystems (e.g., NVDA: TSMC → ASML → chemicals/packaging suppliers), then automate extraction from 10-Ks.

## 15. Insider Networks & Ecosystems

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Insider transactions | SEC Form 4 via EDGAR (free, near-real-time) | 1 | Cluster buys are the classic signal |
| Executive hiring/departures | 8-K filings (Item 5.02) via EDGAR | 1 | |
| Job openings by function | Company career pages, Greenhouse/Lever public APIs | 2 | |
| Congressional trading | Senate/House disclosure sites; Quiver Quant API | 2–3 | |

## 16. Patent Activity

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Patent filings & grants | **USPTO PatentsView API / bulk data** (free) | 1 | Assignee, inventors, CPC classes, citations |
| Global filings | EPO OPS API (free tier), WIPO | 2 | |
| Citation growth / tech clustering | Computed from PatentsView | 1 | Our own derived signal |

## 17. Regulatory Filings Beyond SEC

| Signal | Source | Tier | Notes |
|---|---|---|---|
| FDA approvals/submissions | openFDA API, FDA calendars (PDUFA dates) | 1–2 | Biotech catalysts |
| FCC filings | FCC ECFS API (free) | 1 | Spectrum, device certifications (new hardware leaks here) |
| FAA certifications | FAA registry + certification data | 2 | |
| DOE/ARPA-E grants | Grants.gov API, DOE announcements | 1–2 | |
| EPA permits | EPA Envirofacts API | 2 | |
| FERC filings | FERC eLibrary | 2 | Energy/utilities |
| Clinical trials | ClinicalTrials.gov API (free) | 1 | Trial starts/completions/terminations |

## 18. Commodity Flow Data

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Oil storage, refinery throughput | EIA API (free, weekly) | 1 | |
| Natural gas / LNG exports | EIA + DOE LNG reports | 1 | |
| Electricity demand | EIA hourly grid monitor API | 1 | Also a datacenter-buildout proxy |
| Pipeline flows | Genscape/Wood Mackenzie | 4 | |
| Ag flows | USDA reports (free) | 1 | |

## 19. Labor Market Signals

| Signal | Source | Tier | Notes |
|---|---|---|---|
| Job postings per company | Career-page scraping (Greenhouse/Lever/Workday JSON endpoints) | 2 | Hiring velocity = expansion signal |
| Layoffs | WARN Act notices (per-state, scrapable), layoffs.fyi | 2 | WARN filings precede press coverage |
| H-1B / visa filings | DOL LCA disclosure files (free, quarterly) | 1 | Reveals which roles companies invest in |
| Aggregate labor data | BLS API (free) | 1 | Macro backdrop |
| Glassdoor/review trends | Scraping (ToS-sensitive) or Thinknum/Revelio | 3–4 | |

## 20. Open Source Intelligence (OSINT)

| Signal | Source | Tier | Notes |
|---|---|---|---|
| GitHub activity | GitHub REST/GraphQL API + GH Archive (free BigQuery dataset) | 1 | Commits/releases/hiring of maintainers for a company's orgs |
| Domain registrations | Zone file access (ICANN CZDS, free), WhoisXML | 2–3 | New product-name domains |
| Certificate Transparency logs | crt.sh, Certstream (free) | 1 | New subdomains reveal unlaunched products |
| Mobile app updates | App store scraping | 2 | Version-note diffing |
| Package releases | npm/PyPI/crates.io APIs (free) | 1 | New SDKs precede product launches |
| DNS changes | Passive DNS (SecurityTrails free tier) | 2–3 | |

---

## Priority Summary

**Highest signal-per-dollar (build first):**
1. USASpending.gov + SAM.gov (government contracts) — Tier 1
2. SEC EDGAR: Form 4 insider transactions, 8-K, 13F, full-text search — Tier 1
3. USPTO PatentsView (patents) — Tier 1
4. FINRA short interest + SEC FTDs + Reg SHO daily short volume — Tier 1
5. GitHub/OSINT (GH Archive, Certificate Transparency, package registries) — Tier 1
6. Job postings + WARN notices + H-1B disclosures — Tier 1–2
7. Macro liquidity composite (FRED/NY Fed/Treasury) — Tier 1
8. FINRA ATS dark pool weekly volumes + free DIX/GEX — Tier 1

**First paid additions (once correlation engine proves out):**
- Options chain feed for computed GEX/vanna/charm (Polygon or Tradier)
- Dark pool prints (Quiver/Unusual Whales)
- Bills of lading (ImportGenius) if supply-chain signals show value
