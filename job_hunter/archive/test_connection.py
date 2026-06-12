# test_connection.py — Diagnostico de conexion Job Hunter MCP
# Ejecutar: python test_connection.py

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

API_BASE   = "http://127.0.0.1:8000"
PYTHON_EXE = r"C:\Users\GIRTEC\AppData\Local\Programs\Python\Python313\python.exe"
MCP_SCRIPT = os.path.join(os.path.dirname(__file__), "src", "mcp_server.py")
CONFIG_PATH = os.path.expandvars(r"%APPDATA%\Claude\claude_desktop_config.json")
LOG_PATH    = os.path.expandvars(r"%APPDATA%\Claude\logs\mcp-server-job-hunter.log")

OK  = "✅"
ERR = "❌"
WRN = "⚠️ "

results = []

# ─────────────────────────────────────────────────────────────────────────────
# 1. API health
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  JOB HUNTER — Diagnóstico de Conexión MCP")
print("="*60)

print("\n[1/4] Verificando API Flask en http://127.0.0.1:8000 ...")
try:
    with urllib.request.urlopen(f"{API_BASE}/scrape/status", timeout=4) as r:
        body = json.loads(r.read())
        print(f"  {OK} API responde — status HTTP {r.status}")
        print(f"       Respuesta: {json.dumps(body)[:120]}")
        api_ok = True
except urllib.error.URLError as e:
    print(f"  {ERR} API NO responde: {e.reason}")
    print(f"       Solución: ejecuta  .\\start_api.ps1  en otra terminal")
    api_ok = False
except Exception as e:
    print(f"  {ERR} Error inesperado: {e}")
    api_ok = False

# ─────────────────────────────────────────────────────────────────────────────
# 2. PATCH de status
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2/4] Probando PATCH de status (vacante #1 → No_Creado) ...")
if not api_ok:
    print(f"  {WRN} Saltando (API no disponible)")
else:
    try:
        payload = json.dumps({"status": "No_Creado"}).encode()
        req = urllib.request.Request(
            f"{API_BASE}/vacantes/1/status",
            data=payload, method="PATCH",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"  {OK} PATCH responde — HTTP {r.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"  {ERR} PATCH falló — HTTP {e.code}: {body[:200]}")
    except Exception as e:
        print(f"  {ERR} PATCH error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. Arranque del servidor MCP + handshake JSON-RPC
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3/4] Probando arranque MCP y handshake JSON-RPC ...")

# Mensaje initialize según protocolo MCP
INIT_MSG = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test_connection", "version": "1.0"},
    },
}) + "\n"

# Notificación obligatoria antes de cualquier otra llamada
INITIALIZED_MSG = json.dumps({
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
}) + "\n"

LIST_MSG = json.dumps({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {},
}) + "\n"

if not os.path.exists(PYTHON_EXE):
    print(f"  {ERR} Python no encontrado en: {PYTHON_EXE}")
elif not os.path.exists(MCP_SCRIPT):
    print(f"  {ERR} mcp_server.py no encontrado en: {MCP_SCRIPT}")
else:
    try:
        proc = subprocess.Popen(
            [PYTHON_EXE, MCP_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(MCP_SCRIPT),
        )
        # Protocolo MCP: initialize → initialized (notif) → tools/list
        proc.stdin.write((INIT_MSG + INITIALIZED_MSG + LIST_MSG).encode())
        proc.stdin.flush()
        time.sleep(2)
        proc.stdin.close()

        stdout_raw = proc.stdout.read().decode("utf-8", errors="replace")
        stderr_raw = proc.stderr.read().decode("utf-8", errors="replace")
        proc.wait(timeout=5)

        if stdout_raw.strip():
            lines = [l for l in stdout_raw.strip().splitlines() if l.strip()]
            valid_json = 0
            tools_found = []
            for line in lines:
                try:
                    obj = json.loads(line)
                    valid_json += 1
                    # Buscar lista de tools en respuesta
                    tools = (obj.get("result") or {}).get("tools", [])
                    tools_found.extend([t.get("name") for t in tools])
                except Exception:
                    pass

            if valid_json > 0:
                print(f"  {OK} Servidor MCP responde con JSON-RPC válido ({valid_json} mensajes)")
                if tools_found:
                    print(f"  {OK} Herramientas registradas: {tools_found}")
                else:
                    print(f"  {WRN} No se recibió lista de tools en la respuesta")
            else:
                print(f"  {ERR} Stdout no contiene JSON-RPC válido:")
                print(f"       {stdout_raw[:300]}")
        else:
            print(f"  {ERR} El servidor no respondió (stdout vacío)")

        if stderr_raw.strip():
            print(f"  {WRN} stderr del servidor:")
            for line in stderr_raw.strip().splitlines()[:10]:
                print(f"       {line}")

    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"  {ERR} El servidor no cerró en 5s (posible cuelgue)")
    except Exception as e:
        print(f"  {ERR} No se pudo lanzar el servidor: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 4. claude_desktop_config.json
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4/4] Verificando claude_desktop_config.json ...")
if not os.path.exists(CONFIG_PATH):
    print(f"  {ERR} Archivo no encontrado: {CONFIG_PATH}")
else:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        servers = cfg.get("mcpServers", {})
        if not servers:
            print(f"  {ERR} No hay entradas en 'mcpServers'")
        else:
            print(f"  {OK} mcpServers encontrados: {list(servers.keys())}")
            for name, conf in servers.items():
                cmd  = conf.get("command", "")
                args = conf.get("args", [])
                cwd  = conf.get("cwd", "")
                cmd_ok  = os.path.exists(cmd)
                args_ok = all(os.path.exists(a) for a in args if a.endswith(".py"))
                cwd_ok  = not cwd or os.path.isdir(cwd)
                print(f"\n  Servidor: '{name}'")
                print(f"    command  : {cmd}")
                print(f"    args     : {args}")
                print(f"    cwd      : {cwd or '(no especificado)'}")
                print(f"    cmd existe  : {OK if cmd_ok  else ERR}")
                print(f"    args existen: {OK if args_ok else ERR}")
                print(f"    cwd existe  : {OK if cwd_ok  else ERR}")
                if not cmd_ok:
                    print(f"    {ERR} PROBLEMA: Python no encontrado en '{cmd}'")
                if not args_ok:
                    print(f"    {ERR} PROBLEMA: Algún script no existe — verifica la ruta")
    except json.JSONDecodeError as e:
        print(f"  {ERR} JSON inválido en el config: {e}")
        print(f"       Abre el archivo y busca la coma o llave faltante")
    except Exception as e:
        print(f"  {ERR} Error leyendo config: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Resumen
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  LOG del MCP (últimas 15 líneas):")
print("="*60)
debug_log = os.path.join(os.path.dirname(__file__), "mcp_debug.log")
if os.path.exists(debug_log):
    with open(debug_log, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[-15:]:
        print(" ", line.rstrip())
else:
    print("  (mcp_debug.log no existe aún)")

print("\n" + "="*60)
print("  LOG de Claude Desktop:")
print("="*60)
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for line in lines[-15:]:
        print(" ", line.rstrip())
else:
    # Buscar cualquier log de MCP en la carpeta de logs
    logs_dir = os.path.expandvars(r"%APPDATA%\Claude\logs")
    if os.path.isdir(logs_dir):
        mcp_logs = [f for f in os.listdir(logs_dir) if "mcp" in f.lower()]
        if mcp_logs:
            print(f"  Logs MCP encontrados: {mcp_logs}")
            for lf in mcp_logs[:3]:
                lp = os.path.join(logs_dir, lf)
                print(f"\n  --- {lf} ---")
                with open(lp, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                for line in lines[-10:]:
                    print(" ", line.rstrip())
        else:
            print("  No se encontraron logs MCP en", logs_dir)
    else:
        print(f"  Directorio de logs no encontrado: {logs_dir}")

print("\n" + "="*60 + "\n")
