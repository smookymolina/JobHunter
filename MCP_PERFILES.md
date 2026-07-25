# Configurar el MCP al cambiar de perfil de sesión

Guía operativa para que el generador de CVs use **los datos del usuario correcto** y los inyecte en **su carpeta correcta**.

> Regla de oro: **un servidor MCP = un usuario**. El usuario no se elige en el chat, se fija con variables de entorno al arrancar el contenedor. Si quieres generar CVs para otra persona, apuntas a **otro puerto**, no cambias nada dentro de la conversación.

---

## 0. Antes de empezar una sesión de pruebas

Cuatro pasos, en orden. Saltarse el 3 es lo que ha causado casi todos los errores.

1. **Servicios arriba** — `docker compose ps` → `api` y `postgres` en `healthy`.
2. **Si tocaste código** — `docker compose build api mcp-marulanda && docker compose up -d api mcp-marulanda` (§6). Tras un *recreate*, los MCP tardan ~30–60 s en aceptar llamadas; con `restart` bastan ~3 s.
3. **Elige el servidor del candidato correcto** y confírmalo con `get_my_profile`. El servidor lleva el nombre de su titular: `job-hunter · Maria del Pilar Marulanda Villasmil`.
4. **Trabaja siempre dentro de ese mismo servidor** — vacante, perfil y guardado. No cruces tools entre perfiles.

No hace falta configurar nada más: el servidor envía sus propias reglas al conectar (§5). Y usa el **prompt canónico** de §5, no el que pide leer `mi_perfil.md`.

Si una vacante «no existe», no concluyas nada: comprueba de quién es (§1).

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

Desde `mcp_server.py`, el 404 ya no es mudo: `_friendly_error()` lo traduce a un mensaje que explica que el sistema es multi-cuenta y que hay que buscar en el servidor hermano. Está aplicado en los cuatro puntos que consultan una vacante por ID (`get_vacancy_by_id`, `reset_vacancy`, `save_latex_cv`, `save_latex_cl`).

### 🚫 Nunca mezcles tools de dos servidores

Si descubres que la vacante pertenece al otro perfil, **cambia de servidor por completo**. No uses `get_vacancy_by_id` de un servidor y `save_latex_cv` del otro.

Ocurrió con la vacante 22 (Grupo Modelo, de Maria) pidiéndola desde la sesión de Jair: se acabó llamando al `save_latex_cv` de Marulanda desde la conversación de Jair. Salió bien de casualidad, pero es frágil — basta que los datos personales se tomen del perfil de un servidor y el guardado del otro para producir un CV con identidad cruzada.

Las tres tools de un mismo CV (`get_vacancy_by_id`, `get_my_profile`, `save_latex_cv`) **deben venir del mismo servidor**. Comprueba el `[PERFIL: …]` de cada una si tienes duda.

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

No se puede borrar ese archivo: lo usan `api.py` (`/perfil`, `/perfil/upload`) y `gemini_engine.py`. Lo que sí se corrigió es su uso como respaldo — antes, si a un usuario le faltaba su `.md`, el sistema caía a este archivo global y devolvía el perfil de Jair para cualquiera. Ahora ese respaldo solo aplica a `default_user`, que es de quien son los datos.

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

### El MCP ya se autoconfigura en cada sesión

No hay que preparar nada al abrir una conversación nueva. Cada servidor envía sus reglas al cliente en el `initialize` (parámetro `instructions` de `Server`, en `mcp_server.py`), personalizadas con su titular:

> «Este servidor genera CVs EXCLUSIVAMENTE para *Maria del Pilar Marulanda Villasmil* (`user_id=538dfb32…`)…»

Las cinco reglas que se envían: usar siempre `get_my_profile` (y **desobedecer** cualquier prompt que pida leer un perfil por ruta), no mezclar tools entre servidores, tratar el 404 como «es de otro candidato», el orden del flujo, y no escribir el encabezado a mano.

Esto se aplica solo, sin recordarlo tú. Cambiar de sesión o de perfil no requiere reconfigurar nada — únicamente **elegir el servidor correcto**.

### Prompt canónico

```
1. Usa 'get_vacancy_by_id' con el id <N>.
2. Usa 'get_my_profile' para obtener mis datos exactos.
3. Genera un CV LaTeX profesional adaptado a esa vacante.
4. Usa 'save_latex_cv' con (<N>, tex_content: <CÓDIGO>).
```

### ⚠️ No uses el prompt antiguo

Circula una versión cuyo paso 2 dice *«Lee `/app/context/mi_perfil.md` para extraer mis datos personales»*. **No la uses.** Ese archivo es el perfil legacy de Jair: si el cliente consigue leerlo, produce un CV con el nombre de un candidato y la trayectoria de otro. Ha fallado ya en dos pruebas; se salvó solo porque el cliente no tenía acceso al archivo y recurrió a `get_my_profile`.

La regla 1 de las `instructions` ahora indica explícitamente ignorar esa instrucción, pero lo robusto es no pedirla: usa el prompt canónico de arriba.

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

## 6. Si editas `mcp_server.py`, hay que reconstruir la imagen

El `Dockerfile` hace `COPY . .` y **`src/` no está montado como volumen** (solo lo están `outputs`, `data`, `context`, `logs`). El código Python vive **dentro de la imagen**.

Además, Claude Desktop **no ejecuta** el servidor MCP: se conecta con `mcp-remote` a un servidor que ya corre en Docker. Por eso:

> Reiniciar Claude Desktop **no** aplica cambios de código. Editar el `.py` y reconectar el cliente deja el contenedor sirviendo la versión anterior, en silencio.

Secuencia correcta:

```bash
docker compose build api mcp-marulanda
docker compose up -d api mcp-marulanda
```

Y **verifica que el cambio llegó** (esto es lo que delata el fallo):

```bash
docker exec jobhunter-api-1        sh -c "grep -c '_friendly_error' /app/src/mcp_server.py"
docker exec jobhunter-mcp-marulanda-1 sh -c "grep -c '_friendly_error' /app/src/mcp_server.py"
```

Si devuelve `0`, el contenedor sigue con el código viejo. Sustituye `_friendly_error` por algo propio de tu cambio.

Solo hay que reconstruir para cambios en **código** (`src/`) o en el `Dockerfile`. Los perfiles (`data/`, `context/`) y los CVs (`outputs/`) van por volumen y se ven al instante.

---

## 7. Verificación rápida

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

## 8. Fallos conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| Claude Desktop no muestra las tools | Editaste el config de `%APPDATA%`, que MSIX ignora | Usa la ruta de `LocalCache` (§4) |
| SSE responde pero el POST corta la conexión (`curl` exit 56 / HTTP 000, log con `TypeError: 'NoneType' object is not callable`) | El contenedor recién **recreado** aún hace login y sincroniza perfil | Espera 30–60 s y reintenta. Con `restart` (sin recrear) está listo en ~3 s |
| «La vacante N no existe» y te ofrece otras | Estás en el MCP del usuario equivocado; esa vacante es de otro titular | Comprueba el dueño en la BD (§1) y cambia de servidor |
| Editaste `mcp_server.py` y el comportamiento no cambia | El código va dentro de la imagen; reiniciar Claude Desktop no lo actualiza | `docker compose build` + `up -d`, y verifica con `grep` dentro del contenedor (§6) |
| CV con datos de un perfil guardado desde otro | Se mezclaron tools de dos servidores en la misma conversación | Las 3 tools del CV deben venir del mismo servidor (§1) |
| CV con nombre de una persona y experiencia de otra | El prompt citaba `context/mi_perfil.md` a mano | Usa `get_my_profile` (§2) |
| `Package babel Error: Unknown option 'spanish'` | Falta `texlive-lang-spanish` en la imagen | Ya está en el `Dockerfile`; si reaparece, rebuild |
| Las líneas bajo los títulos no salen | Falta `\usepackage{xcolor}` | Usa el preámbulo oficial (§5) |
| Las tools existen pero todo da error de API | Credenciales `MCP_API_*` no coinciden con la BD | Verifica con `POST /auth/login` |

---

## 9. Nota de seguridad

`docker-compose.yml` lleva contraseñas en texto plano como valores por defecto (`MCP_API_PASSWORD`, `MCP_MARULANDA_PASSWORD`) y está versionado en git. Antes de compartir o publicar el repo, muévelas a un `.env` fuera de control de versiones y deja solo `${VAR}` sin default.
