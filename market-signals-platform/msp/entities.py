"""Company entity loading.

Seeds the companies table from SEC's free CIK<->ticker<->name mapping:
https://www.sec.gov/files/company_tickers.json
"""

from sqlalchemy import select

from .db import Company, get_session
from .ingest.edgar import EdgarClient

COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def load_companies(client: EdgarClient | None = None) -> int:
    client = client or EdgarClient()
    data = client.get_json(COMPANY_TICKERS_URL)

    loaded = 0
    with get_session() as session:
        by_cik = {c.cik: c for c in session.scalars(select(Company))}
        seen_this_run: set[int] = set()

        # File format: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
        # A CIK can appear multiple times (share classes, e.g. GOOGL/GOOG);
        # the file lists the primary ticker first, so keep the first occurrence.
        for entry in data.values():
            cik = int(entry["cik_str"])
            if cik in seen_this_run:
                continue
            seen_this_run.add(cik)

            ticker = entry["ticker"].upper()
            name = entry["title"]
            if cik in by_cik:
                by_cik[cik].ticker = ticker
                by_cik[cik].name = name
            else:
                session.add(Company(cik=cik, ticker=ticker, name=name))
                loaded += 1
        session.commit()
    return loaded


def ticker_for_cik(session, cik: int) -> str | None:
    return session.scalar(select(Company.ticker).where(Company.cik == cik))
