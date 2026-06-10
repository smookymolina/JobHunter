'use client'

import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useSession } from 'next-auth/react'
import {
  AlertCircle, Bot, Clipboard, ClipboardCheck, Clock, ExternalLink,
  Loader2, MessageCircle, Plus, Radio, RefreshCw, Send, Sparkles,
  Star, WifiOff, X,
} from 'lucide-react'
import Loader from '@/components/ui/Loader'
import { api, type Status, type SyncHealthReport, type Vacante } from '@/lib/api'
import AddVacanteModal from '@/components/AddVacanteModal'
import KanbanBoard from '@/components/KanbanBoard'
import StatusBadge, { compatBadge } from '@/components/StatusBadge'

const STAT_COLS: {
  id: Status
  label: string
  numberColor: string
  icon: React.ElementType
  cardClass: string
}[] = [
  {
    id: 'No_Creado',
    label: 'Sin Iniciar',
    numberColor: 'text-slate-600 dark:text-slate-300',
    icon: Clock,
    cardClass: '',
  },
  {
    id: 'En_Proceso',
    label: 'En Proceso',
    numberColor: 'text-blue-500',
    icon: Loader2,
    cardClass: '',
  },
  {
    id: 'Revisado_IA',
    label: 'Revisado IA',
    numberColor: 'text-amber-500',
    icon: Bot,
    cardClass: '',
  },
  {
    id: 'Requiere_Correccion',
    label: 'Con Error',
    numberColor: 'text-rose-500',
    icon: AlertCircle,
    cardClass: '',
  },
  {
    id: 'Listo_Manual',
    label: 'CV Enviado',
    numberColor: 'text-emerald-500',
    icon: Send,
    cardClass: 'border-emerald-100 bg-emerald-50/60 dark:border-emerald-800/50 dark:bg-emerald-900/10',
  },
  {
    id: 'Entrevista',
    label: 'Entrevistas',
    numberColor: 'text-purple-500',
    icon: MessageCircle,
    cardClass: 'border-purple-100 bg-purple-50/60 dark:border-purple-800/50 dark:bg-purple-900/10',
  },
]

const _MAESTRO = String.raw`C:\Users\GIRTEC\Desktop\Trabajo\job_hunter\data\perfil_maestro.json`
function buildMcpPrompt(id: number) {
  return (
    `1. Usa 'get_vacancy_by_id' (${id}). ` +
    `2. Lee '${_MAESTRO}' para extraer mis datos personales exactos (NOMBRE, APELLIDOS, CONTACTO). ` +
    `3. Genera CV LaTeX profesional usando esos datos. ` +
    `4. Usa 'save_latex_cv' (${id}, tex_content: <CÓDIGO>).`
  )
}

function JobDetailsModal({ vacante, onClose }: { vacante: Vacante; onClose: () => void }) {
  const [copied, setCopied] = useState(false)
  const [latexOpen, setLatexOpen] = useState(false)
  const [latexContent, setLatexContent] = useState<string | null>(null)
  const [latexLoading, setLatexLoading] = useState(false)
  const [latexCopied, setLatexCopied] = useState(false)
  const prompt = buildMcpPrompt(vacante.id)

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [])

  const handleToggleLatex = async () => {
    if (!latexOpen && latexContent === null) {
      setLatexLoading(true)
      try {
        const tex = await api.getLatex(vacante.id)
        setLatexContent(tex)
      } catch {
        setLatexContent('(No hay contenido LaTeX generado aún para esta vacante.)')
      } finally {
        setLatexLoading(false)
      }
    }
    setLatexOpen(prev => !prev)
  }

  const handleCopyLatex = async () => {
    if (!latexContent) return
    try {
      await navigator.clipboard.writeText(latexContent)
      setLatexCopied(true)
      setTimeout(() => setLatexCopied(false), 2500)
    } catch { /* silent */ }
  }

  if (typeof document === 'undefined') return null

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch { /* silent */ }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex h-[88vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-900"
        onClick={e => e.stopPropagation()}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-500/60 to-transparent" />

        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div className="min-w-0 flex-1 pr-4">
            <h2 className="text-[17px] font-semibold leading-snug text-slate-900 dark:text-slate-100">
              {vacante.titulo}
            </h2>
            <p className="mt-1 text-[13px] font-medium text-slate-500 dark:text-slate-400">{vacante.empresa}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <StatusBadge status={vacante.status} />
              <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${compatBadge(vacante.compatibilidad)}`}>
                {vacante.compatibilidad}
              </span>
              {vacante.fecha_registro && (
                <span className="inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                  {vacante.fecha_registro.slice(0, 10)}
                </span>
              )}
              {vacante.fecha_postulacion && (
                <span className="inline-flex items-center rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                  Postulada {vacante.fecha_postulacion.slice(0, 10)}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-200 p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X size={15} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 space-y-4 overflow-y-auto p-5 [scrollbar-width:thin]">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Descripción / Requerimientos
            </p>
            <div className="whitespace-pre-wrap rounded-xl border border-slate-100 bg-slate-50 p-4 text-[13px] leading-relaxed text-slate-600 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
              {(vacante.requerimientos ?? '').trim() || 'Sin descripción capturada.'}
            </div>
          </div>

          <div>
            <button
              onClick={handleToggleLatex}
              className="mb-2 flex w-full items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-500 dark:hover:bg-slate-800/50"
            >
              <span>Contenido LaTeX Generado</span>
              <span className="text-[10px] normal-case tracking-normal">
                {latexOpen ? '▲ ocultar' : '▼ expandir'}
              </span>
            </button>
            {latexOpen && (
              <div className="relative">
                {latexLoading ? (
                  <div className="flex items-center justify-center rounded-xl border border-slate-100 bg-slate-50 py-6 dark:border-slate-700 dark:bg-slate-800/50">
                    <Loader2 size={16} className="animate-spin text-slate-400" />
                  </div>
                ) : (
                  <>
                    <textarea
                      readOnly
                      value={latexContent ?? ''}
                      rows={12}
                      className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-4 pr-10 font-mono text-[11px] leading-relaxed text-slate-600 focus:outline-none dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-400"
                    />
                    <button
                      onClick={handleCopyLatex}
                      title={latexCopied ? 'Copiado' : 'Copiar LaTeX'}
                      className="absolute right-2 top-2 rounded-lg border border-slate-200 p-1.5 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                    >
                      {latexCopied
                        ? <ClipboardCheck size={13} className="text-emerald-500" />
                        : <Clipboard size={13} className="text-slate-400" />}
                    </button>
                    {latexCopied && <p className="mt-1 text-[11px] text-emerald-500">¡LaTeX copiado!</p>}
                  </>
                )}
              </div>
            )}
          </div>

          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              Prompt MCP — CV Generator
            </p>
            <div className="relative rounded-xl border border-slate-200 bg-slate-50 p-4 pr-10 font-mono text-[11px] leading-relaxed text-slate-600 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-400">
              {prompt}
              <button
                onClick={handleCopy}
                title={copied ? 'Copiado' : 'Copiar prompt'}
                className="absolute right-2 top-2 rounded-lg border border-slate-200 p-1.5 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                {copied
                  ? <ClipboardCheck size={13} className="text-emerald-500" />
                  : <Clipboard size={13} className="text-slate-400" />}
              </button>
            </div>
            {copied && <p className="mt-1 text-[11px] text-emerald-500">¡Copiado al portapapeles!</p>}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center gap-2 border-t border-slate-100 px-5 py-3 dark:border-slate-800">
          {vacante.enlace && (
            <a
              href={vacante.enlace}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-[12px] text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <ExternalLink size={12} /> Ver original
            </a>
          )}
          <button
            onClick={handleCopy}
            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-1.5 text-[12px] font-semibold transition-colors ${
              copied
                ? 'border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-700/30 dark:bg-emerald-950/30 dark:text-emerald-300'
                : 'bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100'
            }`}
          >
            {copied ? <ClipboardCheck size={12} /> : <Clipboard size={12} />}
            {copied ? 'Copiado' : 'Copiar Prompt CV'}
          </button>
          <button
            onClick={onClose}
            className="ml-auto text-[12px] text-slate-400 transition-colors hover:text-slate-600 dark:hover:text-slate-300"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}

export default function DashboardPage() {
  const { status } = useSession()
  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [spinning, setSpinning] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [scrapeRunning, setScrapeRunning] = useState(false)
  const [health, setHealth] = useState<SyncHealthReport | null>(null)
  const [activeFilter, setActiveFilter] = useState<Status | null>(null)
  const [selectedJob, setSelectedJob] = useState<Vacante | null>(null)

  const fetchVacantes = useCallback(async (silent = false) => {
    let data: Vacante[] | null = null
    let failed = false
    try {
      data = await api.vacantes()
    } catch {
      // One retry after 500ms — covers auth-token race on hard reload
      await new Promise<void>(r => setTimeout(r, 500))
      try {
        data = await api.vacantes()
      } catch {
        failed = true
      }
    }
    if (data !== null) {
      setVacantes(data)
      if (!silent) setError('')
    } else if (failed && !silent) {
      setError('No se pudo conectar con la API. Verifica http://127.0.0.1:8000.')
    }
    if (!silent) {
      setLoading(false)
      setSpinning(false)
    }
  }, [])

  useEffect(() => {
    const checkScrape = async () => {
      try {
        const s = await api.scrapeStatus()
        setScrapeRunning(s.running)
      } catch {
        setScrapeRunning(false)
      }
    }
    void checkScrape()
    const id = setInterval(checkScrape, 3000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setHealth(await api.debugSyncHealth())
      } catch {
        setHealth(null)
      }
    }
    void checkHealth()
    const id = setInterval(checkHealth, 5000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    if (status === 'loading') {
      setLoading(true)
      return
    }
    if (status !== 'authenticated') {
      setLoading(false)
      setError('Sesión no autenticada.')
      return
    }
    void fetchVacantes()
  }, [fetchVacantes, status])

  useEffect(() => {
    if (status !== 'authenticated') return
    const id = setInterval(() => {
      void fetchVacantes(true)
    }, 2000)
    return () => clearInterval(id)
  }, [fetchVacantes, status])

  const handleRefresh = () => {
    setSpinning(true)
    void fetchVacantes()
  }

  const count = (s: Status) => vacantes.filter(v => v.status === s).length
  const healthState = health?.state ?? 'idle'

  const healthBadge =
    healthState === 'healthy'
      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800'
      : healthState === 'degraded'
        ? 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800'
        : 'bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-800/50 dark:text-slate-400 dark:border-slate-700'

  const healthDotColor =
    healthState === 'healthy'
      ? 'bg-emerald-500'
      : healthState === 'degraded'
        ? 'bg-amber-400'
        : 'bg-slate-400 dark:bg-slate-500'

  return (
    <div className="flex h-full flex-col overflow-hidden bg-radial-indigo">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 flex shrink-0 flex-col gap-2 border-b border-slate-100 bg-white/90 px-6 py-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">
              Dashboard
            </h1>
            <div className="mt-1.5 flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${healthBadge}`}>
                <span className={`h-1.5 w-1.5 animate-pulse rounded-full ${healthDotColor}`} />
                {healthState === 'healthy'
                  ? 'Salud del sistema: estable'
                  : healthState === 'degraded'
                    ? `Degradada · ${health?.issues.length ?? 0} incidencias`
                    : `Sin telemetría · ${vacantes.length} vacantes`}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={spinning}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <RefreshCw
                size={13}
                className={`transition-transform duration-500 ${spinning ? 'animate-spin' : 'hover:rotate-180'}`}
              />
              Actualizar
            </button>
            <button
              onClick={() => setAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-1.5 text-[12px] font-semibold text-white shadow-sm transition-all duration-200 hover:scale-105 hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
            >
              <Plus size={14} />
              Añadir Vacante
            </button>
          </div>
        </div>

        {scrapeRunning && (
          <div className="flex items-center gap-2 self-start rounded-xl border border-blue-200 bg-blue-50 px-3 py-1.5 text-[12px] text-blue-700 dark:border-blue-800/40 dark:bg-blue-950/30 dark:text-blue-300">
            <Radio size={13} className="animate-pulse" />
            Buscando vacantes de forma autónoma...
            <Loader2 size={12} className="animate-spin opacity-70" />
          </div>
        )}
      </header>

      {/* ── Stat Cards ─────────────────────────────────────────────── */}
      {!loading && !error && (
        <div className="shrink-0 border-b border-slate-100 px-6 py-4 dark:border-slate-800">
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
            {STAT_COLS.map(({ id, label, numberColor, icon: Icon, cardClass }) => {
              const isActive = activeFilter === id
              return (
                <button
                  key={id}
                  onClick={() => setActiveFilter(isActive ? null : id)}
                  className={`group relative flex flex-col rounded-2xl border bg-white p-4 text-left transition-all duration-200 hover:scale-[1.02] hover:shadow-md dark:bg-slate-900 ${
                    isActive
                      ? 'ring-2 ring-emerald-500 shadow-lg border-emerald-200 dark:border-emerald-800/60 dark:bg-slate-800'
                      : activeFilter !== null
                        ? 'opacity-60 border-slate-100 dark:border-slate-800'
                        : 'border-slate-100 dark:border-slate-800'
                  } ${cardClass}`}
                >
                  <div className="flex items-start justify-between">
                    <span className={`text-3xl font-bold leading-none ${numberColor}`}>
                      {count(id)}
                    </span>
                    <Icon size={16} className={`mt-0.5 transition-colors ${isActive ? 'text-emerald-500' : 'text-slate-300 dark:text-slate-600'}`} />
                  </div>
                  <p className="mt-2 text-[11px] font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                    {label}
                  </p>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Main ───────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden px-4 py-4">
        {loading && (
          <div className="flex h-full items-center justify-center">
            <Loader size={36} label="Cargando vacantes..." />
          </div>
        )}

        {error && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <WifiOff size={32} className="text-slate-300 dark:text-slate-700" />
            <p className="max-w-sm text-[13px] text-slate-500">{error}</p>
            <button
              onClick={handleRefresh}
              className="text-[12px] text-rose-500 transition-colors hover:text-rose-400"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && activeFilter === null && (
          <>
            <KanbanBoard
              vacantes={vacantes}
              onRefresh={handleRefresh}
              activeFilter={null}
              setActiveFilter={setActiveFilter}
            />
            <button
              onClick={() => setAddOpen(true)}
              className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-[13px] font-semibold text-white shadow-lg shadow-slate-900/20 transition-transform duration-200 hover:scale-105 active:scale-95 dark:bg-white dark:text-slate-900 dark:shadow-white/10"
            >
              <Sparkles size={15} />
              Añadir Vacante
            </button>
          </>
        )}

        {!loading && !error && activeFilter !== null && (() => {
          const col = STAT_COLS.find(c => c.id === activeFilter)!
          const ColIcon = col.icon
          const compatRank: Record<string, number> = { Alta: 3, Media: 2, Baja: 1, Nula: 0 }
          const rows = [...vacantes]
            .filter(v => v.status === activeFilter)
            .sort((a, b) => {
              if (b.favorito !== a.favorito) return b.favorito - a.favorito
              const ca = compatRank[a.compatibilidad] ?? 0
              const cb = compatRank[b.compatibilidad] ?? 0
              if (cb !== ca) return cb - ca
              return b.id - a.id
            })
          return (
            <div className="flex h-full flex-col overflow-hidden">
              <div className="mb-3 flex shrink-0 items-center justify-between">
                <div className="flex items-center gap-2">
                  <ColIcon size={15} className={col.numberColor} />
                  <span className="text-[13px] font-semibold text-slate-700 dark:text-slate-300">
                    {col.label}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                    {rows.length}
                  </span>
                </div>
                <button
                  onClick={() => setActiveFilter(null)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                >
                  <X size={12} />
                  Ver tablero completo
                </button>
              </div>

              <div className="flex-1 overflow-auto rounded-2xl border border-slate-100 shadow-sm dark:border-slate-800">
                <table className="w-full text-left text-[12px]">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                      <th className="px-4 py-3 font-semibold text-slate-500 dark:text-slate-500">ID</th>
                      <th className="px-4 py-3 font-semibold text-slate-500 dark:text-slate-500">Puesto</th>
                      <th className="px-4 py-3 font-semibold text-slate-500 dark:text-slate-500">Empresa</th>
                      <th className="px-4 py-3 font-semibold text-slate-500 dark:text-slate-500">Compat.</th>
                      <th className="px-4 py-3 font-semibold text-slate-500 dark:text-slate-500">Status</th>
                      <th className="px-4 py-3 font-semibold text-slate-500 dark:text-slate-500">Fecha</th>
                      <th className="px-4 py-3 font-semibold text-slate-500 dark:text-slate-500"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50 dark:divide-slate-800/60">
                    {rows.map((v, i) => (
                      <tr
                        key={v.id}
                        onClick={() => setSelectedJob(v)}
                        className={`cursor-pointer transition-colors hover:bg-indigo-50/60 dark:hover:bg-indigo-900/10 ${
                          i % 2 === 0 ? 'bg-white dark:bg-slate-900' : 'bg-slate-50/40 dark:bg-slate-900/60'
                        }`}
                      >
                        <td className="px-4 py-3 text-slate-400 dark:text-slate-600">
                          <span className="flex items-center gap-1">
                            #{v.id}
                            {!!v.favorito && <Star size={10} className="fill-amber-400 text-amber-400" />}
                          </span>
                        </td>
                        <td className="max-w-[220px] px-4 py-3">
                          <p className="truncate font-medium text-slate-800 dark:text-slate-200">{v.titulo}</p>
                        </td>
                        <td className="px-4 py-3 text-slate-500 dark:text-slate-500">{v.empresa}</td>
                        <td className="px-4 py-3">
                          <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${compatBadge(v.compatibilidad)}`}>
                            {v.compatibilidad}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={v.status} />
                        </td>
                        <td className="px-4 py-3 text-slate-400 dark:text-slate-600">{v.fecha_registro?.slice(0, 10)}</td>
                        <td className="px-4 py-3">
                          {v.enlace && (
                            <a
                              href={v.enlace}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={e => e.stopPropagation()}
                              className="text-slate-400 transition-colors hover:text-slate-600 dark:text-slate-600 dark:hover:text-slate-400"
                            >
                              <ExternalLink size={13} />
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                    {rows.length === 0 && (
                      <tr>
                        <td colSpan={7} className="px-4 py-10 text-center text-slate-400 dark:text-slate-600">
                          No hay vacantes en este estado.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })()}
      </main>

      <AddVacanteModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSuccess={handleRefresh}
      />

      {selectedJob && (
        <JobDetailsModal
          vacante={selectedJob}
          onClose={() => setSelectedJob(null)}
        />
      )}
    </div>
  )
}
