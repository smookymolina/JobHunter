# Job Hunter — Setup en nuevo dispositivo

Prompt para Claude (o cualquier agente IA) al migrar el proyecto:

---

## PROMPT DE MIGRACIÓN

```
Estoy configurando el proyecto "Job Hunter" en un nuevo dispositivo Windows.
Necesitas hacer el setup completo y verificar que todo funciona correctamente.

## Repositorio
El proyecto está en: [RUTA_DEL_PROYECTO]
Estructura principal:
  job_hunter/src/api.py          → Backend FastAPI (puerto 8000)
  job_hunter/src/mcp_server.py   → Servidor MCP para Claude Desktop
  job_hunter/src/gemini_engine.py → Motor de IA + compilación LaTeX
  frontend/                      → Next.js (puerto 3000)
  job_hunter/data/perfil_maestro.json → Perfil del usuario (NO modificar)
  job_hunter/db/vacantes.db      → Base de datos SQLite

## Pasos que debes ejecutar en orden:

### 1. Verificar Python y dependencias
- Python 3.11+ requerido
- Instalar dependencias: `pip install -r job_hunter/requirements.txt`
- Verificar imports críticos: fastapi, uvicorn, sqlite3, subprocess

### 2. Instalar y configurar pdflatex (CRÍTICO)
El proyecto compila CVs en PDF usando pdflatex. Sin esto el status nunca
llega a "Revisado_IA". Debes:

a) Instalar MiKTeX desde https://miktex.org/download (Windows)
   - Elegir "Install for all users"
   - Habilitar "Install missing packages automatically"

b) Verificar que pdflatex está en PATH:
   `pdflatex --version`
   Si falla: agregar `C:\Users\[USER]\AppData\Local\Programs\MiKTeX\miktex\bin\x64`
   a la variable PATH del sistema.

c) Instalar paquetes LaTeX requeridos (ejecutar UNA VEZ):
   `pdflatex -interaction=nonstopmode job_hunter/latex_templates/default_template.tex`
   MiKTeX descargará los paquetes faltantes automáticamente.

d) IMPORTANTE: La plantilla default_template.tex NO usa fontawesome5 ni
   babel con opción [spanish] — estos fueron eliminados por causar errores.
   Si alguien los reintroduce, el PDF fallará silenciosamente.

### 3. Verificar la base de datos
- El archivo vacantes.db debe existir en job_hunter/db/
- Si no existe: `python job_hunter/src/init_db.py`
- Verificar esquema: tabla `vacantes` con columnas:
  id, titulo, empresa, enlace, requerimientos, compatibilidad, status, fecha_registro
- Valores válidos de status: No_Creado | En_Proceso | Revisado_IA | Requiere_Correccion | Listo_Manual

### 4. Variables de entorno
Crear archivo `job_hunter/.env` con:
```
GROQ_API_KEY=...       # o GEMINI_API_KEY según el motor configurado
```

### 5. Levantar los servicios (3 terminales)
Terminal 1 — API:
  `cd job_hunter/src && python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload`

Terminal 2 — Frontend:
  `cd frontend && npm install && npm run dev`

Terminal 3 — Bot Telegram (opcional):
  `cd job_hunter/src && python bot.py`

### 6. Verificar que todo funciona
Ejecutar estos comandos en PowerShell:

# Health check API
Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -Method GET

# Listar vacantes
Invoke-WebRequest -Uri "http://127.0.0.1:8000/vacantes" -Method GET

# Si hay vacantes con status desactualizado (Sin Iniciar pero con PDF ya generado):
Invoke-WebRequest -Uri "http://127.0.0.1:8000/vacantes/[ID]/sync" -Method POST

# Abrir dashboard
start http://localhost:3000/dashboard

### 7. Configurar MCP en Claude Desktop
Editar `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "job-hunter": {
      "command": "python",
      "args": ["C:/[RUTA]/job_hunter/src/mcp_server.py"]
    }
  }
}
```
Reiniciar Claude Desktop y verificar que aparecen las tools:
  - get_vacancy_by_id
  - save_latex_cv
  - get_pending_vacancies
  - update_compatibility

## Bugs conocidos y sus fixes (ya aplicados en el código)

### Bug 1: pdflatex no en PATH → status se queda en "Sin iniciar"
FIX en gemini_engine.py — compilar_pdf():
  - Si PDF ya existe y es >= reciente que el .tex → lo reutiliza sin relanzar pdflatex
  - Si pdflatex no está en PATH pero existe PDF previo → lo usa
  - Si pdflatex no está y no hay PDF → error claro con instrucciones de instalación

### Bug 2: /latex/{vid} no actualizaba status al fallar compilación
FIX en api.py — POST /latex/{vid}:
  - Ahora marca Requiere_Correccion cuando el PDF no se genera

### Bug 3: Sin forma de sincronizar status cuando PDF se compiló fuera del pipeline
FIX en api.py — nuevo endpoint POST /vacantes/{vid}/sync:
  - Detecta PDF existente en outputs/ → marca Revisado_IA
  - Si solo hay .tex → intenta compilar → marca Revisado_IA o Requiere_Correccion

### Bug 4: fontawesome5 no instalado en TeX Live del sandbox
FIX en default_template.tex y en todos los CVs generados:
  - Eliminado \usepackage{fontawesome5}
  - Iconos reemplazados por \textbf{Email:}, \textbf{Tel:}, etc.

### Bug 5: \usepackage[spanish]{babel} falla en TeX Live sin babel-spanish
FIX en default_template.tex:
  - Cambiado a \usepackage{babel} sin opción de idioma
  - Los acentos se escapan manualmente (\'a, \'e, \~n, etc.)

## Notas de PowerShell vs curl
En PowerShell, `curl` es un alias de Invoke-WebRequest con sintaxis diferente:

# Incorrecto (falla en PowerShell):
curl -X POST http://127.0.0.1:8000/vacantes/1/sync

# Correcto:
Invoke-WebRequest -Uri "http://127.0.0.1:8000/vacantes/1/sync" -Method POST

# GET con output legible:
(Invoke-WebRequest -Uri "http://127.0.0.1:8000/vacantes" -Method GET).Content

# Para instalar curl real en Windows:
winget install curl.curl
# Luego usar: curl.exe -X POST http://...

## Checklist de verificación final
[ ] pdflatex --version responde correctamente
[ ] API responde en http://127.0.0.1:8000/
[ ] Frontend carga en http://localhost:3000/dashboard
[ ] Dashboard muestra "API conectada"
[ ] Generar CV para una vacante de prueba y verificar que llega a "Revisado por IA"
[ ] Bot Telegram responde (si aplica)
```

---

Última actualización: 2026-06-03
