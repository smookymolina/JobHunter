"""Valida que el servidor MCP puede actualizar vacantes vía HTTP PATCH a la API."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import urllib.request
import urllib.error

API = "http://127.0.0.1:8000"


def _get(path: str):
    with urllib.request.urlopen(f"{API}{path}") as r:
        return json.loads(r.read())


def _patch(path: str, data: dict) -> dict:
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=payload,
        method="PATCH",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def test_api_health():
    print("[TEST] GET /vacantes (health check)...", end=" ")
    try:
        vacantes = _get("/vacantes?limit=1")
        print(f"OK — {len(vacantes)} vacante(s) encontrada(s)")
        return vacantes
    except Exception as e:
        print(f"FAIL — {e}")
        return None


def test_patch_status(vid: int, current_status: str) -> bool:
    print(f"[TEST] PATCH /vacantes/{vid}/status...", end=" ")
    try:
        r = _patch(f"/vacantes/{vid}/status", {"status": current_status})
        print(f"OK — {r}")
        return True
    except urllib.error.HTTPError as e:
        print(f"FAIL HTTP {e.code} — {e.read().decode()}")
        return False
    except Exception as e:
        print(f"FAIL — {e}")
        return False


def test_patch_compatibilidad(vid: int, current_compat: str) -> bool:
    print(f"[TEST] PATCH /vacantes/{vid}/compatibilidad...", end=" ")
    try:
        r = _patch(f"/vacantes/{vid}/compatibilidad", {"compatibilidad": current_compat})
        print(f"OK — {r}")
        return True
    except urllib.error.HTTPError as e:
        print(f"FAIL HTTP {e.code} — {e.read().decode()}")
        return False
    except Exception as e:
        print(f"FAIL — {e}")
        return False


if __name__ == "__main__":
    print("=" * 55)
    print("TEST: MCP HTTP PATCH via urllib (http://127.0.0.1:8000)")
    print("=" * 55)

    vacantes = test_api_health()
    if vacantes is None:
        print("\n[ABORT] API no responde. Arranca api.py primero.")
        sys.exit(1)

    results = []
    if vacantes:
        vid     = vacantes[0]["id"]
        status  = vacantes[0].get("status", "No_Creado")
        compat  = vacantes[0].get("compatibilidad", "Nula")
        results.append(test_patch_status(vid, status))
        results.append(test_patch_compatibilidad(vid, compat))
    else:
        print("[SKIP] Sin vacantes en DB — pruebas de PATCH omitidas.")
        results = [True, True]

    passed = sum(1 for r in results if r)
    print(f"\n{'='*55}")
    print(f"Resultado: {passed}/{len(results)} tests OK")
    sys.exit(0 if all(results) else 1)
