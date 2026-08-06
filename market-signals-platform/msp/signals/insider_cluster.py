"""Insider cluster-buy detection.

The classic strong insider signal: multiple distinct insiders making
open-market purchases (transaction code P) of the same company within a
short window. One insider buying can mean anything; three insiders buying
the same week rarely happens by accident.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select

from ..db import InsiderTransaction, Signal, get_session

SIGNAL_FAMILY = "insider"
SIGNAL_TYPE = "cluster_buy"


@dataclass
class ClusterBuy:
    issuer_cik: int
    issuer_name: str
    issuer_ticker: str | None
    buyer_names: list[str]
    total_shares: float
    total_value: float
    first_buy: date
    last_buy: date
    raw_event_ids: list[int]

    @property
    def n_buyers(self) -> int:
        return len(self.buyer_names)


def find_cluster_buys(
    as_of: date,
    window_days: int = 14,
    min_buyers: int = 2,
    min_total_value: float = 50_000,
) -> list[ClusterBuy]:
    """Find companies with >= min_buyers distinct open-market insider buyers
    in the window ending at as_of.

    min_total_value filters out token purchases that carry no information.
    """
    window_start = as_of - timedelta(days=window_days)

    with get_session() as session:
        rows = session.scalars(
            select(InsiderTransaction).where(
                InsiderTransaction.transaction_code == "P",
                InsiderTransaction.acquired_disposed == "A",
                InsiderTransaction.transaction_date >= window_start,
                InsiderTransaction.transaction_date <= as_of,
            )
        ).all()

        by_issuer: dict[int, list[InsiderTransaction]] = {}
        for row in rows:
            by_issuer.setdefault(row.issuer_cik, []).append(row)

        clusters = []
        for issuer_cik, txns in by_issuer.items():
            buyers = {t.owner_name for t in txns if t.owner_name}
            if len(buyers) < min_buyers:
                continue
            total_value = sum(t.total_value or 0 for t in txns)
            if total_value < min_total_value:
                continue
            dates = [t.transaction_date for t in txns]
            clusters.append(
                ClusterBuy(
                    issuer_cik=issuer_cik,
                    issuer_name=txns[0].issuer_name,
                    issuer_ticker=txns[0].issuer_ticker,
                    buyer_names=sorted(buyers),
                    total_shares=sum(t.shares or 0 for t in txns),
                    total_value=total_value,
                    first_buy=min(dates),
                    last_buy=max(dates),
                    raw_event_ids=sorted({t.raw_event_id for t in txns}),
                )
            )

        clusters.sort(key=lambda c: (c.n_buyers, c.total_value), reverse=True)
        return clusters


def store_signals(clusters: list[ClusterBuy]) -> int:
    """Upsert cluster-buy signals; event_date is the latest buy in the cluster."""
    stored = 0
    with get_session() as session:
        for cluster in clusters:
            existing = session.scalar(
                select(Signal).where(
                    Signal.signal_family == SIGNAL_FAMILY,
                    Signal.signal_type == SIGNAL_TYPE,
                    Signal.company_cik == cluster.issuer_cik,
                    Signal.event_date == cluster.last_buy,
                )
            )
            details = {
                "issuer_name": cluster.issuer_name,
                "issuer_ticker": cluster.issuer_ticker,
                "buyers": cluster.buyer_names,
                "total_shares": cluster.total_shares,
                "total_value": cluster.total_value,
                "first_buy": cluster.first_buy.isoformat(),
                "last_buy": cluster.last_buy.isoformat(),
            }
            if existing:
                existing.value = cluster.n_buyers
                existing.details = details
                existing.raw_event_ids = cluster.raw_event_ids
            else:
                session.add(
                    Signal(
                        company_cik=cluster.issuer_cik,
                        signal_family=SIGNAL_FAMILY,
                        signal_type=SIGNAL_TYPE,
                        event_date=cluster.last_buy,
                        value=cluster.n_buyers,
                        details=details,
                        raw_event_ids=cluster.raw_event_ids,
                    )
                )
                stored += 1
        session.commit()
    return stored
