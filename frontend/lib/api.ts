const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

let _token: string | null = null

export function setAuthToken(token: string | null) {
  _token = token
}

export interface PerfilMaestro {
  nombre: string
  apellidos: string
  titulo_profesional: string
  email: string
  telefono: string
  ubicacion: string
  linkedin: string
  github: string
  resumen: string
  habilidades: {
    mecanica_manufactura: string[]
    iot_embebidos: string[]
    software_fullstack: string[]
    idiomas: string[]
  }
  experiencia: { puesto: string; empresa: string; periodo: string; logros: string[] }[]
  educacion: { titulo: string; institucion: string; anio: string }[]
  proyectos: { nombre: string; descripcion: string; tecnologias: string[] }[]
}

export type Compatibilidad = 'Alta' | 'Media' | 'Baja' | 'Nula'
export type Status =
  | 'No_Creado'
  | 'En_Proceso'
  | 'Revisado_IA'
  | 'Listo_Manual'
  | 'Requiere_Correccion'

export interface Vacante {
  id: number
  titulo: string
  empresa: string
  enlace: string
  requerimientos: string
  compatibilidad: Compatibilidad
  status: Status
  fecha_registro: string
  fecha_postulacion?: string | null
  favorito: number
}

export interface FiltrosBusqueda {
  ubicacion: string
  modalidad: 'any' | 'remoto' | 'hibrido' | 'presencial'
  pais: string
}

export interface VacanteEliminada {
  id: number
  enlace: string
  titulo: string
  fecha_eliminacion: string
}

export interface VacanteCreateInput {
  titulo: string
  empresa: string
  enlace: string
  requerimientos: string
  compatibilidad?: Compatibilidad
}

export interface VacanteBulkInput {
  titulo: string
  empresa: string
  enlace: string
  requerimientos: string
}

export interface LatexSaveResult {
  ok: boolean
  pdf: boolean
  tex_path?: string
  pdf_path?: string
  error?: string
}

export interface TemplateInfo {
  activa: string
  personalizada: boolean
  size_kb?: number | null
  modified?: number | null
}

export interface SyncHealthReport {
  ok: boolean
  state: 'healthy' | 'degraded' | 'idle'
  total: number
  by_status: Record<string, number>
  issues: Array<{
    id: number
    status: string
    pdf_exists: boolean
    tex_exists: boolean
    pdf: string
    tex: string
    desired_status?: string | null
    changed?: boolean
    error?: string | null
  }>
  dry_run: boolean
  timestamp: number
  watcher?: {
    running: boolean
    interval_seconds: number | null
    last_error: string | null
    last_snapshot: unknown
  }
}

async function req<T>(input: string, init?: RequestInit): Promise<T> {
  const hdrs: Record<string, string> = { ...(init?.headers as Record<string, string> ?? {}) }
  if (_token) hdrs['Authorization'] = `Bearer ${_token}`
  const res = await fetch(`${API}${input}`, { ...init, headers: hdrs })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json() as Promise<T>
}

export const api = {
  vacantes: (limit = 100) =>
    req<Vacante[]>(`/vacantes?limit=${limit}`),

  vacanteDetalle: (id: number) =>
    req<Vacante>(`/vacantes/${id}`),

  createVacante: (body: VacanteCreateInput) =>
    req<{ ok: boolean; id: number }>(`/vacantes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  bulkVacantes: (items: VacanteBulkInput[]) =>
    req<{ ok: boolean; insertadas: number; duplicadas: number; ids: number[]; status: string }>(`/vacantes/bulk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(items),
    }),

  deleteVacante: (id: number) =>
    req<{ ok: boolean; id: number }>(`/vacantes/${id}`, { method: 'DELETE' }),

  cambiarStatus: (id: number, status: Status) =>
    req<{ ok: boolean }>(`/vacantes/${id}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }),

  cambiarCompatibilidad: (id: number, nivel: string) =>
    req<{ ok: boolean }>(`/vacantes/${id}/compatibilidad`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ compatibilidad: nivel }),
    }),

  getLatex: async (id: number): Promise<string> => {
    const hdrs: Record<string, string> = {}
    if (_token) hdrs['Authorization'] = `Bearer ${_token}`
    const res = await fetch(`${API}/latex/${id}`, { headers: hdrs })
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
    return res.text()
  },

  saveLatex: async (id: number, content: string): Promise<LatexSaveResult> => {
    const hdrs: Record<string, string> = { 'Content-Type': 'text/plain; charset=utf-8' }
    if (_token) hdrs['Authorization'] = `Bearer ${_token}`
    const res = await fetch(`${API}/latex/${id}`, { method: 'POST', headers: hdrs, body: content })
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
    return res.json() as Promise<LatexSaveResult>
  },

  uploadTemplate: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return req<{ ok: boolean; mensaje: string }>('/upload_template', { method: 'POST', body: form })
  },

  templateActiva: () => req<TemplateInfo>('/template/activa'),
  deleteTemplate: () => req<{ ok: boolean; mensaje: string }>('/template/custom', { method: 'DELETE' }),
  downloadTemplateUrl: () => `${API}/template/download`,

  pdfUrl: (id: number) => `${API}/pdf/${id}`,

  getPdfBlob: async (id: number): Promise<Blob> => {
    const hdrs: Record<string, string> = {}
    if (_token) hdrs['Authorization'] = `Bearer ${_token}`
    const res = await fetch(`${API}/pdf/${id}`, { headers: hdrs })
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
    return res.blob()
  },

  scrape: (cantidad: number, terminos?: string[], filtros?: Partial<FiltrosBusqueda>) =>
    req<{ ok: boolean; mensaje: string; terminos?: string[]; filtros?: FiltrosBusqueda }>('/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        cantidad,
        ...(terminos?.length ? { terminos } : {}),
        ...(filtros ? { filtros } : {}),
      }),
    }),

  searchTerms: () =>
    req<{ terminos: string[]; fuente: string }>('/api/search-terms'),

  scrapeStatus: () =>
    req<{ running: boolean; last: string | null }>('/scrape/status'),

  debugSyncHealth: () =>
    req<SyncHealthReport>('/debug/sync-health'),

  perfil: () =>
    req<{ ok: boolean; contenido: string; ruta: string }>('/perfil'),

  uploadPerfil: (files: File[]) => {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    return req<{ ok: boolean; mensaje: string; archivos: string[]; chars: number; ruta: string }>('/perfil/upload', {
      method: 'POST',
      body: form,
    })
  },

  toggleFavorito: (id: number) =>
    req<{ ok: boolean; id: number; favorito: boolean }>(`/vacantes/${id}/favorito`, { method: 'PATCH' }),

  vacantesEliminadas: (limit = 200) =>
    req<VacanteEliminada[]>(`/vacantes/eliminadas?limit=${limit}`),

  restaurarEliminada: (id: number) =>
    req<{ ok: boolean; id: number }>(`/vacantes/eliminadas/${id}`, { method: 'DELETE' }),

  getPerfilMaestro: () =>
    req<PerfilMaestro>('/api/perfil'),

  savePerfilMaestro: (data: PerfilMaestro) =>
    req<{ ok: boolean; mensaje: string }>('/api/perfil', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }),
}
