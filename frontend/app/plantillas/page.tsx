'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Upload, FileCode2, CheckCircle, AlertTriangle, Loader2, X } from 'lucide-react'
import { api, type TemplateInfo } from '@/lib/api'

type UploadState = 'idle' | 'uploading' | 'success' | 'error'

export default function PlantillasPage() {
  const [template, setTemplate] = useState<TemplateInfo | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploadState, setUpState] = useState<UploadState>('idle')
  const [message, setMessage] = useState('')
  const [fileName, setFileName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.templateActiva().then(setTemplate).catch(() => null)
  }, [])

  const upload = useCallback(async (file: File) => {
    if (!file.name.endsWith('.tex')) {
      setUpState('error')
      setMessage('Solo se aceptan archivos .tex')
      return
    }
    setFileName(file.name)
    setUpState('uploading')
    setMessage('')
    try {
      const res = await api.uploadTemplate(file)
      setMessage(res.mensaje)
      setUpState('success')
      setTemplate({ activa: 'mi_estilo.tex', personalizada: true })
    } catch (e) {
      setUpState('error')
      setMessage(e instanceof Error ? e.message : 'Error al subir la plantilla.')
    }
  }, [])

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
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
        <p className="text-[12px] text-slate-400 dark:text-slate-500">Sube tu diseño personalizado para que la IA lo respete</p>
      </header>

      <main className="flex flex-1 flex-col gap-5 overflow-y-auto px-6 py-6">

        {/* Plantilla activa */}
        <div className="flex items-start gap-4 rounded-2xl border border-slate-100 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
          <div className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
            template?.personalizada
              ? 'bg-indigo-50 text-indigo-500 dark:bg-indigo-950 dark:text-indigo-400'
              : 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500'
          }`}>
            <FileCode2 size={16} />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-slate-800 dark:text-slate-200">Plantilla activa</p>
            <p className="mt-0.5 text-[12px] text-slate-500">
              {template?.activa ?? '...'}
              {template?.personalizada && (
                <span className="ml-2 rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-medium text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400">
                  Personalizada
                </span>
              )}
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-slate-400 dark:text-slate-600">
              {template?.personalizada
                ? 'La IA respetará tu diseño en el próximo /generar_cv.'
                : 'Usando la plantilla base. Sube un .tex para personalizarla.'}
            </p>
          </div>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => uploadState !== 'uploading' && inputRef.current?.click()}
          className={`group relative flex cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-16 text-center transition-all duration-200 ${
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
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm transition-colors group-hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:group-hover:border-slate-600">
                <Upload size={22} className="text-slate-400 transition-colors group-hover:text-slate-600 dark:group-hover:text-slate-300" />
              </div>
              <div>
                <p className="text-[14px] font-medium text-slate-700 dark:text-slate-300">
                  {dragOver ? 'Suelta aquí tu .tex' : 'Arrastra tu plantilla .tex'}
                </p>
                <p className="mt-1 text-[12px] text-slate-400 dark:text-slate-600">
                  o haz clic para seleccionar el archivo
                </p>
              </div>
              <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                Solo archivos .tex
              </span>
            </>
          )}

          {uploadState === 'uploading' && (
            <>
              <Loader2 size={28} className="animate-spin text-indigo-500 dark:text-indigo-400" />
              <div>
                <p className="text-[13px] font-medium text-slate-700 dark:text-slate-300">Subiendo {fileName}...</p>
                <p className="mt-1 text-[12px] text-slate-400 dark:text-slate-600">Guardando en latex_templates/mi_estilo.tex</p>
              </div>
            </>
          )}

          {uploadState === 'success' && (
            <>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 dark:bg-emerald-950">
                <CheckCircle size={24} className="text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-emerald-700 dark:text-emerald-300">¡Plantilla actualizada!</p>
                <p className="mt-1 text-[12px] text-slate-500">{message}</p>
              </div>
              <button
                onClick={e => { e.stopPropagation(); reset() }}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
              >
                <X size={12} /> Subir otra
              </button>
            </>
          )}

          {uploadState === 'error' && (
            <>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 dark:bg-rose-950">
                <AlertTriangle size={24} className="text-rose-600 dark:text-rose-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-rose-700 dark:text-rose-300">Error al subir</p>
                <p className="mt-1 text-[12px] text-slate-500">{message}</p>
              </div>
              <button
                onClick={e => { e.stopPropagation(); reset() }}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-200"
              >
                <X size={12} /> Reintentar
              </button>
            </>
          )}
        </div>

        {/* Info cards */}
        <div className="grid grid-cols-2 gap-3 pb-4">
          {[
            {
              title: 'Cómo funciona',
              body: 'Sube tu archivo .tex con el diseño que prefieras. El sistema lo usará como guía visual para cada CV que generes.',
            },
            {
              title: 'Estructura recomendada',
              body: 'Usa marcadores {{NOMBRE}}, {{EXPERIENCIA}}, {{HABILIDADES}} en tu plantilla. La IA los sustituirá con contenido adaptado.',
            },
          ].map(({ title, body }) => (
            <div key={title} className="rounded-xl border border-slate-100 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
              <p className="text-[12px] font-semibold text-slate-700 dark:text-slate-300">{title}</p>
              <p className="mt-1.5 text-[12px] leading-relaxed text-slate-500 dark:text-slate-500">{body}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
