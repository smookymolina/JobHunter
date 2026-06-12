'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { AlertTriangle, CheckCircle2, FileJson, Loader2, Plus, RefreshCw, Search, Upload, X } from 'lucide-react'
import Link from 'next/link'
import { api, ApiError, type VacanteBulkInput, type FiltrosBusqueda } from '@/lib/api'

type Tab = 'manual' | 'bulk' | 'scrape'
type State = 'idle' | 'saving' | 'success' | 'error'

const PLATFORMS = [
  { id: 'computrabajo', label: 'Computrabajo' },
  { id: 'occ',          label: 'OCC' },
  { id: 'indeed',       label: 'Indeed RSS' },
  { id: 'bumeran',      label: 'Bumeran' },
  { id: 'getonbrd',     label: 'GetOnBrd' },
  { id: 'remotive',     label: 'Remotive' },
  { id: 'linkedin',     label: 'LinkedIn ⚡' },
] as const

const _ALL_PLATFORM_IDS = PLATFORMS.map(p => p.id)

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

const EMPTY_MANUAL = {
  titulo: '',
  empresa: '',
  enlace: '',
  requerimientos: '',
}

export default function AddVacanteModal({ open, onClose, onSuccess }: Props) {
  const [tab, setTab] = useState<Tab>('manual')
  const [state, setState] = useState<State>('idle')
  const [message, setMessage] = useState('')
  const [isPaywall, setIsPaywall] = useState(false)
  const [manual, setManual] = useState(EMPTY_MANUAL)
  const [bulkItems, setBulkItems] = useState<VacanteBulkInput[]>([])
  const [bulkName, setBulkName] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [scrapeCount, setScrapeCount]         = useState('5')
  const [suggestedTerms, setSuggestedTerms]   = useState<string[]>([])
  const [selectedTerms, setSelectedTerms]     = useState<Set<string>>(new Set())
  const [loadingTerms, setLoadingTerms]       = useState(false)
  const [customTermInput, setCustomTermInput] = useState('')
  const [minCompat, setMinCompat]             = useState<'Alta' | 'Media' | 'Baja' | 'Nula'>('Baja')
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set(_ALL_PLATFORM_IDS))
  const [minSalary, setMinSalary]             = useState('')
  const [filtros, setFiltros] = useState<FiltrosBusqueda>({
    ubicacion: '',
    modalidad: 'any',
    pais: 'Mexico',
  })
  const inputRef = useRef<HTMLInputElement>(null)

  const loadTerms = async () => {
    setLoadingTerms(true)
    try {
      const r = await api.searchTerms()
      setSuggestedTerms(r.terminos)
      setSelectedTerms(new Set(r.terminos))
    } catch { /* silencioso */ }
    finally { setLoadingTerms(false) }
  }

  useEffect(() => {
    if (!open) {
      setTab('manual')
      setState('idle')
      setMessage('')
      setIsPaywall(false)
      setManual(EMPTY_MANUAL)
      setBulkItems([])
      setBulkName('')
      setDragOver(false)
      setScrapeCount('5')
      setSuggestedTerms([])
      setSelectedTerms(new Set())
      setCustomTermInput('')
      setMinCompat('Baja')
      setSelectedPlatforms(new Set(_ALL_PLATFORM_IDS))
      setMinSalary('')
      setFiltros({ ubicacion: '', modalidad: 'any', pais: 'Mexico' })
    }
  }, [open])

  useEffect(() => {
    if (open && tab === 'scrape' && suggestedTerms.length === 0) {
      void loadTerms()
    }
  }, [open, tab])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  const parseBulkFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.json')) {
      throw new Error('Solo se aceptan archivos .json')
    }
    const raw = await file.text()
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      throw new Error('El JSON debe ser un arreglo de objetos.')
    }

    const normalized = parsed.map((item, index) => {
      if (!item || typeof item !== 'object') {
        throw new Error(`Elemento invalido en la posicion ${index + 1}.`)
      }
      const row = item as Record<string, unknown>
      const titulo = String(row.titulo ?? '').trim()
      const empresa = String(row.empresa ?? '').trim() || 'Desconocida'
      const enlace = String(row.enlace ?? '').trim()
      const requerimientos = String(row.requerimientos ?? '').trim()

      if (!titulo) {
        throw new Error(`Falta titulo en el elemento ${index + 1}.`)
      }

      return { titulo, empresa, enlace, requerimientos }
    })

    setBulkItems(normalized)
    setBulkName(file.name)
    setMessage(`${normalized.length} vacantes listas para importar.`)
    setState('idle')
  }

  const onFileChange = async (file?: File) => {
    if (!file) return
    setMessage('')
    try {
      await parseBulkFile(file)
    } catch (error) {
      setState('error')
      setMessage(error instanceof Error ? error.message : 'No se pudo leer el archivo.')
    }
  }

  const _handleError = (error: unknown, fallback: string) => {
    setState('error')
    if (error instanceof ApiError && error.status === 403) {
      setIsPaywall(true)
      setMessage('Límite de vacantes alcanzado.')
    } else {
      setIsPaywall(false)
      setMessage(error instanceof Error ? error.message : fallback)
    }
  }

  const submitManual = async () => {
    setState('saving')
    setMessage('')
    setIsPaywall(false)
    try {
      await api.createVacante(manual)
      setState('success')
      setMessage('Vacante creada correctamente.')
      onSuccess()
      onClose()
    } catch (error) {
      _handleError(error, 'No se pudo crear la vacante.')
    }
  }

  const submitBulk = async () => {
    setState('saving')
    setMessage('')
    setIsPaywall(false)
    try {
      const res = await api.bulkVacantes(bulkItems)
      setState('success')
      setMessage(`Importadas ${res.insertadas} vacantes. Duplicadas: ${res.duplicadas}.`)
      onSuccess()
      onClose()
    } catch (error) {
      _handleError(error, 'No se pudo importar el JSON.')
    }
  }

  const toggleTerm = (term: string) =>
    setSelectedTerms(prev => {
      const next = new Set(prev)
      next.has(term) ? next.delete(term) : next.add(term)
      return next
    })

  const addCustomTerms = useCallback(() => {
    const raw = customTermInput.trim()
    if (!raw) return
    const newTerms = raw.split(',').map(t => t.trim()).filter(Boolean)
    setSuggestedTerms(prev => {
      const existing = new Set(prev)
      const toAdd = newTerms.filter(t => !existing.has(t))
      return toAdd.length ? [...prev, ...toAdd] : prev
    })
    setSelectedTerms(prev => {
      const next = new Set(prev)
      newTerms.forEach(t => next.add(t))
      return next
    })
    setCustomTermInput('')
  }, [customTermInput])

  const submitScrape = async () => {
    const n = parseInt(scrapeCount, 10)
    if (!n || n < 1 || n > 200) {
      setState('error'); setMessage('Ingresa un número entre 1 y 200.')
      return
    }
    if (selectedTerms.size === 0) {
      setState('error'); setMessage('Selecciona al menos un término de búsqueda.')
      return
    }
    setState('saving'); setMessage('')
    try {
      const res = await api.scrape(n, Array.from(selectedTerms), {
        ...filtros,
        ...(minSalary ? { min_salary: parseInt(minSalary, 10) } : {}),
        platforms: Array.from(selectedPlatforms),
      }, minCompat)
      setState('success')
      setMessage(`${res.mensaje} · Tablero se actualiza automáticamente.`)
      onSuccess()
    } catch (error) {
      setState('error')
      setMessage(error instanceof Error ? error.message : 'No se pudo iniciar el scraping.')
    }
  }

  if (!open) return null

  const inputClass = 'w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[13px] text-slate-800 outline-none transition-colors placeholder-slate-400 focus:border-indigo-400 focus:bg-white dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder-slate-500 dark:focus:border-indigo-500/50 dark:focus:bg-slate-700/60'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4 py-6 backdrop-blur-md dark:bg-black/70"
      onMouseDown={onClose}
    >
      <div
        className="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-700 dark:bg-slate-950"
        onMouseDown={e => e.stopPropagation()}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-indigo-500/80 to-transparent" />
        <div className="absolute -right-20 -top-20 h-48 w-48 rounded-full bg-indigo-500/5 blur-3xl dark:bg-indigo-500/10" />
        <div className="absolute -left-20 bottom-0 h-56 w-56 rounded-full bg-emerald-500/5 blur-3xl dark:bg-emerald-500/10" />

        {/* Header */}
        <div className="relative flex items-center justify-between border-b border-slate-100 px-5 py-4 dark:border-slate-800">
          <div>
            <p className="text-[15px] font-semibold text-slate-900 dark:text-slate-100">Añadir vacante</p>
            <p className="text-[12px] text-slate-400 dark:text-slate-500">Alta rápida manual, JSON masivo o búsqueda autónoma</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-xl border border-slate-200 p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:border-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="relative px-5 pt-4">
          <div className="inline-flex rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-800/50">
            {([
              { id: 'manual',  label: 'Manual' },
              { id: 'bulk',    label: 'JSON masivo' },
              { id: 'scrape',  label: 'Búsqueda autónoma' },
            ] as { id: Tab; label: string }[]).map(({ id: current, label }) => (
              <button
                key={current}
                onClick={() => setTab(current)}
                className={`rounded-lg px-4 py-2 text-[12px] font-medium transition-colors ${
                  tab === current
                    ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100'
                    : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="relative flex min-h-0 flex-1 flex-col">
        <div className="flex-1 overflow-y-auto px-5 py-5 [scrollbar-width:thin]">
        <div className="space-y-4">
          {tab === 'manual' && (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-1">
                <span className="text-[12px] font-medium text-slate-500 dark:text-slate-400">Titulo</span>
                <input
                  value={manual.titulo}
                  onChange={e => setManual(prev => ({ ...prev, titulo: e.target.value }))}
                  className={inputClass}
                  placeholder="Frontend Engineer"
                />
              </label>
              <label className="space-y-1">
                <span className="text-[12px] font-medium text-slate-500 dark:text-slate-400">Empresa</span>
                <input
                  value={manual.empresa}
                  onChange={e => setManual(prev => ({ ...prev, empresa: e.target.value }))}
                  className={inputClass}
                  placeholder="Acme Inc."
                />
              </label>
              <label className="space-y-1 md:col-span-2">
                <span className="text-[12px] font-medium text-slate-500 dark:text-slate-400">Enlace</span>
                <input
                  value={manual.enlace}
                  onChange={e => setManual(prev => ({ ...prev, enlace: e.target.value }))}
                  className={inputClass}
                  placeholder="https://..."
                />
              </label>
              <label className="space-y-1 md:col-span-2">
                <span className="text-[12px] font-medium text-slate-500 dark:text-slate-400">Requerimientos</span>
                <textarea
                  value={manual.requerimientos}
                  onChange={e => setManual(prev => ({ ...prev, requerimientos: e.target.value }))}
                  rows={6}
                  className={inputClass}
                  placeholder="Requisitos, stack, beneficios, etc."
                />
              </label>
            </div>
          )}

          {tab === 'bulk' && (
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={async e => {
                e.preventDefault()
                setDragOver(false)
                await onFileChange(e.dataTransfer.files[0])
              }}
              onClick={() => inputRef.current?.click()}
              className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-all ${
                dragOver
                  ? 'border-indigo-400 bg-indigo-50 dark:border-indigo-500 dark:bg-indigo-950/20'
                  : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white dark:border-slate-700 dark:bg-slate-800/30 dark:hover:border-slate-600'
              }`}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={e => onFileChange(e.target.files?.[0])}
              />
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
                <Upload size={22} className="text-slate-400 dark:text-slate-400" />
              </div>
              <div>
                <p className="text-[14px] font-medium text-slate-700 dark:text-slate-200">
                  {bulkName || 'Arrastra un archivo JSON o haz clic para seleccionarlo'}
                </p>
                <p className="mt-1 text-[12px] text-slate-400 dark:text-slate-500">
                  Formato esperado: array con llaves titulo, empresa, enlace y requerimientos
                </p>
              </div>
              <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400">
                <FileJson size={12} />
                {bulkItems.length > 0 ? `${bulkItems.length} registros listos` : 'Solo archivos .json'}
              </span>
            </div>
          )}

          {tab === 'scrape' && (
            <div className="space-y-4">
              {/* Términos del perfil */}
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Términos del perfil · {selectedTerms.size}/{suggestedTerms.length} seleccionados
                  </span>
                  <button onClick={loadTerms} disabled={loadingTerms}
                    className="inline-flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-40 dark:text-slate-500 dark:hover:text-slate-300">
                    <RefreshCw size={10} className={loadingTerms ? 'animate-spin' : ''} /> Recargar
                  </button>
                </div>

                {loadingTerms ? (
                  <div className="flex items-center justify-center py-6">
                    <Loader2 size={18} className="animate-spin text-slate-300 dark:text-slate-600" />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-1.5">
                    {suggestedTerms.map(term => (
                      <button
                        key={term}
                        onClick={() => toggleTerm(term)}
                        className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-[11px] transition-colors ${
                          selectedTerms.has(term)
                            ? 'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-500/40 dark:bg-indigo-950/40 dark:text-indigo-200'
                            : 'border-slate-200 bg-slate-50 text-slate-500 hover:text-slate-700 dark:border-slate-700 dark:bg-slate-800/30 dark:text-slate-500 dark:hover:text-slate-300'
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${selectedTerms.has(term) ? 'bg-indigo-400' : 'bg-slate-300 dark:bg-slate-600'}`} />
                        {term}
                      </button>
                    ))}
                  </div>
                )}

                {/* Custom terms input */}
                <div className="mt-2 flex gap-1.5">
                  <input
                    value={customTermInput}
                    onChange={e => setCustomTermInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addCustomTerms() } }}
                    placeholder="Agregar términos custom (separados por coma)"
                    className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[11px] text-slate-700 placeholder-slate-400 outline-none focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder-slate-500 dark:focus:border-indigo-500/40"
                  />
                  <button
                    onClick={addCustomTerms}
                    disabled={!customTermInput.trim()}
                    className="flex items-center gap-1 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-[11px] font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-40 dark:border-indigo-500/40 dark:bg-indigo-950/40 dark:text-indigo-300 dark:hover:bg-indigo-950/60"
                  >
                    <Plus size={12} /> Añadir
                  </button>
                </div>
              </div>

              {/* Compatibilidad mínima */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Compatibilidad mínima
                  </span>
                  <span className="text-[10px] text-slate-400 dark:text-slate-500">filtra antes de guardar</span>
                </div>
                <div className="flex gap-1.5">
                  {(['Alta', 'Media', 'Baja', 'Nula'] as const).map(level => {
                    const labels: Record<string, string> = { Alta: 'Alta', Media: 'Media', Baja: 'Baja+', Nula: 'Todas' }
                    const colors: Record<string, string> = {
                      Alta:  'border-green-200 bg-green-50 text-green-700 dark:border-green-500/40 dark:bg-green-950/40 dark:text-green-300',
                      Media: 'border-yellow-200 bg-yellow-50 text-yellow-700 dark:border-yellow-500/40 dark:bg-yellow-950/40 dark:text-yellow-300',
                      Baja:  'border-orange-200 bg-orange-50 text-orange-700 dark:border-orange-500/40 dark:bg-orange-950/40 dark:text-orange-300',
                      Nula:  'border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-800/30 dark:text-slate-400',
                    }
                    const active = minCompat === level
                    return (
                      <button
                        key={level}
                        onClick={() => setMinCompat(level)}
                        className={`flex-1 rounded-lg border px-2 py-1.5 text-[11px] font-medium transition-colors ${
                          active ? colors[level] : 'border-slate-200 text-slate-400 hover:text-slate-600 dark:border-slate-700 dark:text-slate-500'
                        }`}
                      >
                        {labels[level]}
                        {level === 'Baja' && !active && <span className="ml-1 text-[9px] text-indigo-400">por defecto</span>}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Filtros de búsqueda */}
              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/30">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Filtros de búsqueda</p>

                <div className="space-y-1.5">
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">Modalidad</span>
                  <div className="flex flex-wrap gap-1.5">
                    {([
                      { val: 'any',        label: 'Cualquiera' },
                      { val: 'remoto',     label: 'Remoto' },
                      { val: 'hibrido',    label: 'Híbrido' },
                      { val: 'presencial', label: 'Presencial' },
                    ] as { val: FiltrosBusqueda['modalidad']; label: string }[]).map(({ val, label }) => (
                      <button
                        key={val}
                        onClick={() => setFiltros(f => ({ ...f, modalidad: val, ubicacion: val === 'remoto' ? '' : f.ubicacion }))}
                        className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-colors ${
                          filtros.modalidad === val
                            ? 'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-500/50 dark:bg-indigo-950/50 dark:text-indigo-200'
                            : 'border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-700 dark:border-slate-700 dark:text-slate-400 dark:hover:text-slate-300'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {filtros.modalidad !== 'remoto' && (
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">Ubicación</span>
                      <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[9px] text-slate-400 dark:bg-slate-700 dark:text-slate-500">
                        Alias: CDMX, GDL, MTY, NL, EdomEx…
                      </span>
                    </div>
                    <input
                      value={filtros.ubicacion}
                      onChange={e => setFiltros(f => ({ ...f, ubicacion: e.target.value }))}
                      placeholder="Ciudad de México / CDMX / GDL… (vacío = cualquiera)"
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[12px] text-slate-700 placeholder-slate-400 outline-none focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:placeholder-slate-500 dark:focus:border-indigo-500/40"
                    />
                  </div>
                )}

                <div className="space-y-1.5">
                  <span className="text-[11px] text-slate-500 dark:text-slate-400">País</span>
                  <select
                    value={filtros.pais}
                    onChange={e => setFiltros(f => ({ ...f, pais: e.target.value }))}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[12px] text-slate-700 outline-none focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:focus:border-indigo-500/40"
                  >
                    <option value="Mexico">México</option>
                    <option value="España">España</option>
                    <option value="Argentina">Argentina</option>
                    <option value="Colombia">Colombia</option>
                    <option value="Chile">Chile</option>
                    <option value="Internacional">Internacional (multi-país)</option>
                  </select>
                </div>
              </div>

              {/* Salario mínimo */}
              <div className="space-y-1.5 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/30">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">Salario mínimo mensual (MXN)</p>
                <div className="flex items-center gap-2">
                  <span className="text-[13px] text-slate-400">$</span>
                  <input
                    type="number" min={0} step={1000}
                    value={minSalary}
                    onChange={e => setMinSalary(e.target.value)}
                    placeholder="Sin filtro"
                    className="w-36 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-[12px] text-slate-700 outline-none focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:focus:border-indigo-500/40"
                  />
                  <span className="text-[11px] text-slate-400 dark:text-slate-600">MXN/mes (opcional)</span>
                </div>
              </div>

              {/* Plataformas */}
              <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/30">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    Plataformas · {selectedPlatforms.size}/{PLATFORMS.length}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setSelectedPlatforms(new Set(_ALL_PLATFORM_IDS))}
                      className="text-[10px] text-indigo-500 hover:text-indigo-700 transition-colors dark:text-indigo-400"
                    >
                      Todas
                    </button>
                    <span className="text-slate-300 dark:text-slate-600">·</span>
                    <button
                      onClick={() => setSelectedPlatforms(new Set())}
                      className="text-[10px] text-slate-400 hover:text-slate-600 transition-colors dark:text-slate-500"
                    >
                      Ninguna
                    </button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-4">
                  {PLATFORMS.map(({ id, label }) => {
                    const active = selectedPlatforms.has(id)
                    return (
                      <button
                        key={id}
                        onClick={() => setSelectedPlatforms(prev => {
                          const next = new Set(prev)
                          next.has(id) ? next.delete(id) : next.add(id)
                          return next
                        })}
                        className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                          active
                            ? 'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-500/40 dark:bg-indigo-950/40 dark:text-indigo-200'
                            : 'border-slate-200 text-slate-400 hover:text-slate-600 dark:border-slate-700 dark:text-slate-500'
                        }`}
                      >
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${active ? 'bg-indigo-400' : 'bg-slate-300 dark:bg-slate-600'}`} />
                        {label}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Cantidad */}
              <div className="flex items-center gap-3">
                <label className="text-[12px] text-slate-500 dark:text-slate-400 shrink-0">Vacantes a extraer</label>
                <input
                  type="number" min={1} max={200}
                  value={scrapeCount}
                  onChange={e => setScrapeCount(e.target.value)}
                  className="w-24 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-center text-[16px] font-bold text-slate-800 outline-none focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:focus:border-indigo-500/50"
                />
                <span className="text-[11px] text-slate-400 dark:text-slate-600">máx. 200</span>
              </div>
            </div>
          )}

        </div>
        </div>

          {(state === 'error' || message) && (
            <div className={`mx-5 mb-2 flex items-start gap-2 rounded-xl border px-4 py-3 text-[12px] ${
              state === 'error'
                ? 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-800/30 dark:bg-rose-950/20 dark:text-rose-300'
                : 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800/30 dark:bg-emerald-950/20 dark:text-emerald-300'
            }`}>
              {state === 'error'
                ? <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                : <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
              }
              <p className="leading-relaxed">
                {message}
                {isPaywall && (
                  <>
                    {' '}
                    <Link
                      href="/pricing"
                      onClick={onClose}
                      className="font-semibold underline underline-offset-2 hover:opacity-80 transition-opacity"
                    >
                      Ver planes de mejora →
                    </Link>
                  </>
                )}
              </p>
            </div>
          )}

          <div className="flex shrink-0 items-center justify-end gap-2 border-t border-slate-100 px-5 py-4 dark:border-slate-800">
            <button
              onClick={onClose}
              className="rounded-xl border border-slate-200 px-4 py-2 text-[12px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              Cancelar
            </button>
            <button
              disabled={state === 'saving' || (tab === 'bulk' && bulkItems.length === 0)}
              onClick={
                tab === 'manual' ? submitManual
                : tab === 'bulk'  ? submitBulk
                : submitScrape
              }
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-[12px] font-semibold text-white shadow-md shadow-indigo-500/20 transition-transform hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
            >
              {state === 'saving'
                ? <Loader2 size={14} className="animate-spin" />
                : tab === 'scrape' ? <Search size={14} /> : <Plus size={14} />
              }
              {tab === 'manual' ? 'Crear vacante'
               : tab === 'bulk'  ? 'Importar JSON'
               : 'Iniciar búsqueda'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
