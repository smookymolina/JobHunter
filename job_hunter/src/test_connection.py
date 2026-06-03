"""Diagnóstico rápido: API + MCP + PATCH de estado."""
import sys, json, os, urllib.request, urllib.error, subprocess
sys.stdout.reconfigure(encoding='utf-8')

API = "http://127.0.0.1:8000"
PY  = sys.executable
MCP = os.path.join(os.path.dirname(__file__), "mcp_server.py")

OK  = "\033[32m✓\033[0m"
ERR = "\033[31m✗\033[0m"

def check(label, fn):
    try:
        result = fn()
        print(f"  {OK}  {label}: {result}")
        return True
    except Exception as e:
        print(f"  {ERR}  {label}: {e}")
        return False

print("\n========== Job Hunter — Diagnóstico de Conexión ==========\n")

# 1. API health
def _api():
    with urllib.request.urlopen(f"{API}/scrape/status", timeout=4) as r:
        return f"HTTP {r.status} — {json.loads(r.read())}"
api_ok = check("API responde en 127.0.0.1:8000", _api)

# 2. PATCH status
def _patch():
    if not api_ok:
        raise RuntimeError("API caída — saltar test")
    with urllib.request.urlopen(f"{API}/vacantes?limit=1", timeout=4) as r:
        vacantes = json.loads(r.read())
    if not vacantes:
        return "sin vacantes (OK — endpoint accesible)"
    vid = vacantes[0]["id"]
    status = vacantes[0]["status"]
    payload = json.dumps({"status": status}).encode()
    req = urllib.request.Request(f"{API}/vacantes/{vid}/status",
          data=payload, method="PATCH",
          headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=4) as r:
        return f"PATCH vacante #{vid} → HTTP {r.status}"
check("PATCH /vacantes/{id}/status", _patch)

# 3. MCP server arranca sin crash
def _mcp():
    proc = subprocess.Popen(
        [PY, MCP], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, cwd=os.path.dirname(MCP)
    )
    # Enviar initialize
    msg = json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize",
        "params":{"protocolVersion":"2024-11-05","capabilities":{},
                  "clientInfo":{"name":"test","version":"1.0"}}}) + "\n"
    try:
        out, err = proc.communicate(msg.encode("utf-8"), timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill(); out, err = proc.communicate()
    if err:
        stderr_text = err.decode("utf-8", errors="replace").strip()
        if "Internal Server Error" not in stderr_text and stderr_text:
            raise RuntimeError(stderr_text[:200])
    if out:
        first_line = out.decode("utf-8", errors="replace").strip().split("\n")[0]
        parsed = json.loads(first_line) if first_line.startswith("{") else first_line
        return f"responde JSON-RPC: {str(parsed)[:80]}"
    return "proceso arrancó sin errores (stdio en espera)"
check("MCP server arranca y responde JSON-RPC", _mcp)

# 4. Verificar config Claude Desktop
def _cfg():
    cfg = os.path.join(os.environ["APPDATA"], "Claude", "claude_desktop_config.json")
    if not os.path.exists(cfg):
        raise RuntimeError(f"NO EXISTE: {cfg}")
    with open(cfg, encoding="utf-8") as f:
        data = json.load(f)
    servers = list(data.get("mcpServers", {}).keys())
    server_cfg = data["mcpServers"].get("job-hunter", {})
    cmd = server_cfg.get("command","")
    cwd = server_cfg.get("cwd","")
    py_exists = os.path.exists(cmd)
    cwd_exists = os.path.exists(cwd)
    return f"servers={servers}  python_exe={'OK' if py_exists else 'NO EXISTE'}  cwd={'OK' if cwd_exists else 'NO EXISTE'}"
check("claude_desktop_config.json válido", _cfg)

print("\n===========================================================")
print("→ Si todo es ✓: reinicia Claude Desktop completamente.")
print("→ Revisa job_hunter/mcp_debug.log para ver si Claude conectó.")
print("===========================================================\n")
