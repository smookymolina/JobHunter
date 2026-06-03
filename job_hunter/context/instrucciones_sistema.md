# Instrucciones del Sistema — Job Hunter

## ⚠ REQUISITO PREVIO OBLIGATORIO
Antes de usar cualquier herramienta MCP, la API DEBE estar corriendo:
```
cd C:\Users\GIRTEC\Desktop\Trabajo\job_hunter
.\start_api.ps1
```
Si `get_vacancy_by_id` o `save_latex_cv` devuelven error de conexión:
**DETENTE. NO uses bash ni SQLite como alternativa. Ejecuta start_api.ps1 y reintenta.**

## Fuente de Verdad del Perfil
- JSON maestro: `C:\Users\GIRTEC\Desktop\Trabajo\job_hunter\data\perfil_maestro.json`
- Nombre completo: Jair Molina Arce
- Email: ingjairmolina@gmail.com
- Teléfono: 5652646108
- Ubicación: Ciudad de México, México

## Propósito
Automatizar la búsqueda, clasificación y postulación a vacantes técnicas alineadas con el perfil del usuario.

## Reglas de Compatibilidad
- **Alta**: ≥3 skills del perfil coinciden con los requerimientos
- **Media**: 1-2 skills coinciden
- **Baja**: coincidencia tangencial (industria o dominio similar)
- **Nula**: sin relación con el perfil

## Flujo de Estados (vía API REST, NUNCA sqlite directo)
`No_Creado` → `En_Proceso` → `Revisado_IA` → `Listo_Manual`
                                ↘ `Requiere_Correccion`

| Estado              | Lo activa                                                                   |
|---------------------|-----------------------------------------------------------------------------|
| En_Proceso          | **Primer paso al recibir el prompt de generación** — antes de leer perfil ni escribir LaTeX |
| Revisado_IA         | save_latex_cv exitoso (PDF compilado sin errores)                           |
| Requiere_Correccion | save_latex_cv falla (error de compilación, escritura o vacante inválida)    |
| Listo_Manual        | El usuario lo marca manualmente en el dashboard                             |

## Reglas de Generación de CV
- Leer datos REALES desde `data/perfil_maestro.json` — PROHIBIDO inventar datos
- PROHIBIDO usar corchetes [NOMBRE], [EMAIL] u otros placeholders
- Adaptar el CV al lenguaje exacto de la vacante
- Priorizar logros cuantificables sobre responsabilidades genéricas
- Máximo 1 página para posiciones junior/mid, 2 páginas para senior
- Formato LaTeX compilado a PDF con pdflatex

## Términos de Búsqueda Activos (derivados del perfil)
- "Ingeniero Mecánico"
- "Ingeniero IoT"
- "Desarrollador IoT"
- "Ingeniero Sistemas Embebidos"
- "Embedded Systems Engineer"
- "Desarrollador Full Stack"
- "Full Stack Developer Python"
- "Automatización Industrial"
- "Domótica Automatización"
- "SmartCity Developer"
- "Desarrollador Python Flask"

## Fuentes de Búsqueda
- Computrabajo México
- OCC Mundial
