# Pipeline IA — Generación de CVs y Evaluación

Job Hunter utiliza un modelo híbrido para la generación de CVs, priorizando la autonomía del servidor pero manteniendo la flexibilidad del agente local.

## 1. Flujo Primario: Generación One-click (Cloud-side)

Desde el Dashboard, el usuario puede lanzar la generación completa de un CV con un solo click. Esto es posible gracias a la integración directa con LLMs en la nube.

### Proceso:
1. **Dashboard** -> `POST /generar_cv/{id}`.
2. **API (Python)**:
    - Consulta el Perfil Maestro del usuario en PostgreSQL.
    - Envía el contexto (perfil + vacante + instrucciones) a **Groq (Llama 3.3 70B)**.
    - Recibe el código LaTeX generado.
    - Lo guarda en `outputs/{user_id}/cv_vacante_{id}.tex`.
    - Llama a `pdflatex` dentro del contenedor Docker.
3. **Resultado**: PDF generado en `outputs/{user_id}/cv_vacante_{id}.pdf` y estado actualizado a `Revisado_IA`.

## 2. Flujo Secundario: Human-in-the-Loop vía MCP

Para casos donde se requiere una edición creativa avanzada o se prefiere usar Claude 3.5 Sonnet de forma local, se mantiene el soporte para **Model Context Protocol (MCP)**.

### Herramientas MCP (`src/mcp_server.py`):
- `get_vacancy_by_id`: Recupera datos de la vacante.
- `update_compatibility`: Actualiza el nivel de match desde el chat.
- `save_latex_cv`: Escribe el código LaTeX y dispara la compilación en el servidor.

## 3. Evaluación de Compatibilidad (IA Rápida)

Cada vacante ingresada es evaluada automáticamente por un agente de Groq con un prompt de baja latencia:
- **Alta**: Cumple con >80% de los requisitos técnicos.
- **Media**: Match parcial, requiere ajustes en el CV.
- **Baja**: Pocas coincidencias de stack.
- **Nula**: No coincide con el perfil.

## 4. Editor LaTeX Integrado

Para vacantes en estado `Revisado_IA`, el frontend ofrece:
- **Ver PDF**: Previsualización instantánea en un modal.
- **Editar LaTeX**: Editor de código en vivo. Al guardar, el servidor recompila el PDF en milisegundos para reflejar los cambios manuales.

---
*Documento actualizado: 2026-06-08 (Versión multi-usuario)*
