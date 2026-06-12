'use client'

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  Briefcase, ChevronDown, Clipboard, ClipboardCheck, Code,
  Download, ExternalLink, FileText, Loader2, Sparkles, X, Zap,
} from 'lucide-react'
import { api, type Vacante, type Status } from '@/lib/api'
import StatusBadge, { compatBadge } from './StatusBadge'

// ── Constants ─────────────────────────────────────────────────────────────────

const PDF_STATUSES: Status[] = ['Revisado_IA', 'Listo_Manual', 'Entrevista']

const STATUS_ACCENT: Partial<Record<Status, string>> = {
  Revisado_IA:         'via-amber-400/60',
  Listo_Manual:        'via-emerald-500/60',
  Entrevista:          'via-purple-500/60',
  En_Proceso:          'via-blue-500/60',
  Requiere_Correccion: 'via-rose-500/60',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function parseJobMeta(text: string) {
  const s = text.match(/(?:sueldo|salario|compensaci[oó]n)[:\s]+([^\n]{3,70})/i)
  const m = text.match(/(?:modalidad|esquema de trabajo|tipo de trabajo|trabajo)[:\s]+((?:remoto|presencial|h[íi]brido|home office)[^\n]{0,40})/i)
  const u = text.match(/(?:ubicaci[oó]n|lugar de trabajo)\s*:\s*([^\n]{3,60})/i)
  return {
    sueldo:    s?.[1].trim(),
    modalidad: m?.[1].trim(),
    ubicacion: u?.[1].trim(),
  }
}

type Tab = 'resumen' | 'descripcion' | 'cv'

// ── Component ─────────────────────────────────────────────────────────────────

export default function JobDetailsModal({
  vacante: initialVacante,
  onClose,
  onRefresh,
}: {
  vacante: Vacante
  onClose: () => void
  onRefresh?: () => void
}) {
  const [vacante, setVacante] = useState(initialVacante)
  const hasPdf = PDF_STATUSES.includes(vacante.status)

  const [tab, setTab] = useState<Tab>(hasPdf ? 'cv' : 'resumen')

  // PDF
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError]     = useState(false)

  // LaTeX editor
  const [latexContent, setLatexContent] = useState<string | null>(null)
  const [latexLoading, setLatexLoading] = useState(false)
  const [showLatex, setShowLatex]       = useState(false)
  const [latexSaving, setLatexSaving]   = useState(false)
  const [latexResult, setLatexResult]   = useState<{ ok: boolean; msg: string } | null>(null)
  const [latexCopied, setLatexCopied]   = useState(false)

  // CV generation
  const [generating, setGenerating] = useState(false)
  const [genResult, setGenResult]   = useState<{ ok: boolean; msg: string } | null>(null)

  // MCP prompt
  const [copied, setCopied]         = useState(false)
  const [profilePath, setProfilePath] = useState<string | null>(null)

  const meta   = parseJobMeta(vacante.requerimientos ?? '')
  const accent = STATUS_ACCENT[vacante.status] ?? 'via-slate-400/40'

  // Fetch profile path for dynamic MCP prompt
  useEffect(() => {
    api.perfil().then(r => setProfilePath(r.ruta)).catch(() => {})
  }, [])

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [])

  // Cleanup blob URL on unmount
  useEffect(() => () => { if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl) }, [pdfBlobUrl])

  // Auto-load PDF when CV tab is active and vacancy has a PDF
  useEffect(() => {
    if (tab === 'cv' && hasPdf && !pdfBlobUrl && !pdfError && !pdfLoading) {
      setPdfLoading(true)
      api.getPdfBlob(vacante.id)
        .then(blob => setPdfBlobUrl(URL.createObjectURL(blob)))
        .catch(() => setPdfError(true))
        .finally(() => setPdfLoading(false))
    }
  }, [tab, hasPdf, vacante.id, pdfBlobUrl, pdfError, pdfLoading])

  const mcpPrompt = (() => {
    const path = profilePath ?? '[ruta del perfil maestro]'
    return (
      `1. Usa 'get_vacancy_by_id' (${vacante.id}). ` +
      `2. Lee '${path}' para extraer mis datos personales exactos (NOMBRE, APELLIDOS, CONTACTO). ` +
      `3. Genera CV LaTeX profesional con esos datos. ` +
      `4. Usa 'save_latex_cv' (${vacante.id}, tex_content: <CÓDIGO>).`
    )
  })()

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(mcpPrompt)
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    } catch { /* silent */ }
  }

  const handleGenerateCv = async () => {
    setGenerating(true)
    setGenResult(null)
    try {
      const r = await api.generateCv(vacante.id)
      if (r.ok) {
        const fresh = await api.vacanteDetalle(vacante.id)
        setVacante(fresh)
        if (pdfBlobUrl) { URL.revokeObjectURL(pdfBlobUrl); setPdfBlobUrl(null) }
        setPdfError(false)
        setTab('cv')
        onRefresh?.()
      }
      setGenResult({
        ok: r.ok,
        msg: r.ok
          ? '✓ CV generado y PDF compilado correctamente.'
          : `⚠ ${r.error ?? 'Error al compilar PDF. Usa el editor LaTeX para corregir.'}`,
      })
    } catch (e) {
      setGenResult({ ok: false, msg: e instanceof Error ? e.message : 'Error al generar CV.' })
    } finally {
      setGenerating(false)
    }
  }

  const handleToggleLatex = async () => {
    if (!showLatex && latexContent === null) {
      setLatexLoading(true)
      try { setLatexContent(await api.getLatex(vacante.id)) }
      catch { setLatexContent('% No hay LaTeX generado aún para esta vacante.') }
      finally { setLatexLoading(false) }
    }
    setShowLatex(v => !v)
  }

  const handleSaveLatex = async () => {
    if (!latexContent) return
    setLatexSaving(true)
    setLatexResult(null)
    try {
      const r = await api.saveLatex(vacante.id, latexContent)
      setLatexResult({
        ok: r.pdf,
        msg: r.pdf ? '✓ PDF compilado.' : `⚠ ${r.error ?? 'Error de compilación.'}`,
      })
      if (r.pdf) {
        if (pdfBlobUrl) { URL.revokeObjectURL(pdfBlobUrl); setPdfBlobUrl(null) }
        setPdfError(false)
        const fresh = await api.vacanteDetalle(vacante.id)
        setVacante(fresh)
        onRefresh?.()
      }
    } catch (e) {
      setLatexResult({ ok: false, msg: e instanceof Error ? e.message : 'Error.' })
    } finally {
      setLatexSaving(false)
    }
  }

  const handleDownload = () => {
    if (!pdfBlobUrl) return
    const a = document.createElement('a')
    a.href = pdfBlobUrl
    a.download = `cv_${vacante.id}_${(vacante.empresa ?? 'vacante').replace(/[^a-z0-9]/gi, '_')}.pdf`
    a.click()
  }

  if (typeof document === 'undefined') return null

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(10px)' }}
      onClick={onClose}
    >
      <div
        className="relative flex h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-white/10 bg-white/95 shadow-2xl backdrop-blur-xl dark:border-slate-700/40 dark:bg-slate-900/95"
        onClick={e => e.stopPropagation()}
      >
        {/* Accent line */}
        <div className={`absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent ${accent} to-transparent`} />

        {/* ── STICKY HEADER ─────────────────────────────────────────── */}
        <div className="shrink-0 border-b border-slate-100/80 bg-white/95 px-5 pt-5 pb-0 dark:border-slate-800/80 dark:bg-slate-900/95">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h2 className="truncate text-[15px] font-semibold leading-snug text-slate-900 dark:text-slate-100">
                  {vacante.titulo}
                </h2>
                <span className="shrink-0 rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-400 dark:bg-slate-800 dark:text-slate-500">
                  #{vacante.id}
                </span>
              </div>
              <p className="mt-0.5 truncate text-[12px] text-slate-500 dark:text-slate-400">
                {vacante.empresa}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-1.5">
                <StatusBadge status={vacante.status} />
                <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${compatBadge(vacante.compatibilidad)}`}>
                  {vacante.compatibilidad === 'Alta' && <span className="text-[8px]">●</span>}
                  Match: {vacante.compatibilidad}
                </span>
                {vacante.fecha_postulacion && (
                  <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400">
                    Postulada {vacante.fecha_postulacion.slice(0, 10)}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="shrink-0 rounded-lg border border-slate-200/60 p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <X size={14} />
            </button>
          </div>

          {/* Tab bar */}
          <div className="mt-3 flex">
            {([
              { id: 'resumen' as Tab,     label: 'Resumen',     Icon: Briefcase },
              { id: 'descripcion' as Tab, label: 'Descripción', Icon: FileText  },
              { id: 'cv' as Tab,          label: hasPdf ? 'CV / PDF' : 'Generar CV', Icon: hasPdf ? FileText : Sparkles },
            ]).map(({ id, label, Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`relative flex items-center gap-1.5 px-4 py-2.5 text-[12px] font-medium transition-colors ${
                  tab === id
                    ? 'text-indigo-600 dark:text-indigo-400'
                    : 'text-slate-500 hover:text-slate-700 dark:text-slate-500 dark:hover:text-slate-300'
                }`}
              >
                <Icon size={12} className="opacity-70" />
                {label}
                {tab === id && (
                  <span className="absolute inset-x-0 bottom-0 h-[2px] rounded-full bg-indigo-500 dark:bg-indigo-400" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* ── BODY (tab-aware) ───────────────────────────────────────── */}
        <div className="min-h-0 flex-1 overflow-hidden">

          {/* TAB: Resumen */}
          {tab === 'resumen' && (
            <div className="h-full space-y-4 overflow-y-auto px-5 py-5 [scrollbar-width:thin]">
              {/* Meta chips */}
              {(meta.sueldo || meta.modalidad || meta.ubicacion) ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {[
                    { label: 'Sueldo',    value: meta.sueldo },
                    { label: 'Modalidad', value: meta.modalidad },
                    { label: 'Ubicación', value: meta.ubicacion },
                  ].filter(x => x.value).map(({ label, value }) => (
                    <div key={label} className="rounded-xl border border-slate-100 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-800/40">
                      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">{label}</p>
                      <p className="mt-1 line-clamp-2 text-[13px] font-semibold text-slate-800 dark:text-slate-200">{value}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-3 text-[12px] text-slate-400 dark:border-slate-800 dark:bg-slate-800/20">
                  Metadata no detectada en el texto (sueldo, modalidad, ubicación).
                </div>
              )}

              {/* MCP Prompt */}
              <div>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-600">
                  Prompt MCP — CV Generator
                </p>
                <div className="relative rounded-xl border border-slate-200/60 bg-slate-50/80 p-4 pr-10 font-mono text-[11px] leading-relaxed text-slate-600 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
                  {mcpPrompt}
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
              </div>
            </div>
          )}

          {/* TAB: Descripción */}
          {tab === 'descripcion' && (
            <div className="h-full overflow-y-auto px-5 py-5 [scrollbar-width:thin]">
              <div className="whitespace-pre-wrap rounded-xl border border-slate-100 bg-slate-50/60 p-4 text-[13px] leading-relaxed text-slate-600 dark:border-slate-700 dark:bg-slate-800/30 dark:text-slate-300">
                {(vacante.requerimientos ?? '').trim() || 'Sin descripción capturada.'}
              </div>
            </div>
          )}

          {/* TAB: CV */}
          {tab === 'cv' && (
            <div className="flex h-full flex-col">

              {/* ─ No PDF yet ─ */}
              {!hasPdf && (
                <div className="flex h-full flex-col items-center justify-center gap-5 overflow-y-auto px-8 py-10 text-center [scrollbar-width:thin]">
                  {generating ? (
                    <>
                      <Loader2 size={32} className="animate-spin text-indigo-500" />
                      <div>
                        <p className="text-[14px] font-semibold text-slate-700 dark:text-slate-200">
                          Generando CV con Groq AI...
                        </p>
                        <p className="mt-1 text-[12px] text-slate-400">Esto puede tardar 10–30 segundos</p>
                      </div>
                    </>
                  ) : genResult ? (
                    <div className="flex flex-col items-center gap-3">
                      <div className={`max-w-sm rounded-xl border px-6 py-4 text-[13px] ${
                        genResult.ok
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-700/30 dark:bg-emerald-950/20 dark:text-emerald-300'
                          : 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-700/30 dark:bg-rose-950/20 dark:text-rose-300'
                      }`}>
                        {genResult.msg}
                      </div>
                      {!genResult.ok && (
                        <button
                          onClick={handleGenerateCv}
                          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-[12px] text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
                        >
                          <Zap size={12} /> Reintentar
                        </button>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-50 dark:bg-indigo-950/40">
                        <Sparkles size={28} className="text-indigo-500" />
                      </div>
                      <div>
                        <p className="text-[15px] font-semibold text-slate-800 dark:text-slate-200">
                          {vacante.status === 'Requiere_Correccion' ? 'El CV anterior falló' : 'CV aún no generado'}
                        </p>
                        <p className="mt-1 max-w-xs text-[12px] text-slate-400">
                          {vacante.status === 'Requiere_Correccion'
                            ? 'Puedes regenerarlo o editar el LaTeX manualmente.'
                            : 'Genera un CV personalizado con Groq AI en segundos.'}
                        </p>
                      </div>
                      <button
                        onClick={handleGenerateCv}
                        className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-2.5 text-[13px] font-semibold text-white shadow-lg shadow-indigo-500/25 transition-transform hover:scale-[1.02] active:scale-[0.98]"
                      >
                        <Zap size={14} /> Generar CV con IA
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* ─ Has PDF ─ */}
              {hasPdf && (
                <>
                  {/* PDF viewer */}
                  <div className="relative flex-1 overflow-hidden">
                    {pdfLoading && (
                      <div className="flex h-full items-center justify-center gap-2">
                        <Loader2 size={18} className="animate-spin text-indigo-500" />
                        <span className="text-[12px] text-slate-400">Cargando PDF...</span>
                      </div>
                    )}
                    {pdfError && !pdfLoading && (
                      <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
                        <FileText size={28} className="text-slate-300" />
                        <p className="text-[12px] text-slate-400">No se pudo cargar el PDF.</p>
                        <button
                          onClick={() => { setPdfError(false); setPdfBlobUrl(null) }}
                          className="text-[11px] text-indigo-500 hover:underline"
                        >
                          Reintentar
                        </button>
                      </div>
                    )}
                    {pdfBlobUrl && !pdfError && (
                      <iframe
                        src={pdfBlobUrl}
                        className="h-full w-full border-none"
                        title={`CV vacante #${vacante.id}`}
                      />
                    )}
                  </div>

                  {/* LaTeX collapsible editor */}
                  <div className="shrink-0 border-t border-slate-100 dark:border-slate-800">
                    <button
                      onClick={handleToggleLatex}
                      className="flex w-full items-center justify-between px-4 py-2.5 text-left transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30"
                    >
                      <span className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                        <Code size={12} className="opacity-70" />
                        Editor LaTeX
                      </span>
                      <ChevronDown
                        size={13}
                        className={`text-slate-400 transition-transform duration-200 ${showLatex ? '-rotate-180' : ''}`}
                      />
                    </button>
                    <div className={`grid transition-all duration-200 ${showLatex ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
                      <div className="overflow-hidden">
                        <div className="px-4 pb-3">
                          {latexLoading ? (
                            <div className="flex items-center gap-2 py-3 text-slate-400">
                              <Loader2 size={14} className="animate-spin" />
                              <span className="text-[12px]">Cargando...</span>
                            </div>
                          ) : (
                            <>
                              <textarea
                                value={latexContent ?? ''}
                                onChange={e => setLatexContent(e.target.value)}
                                rows={9}
                                className="w-full resize-y rounded-xl border border-slate-200 bg-slate-50 p-3 font-mono text-[11px] leading-relaxed text-slate-700 outline-none transition-colors focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-300 dark:focus:border-indigo-500/40 [scrollbar-width:thin]"
                                spellCheck={false}
                              />
                              {latexResult && (
                                <p className={`mt-1.5 text-[11px] ${latexResult.ok ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500 dark:text-rose-400'}`}>
                                  {latexResult.msg}
                                </p>
                              )}
                              <div className="mt-2 flex justify-end gap-2">
                                <button
                                  onClick={() => {
                                    if (!latexContent) return
                                    navigator.clipboard.writeText(latexContent).then(() => {
                                      setLatexCopied(true)
                                      setTimeout(() => setLatexCopied(false), 2000)
                                    })
                                  }}
                                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-[11px] text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                                >
                                  {latexCopied ? <ClipboardCheck size={11} className="text-emerald-500" /> : <Clipboard size={11} />}
                                  {latexCopied ? 'Copiado' : 'Copiar'}
                                </button>
                                <button
                                  onClick={handleSaveLatex}
                                  disabled={latexSaving}
                                  className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-1.5 text-[11px] font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                                >
                                  {latexSaving ? <Loader2 size={11} className="animate-spin" /> : <Code size={11} />}
                                  {latexSaving ? 'Compilando...' : 'Guardar y Compilar'}
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* ── STICKY FOOTER ─────────────────────────────────────────── */}
        <div className="shrink-0 flex items-center gap-2 border-t border-slate-100/80 bg-white/95 px-5 py-3 dark:border-slate-800/80 dark:bg-slate-900/95">
          {vacante.enlace && (
            <a
              href={vacante.enlace}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200/80 px-3 py-1.5 text-[12px] text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-700 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <ExternalLink size={12} />
              Ver original
            </a>
          )}

          <div className="flex-1" />

          {/* Generate button — only when no PDF */}
          {!hasPdf && !generating && (
            <button
              onClick={() => { setTab('cv'); setGenResult(null) }}
              className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-[12px] font-semibold text-white shadow-md shadow-indigo-500/20 transition-transform hover:scale-[1.01]"
            >
              <Zap size={13} /> Generar CV
            </button>
          )}

          {!hasPdf && generating && (
            <button disabled className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600/70 px-4 py-2 text-[12px] font-semibold text-white opacity-70">
              <Loader2 size={13} className="animate-spin" /> Generando...
            </button>
          )}

          {/* PDF actions — only when PDF exists */}
          {hasPdf && tab !== 'cv' && (
            <button
              onClick={() => setTab('cv')}
              className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-[12px] font-medium text-amber-700 transition-colors hover:bg-amber-100 dark:border-amber-700/30 dark:bg-amber-950/20 dark:text-amber-300"
            >
              <FileText size={12} /> Ver PDF
            </button>
          )}

          {hasPdf && pdfBlobUrl && (
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-[12px] text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <Download size={12} /> Descargar
            </button>
          )}

          {/* MCP copy — always visible */}
          <button
            onClick={handleCopy}
            title="Copiar prompt para Claude Desktop (MCP)"
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-medium transition-colors ${
              copied
                ? 'border border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-700/30 dark:bg-emerald-950/20 dark:text-emerald-300'
                : 'border border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800'
            }`}
          >
            {copied ? <ClipboardCheck size={12} /> : <Clipboard size={12} />}
            {copied ? 'Copiado' : 'MCP'}
          </button>

          <button
            onClick={onClose}
            className="ml-1 text-[12px] text-slate-400 transition-colors hover:text-slate-600 dark:hover:text-slate-300"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
