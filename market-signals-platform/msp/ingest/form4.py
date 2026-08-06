"""EDGAR Form 4 (insider transactions) connector.

Flow:
1. Fetch the EDGAR daily form index for a date.
2. Filter to Form 4 filings.
3. Fetch each full submission, extract the embedded <ownershipDocument> XML.
4. Parse issuer, reporting owners, and non-derivative transactions.
5. Store an immutable raw event plus normalized transaction rows.

Idempotent: filings are deduped on accession number, so re-running a day is safe.
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select

from ..db import InsiderTransaction, RawEvent, get_session
from .edgar import EdgarClient

SOURCE_ID = "edgar_form4"
ARCHIVES_BASE = "https://www.sec.gov/Archives/"


@dataclass
class IndexEntry:
    form_type: str
    company_name: str
    cik: int
    date_filed: date
    file_path: str  # e.g. edgar/data/320193/0000320193-26-000055.txt

    @property
    def accession(self) -> str:
        return self.file_path.rsplit("/", 1)[-1].removesuffix(".txt")

    @property
    def url(self) -> str:
        return ARCHIVES_BASE + self.file_path


@dataclass
class Owner:
    cik: int | None
    name: str
    is_director: bool = False
    is_officer: bool = False
    officer_title: str | None = None


@dataclass
class Transaction:
    transaction_date: date
    code: str
    shares: float | None
    price_per_share: float | None
    acquired_disposed: str | None


@dataclass
class ParsedForm4:
    issuer_cik: int
    issuer_name: str
    issuer_ticker: str | None
    owners: list[Owner] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)


def daily_index_url(day: date) -> str:
    quarter = (day.month - 1) // 3 + 1
    return (
        f"https://www.sec.gov/Archives/edgar/daily-index/"
        f"{day.year}/QTR{quarter}/form.{day:%Y%m%d}.idx"
    )


def parse_daily_index(text: str, form_type: str = "4") -> list[IndexEntry]:
    entries = []
    in_body = False
    for line in text.splitlines():
        if line.startswith("---"):
            in_body = True
            continue
        if not in_body or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 5 or parts[0] != form_type:
            continue
        file_path, date_str, cik = parts[-1], parts[-2], parts[-3]
        try:
            entries.append(
                IndexEntry(
                    form_type=parts[0],
                    company_name=" ".join(parts[1:-3]),
                    cik=int(cik),
                    date_filed=datetime.strptime(date_str, "%Y%m%d").date(),
                    file_path=file_path,
                )
            )
        except ValueError:
            continue
    return entries


def extract_ownership_xml(submission_text: str) -> str | None:
    """Pull the <ownershipDocument> XML block out of a full-submission .txt file."""
    for match in re.finditer(r"<XML>(.*?)</XML>", submission_text, re.DOTALL):
        block = match.group(1).strip()
        if "<ownershipDocument" in block:
            return block
    return None


def _text(node, path: str) -> str | None:
    found = node.find(path)
    if found is not None and found.text is not None:
        return found.text.strip()
    return None


def _value(node, path: str) -> str | None:
    """Form 4 wraps most values as <element><value>x</value></element>."""
    return _text(node, path + "/value") or _text(node, path)


def _flag(node, path: str) -> bool:
    return (_value(node, path) or "").lower() in ("1", "true")


def _number(node, path: str) -> float | None:
    raw = _value(node, path)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def parse_form4(xml_text: str) -> ParsedForm4:
    root = ET.fromstring(xml_text)

    issuer = root.find("issuer")
    parsed = ParsedForm4(
        issuer_cik=int(_text(issuer, "issuerCik")),
        issuer_name=_text(issuer, "issuerName") or "",
        issuer_ticker=(_text(issuer, "issuerTradingSymbol") or "").upper() or None,
    )

    for owner_node in root.findall("reportingOwner"):
        ident = owner_node.find("reportingOwnerId")
        relationship = owner_node.find("reportingOwnerRelationship")
        cik_raw = _text(ident, "rptOwnerCik") if ident is not None else None
        parsed.owners.append(
            Owner(
                cik=int(cik_raw) if cik_raw else None,
                name=(_text(ident, "rptOwnerName") if ident is not None else None) or "",
                is_director=_flag(relationship, "isDirector") if relationship is not None else False,
                is_officer=_flag(relationship, "isOfficer") if relationship is not None else False,
                officer_title=_value(relationship, "officerTitle") if relationship is not None else None,
            )
        )

    for txn_node in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        date_raw = _value(txn_node, "transactionDate")
        code = _text(txn_node, "transactionCoding/transactionCode")
        if not date_raw or not code:
            continue
        parsed.transactions.append(
            Transaction(
                transaction_date=datetime.strptime(date_raw, "%Y-%m-%d").date(),
                code=code,
                shares=_number(txn_node, "transactionAmounts/transactionShares"),
                price_per_share=_number(txn_node, "transactionAmounts/transactionPricePerShare"),
                acquired_disposed=_value(
                    txn_node, "transactionAmounts/transactionAcquiredDisposedCode"
                ),
            )
        )

    return parsed


def fetch_index_entries(client: EdgarClient, day: date) -> list[IndexEntry]:
    """Form 4 entries from the daily index; empty on weekends/holidays (404)."""
    import requests

    try:
        text = client.get_text(daily_index_url(day))
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return []
        raise
    return parse_daily_index(text)


def ingest_day(day: date, limit: int | None = None, client: EdgarClient | None = None) -> dict:
    """Ingest all Form 4 filings for one day. Returns counters."""
    client = client or EdgarClient()
    entries = fetch_index_entries(client, day)
    if limit:
        entries = entries[:limit]

    stats = {"index_entries": len(entries), "ingested": 0, "skipped_existing": 0,
             "no_xml": 0, "parse_errors": 0, "transactions": 0}

    with get_session() as session:
        existing = set(
            session.scalars(
                select(RawEvent.source_native_id).where(RawEvent.source_id == SOURCE_ID)
            )
        )
        for entry in entries:
            # The daily index lists one row per filer, so a Form 4 appears
            # under both the issuer's CIK and each reporting owner's CIK.
            if entry.accession in existing:
                stats["skipped_existing"] += 1
                continue
            existing.add(entry.accession)

            submission = client.get_text(entry.url)
            xml_text = extract_ownership_xml(submission)
            if xml_text is None:
                stats["no_xml"] += 1
                continue
            try:
                parsed = parse_form4(xml_text)
            except (ET.ParseError, ValueError, TypeError):
                stats["parse_errors"] += 1
                continue

            raw = RawEvent(
                source_id=SOURCE_ID,
                source_native_id=entry.accession,
                event_time=datetime.combine(entry.date_filed, datetime.min.time()),
                document_url=entry.url,
                payload={
                    "issuer_cik": parsed.issuer_cik,
                    "issuer_name": parsed.issuer_name,
                    "issuer_ticker": parsed.issuer_ticker,
                    "owners": [vars(o) for o in parsed.owners],
                    "transactions": [
                        {**vars(t), "transaction_date": t.transaction_date.isoformat()}
                        for t in parsed.transactions
                    ],
                },
            )
            session.add(raw)
            session.flush()  # get raw.id for provenance links

            for owner in parsed.owners:
                for txn in parsed.transactions:
                    session.add(
                        InsiderTransaction(
                            raw_event_id=raw.id,
                            accession=entry.accession,
                            issuer_cik=parsed.issuer_cik,
                            issuer_name=parsed.issuer_name,
                            issuer_ticker=parsed.issuer_ticker,
                            owner_cik=owner.cik,
                            owner_name=owner.name,
                            is_director=owner.is_director,
                            is_officer=owner.is_officer,
                            officer_title=owner.officer_title,
                            transaction_date=txn.transaction_date,
                            transaction_code=txn.code,
                            acquired_disposed=txn.acquired_disposed,
                            shares=txn.shares,
                            price_per_share=txn.price_per_share,
                            filed_at=datetime.combine(entry.date_filed, datetime.min.time()),
                        )
                    )
                    stats["transactions"] += 1

            stats["ingested"] += 1
            session.commit()

    return stats
