'use client'

import { useEffect, useState } from 'react'
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
  Trash2,
  X,
} from 'lucide-react'
import { api, type Vacante, type Status } from '@/lib/api'
import StatusBadge, { compatBadge } from './StatusBadge'

const PROFILE_DIR = String.raw`C:\Users\GIRTEC\Desktop\Trabajo\Trabajo`

const MAESTRO_PATH = String.raw`C:\Users\GIRTEC\Desktop\Trabajo\job_hunter\data\perfil_maestro.json`

function buildMcpPrompt(id: number): string {
  return (
    `1. Usa 'get_vacancy_by_id' (${id}). ` +
    `2. Lee '${MAESTRO_PATH}' para extraer mis datos personales exactos (NOMBRE, APELLIDOS, CONTACTO). ` +
    `3. Genera CV LaTeX profesional usando esos datos. ` +
    `4. Usa 'save_latex_cv' (${id}, tex_content: <CÓDIGO>).`
  )
}

// ── Modales ───────────────────────────────────────────────────────────────────

function PdfModal({ vacanteId, onClose }: { vacanteId: number; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
      <div
        className="flex h-[92vh] w-full max-w-4xl flex-col rounded-xl border border-white/[0.08] bg-zinc-900"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
          <span className="text-[13px] font-medium text-zinc-300">
            CV PDF — vacante #{vacanteId}
          </span>
          <div className="flex items-center gap-2">
            <a
              href={`http://127.0.0.1:8000/pdf/${vacanteId}?download=true`}
              className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.06] px-2.5 py-1 text-[11px] text-zinc-400 transition-colors hover:bg-white/[0.05] hover:text-zinc-200"
            >
              <Download size={11} /> Descargar
            </a>
            <button
              onClick={onClose}
              className="rounded-md p-1 text-zinc-500 transition-colors hover:bg-white/[0.06] hover:text-zinc-200"
            >
              <X size={15} />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-hidden">
          <iframe
            src={`http://127.0.0.1:8000/pdf/${vacanteId}`}
            width="100%"
            height="100%"
            className="block bg-zinc-800"
            title={`CV vacante #${vacanteId}`}
          />
        </div>
      </div>
    </div>
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
  const [tex, setTex]       = useState('')
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
      onClick={onClose}
    >
      <div
        className="flex h-[92vh] w-full max-w-4xl flex-col rounded-xl border border-white/[0.08] bg-zinc-900"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
          <span className="text-[13px] font-medium text-zinc-300">
            Editor LaTeX — vacante #{vacanteId}
          </span>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-zinc-500 transition-colors hover:bg-white/[0.06] hover:text-zinc-200"
          >
            <X size={15} />
          </button>
        </div>

        <div className="flex-1 overflow-hidden p-3">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 size={20} className="animate-spin text-zinc-600" />
            </div>
          ) : (
            <textarea
              value={tex}
              onChange={e => setTex(e.target.value)}
              className="h-full w-full resize-none rounded-lg border border-white/[0.06] bg-zinc-950/60 p-3 font-mono text-[12px] leading-relaxed text-zinc-300 outline-none focus:border-white/[0.14]"
              spellCheck={false}
            />
          )}
        </div>

        {result && (
          <div className={`mx-3 mb-2 rounded-md px-3 py-2 text-[12px] ${
            result.ok
              ? 'border border-emerald-700/30 bg-emerald-950/30 text-emerald-300'
              : 'border border-rose-700/30 bg-rose-950/30 text-rose-300'
          }`}>
            {result.msg}
          </div>
        )}

        <div className="flex justify-end gap-2 border-t border-white/[0.06] px-4 py-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-white/[0.06] px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:bg-white/[0.04] hover:text-zinc-200"
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
  { value: 'Listo_Manual',        label: 'Listo' },
]

export default function VacanteCard({ vacante, onStatusChange }: Props) {
  const [copied, setCopied]           = useState(false)
  const [expanded, setExpanded]       = useState(false)
  const [pdfOpen, setPdfOpen]         = useState(false)
  const [latexOpen, setLatexOpen]     = useState(false)
  const [busyAction, setBusyAction]   = useState<'status' | 'delete' | null>(null)
  const [statusDraft, setStatusDraft] = useState<Status>(vacante.status)
  const [errMsg, setErrMsg]           = useState('')

  useEffect(() => { setStatusDraft(vacante.status) }, [vacante.status])

  const handleCopiarPrompt = async () => {
    try {
      await navigator.clipboard.writeText(buildMcpPrompt(vacante.id))
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
    setBusyAction('status')
    try { await api.cambiarStatus(vacante.id, nextStatus); onStatusChange?.() }
    catch (error) {
      setErrMsg(error instanceof Error ? error.message : 'No se pudo cambiar el estado.')
      setStatusDraft(vacante.status)
    }
    finally { setBusyAction(null) }
  }

  return (
    <>
      <article className="card-hover group relative flex flex-col rounded-xl border border-white/[0.06] bg-zinc-900/60 p-3">
        {/* Barra de compatibilidad */}
        <div className={`absolute left-0 top-2 bottom-2 w-[3px] rounded-full ${
          vacante.compatibilidad === 'Alta'  ? 'bg-emerald-500' :
          vacante.compatibilidad === 'Media' ? 'bg-amber-500'   :
          vacante.compatibilidad === 'Baja'  ? 'bg-zinc-600'    : 'bg-zinc-800'
        }`} />

        {/* ── Vista colapsada ──────────────────────────────────────────── */}
        <div className="pl-3 flex items-center justify-between gap-2 min-w-0">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <p className="truncate text-[13px] font-semibold leading-tight text-zinc-100">
                {vacante.titulo}
              </p>
              {vacante.status === 'En_Proceso' && (
                <Loader2 size={12} className="shrink-0 animate-spin text-blue-400" />
              )}
            </div>
            <div className="mt-0.5 flex items-center gap-1.5 flex-wrap">
              <p className="truncate text-[11px] text-zinc-500">{vacante.empresa}</p>
              <StatusBadge status={vacante.status} />
              <span className={`inline-flex rounded-full border px-1.5 py-0 text-[10px] font-medium ${compatBadge(vacante.compatibilidad)}`}>
                {vacante.compatibilidad}
              </span>
            </div>
          </div>
          <button
            onClick={() => setExpanded(v => !v)}
            className="shrink-0 inline-flex items-center gap-1 rounded-md border border-white/[0.06] px-2 py-1 text-[11px] text-zinc-500 transition-colors hover:bg-white/[0.05] hover:text-zinc-200"
          >
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            <span className="hidden sm:inline">{expanded ? 'Cerrar' : 'Detalles'}</span>
          </button>
        </div>

        {/* ── Vista expandida ──────────────────────────────────────────── */}
        <div className={`pl-3 overflow-hidden transition-all duration-200 ${
          expanded ? 'max-h-[600px] opacity-100 mt-3' : 'max-h-0 opacity-0'
        }`}>
          <div className="space-y-2">
            {/* Fecha + enlace */}
            <div className="flex items-center gap-3 text-[11px] text-zinc-600">
              {vacante.fecha_registro && <span>{vacante.fecha_registro.slice(0, 10)}</span>}
              {vacante.enlace && (
                <a
                  href={vacante.enlace}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-zinc-400 hover:text-zinc-200 transition-colors"
                >
                  Abrir <ExternalLink size={10} />
                </a>
              )}
            </div>

            {/* Requerimientos */}
            <div className="max-h-32 overflow-y-auto whitespace-pre-wrap rounded-md border border-white/[0.05] bg-zinc-950/40 p-2 text-[12px] leading-relaxed text-zinc-400">
              {(vacante.requerimientos ?? '').trim() || 'Sin requerimientos capturados.'}
            </div>

            {/* Portapapeles MCP */}
            {(vacante.status === 'No_Creado' || vacante.status === 'Requiere_Correccion') && (
              <button
                onClick={handleCopiarPrompt}
                className={`btn-shimmer inline-flex w-full items-center justify-center gap-2 rounded-lg px-3 py-1.5 text-[12px] font-semibold shadow-lg transition-colors ${
                  copied
                    ? 'border border-emerald-700/40 bg-emerald-950/40 text-emerald-300'
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
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-amber-700/30 bg-amber-950/30 px-3 py-1.5 text-[12px] font-medium text-amber-300 transition-colors hover:bg-amber-900/40"
                >
                  <FileText size={13} /> Ver PDF
                </button>
                <button
                  onClick={() => setLatexOpen(true)}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg border border-indigo-700/30 bg-indigo-950/30 px-3 py-1.5 text-[12px] font-medium text-indigo-300 transition-colors hover:bg-indigo-900/40"
                >
                  <Code size={13} /> Editar LaTeX
                </button>
                <a
                  href={`http://127.0.0.1:8000/pdf/${vacante.id}?download=true`}
                  className="inline-flex items-center justify-center rounded-lg border border-white/[0.06] px-2.5 py-1.5 text-zinc-400 transition-colors hover:bg-white/[0.05] hover:text-zinc-200"
                  title="Descargar PDF"
                >
                  <Download size={13} />
                </a>
              </div>
            )}

            {vacante.status === 'Listo_Manual' && (
              <div className="flex items-center gap-2 text-[12px] text-emerald-500">
                <CheckCircle size={13} /> Listo para postular
              </div>
            )}

            {errMsg && <p className="text-[11px] text-rose-400">{errMsg}</p>}

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
                className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-[12px] text-zinc-300 outline-none transition-colors focus:border-white/[0.14] disabled:opacity-50"
              >
                {STATUS_OPTIONS.map(o => (
                  <option key={o.value} value={o.value} className="bg-zinc-900 text-zinc-200">{o.label}</option>
                ))}
              </select>
              <button
                onClick={handleDelete}
                disabled={busyAction === 'delete'}
                className="inline-flex items-center justify-center rounded-lg border border-rose-800/30 bg-rose-950/20 px-3 py-1.5 text-[12px] text-rose-300 transition-colors hover:bg-rose-950/40 disabled:opacity-50"
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

      {/* Modales (fixed, fuera del overflow de la tarjeta) */}
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
    </>
  )
}
