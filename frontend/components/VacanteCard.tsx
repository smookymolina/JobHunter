'use client'

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clipboard,
  ClipboardCheck,
  Code,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Maximize2,
  MessageCircle,
  RotateCcw,
  Star,
  Trash2,
  X,
} from 'lucide-react'
import { api, type Vacante, type Status } from '@/lib/api'
import StatusBadge, { compatBadge } from './StatusBadge'
import JobDetailsModal from './JobDetailsModal'

// ── Modales ───────────────────────────────────────────────────────────────────

function PdfModal({ vacanteId, onClose }: { vacanteId: number; onClose: () => void }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loadingPdf, setLoadingPdf] = useState(true)
  const [pdfErr, setPdfErr] = useState('')
  const pdfUrl = blobUrl ?? ''

  useEffect(() => {
    let objectUrl = ''
    api.getPdfBlob(vacanteId)
      .then(blob => {
        objectUrl = URL.createObjectURL(blob)
        setBlobUrl(objectUrl)
      })
      .catch(e => setPdfErr(e instanceof Error ? e.message : 'Error al cargar el PDF.'))
      .finally(() => setLoadingPdf(false))
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [vacanteId])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  if (typeof document === 'undefined') return null

  const handleDownload = () => {
    if (!blobUrl) return
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = `cv-vacante-${vacanteId}.pdf`
    a.click()
  }

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl bg-zinc-900 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-between items-center border-b border-zinc-800 bg-zinc-950 p-3">
          <h3 className="font-medium text-white">Visor de CV</h3>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">Cerrar ✕</button>
        </div>
        <div className="relative flex-1 bg-zinc-950 overflow-hidden">
          {loadingPdf && (
            <div className="absolute inset-0 flex items-center justify-center gap-2 text-zinc-400">
              <Loader2 size={18} className="animate-spin" />
              <span className="text-[12px]">Cargando PDF...</span>
            </div>
          )}
          {pdfErr && (
            <div className="absolute inset-0 flex items-center justify-center p-4 text-center">
              <p className="text-[12px] text-rose-400">{pdfErr}</p>
            </div>
          )}
          {pdfUrl && !pdfErr && (
            <iframe
              src={pdfUrl}
              className="h-full w-full border-none"
              title={`CV vacante #${vacanteId}`}
            />
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}

function LatexModal({
  vacanteId,
  onClose,
  onSaved,
}: {
  vacanteId: number
  onClose: () => void
  onSaved: () => void
}) {
  const [tex, setTex]         = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [result, setResult]   = useState<{ ok: boolean; msg: string } | null>(null)

  useEffect(() => {
    api.getLatex(vacanteId)
      .then(setTex)
      .catch(() => setTex('% Error cargando el archivo .tex'))
      .finally(() => setLoading(false))
  }, [vacanteId])

  const handleSave = async () => {
    setSaving(true); setResult(null)
    try {
      const r = await api.saveLatex(vacanteId, tex)
      setResult({
        ok: r.pdf,
        msg: r.pdf ? '✓ PDF compilado correctamente. Abre el visor para verlo.' : `⚠ ${r.error}`,
      })
      if (r.pdf) onSaved()
    } catch (e) {
      setResult({ ok: false, msg: e instanceof Error ? e.message : 'Error desconocido.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative flex h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-950"
        onClick={e => e.stopPropagation()}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-500/60 to-transparent" />
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Code size={13} className="text-indigo-500 dark:text-indigo-400" />
            <span className="text-[13px] font-medium text-slate-700 dark:text-slate-200">Editor LaTeX — vacante #{vacanteId}</span>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-200 p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X size={14} />
          </button>
        </div>

        <div className="flex-1 overflow-hidden p-3">
          {loading ? (
            <div className="flex h-full items-center justify-center gap-2 text-slate-400 dark:text-slate-600">
              <Loader2 size={18} className="animate-spin" />
              <span className="text-[12px]">Cargando LaTeX...</span>
            </div>
          ) : (
            <textarea
              value={tex}
              onChange={e => setTex(e.target.value)}
              className="h-full w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-[12px] leading-relaxed text-slate-700 outline-none transition-colors focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300 dark:focus:border-indigo-500/40 [scrollbar-width:thin]"
              spellCheck={false}
            />
          )}
        </div>

        {result && (
          <div className={`mx-3 mb-2 rounded-xl border px-3 py-2 text-[12px] ${
            result.ok
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-700/30 dark:bg-emerald-950/30 dark:text-emerald-300'
              : 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-700/30 dark:bg-rose-950/30 dark:text-rose-300'
          }`}>
            {result.msg}
          </div>
        )}

        <div className="flex shrink-0 justify-end gap-2 border-t border-slate-100 px-4 py-3 dark:border-slate-800">
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-[12px] text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="btn-shimmer inline-flex items-center gap-2 rounded-lg px-4 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50"
          >
            {saving ? <Loader2 size={12} className="animate-spin" /> : <Code size={12} />}
            {saving ? 'Compilando...' : 'Guardar y Compilar'}
          </button>
        </div>
      </div>
    </div>
  )
}


function UndoToast({
  newLabel,
  onUndo,
  onClose,
}: {
  newLabel: string
  onUndo: () => void
  onClose: () => void
}) {
  if (typeof document === 'undefined') return null
  return createPortal(
    <div className="fixed bottom-5 right-5 z-[70] flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
      <span className="text-[12px] text-slate-700 dark:text-slate-300">
        Movido a <strong className="font-semibold">{newLabel}</strong>
      </span>
      <button
        onClick={onUndo}
        className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500 px-3 py-1 text-[11px] font-bold text-white hover:bg-rose-600"
      >
        <RotateCcw size={11} /> Deshacer
      </button>
      <button onClick={onClose} className="text-slate-400 transition-colors hover:text-slate-600 dark:hover:text-slate-200">
        <X size={14} />
      </button>
    </div>,
    document.body,
  )
}

// ── Tarjeta ───────────────────────────────────────────────────────────────────

interface Props {
  vacante: Vacante
  onStatusChange?: () => void
}

const STATUS_OPTIONS: { value: Status; label: string }[] = [
  { value: 'No_Creado',            label: 'Sin iniciar' },
  { value: 'En_Proceso',          label: 'En proceso' },
  { value: 'Revisado_IA',         label: 'Revisado IA' },
  { value: 'Requiere_Correccion', label: 'Requiere corrección' },
  { value: 'Listo_Manual',        label: 'CV Enviado' },
  { value: 'Entrevista',          label: 'Entrevista' },
]

export default function VacanteCard({ vacante, onStatusChange }: Props) {
  const [copied, setCopied]           = useState(false)
  const [expanded, setExpanded]       = useState(false)
  const [pdfOpen, setPdfOpen]         = useState(false)
  const [latexOpen, setLatexOpen]     = useState(false)
  const [detailOpen, setDetailOpen]   = useState(false)
  const [busyAction, setBusyAction]   = useState<'status' | 'delete' | 'fav' | null>(null)
  const [statusDraft, setStatusDraft] = useState<Status>(vacante.status)
  const [errMsg, setErrMsg]           = useState('')
  const [esFavorito, setEsFavorito]   = useState(!!vacante.favorito)
  const [toast, setToast]             = useState<{ prevStatus: Status; newStatus: Status } | null>(null)
  const toastTidRef                   = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => { setStatusDraft(vacante.status) }, [vacante.status])
  useEffect(() => { setEsFavorito(!!vacante.favorito) }, [vacante.favorito])
  useEffect(() => () => { if (toastTidRef.current) clearTimeout(toastTidRef.current) }, [])

  const handleFavorito = async () => {
    setBusyAction('fav')
    try {
      const r = await api.toggleFavorito(vacante.id)
      setEsFavorito(r.favorito)
      onStatusChange?.()
    } catch { /* silent */ }
    finally { setBusyAction(null) }
  }

  const handleCopiarPrompt = async () => {
    try {
      let path = '[ruta del perfil maestro]'
      try { path = (await api.perfil()).ruta } catch { /* use placeholder */ }
      const prompt = (
        `1. Usa 'get_vacancy_by_id' (${vacante.id}). ` +
        `2. Lee '${path}' para extraer mis datos personales exactos (NOMBRE, APELLIDOS, CONTACTO). ` +
        `3. Genera CV LaTeX profesional. ` +
        `4. Usa 'save_latex_cv' (${vacante.id}, tex_content: <CÓDIGO>).`
      )
      await navigator.clipboard.writeText(prompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch {
      setErrMsg('No se pudo acceder al portapapeles.')
    }
  }

  const handleDelete = async () => {
    if (!window.confirm(`Eliminar la vacante #${vacante.id}?`)) return
    setBusyAction('delete')
    try { await api.deleteVacante(vacante.id); onStatusChange?.() }
    catch (error) { setErrMsg(error instanceof Error ? error.message : 'No se pudo borrar.') }
    finally { setBusyAction(null) }
  }

  const handleStatusChange = async (nextStatus: Status) => {
    if (nextStatus === vacante.status) return
    const prevStatus = vacante.status
    setBusyAction('status')
    try {
      await api.cambiarStatus(vacante.id, nextStatus)
      onStatusChange?.()
      if (toastTidRef.current) clearTimeout(toastTidRef.current)
      toastTidRef.current = setTimeout(() => setToast(null), 6000)
      setToast({ prevStatus, newStatus: nextStatus })
    } catch (error) {
      setErrMsg(error instanceof Error ? error.message : 'No se pudo cambiar el estado.')
      setStatusDraft(vacante.status)
    } finally {
      setBusyAction(null)
    }
  }

  const handleUndo = async () => {
    if (!toast) return
    const { prevStatus } = toast
    if (toastTidRef.current) clearTimeout(toastTidRef.current)
    toastTidRef.current = null
    setToast(null)
    setBusyAction('status')
    setStatusDraft(prevStatus)
    try {
      await api.cambiarStatus(vacante.id, prevStatus)
      onStatusChange?.()
    } catch (error) {
      setErrMsg(error instanceof Error ? error.message : 'No se pudo deshacer.')
      setStatusDraft(vacante.status)
    } finally {
      setBusyAction(null)
    }
  }

  const dismissToast = () => {
    if (toastTidRef.current) clearTimeout(toastTidRef.current)
    toastTidRef.current = null
    setToast(null)
  }

  return (
    <>
      <article className="card-hover group relative flex flex-col rounded-xl border border-slate-100 bg-white p-3 shadow-sm hover:shadow-md dark:border-slate-700/50 dark:bg-slate-800">
        {/* Barra de compatibilidad */}
        <div className={`absolute left-0 top-2 bottom-2 w-[3px] rounded-r-full ${
          vacante.compatibilidad === 'Alta'  ? 'bg-emerald-400' :
          vacante.compatibilidad === 'Media' ? 'bg-amber-400'   :
          vacante.compatibilidad === 'Baja'  ? 'bg-slate-300 dark:bg-slate-600' : 'bg-slate-200 dark:bg-slate-700'
        }`} />

        {/* ── Vista colapsada ──────────────────────────────────────── */}
        <div className="pl-3 flex items-center justify-between gap-2 min-w-0">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <p className="truncate text-[13px] font-semibold leading-tight text-slate-800 dark:text-slate-100">
                {vacante.titulo}
              </p>
              {vacante.status === 'En_Proceso' && (
                <Loader2 size={12} className="shrink-0 animate-spin text-blue-400" />
              )}
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 flex-wrap">
              <p className="truncate text-[11px] text-slate-400 dark:text-slate-500">{vacante.empresa}</p>
              <StatusBadge status={vacante.status} />
              <span className={`inline-flex rounded-full border px-1.5 py-0 text-[10px] font-medium ${compatBadge(vacante.compatibilidad)}`}>
                {vacante.compatibilidad}
              </span>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button
              onClick={handleFavorito}
              disabled={busyAction === 'fav'}
              title={esFavorito ? 'Quitar de favoritos' : 'Marcar como favorito'}
              className="rounded-md p-1 transition-colors hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-700"
            >
              <Star
                size={14}
                className={esFavorito ? 'fill-amber-400 text-amber-400' : 'text-slate-300 hover:text-amber-400 dark:text-slate-600'}
              />
            </button>
            <button
              onClick={() => setDetailOpen(true)}
              title="Ver detalle completo"
              className="rounded-md p-1 transition-colors hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              <Maximize2 size={13} className="text-slate-300 dark:text-slate-600" />
            </button>
            <button
              onClick={() => setExpanded(v => !v)}
              className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-[11px] text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:border-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
            >
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              <span className="hidden sm:inline">{expanded ? 'Cerrar' : 'Detalles'}</span>
            </button>
          </div>
        </div>

        {/* ── Vista expandida ──────────────────────────────────────── */}
        <div className={`pl-3 overflow-hidden transition-all duration-200 ${
          expanded ? 'max-h-[600px] opacity-100 mt-3' : 'max-h-0 opacity-0'
        }`}>
          <div className="space-y-2">
            {/* Fecha + enlace */}
            <div className="flex items-center gap-3 text-[11px] text-slate-400 dark:text-slate-500">
              {vacante.fecha_registro && <span>{vacante.fecha_registro.slice(0, 10)}</span>}
              {vacante.enlace && (
                <a
                  href={vacante.enlace}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors dark:text-slate-400 dark:hover:text-slate-200"
                >
                  Abrir <ExternalLink size={10} />
                </a>
              )}
            </div>

            {/* Requerimientos */}
            <div className="max-h-32 overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50 p-2 text-[12px] leading-relaxed text-slate-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-400">
              {(vacante.requerimientos ?? '').trim() || 'Sin requerimientos capturados.'}
            </div>

            {/* Portapapeles MCP */}
            {(vacante.status === 'No_Creado' || vacante.status === 'Requiere_Correccion') && (
              <button
                onClick={handleCopiarPrompt}
                className={`btn-shimmer inline-flex w-full items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-[12px] font-semibold shadow-lg transition-colors ${
                  copied
                    ? 'border border-emerald-200 bg-emerald-50 !bg-none text-emerald-700 dark:border-emerald-700/40 dark:bg-emerald-950/40 dark:text-emerald-300'
                    : 'text-white'
                }`}
              >
                {copied ? <ClipboardCheck size={13} /> : <Clipboard size={13} />}
                {copied
                  ? 'Copiado al portapapeles'
                  : vacante.status === 'Requiere_Correccion'
                    ? 'Copiar Prompt MCP (corrección)'
                    : 'Copiar Prompt MCP'}
              </button>
            )}

            {/* PDF + Editor LaTeX para Revisado_IA */}
            {vacante.status === 'Revisado_IA' && (
              <div className="flex gap-1.5">
                <button
                  onClick={() => setPdfOpen(true)}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-[12px] font-medium text-amber-700 transition-colors hover:bg-amber-100 dark:border-amber-700/30 dark:bg-amber-950/30 dark:text-amber-300 dark:hover:bg-amber-900/40"
                >
                  <FileText size={13} /> Ver PDF
                </button>
                <button
                  onClick={() => setLatexOpen(true)}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-[12px] font-medium text-indigo-700 transition-colors hover:bg-indigo-100 dark:border-indigo-700/30 dark:bg-indigo-950/30 dark:text-indigo-300 dark:hover:bg-indigo-900/40"
                >
                  <Code size={13} /> Editar LaTeX
                </button>
                <button
                  onClick={async () => {
                    try {
                      const blob = await api.getPdfBlob(vacante.id)
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url; a.download = `cv-vacante-${vacante.id}.pdf`; a.click()
                      setTimeout(() => URL.revokeObjectURL(url), 5000)
                    } catch { /* silent */ }
                  }}
                  className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-2.5 py-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 dark:border-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-200"
                  title="Descargar PDF"
                >
                  <Download size={13} />
                </button>
              </div>
            )}

            {vacante.status === 'Entrevista' && (
              <div className="flex flex-col gap-0.5 rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 dark:border-purple-700/25 dark:bg-purple-950/25">
                <div className="flex items-center gap-2 text-[12px] font-medium text-purple-700 dark:text-purple-400">
                  <MessageCircle size={13} /> En etapa de entrevista — sigue adelante!
                </div>
              </div>
            )}

            {vacante.status === 'Listo_Manual' && (
              <div className="flex flex-col gap-0.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 dark:border-emerald-700/25 dark:bg-emerald-950/25">
                <div className="flex items-center gap-2 text-[12px] font-medium text-emerald-700 dark:text-emerald-400">
                  <CheckCircle size={13} /> CV enviado — esperando respuesta de la empresa
                </div>
                {vacante.fecha_postulacion && (
                  <p className="text-[11px] text-slate-500 pl-[21px] dark:text-slate-500">
                    Postulado el {vacante.fecha_postulacion.slice(0, 16).replace('T', ' ')}
                  </p>
                )}
              </div>
            )}

            {errMsg && <p className="text-[11px] text-rose-500">{errMsg}</p>}

            {/* Status + delete */}
            <div className="grid grid-cols-[1fr_auto] gap-2">
              <select
                value={statusDraft}
                disabled={busyAction === 'status'}
                onChange={e => {
                  const next = e.target.value as Status
                  setStatusDraft(next)
                  void handleStatusChange(next)
                }}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[12px] text-slate-700 outline-none transition-colors focus:border-indigo-400 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:focus:border-slate-600"
              >
                {STATUS_OPTIONS.map(o => (
                  <option key={o.value} value={o.value} className="bg-white text-slate-800 dark:bg-slate-800 dark:text-slate-200">{o.label}</option>
                ))}
              </select>
              <button
                onClick={handleDelete}
                disabled={busyAction === 'delete'}
                className="inline-flex items-center justify-center rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-[12px] text-rose-600 transition-colors hover:bg-rose-100 disabled:opacity-50 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300 dark:hover:bg-rose-950/40"
                aria-label="Borrar vacante"
              >
                {busyAction === 'delete'
                  ? <Loader2 size={13} className="animate-spin" />
                  : <Trash2 size={13} />}
              </button>
            </div>
          </div>
        </div>
      </article>

      {/* Modales */}
      {pdfOpen && (
        <PdfModal vacanteId={vacante.id} onClose={() => setPdfOpen(false)} />
      )}
      {latexOpen && (
        <LatexModal
          vacanteId={vacante.id}
          onClose={() => setLatexOpen(false)}
          onSaved={() => setLatexOpen(false)}
        />
      )}
      {detailOpen && (
        <JobDetailsModal
          vacante={vacante}
          onClose={() => setDetailOpen(false)}
          onRefresh={onStatusChange}
        />
      )}
      {toast && (
        <UndoToast
          newLabel={STATUS_OPTIONS.find(o => o.value === toast.newStatus)?.label ?? toast.newStatus}
          onUndo={handleUndo}
          onClose={dismissToast}
        />
      )}
    </>
  )
}
