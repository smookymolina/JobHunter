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
      <header className="shrink-0 border-b border-white/[0.06] px-6 py-4">
        <h1 className="text-[18px] font-semibold tracking-tight text-zinc-50">Plantillas LaTeX</h1>
        <p className="text-[12px] text-zinc-500">Sube tu diseño personalizado para que la IA lo respete</p>
      </header>

      <main className="flex flex-1 flex-col gap-6 overflow-auto px-6 py-6">
        <div className="flex items-start gap-4 rounded-xl border border-white/[0.06] bg-zinc-900/50 p-4">
          <div className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
            template?.personalizada
              ? 'bg-indigo-950 text-indigo-400'
              : 'bg-zinc-800 text-zinc-500'
          }`}>
            <FileCode2 size={16} />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-zinc-200">Plantilla activa</p>
            <p className="mt-0.5 text-[12px] text-zinc-500">
              {template?.activa ?? '...'}
              {template?.personalizada && (
                <span className="ml-2 rounded-full bg-indigo-950 px-2 py-0.5 text-[10px] text-indigo-400">
                  Personalizada
                </span>
              )}
            </p>
            <p className="mt-1 text-[11px] leading-relaxed text-zinc-600">
              {template?.personalizada
                ? 'La IA respetará tu diseño en el próximo /generar_cv.'
                : 'Usando la plantilla base. Sube un .tex para personalizarla.'}
            </p>
          </div>
        </div>

        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => uploadState !== 'uploading' && inputRef.current?.click()}
          className={`group relative flex cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-16 text-center transition-all duration-200 ${
            dragOver
              ? 'border-indigo-500 bg-indigo-950/20'
              : uploadState === 'success'
              ? 'border-emerald-600/50 bg-emerald-950/10'
              : uploadState === 'error'
              ? 'border-rose-600/50 bg-rose-950/10'
              : 'border-white/[0.08] bg-white/[0.02] hover:border-white/[0.14] hover:bg-white/[0.03]'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".tex"
            className="hidden"
            onChange={onFileInput}
          />

          {uploadState === 'idle' && (
            <>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/[0.08] bg-zinc-900 transition-colors group-hover:border-white/[0.14]">
                <Upload size={22} className="text-zinc-500 transition-colors group-hover:text-zinc-300" />
              </div>
              <div>
                <p className="text-[14px] font-medium text-zinc-300">
                  {dragOver ? 'Suelta aquí tu .tex' : 'Arrastra tu plantilla .tex'}
                </p>
                <p className="mt-1 text-[12px] text-zinc-600">
                  o haz clic para seleccionar el archivo
                </p>
              </div>
              <span className="rounded-full border border-white/[0.06] bg-white/[0.03] px-3 py-1 text-[11px] text-zinc-600">
                Solo archivos .tex
              </span>
            </>
          )}

          {uploadState === 'uploading' && (
            <>
              <Loader2 size={28} className="animate-spin text-indigo-400" />
              <div>
                <p className="text-[13px] font-medium text-zinc-300">Subiendo {fileName}...</p>
                <p className="mt-1 text-[12px] text-zinc-600">Guardando en latex_templates/mi_estilo.tex</p>
              </div>
            </>
          )}

          {uploadState === 'success' && (
            <>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-950">
                <CheckCircle size={24} className="text-emerald-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-emerald-300">¡Plantilla actualizada!</p>
                <p className="mt-1 text-[12px] text-zinc-500">{message}</p>
              </div>
              <button
                onClick={e => { e.stopPropagation(); reset() }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.06] px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:bg-white/[0.05] hover:text-zinc-200"
              >
                <X size={12} /> Subir otra
              </button>
            </>
          )}

          {uploadState === 'error' && (
            <>
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-950">
                <AlertTriangle size={24} className="text-rose-400" />
              </div>
              <div>
                <p className="text-[14px] font-semibold text-rose-300">Error al subir</p>
                <p className="mt-1 text-[12px] text-zinc-500">{message}</p>
              </div>
              <button
                onClick={e => { e.stopPropagation(); reset() }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/[0.06] px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:bg-white/[0.05] hover:text-zinc-200"
              >
                <X size={12} /> Reintentar
              </button>
            </>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
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
            <div key={title} className="rounded-xl border border-white/[0.06] bg-zinc-900/40 p-4">
              <p className="text-[12px] font-semibold text-zinc-300">{title}</p>
              <p className="mt-1.5 text-[12px] leading-relaxed text-zinc-600">{body}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
