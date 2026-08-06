import os
from pathlib import Path

# SQLite for Phase 0; swap DATABASE_URL to Postgres later without code changes.
DATA_DIR = Path(os.environ.get("MSP_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATABASE_URL = os.environ.get("MSP_DATABASE_URL", f"sqlite:///{DATA_DIR / 'msp.db'}")

# SEC requires a descriptive User-Agent with contact info on all EDGAR requests.
SEC_USER_AGENT = os.environ.get(
    "MSP_SEC_USER_AGENT", "market-signals-platform/0.1 (asasmith3434@gmail.com)"
)

# Stay well under SEC's 10 requests/second limit.
SEC_MIN_REQUEST_INTERVAL_SECONDS = 0.15
