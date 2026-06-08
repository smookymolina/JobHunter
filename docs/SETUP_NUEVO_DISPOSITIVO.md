# Job Hunter — Setup en nuevo dispositivo

> Última actualización: 2026-06-07

## Estructura del proyecto

```
C:\Users\GIRTEC\Desktop\CODEMAGA\JobHunter\
  job_hunter/
    src/
      api.py              → Backend FastAPI (puerto 8000)
      auth.py             → JWT + password hashing (stdlib puro)
      gemini_engine.py    → Motor IA + LaTeX + helpers multi-tenant
      mcp_server.py       → Servidor MCP para Claude Desktop
      browser_agent.py    → Scraper de vacantes
      watcher.py          → DeepHealthWatcher (sync automático)
      inspector.py        → Auditor IA de CVs
    data/
      perfil_maestro.json          → Perfil de default_user (legacy)
      {user_id}_perfil.json        → Perfil aislado por usuario
    outputs/
      {user_id}/
        cv_vacante_{id}.tex/.pdf   → Outputs aislados por usuario
    context/
      mi_perfil.md                 → Contexto IA (legacy/global)
    latex_templates/
      default_template.tex         → Plantilla base
      mi_estilo.tex                → Plantilla personalizada (si existe)
    requirements.txt
    .env
  frontend/
    app/
      login/page.tsx      → Página de login (NextAuth v5)
      register/page.tsx   → Página de registro
      dashboard/          → Panel principal
      perfil/page.tsx     → Gestión perfil maestro (requiere JWT)
      vacantes/           → CRUD vacantes
    auth.ts               → NextAuth config (Credentials provider)
    middleware.ts         → Protege rutas; permite /login y /register sin auth
    lib/api.ts            → Cliente HTTP; inyecta Bearer token automáticamente
    components/
      ConditionalLayout.tsx → Sidebar condicional + sync JWT
    .env.local
```

## Variables de entorno

### `job_hunter/.env`

```env
GROQ_API_KEY=gsk_...
AUTH_SECRET=tu-secreto-jwt-aqui
DATABASE_URL=postgresql://usuario:password@localhost:5432/jobhunter
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
AUTH_URL=http://localhost:3000
AUTH_SECRET=tu-secreto-jwt-aqui          # Debe coincidir con el backend
AUTH_TRUST_HOST=true
# En Docker, el frontend usa la URL interna:
# BACKEND_URL=http://api:8000
```

## Setup paso a paso

### 1. PostgreSQL

```powershell
# Instalar PostgreSQL 16+ y crear la BD:
createdb jobhunter
# La API crea todas las tablas automáticamente al arrancar (lifespan)
```

### 2. Python y dependencias

```powershell
cd job_hunter
pip install -r requirements.txt
```

### 3. pdflatex (para compilar CVs en PDF)

Instalar MiKTeX desde https://miktex.org/download (Windows)
- Elegir "Install for all users"
- Habilitar "Install missing packages automatically"

Verificar:
```powershell
pdflatex --version
```

### 4. Levantar servicios

**Terminal 1 — Backend:**
```powershell
cd job_hunter\src
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

### 5. Verificar

```powershell
# Health check API
Invoke-WebRequest -Uri "http://127.0.0.1:8000/" | Select-Object -ExpandProperty Content

# Swagger docs
start http://127.0.0.1:8000/docs

# App
start http://localhost:3000/login
```

## Credenciales por defecto

| Campo | Valor |
|---|---|
| Email | `test@jobhunter.com` |
| Password | `jobhunter123` |
| user_id | `default_user` |

Estos son creados automáticamente por el seed en `lifespan` de `api.py`.

## Flujo de autenticación

1. **Login**: `POST /auth/login` → backend valida credenciales en tabla `usuarios` → retorna JWT de 7 días.
2. **NextAuth**: `frontend/auth.ts` llama al backend con Credentials provider → guarda `accessToken` en session.
3. **Inyección de token**: `ConditionalLayout.tsx` detecta cambio de session y llama `setAuthToken()` → `lib/api.ts` inyecta `Authorization: Bearer` en todas las requests.
4. **Registro**: `POST /auth/register` crea usuario con `uuid4().hex` como `user_id` y genera el perfil JSON inicial. Redirige a `/login?registered=true`.
5. **Middleware**: protege todas las rutas excepto `/login` y `/register`.

## Configurar MCP en Claude Desktop

Editar `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "job-hunter": {
      "command": "python",
      "args": ["C:/Users/GIRTEC/Desktop/CODEMAGA/JobHunter/job_hunter/src/mcp_server.py"]
    }
  }
}
```

## Checklist de verificación

- [ ] `pdflatex --version` responde correctamente
- [ ] PostgreSQL corriendo con BD `jobhunter`
- [ ] API responde en `http://127.0.0.1:8000/`
- [ ] Frontend carga en `http://localhost:3000/login`
- [ ] Login con `test@jobhunter.com` / `jobhunter123` redirige a `/dashboard`
- [ ] Registro de nuevo usuario en `/register` redirige a `/login?registered=true`
- [ ] Perfil en `/perfil` carga y guarda correctamente para el usuario autenticado
- [ ] Generar CV para una vacante llega a status `Revisado_IA`

## Notas LaTeX

- `default_template.tex` NO usa `fontawesome5` ni `\usepackage[spanish]{babel}` — no reintroducir.
- `mi_estilo.tex` (plantilla personalizada) se sube vía `POST /upload_template`.
