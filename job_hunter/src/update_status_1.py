import requests, sys

vacante_id = 1
base = "http://127.0.0.1:8000"

# 1. Marcar En_Proceso
r1 = requests.patch(f"{base}/vacantes/{vacante_id}/status", json={"status": "En_Proceso"})
print(f"En_Proceso: {r1.status_code} {r1.text}")

# 2. Marcar Revisado_IA
r2 = requests.patch(f"{base}/vacantes/{vacante_id}/status", json={"status": "Revisado_IA"})
print(f"Revisado_IA: {r2.status_code} {r2.text}")
