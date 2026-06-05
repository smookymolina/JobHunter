'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Upload, FileCode2, CheckCircle, AlertTriangle, Loader2,
  X, Download, Trash2, RefreshCw,
} from 'lucide-react'
import Loader from '@/components/ui/Loader'
import { api, type TemplateInfo } from '@/lib/api'

type UploadState = 'idle' | 'uploading' | 'success' | 'error'

const MARKERS = [
  { label: 'Datos personales', items: ['{{NOMBRE_COMPLETO}}', '{{TITULO_PROFESIONAL_ADAPTADO}}', '{{EMAIL}}', '{{TELEFONO}}', '{{UBICACION}}'] },
  { label: 'Perfil y skills', items: ['{{RESUMEN_EJECUTIVO}}', '{{CATEGORIA_SKILL_1}}', '{{LISTA_SKILLS_1}}', '{{IDIOMAS}}'] },
  { label: 'Experiencia', items: ['{{PUESTO_1}}', '{{EMPRESA_1}}', '{{FECHA_INICIO_1}}', '{{FECHA_FIN_1}}', '{{LOGRO_1_1}}'] },
  { label: 'Educación y proyectos', items: ['{{TITULO_ACADEMICO}}', '{{INSTITUCION}}', '{{ANIO_EGRESO}}', '{{PROYECTO_1}}', '{{DESCRIPCION_PROYECTO_1}}'] },
]

function fmtDate(ts: number) {
  return new Date(ts * 1000).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
}

export default function PlantillasPage() {
  const [template, setTemplate] = useState<TemplateInfo | null>(null)
  const [pageLoading, setPageLoading] = useState(true)
  const [dragOver, setDragOver] = useState(false)
  const [uploadState, setUpState] = useState<UploadState>('idle')
  const [message, setMessage] = useState('')
  const [fileName, setFileName] = useState('')
  const [deleting, setDeleting] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const refresh = useCallback(() => api.templateActiva().then(setTemplate).catch(() => null), [])
  useEffect(() => {
    api.templateActiva()
      .then(setTemplate)
      .catch(() => null)
      .finally(() => setPageLoading(false))
  }, [])

  const upload = useCallback(async (file: File) => {
    if (!file.name.endsWith('.tex')) {
      setUpState('error'); setMessage('Solo se aceptan archivos .tex'); return
    }
    setFileName(file.name); setUpState('uploading'); setMessage('')
    try {
      const res = await api.uploadTemplate(file)
      setMessage(res.mensaje); setUpState('success')
      refresh()
    } catch (e) {
      setUpState('error'); setMessage(e instanceof Error ? e.message : 'Error al subir la plantilla.')
    }
  }, [])

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await api.deleteTemplate()
      refresh()
    } catch {
      // silently ignore if no custom template
    } finally {
      setDeleting(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) upload(file)
  }

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) upload(file)
    if (inputRef.current) inputRef.current.value = ''
  }

  const reset = () => { setUpState('idle'); setMessage(''); setFileName('') }

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-30 shrink-0 border-b border-slate-100 bg-white/90 px-6 py-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90">
        <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">Plantillas LaTeX</h1>
        <p className="text-[12px] text-slate-400 dark:text-slate-500">Diseño personalizado para que la IA respete tu estilo de CV</p>
      </header>

      {pageLoading && (
        <div className="flex flex-1 items-center justify-center">
          <Loader size={36} label="Cargando plantilla..." />
        </div>
      )}

      <main className={`flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5 ${pageLoading ? 'hidden' : ''}`}>

        {/* Plantilla activa */}
        <div className="flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${
            template?.personalizada
              ? 'bg-indigo-50 text-indigo-500 dark:bg-indigo-950/60 dark:text-indigo-400'
              : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'
          }`}>
            <FileCode2 size={18} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="text-[13px] font-semibold text-slate-800 dark:text-slate-200">
                {template?.activa ?? '…'}
              </p>
              {template?.personalizada && (
                <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-medium text-indigo-600 dark:bg-indigo-950/60 dark:text-indigo-400">
                  Personalizada
                </span>
              )}
            </div>
            <p className="mt-0.5 text-[11px] text-slate-400 dark:text-slate-600">
              {template?.size_kb != null && `${template.size_kb} KB`}
              {template?.modified && template?.size_kb != null && ' · '}
              {template?.modified && `Modificado ${fmtDate(template.modified)}`}
              {!template && 'Cargando…'}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <a
              href={api.downloadTemplateUrl()}
              download
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
            >
              <Download size={11} /> Descargar
            </a>
            {template?.personalizada && (
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-[11px] font-medium text-rose-600 transition-colors hover:bg-rose-100 disabled:opacity-50 dark:border-rose-800/40 dark:bg-rose-950/20 dark:text-rose-400 dark:hover:bg-rose-950/40"
              >
                {deleting ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
                Revertir
              </button>
            )}
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => uploadState !== 'uploading' && inputRef.current?.click()}
          className={`group relative flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center transition-all duration-200 ${
            dragOver
              ? 'border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-950/20'
              : uploadState === 'success'
              ? 'border-emerald-400/60 bg-emerald-50 dark:border-emerald-600/50 dark:bg-emerald-950/10'
              : uploadState === 'error'
              ? 'border-rose-400/60 bg-rose-50 dark:border-rose-600/50 dark:bg-rose-950/10'
              : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white dark:border-slate-700 dark:bg-slate-800/20 dark:hover:border-slate-600 dark:hover:bg-slate-800/40'
          }`}
        >
          <input ref={inputRef} type="file" accept=".tex" className="hidden" onChange={onFileInput} />

          {uploadState === 'idle' && (
            <>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm transition-colors group-hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:group-hover:border-slate-600">
                <Upload size={20} className="text-slate-400 transition-colors group-hover:text-slate-600 dark:group-hover:text-slate-300" />
              </div>
              <div>
                <p className="text-[13px] font-medium text-slate-700 dark:text-slate-300">
                  {dragOver ? 'Suelta aquí tu .tex' : 'Arrastra tu plantilla .tex o haz clic'}
                </p>
                <p className="mt-0.5 text-[11px] text-slate-400 dark:text-slate-600">Solo archivos .tex · máx. 1 MB</p>
              </div>
            </>
          )}

          {uploadState === 'uploading' && (
            <>
              <Loader2 size={24} className="animate-spin text-indigo-500 dark:text-indigo-400" />
              <p className="text-[13px] font-medium text-slate-700 dark:text-slate-300">Subiendo {fileName}…</p>
            </>
          )}

          {uploadState === 'success' && (
            <>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100 dark:bg-emerald-950">
                <CheckCircle size={22} className="text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-emerald-700 dark:text-emerald-300">¡Plantilla actualizada!</p>
                <p className="mt-0.5 text-[12px] text-slate-500">{message}</p>
              </div>
              <button onClick={e => { e.stopPropagation(); reset() }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700">
                <RefreshCw size={11} /> Subir otra
              </button>
            </>
          )}

          {uploadState === 'error' && (
            <>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-rose-100 dark:bg-rose-950">
                <AlertTriangle size={22} className="text-rose-600 dark:text-rose-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-rose-700 dark:text-rose-300">Error al subir</p>
                <p className="mt-0.5 text-[12px] text-slate-500">{message}</p>
              </div>
              <button onClick={e => { e.stopPropagation(); reset() }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700">
                <X size={11} /> Reintentar
              </button>
            </>
          )}
        </div>

        {/* Marcadores de referencia */}
        <div className="rounded-2xl border border-slate-100 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-4 flex items-center gap-2">
            <span className="h-4 w-1 shrink-0 rounded-full bg-indigo-500" />
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
              Marcadores disponibles
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            {MARKERS.map(({ label, items }) => (
              <div key={label}>
                <p className="mb-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400">{label}</p>
                <div className="flex flex-col gap-1">
                  {items.map(m => (
                    <code key={m} className="w-fit rounded-md bg-slate-50 px-2 py-0.5 text-[10px] font-mono text-indigo-600 dark:bg-slate-800 dark:text-indigo-400">
                      {m}
                    </code>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-[11px] leading-relaxed text-slate-400 dark:text-slate-600">
            La IA sustituye estos marcadores con contenido adaptado a cada vacante. Usa <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">_1</code>, <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">_2</code>… para múltiples entradas de experiencia o proyectos.
          </p>
        </div>

      </main>
    </div>
  )
}
