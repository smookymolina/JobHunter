import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os
import json
import re

from gemini_engine import GROQ_API_KEY, GROQ_MODEL, DB_PATH, OUTPUTS_DIR, _groq_client


def _get_vacante(vid):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT titulo, empresa, requerimientos FROM vacantes WHERE id=?", (vid,)
    ).fetchone()
    conn.close()
    return row


def _read(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def _parse_json(text: str) -> dict:
    """Extrae JSON de la respuesta aunque venga con texto alrededor."""
    text = text.strip()
    try:
      return json.loads(text)
    except json.JSONDecodeError:
      pass

    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def evaluar_cv(vacante_id: int, tex_path: str) -> dict:
    """
    Evalua el .tex generado contra la vacante usando IA como reclutador.
    Retorna: {"aprobado": bool, "comentarios": str}
    """
    row = _get_vacante(vacante_id)
    if not row:
        return {"aprobado": False, "comentarios": f"Vacante #{vacante_id} no encontrada."}

    titulo, empresa, requerimientos = row

    if not os.path.exists(tex_path):
        return {"aprobado": False, "comentarios": f"Archivo .tex no encontrado: {tex_path}"}

    tex_preview = _read(tex_path)[:5000]

    system_msg = (
        "Eres un Reclutador Tecnico Senior. Evaluas CVs con criterio profesional. "
        "Respondes UNICAMENTE con JSON valido, sin texto adicional, con esta estructura exacta: "
        '{"aprobado": true_o_false, "comentarios": "texto en espanol"}'
    )

    user_msg = f"""Audita este CV en LaTeX contra la vacante.

VACANTE:
- Titulo: {titulo}
- Empresa: {empresa}
- Requerimientos: {(requerimientos or '')[:1500]}

CV (LaTeX):
{tex_preview}

CRITERIOS (todos deben pasar para aprobar):
1. MATCH: El CV menciona >=60% de los skills clave de la vacante?
2. VERACIDAD: Hay datos inventados, fechas imposibles o contradicciones?
3. LaTeX: El codigo tiene errores fatales evidentes que impidan compilar?

Responde SOLO con JSON:
{{"aprobado": true, "comentarios": "Razon concisa en 2-3 puntos."}}"""

    try:
        client = _groq_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content or "{}"
        result = _parse_json(raw)
        return {
            "aprobado": bool(result.get("aprobado", False)),
            "comentarios": str(result.get("comentarios", "Sin comentarios.")),
        }
    except Exception as e:
        return {"aprobado": False, "comentarios": f"Error en inspector: {e}"}


if __name__ == '__main__':
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Uso: python inspector.py <vacante_id>")
        _sys.exit(1)
    vid = int(_sys.argv[1])
    tex = os.path.join(OUTPUTS_DIR, f"cv_vacante_{vid}.tex")
    r = evaluar_cv(vid, tex)
    print(f"Aprobado:    {r['aprobado']}")
    print(f"Comentarios: {r['comentarios']}")
