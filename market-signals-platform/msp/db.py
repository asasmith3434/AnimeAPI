from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from . import config


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    """Canonical company entity, seeded from SEC's CIK<->ticker mapping."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cik: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    ticker: Mapped[str | None] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(256))


class RawEvent(Base):
    """Immutable, append-only record of everything we ingest.

    Every downstream signal keeps a reference back here so alerts are
    always traceable to source documents.
    """

    __tablename__ = "raw_events"
    __table_args__ = (UniqueConstraint("source_id", "source_native_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), index=True)
    source_native_id: Mapped[str] = mapped_column(String(256))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    event_time: Mapped[datetime | None] = mapped_column(DateTime)
    document_url: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON)


class InsiderTransaction(Base):
    """One non-derivative transaction line from a Form 4 filing."""

    __tablename__ = "insider_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_event_id: Mapped[int] = mapped_column(ForeignKey("raw_events.id"), index=True)
    accession: Mapped[str] = mapped_column(String(32), index=True)

    issuer_cik: Mapped[int] = mapped_column(Integer, index=True)
    issuer_name: Mapped[str] = mapped_column(String(256))
    issuer_ticker: Mapped[str | None] = mapped_column(String(16), index=True)

    owner_cik: Mapped[int | None] = mapped_column(Integer, index=True)
    owner_name: Mapped[str] = mapped_column(String(256))
    is_director: Mapped[bool] = mapped_column(default=False)
    is_officer: Mapped[bool] = mapped_column(default=False)
    officer_title: Mapped[str | None] = mapped_column(String(128))

    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    # SEC transaction codes: P=open-market purchase, S=sale, A=award, etc.
    transaction_code: Mapped[str] = mapped_column(String(2), index=True)
    # A = acquired, D = disposed
    acquired_disposed: Mapped[str | None] = mapped_column(String(1))
    shares: Mapped[float | None] = mapped_column(Float)
    price_per_share: Mapped[float | None] = mapped_column(Float)
    filed_at: Mapped[datetime | None] = mapped_column(DateTime)

    @property
    def total_value(self) -> float | None:
        if self.shares is not None and self.price_per_share is not None:
            return self.shares * self.price_per_share
        return None


class Signal(Base):
    """A scored, dated observation about a company, with provenance."""

    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("signal_family", "signal_type", "company_cik", "event_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_cik: Mapped[int] = mapped_column(Integer, index=True)
    signal_family: Mapped[str] = mapped_column(String(32), index=True)
    signal_type: Mapped[str] = mapped_column(String(64))
    event_date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float)
    details: Mapped[dict] = mapped_column(JSON)
    raw_event_ids: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(config.DATABASE_URL)
    return _engine


def get_session() -> Session:
    return Session(get_engine())


def init_db() -> None:
    Base.metadata.create_all(get_engine())
