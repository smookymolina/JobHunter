#!/bin/sh
set -e

cd /app/src

uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1 &
API_PID=$!

echo "[entrypoint] Esperando API..."
for i in $(seq 1 20); do
    if curl -sf http://localhost:8000/ > /dev/null 2>&1; then
        echo "[entrypoint] API lista."
        break
    fi
    sleep 1
done

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_ADMIN_ID" ]; then
    echo "[entrypoint] Iniciando bot Telegram..."
    python bot.py &
    BOT_PID=$!
else
    echo "[entrypoint] Bot Telegram no configurado - omitido"
    BOT_PID=""
fi

echo "[entrypoint] Iniciando MCP server HTTP en :8002..."
python mcp_server_http.py &
MCP_PID=$!

trap 'kill $API_PID ${BOT_PID:-} $MCP_PID 2>/dev/null; exit 0' TERM INT

wait $API_PID ${BOT_PID:-} $MCP_PID
