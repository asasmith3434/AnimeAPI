from datetime import date, datetime

import pytest

from msp import db
from msp.db import InsiderTransaction, RawEvent, Signal, get_session
from msp.signals.insider_cluster import find_cluster_buys, store_signals

AS_OF = date(2026, 8, 5)


def _txn(issuer_cik, issuer_name, ticker, owner, day, code="P", shares=1000, price=10.0,
         raw_event_id=1, acquired="A"):
    return InsiderTransaction(
        raw_event_id=raw_event_id,
        accession=f"acc-{issuer_cik}-{owner}-{day}",
        issuer_cik=issuer_cik,
        issuer_name=issuer_name,
        issuer_ticker=ticker,
        owner_cik=None,
        owner_name=owner,
        transaction_date=day,
        transaction_code=code,
        acquired_disposed=acquired,
        shares=shares,
        price_per_share=price,
        filed_at=datetime(2026, 8, 5),
    )


@pytest.fixture(autouse=True)
def clean_db():
    db.init_db()
    with get_session() as session:
        session.query(InsiderTransaction).delete()
        session.query(RawEvent).delete()
        session.query(Signal).delete()
        session.commit()
    yield


def seed(transactions):
    with get_session() as session:
        session.add(RawEvent(source_id="test", source_native_id="e1", payload={}))
        session.add_all(transactions)
        session.commit()


def test_detects_cluster_of_two_buyers():
    seed([
        _txn(100, "Acme Corp", "ACME", "ALICE", date(2026, 7, 30)),
        _txn(100, "Acme Corp", "ACME", "BOB", date(2026, 8, 2)),
        # Single buyer elsewhere: not a cluster.
        _txn(200, "Solo Inc", "SOLO", "CAROL", date(2026, 8, 1)),
    ])
    clusters = find_cluster_buys(as_of=AS_OF, window_days=14, min_total_value=0)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster.issuer_cik == 100
    assert cluster.buyer_names == ["ALICE", "BOB"]
    assert cluster.total_value == 2 * 1000 * 10.0
    assert cluster.first_buy == date(2026, 7, 30)
    assert cluster.last_buy == date(2026, 8, 2)


def test_ignores_sales_and_awards():
    seed([
        _txn(100, "Acme Corp", "ACME", "ALICE", date(2026, 8, 1), code="S", acquired="D"),
        _txn(100, "Acme Corp", "ACME", "BOB", date(2026, 8, 2), code="A"),
        _txn(100, "Acme Corp", "ACME", "CAROL", date(2026, 8, 3)),
    ])
    assert find_cluster_buys(as_of=AS_OF, window_days=14) == []


def test_respects_window():
    seed([
        _txn(100, "Acme Corp", "ACME", "ALICE", date(2026, 6, 1)),
        _txn(100, "Acme Corp", "ACME", "BOB", date(2026, 8, 2)),
    ])
    assert find_cluster_buys(as_of=AS_OF, window_days=14) == []


def test_min_value_filter():
    seed([
        _txn(100, "Tiny Corp", "TINY", "ALICE", date(2026, 8, 1), shares=10, price=5.0),
        _txn(100, "Tiny Corp", "TINY", "BOB", date(2026, 8, 2), shares=10, price=5.0),
    ])
    assert find_cluster_buys(as_of=AS_OF, window_days=14, min_total_value=50_000) == []
    assert len(find_cluster_buys(as_of=AS_OF, window_days=14, min_total_value=0)) == 1


def test_store_signals_upserts():
    seed([
        _txn(100, "Acme Corp", "ACME", "ALICE", date(2026, 7, 30)),
        _txn(100, "Acme Corp", "ACME", "BOB", date(2026, 8, 2)),
    ])
    clusters = find_cluster_buys(as_of=AS_OF, window_days=14, min_total_value=0)
    assert store_signals(clusters) == 1
    # Re-running stores nothing new but keeps the signal current.
    assert store_signals(clusters) == 0

    with get_session() as session:
        signals = session.query(Signal).all()
        assert len(signals) == 1
        assert signals[0].company_cik == 100
        assert signals[0].value == 2
        assert signals[0].details["issuer_ticker"] == "ACME"
