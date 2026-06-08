# Job Hunter

Plataforma multi-usuario (SaaS-ready) para automatizar la búsqueda de empleo, generar CVs en LaTeX y coordinar el flujo de IA sobre PostgreSQL.

## Lectura base
- `docs/README_IA.md`
- `docs/ARQUITECTURA_Y_BD.md`
- `docs/PIPELINE_IA.md`

## Resumen operativo
- **Backend**: FastAPI (Python 3.11) + PostgreSQL (pg8000).
- **Frontend**: Next.js 16 + NextAuth.js + Tailwind 4.
- **IA Engine**: Generación One-click vía Groq/Cloud (Llama 3).
- **Seguridad**: Autenticación JWT, cifrado simétrico para tokens de Telegram.
- **Infraestructura**: Totalmente contenerizado con `docker-compose`.

## Flujo
```text
Usuario -> NextAuth -> Scrape (Playwright) -> PostgreSQL -> One-click AI -> .tex -> pdflatex -> PDF
```

## Cambios clave (v1.2.0)
- **Multi-tenancy**: Aislamiento completo de vacantes y perfiles por `user_id`.
- **PostgreSQL**: Migración completada desde SQLite para escalabilidad Cloud.
- **One-click Generation**: El backend genera y compila el CV automáticamente sin intervención manual.
- **Telegram Bot**: Integración segura con cifrado de tokens por usuario.
- **Paywall**: Sistema de límites por tier (Free/Pro) integrado en el Dashboard.

## Política de rutas absolutas (rev 2026-06-03)

Todos los módulos usan rutas absolutas derivadas de `__file__`:

```python
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
```

| Constante | Ruta absoluta canónica |
|---|---|
| `DB_PATH` | `job_hunter/db/vacantes.db` |
| `OUTPUTS_DIR` | `job_hunter/outputs/` |
| `TEMPLATES_DIR` | `job_hunter/latex_templates/` |
| `CONTEXT_DIR` | `job_hunter/context/` (o `PROFILE_BASE_DIR` del `.env`) |

Los archivos `.tex` y `.pdf` generados aterrizan **siempre** en `job_hunter/outputs/`.
Nunca se escriben en la raíz del proyecto.
