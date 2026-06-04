#!/bin/sh
set -e

cd /app/src

uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1 &
API_PID=$!

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_ADMIN_ID" ]; then
    python bot.py &
    BOT_PID=$!
else
    echo "[entrypoint] TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_ID not set — bot not started"
    BOT_PID=""
fi

trap 'kill $API_PID ${BOT_PID:-} 2>/dev/null; exit 0' TERM INT

if [ -n "$BOT_PID" ]; then
    wait $API_PID $BOT_PID
else
    wait $API_PID
fi
