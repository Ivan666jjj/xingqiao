import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    db_path: str
    admin_token: str
    webhook_secret: str
    rate_limit_per_min: int
    allowed_origins: tuple[str, ...]


def load_config(db_path: str | None = None) -> Config:
    base = Path(__file__).resolve().parents[1]
    origins = os.getenv("XQ_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Config(
        db_path=db_path or os.getenv("XQ_DB", str(base / "data" / "xingqiao.db")),
        admin_token=os.getenv("XQ_ADMIN_TOKEN", "dev-admin-token"),
        webhook_secret=os.getenv("XQ_WEBHOOK_SECRET", "dev-webhook-secret"),
        rate_limit_per_min=int(os.getenv("XQ_RATE_LIMIT", "120")),
        allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
    )