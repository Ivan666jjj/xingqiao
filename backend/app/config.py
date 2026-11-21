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
    qwen_api_key: str
    qwen_base_url: str
    qwen_text_model: str
    qwen_ws_url: str
    qwen_realtime_model: str
    qwen_timeout: float
    chat_token: str


def load_config(db_path: str | None = None) -> Config:
    base = Path(__file__).resolve().parents[1]
    origins = os.getenv(
        "XQ_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://xingqiao.localhost,http://localhost:8000,http://127.0.0.1:8000,null",
    )
    return Config(
        db_path=db_path or os.getenv("XQ_DB", str(base / "data" / "xingqiao.db")),
        admin_token=os.getenv("XQ_ADMIN_TOKEN", "dev-admin-token"),
        webhook_secret=os.getenv("XQ_WEBHOOK_SECRET", "dev-webhook-secret"),
        rate_limit_per_min=int(os.getenv("XQ_RATE_LIMIT", "120")),
        allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        qwen_api_key=os.getenv("QWEN_API_KEY", ""),
        qwen_base_url=os.getenv(
            "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        qwen_text_model=os.getenv("QWEN_TEXT_MODEL", "qwen-plus"),
        qwen_ws_url=os.getenv(
            "QWEN_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        ),
        qwen_realtime_model=os.getenv(
            "QWEN_REALTIME_MODEL", "qwen3.8-omni-flash-realtime"
        ),
        qwen_timeout=float(os.getenv("QWEN_TIMEOUT", "60")),
        chat_token=os.getenv("XQ_CHAT_TOKEN", "demo-chat-token"),
    )