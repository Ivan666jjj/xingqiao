#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

export XQ_DB="${XQ_DB:-$PWD/data/xingqiao.db}"
export XQ_ADMIN_TOKEN="${XQ_ADMIN_TOKEN:-dev-admin-token}"
export XQ_WEBHOOK_SECRET="${XQ_WEBHOOK_SECRET:-dev-webhook-secret}"
export XQ_RATE_LIMIT="${XQ_RATE_LIMIT:-120}"
export XQ_CHAT_TOKEN="${XQ_CHAT_TOKEN:-demo-chat-token}"

if [ -z "${QWEN_API_KEY:-}" ]; then
  QWEN_API_KEY="$(security find-generic-password -s qwen-dashscope-key -w 2>/dev/null || true)"
  export QWEN_API_KEY
fi

exec python3 -m uvicorn app.main:create_app --factory \
  --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"