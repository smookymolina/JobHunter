# Configurar el MCP al cambiar de perfil de sesión

Guía operativa para que el generador de CVs use **los datos del usuario correcto** y los inyecte en **su carpeta correcta**.

> Regla de oro: **un servidor MCP = un usuario**. El usuario no se elige en el chat, se fija con variables de entorno al arrancar el contenedor. Si quieres generar CVs para otra persona, apuntas a **otro puerto**, no cambias nada dentro de la conversación.

---

## 1. Mapa actual

| Usuario | `MCP_USER_ID` | Puerto | Contenedor | Nombre en Claude Desktop |
|---|---|---|---|---|
| Jair Molina Arce | `default_user` | `8002` | `jobhunter-api-1` | `job-hunter` |
| Maria del Pilar Marulanda | `538dfb32aa5443eb90e2abb133bd51af` | `8003` | `jobhunter-mcp-marulanda-1` | `job-hunter-marulanda` |

El MCP de Jair va embebido en el contenedor `api`. Los demás usuarios corren como servicios aparte (`mcp-marulanda` ejecuta `mcp_server_http.py` y publica `8003:8002`).

### Cómo saber en qué perfil estás

Cada servidor se identifica con el nombre de su titular. En Claude Desktop verás:

```
job-hunter · Jair Molina Arce
job-hunter · Maria del Pilar Marulanda Villasmil
```

y **cada tool declara su dueño** en la descripción:

```
[PERFIL: Maria del Pilar Marulanda Villasmil · user_id=538dfb32aa5443eb90e2abb133bd51af]
```

Esto existe porque los dos servidores exponen tools con **nombres idénticos** (`get_vacancy_by_id`, `save_latex_cv`, …). Sin esa marca son indistinguibles y es fácil generar el CV desde el perfil equivocado. Se construye en `mcp_server.py` (`_owner_label()` → `_TOOL_PREFIX`), leyendo el nombre del perfil del usuario.

### Las vacantes también son por usuario

La tabla `vacantes` tiene columna `user_id` y **cada MCP solo ve las de su titular**. Consecuencia práctica:

> Que una vacante "no exista" **no significa que no exista** — significa que no es de ese usuario.

Es exactamente lo que pasa si pides la vacante 13 (de Maria) estando en el servidor de Jair: responde que no existe y te ofrece las pendientes de Jair. Comprobar a quién pertenece un ID:

```bash
docker exec jobhunter-postgres-1 psql -U jobhunter -d jobhunter_db \
  -c "SELECT id, titulo, status, user_id FROM vacantes WHERE id = <N>;"
```

---

## 2. Archivos que debe tener cada usuario

Para `<UID>` = el `user_id` del usuario:

| Archivo | Qué es | Quién lo genera |
|---|---|---|
| `job_hunter/data/<UID>_perfil.json` | **Fuente de verdad.** De aquí sale el encabezado del CV. | Dashboard al guardar el perfil |
| `job_hunter/context/<UID>_mi_perfil.md` | Versión legible que consume el LLM | La tool `sync_profile` |
| `job_hunter/outputs/<UID>/` | Destino de los `.tex` y `.pdf` | Se crea solo |

Excepción histórica: para `default_user`, si no existe `default_user_perfil.json` se usa `data/perfil_maestro.json` como respaldo (ver `gemini_engine.py:343`).

### ⚠️ Trampa: `context/mi_perfil.md`

Existe un `job_hunter/context/mi_perfil.md` **sin prefijo**, legacy, que contiene los datos de **Jair**. El sistema no lo usa, pero si en un prompt le pides al modelo *"lee `/app/context/mi_perfil.md`"*, generará el CV con los datos de Jair aunque estés en la sesión de otro usuario — y saldrá un CV híbrido difícil de detectar, porque el encabezado sí se corregirá solo.

**Nunca cites rutas de perfil a mano en el prompt. Usa la tool `get_my_profile`**, que resuelve el usuario desde `MCP_USER_ID` y no puede equivocarse.

---

## 3. Añadir un perfil nuevo

**a) Crear el usuario y su perfil**

1. Registra al usuario en la app y guarda su perfil desde el dashboard.
2. Confirma que existe en la BD y anota su `user_id`:

```bash
docker exec jobhunter-postgres-1 psql -U jobhunter -d jobhunter_db \
  -c "SELECT id, user_id, email FROM usuarios ORDER BY id;"
```

3. Confirma que se creó `job_hunter/data/<UID>_perfil.json`.

**b) Añadir el servicio en `docker-compose.yml`**

Copia el bloque `mcp-marulanda` cambiando **puerto**, `MCP_USER_ID`, `MCP_API_EMAIL` y `MCP_API_PASSWORD`:

```yaml
  mcp-<nombre>:
    build:
      context: ./job_hunter
      dockerfile: Dockerfile
    command: ["sh", "-c", "cd /app/src && python mcp_server_http.py"]
    ports:
      - "8004:8002"          # ← puerto libre nuevo en el host
    restart: unless-stopped
    environment:
      - API_BASE_URL=http://api:8000
      - MCP_USER_ID=<UID>
      - MCP_API_EMAIL=<email del usuario>
      - MCP_API_PASSWORD=${MCP_<NOMBRE>_PASSWORD:-<password>}
    volumes:
      - ./job_hunter/outputs:/app/outputs
      - ./job_hunter/data:/app/data
      - ./job_hunter/context:/app/context
      - ./job_hunter/logs:/app/logs
    depends_on:
      api:
        condition: service_healthy
```

Las credenciales deben coincidir con las de la BD: el MCP hace login contra la API al arrancar. Si fallan, el servidor levanta pero ninguna tool funciona.

> Los `${VAR:-default}` del bloque `environment` **ganan** sobre el `env_file`. No intentes cambiar el usuario desde `.env` si está fijado ahí.

**c) Levantar**

```bash
docker compose up -d mcp-<nombre>
```

**d) Registrarlo en Claude Desktop** → siguiente sección.

---

## 4. Claude Desktop: la ruta del config **no** es la que parece

Esta instalación viene de la **Microsoft Store (MSIX)**. Por la redirección de ficheros de MSIX, la app **ignora** `%APPDATA%\Claude\claude_desktop_config.json`. Ese archivo puede existir y estar perfecto sin que sirva de nada.

**Ruta real que la app lee:**

```
%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json
```

Los logs de MCP están al lado, en `...\LocalCache\Roaming\Claude\logs`.

Edita **solo** la clave `mcpServers`, conservando el resto (`coworkUserFilesPath`, `preferences.localAgentModeTrustedFolders`, …):

```json
"mcpServers": {
  "job-hunter": {
    "command": "npx",
    "args": ["-y", "mcp-remote", "http://localhost:8002/sse"]
  },
  "job-hunter-marulanda": {
    "command": "npx",
    "args": ["-y", "mcp-remote", "http://localhost:8003/sse"]
  }
}
```

**Cierra Claude Desktop del todo antes de editar** (ventana + icono de la bandeja). Al salir persiste sus preferencias y puede pisar el cambio.

Comprobar que quedó bien:

```powershell
$cfg = "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json"
(Get-Content $cfg -Raw | ConvertFrom-Json).mcpServers | Get-Member -MemberType NoteProperty | Select-Object Name
```

---

## 5. Generar un CV correctamente

Prompt recomendado (dentro del servidor MCP del usuario deseado):

```
1. Usa 'get_vacancy_by_id' con el id <N>.
2. Usa 'get_my_profile' para obtener mis datos exactos.
3. Genera un CV LaTeX profesional adaptado a esa vacante.
4. Usa 'save_latex_cv' con (<N>, tex_content: <CÓDIGO>).
```

Qué hace `save_latex_cv` por ti — **no lo dupliques en el `.tex`**:

- Detecta el idioma y **reescribe el encabezado**: destruye todo entre `\begin{document}` y la primera `\section`, e inyecta el bloque canónico (nombre, contacto, links) del usuario del MCP. Escribir tu propio encabezado es inútil: se descarta.
- Guarda en `outputs/<UID>/cv_vacante_<N>.tex`, compila el PDF y actualiza el estado a `Revisado_IA` (o `Requiere_Correccion` si falla).

Por eso el `.tex` **debe** empezar su cuerpo con un `\section{...}`, o la inyección no encuentra dónde cortar.

### Preámbulo LaTeX que compila limpio

Usa el de `DEFAULT_TEMPLATE_CONTENT` en `gemini_engine.py:45`. Imprescindibles:

- `\usepackage{xcolor}` — sin él, `\titleformat` con `\color` falla y **las líneas bajo los títulos de sección no se dibujan**.
- `\usepackage{hyperref}` — el encabezado inyectado usa `\href`.
- `\usepackage[spanish]{babel}` — funciona desde que se añadió `texlive-lang-spanish` al `Dockerfile`.

No copies el preámbulo de un `.tex` viejo de `outputs/`: algunos son anteriores a estas correcciones.

---

## 6. Verificación rápida

```bash
# 1. Servicios arriba
docker compose ps

# 2. El contenedor apunta al usuario correcto
docker exec jobhunter-mcp-marulanda-1 env | grep MCP_

# 3. La API responde
curl http://localhost:8000/

# 4. El MCP sirve el perfil correcto  → debe salir el nombre esperado
#    (en Claude Desktop: simplemente pide 'get_my_profile')
```

La comprobación que de verdad importa es la 4: **antes de generar CVs, pide `get_my_profile` y confirma que el nombre es el de la persona correcta.**

Tras generar, verifica el encabezado real del archivo:

```bash
sed -n '/begin{document}/,/section/p' job_hunter/outputs/<UID>/cv_vacante_<N>.tex | head -6
grep -c '^!' job_hunter/outputs/<UID>/cv_vacante_<N>.log   # debe ser 0
```

---

## 7. Fallos conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| Claude Desktop no muestra las tools | Editaste el config de `%APPDATA%`, que MSIX ignora | Usa la ruta de `LocalCache` (§4) |
| SSE responde pero el POST corta la conexión (`curl` exit 56 / HTTP 000, log con `TypeError: 'NoneType' object is not callable`) | El contenedor recién **recreado** aún hace login y sincroniza perfil | Espera 30–60 s y reintenta. Con `restart` (sin recrear) está listo en ~3 s |
| «La vacante N no existe» y te ofrece otras | Estás en el MCP del usuario equivocado; esa vacante es de otro titular | Comprueba el dueño en la BD (§1) y cambia de servidor |
| CV con nombre de una persona y experiencia de otra | El prompt citaba `context/mi_perfil.md` a mano | Usa `get_my_profile` (§2) |
| `Package babel Error: Unknown option 'spanish'` | Falta `texlive-lang-spanish` en la imagen | Ya está en el `Dockerfile`; si reaparece, rebuild |
| Las líneas bajo los títulos no salen | Falta `\usepackage{xcolor}` | Usa el preámbulo oficial (§5) |
| Las tools existen pero todo da error de API | Credenciales `MCP_API_*` no coinciden con la BD | Verifica con `POST /auth/login` |

---

## 8. Nota de seguridad

`docker-compose.yml` lleva contraseñas en texto plano como valores por defecto (`MCP_API_PASSWORD`, `MCP_MARULANDA_PASSWORD`) y está versionado en git. Antes de compartir o publicar el repo, muévelas a un `.env` fuera de control de versiones y deja solo `${VAR}` sin default.
