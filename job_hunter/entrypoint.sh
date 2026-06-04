#!/bin/sh
set -e

cd /app/src

uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1 &
API_PID=$!

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_ADMIN_ID" ]; then
    echo "[entrypoint] Esperando API..."
    for i in $(seq 1 20); do
        if wget -q --spider http://localhost:8000/ 2>/dev/null; then
            echo "[entrypoint] API lista. Iniciando bot..."
            break
        fi
        sleep 1
    done
    python bot.py &
    BOT_PID=$!
else
    echo "[entrypoint] TELEGRAM_BOT_TOKEN o TELEGRAM_ADMIN_ID no configurados — bot no iniciado"
    BOT_PID=""
fi

trap 'kill $API_PID ${BOT_PID:-} 2>/dev/null; exit 0' TERM INT

if [ -n "$BOT_PID" ]; then
    wait $API_PID $BOT_PID
else
    wait $API_PID
fi
