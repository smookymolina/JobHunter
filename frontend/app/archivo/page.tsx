'use client'

import { useCallback, useEffect, useState } from 'react'
import { Archive, ExternalLink, Loader2, RefreshCw, RotateCcw, Trash2, WifiOff } from 'lucide-react'
import { api, type VacanteEliminada } from '@/lib/api'

export default function ArchivoPage() {
  const [items, setItems]     = useState<VacanteEliminada[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [busy, setBusy]       = useState<number | null>(null)

  const load = useCallback(async (silent = false) => {
    try {
      setError('')
      setItems(await api.vacantesEliminadas())
    } catch {
      if (!silent) setError('Sin conexión con la API.')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleRestaurar = async (item: VacanteEliminada) => {
    if (!window.confirm(`¿Restaurar "${item.titulo || item.enlace}"?\nVolverá a aparecer en búsquedas futuras.`)) return
    setBusy(item.id)
    try {
      await api.restaurarEliminada(item.id)
      await load(true)
      setItems(prev => prev.filter(i => i.id !== item.id))
    } catch {
      alert('No se pudo restaurar la entrada.')
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between border-b border-slate-100 bg-white/90 px-6 py-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800">
            <Archive size={14} className="text-slate-500 dark:text-slate-400" />
          </div>
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">
              Vacantes Archivadas
            </h1>
            <p className="text-[12px] text-slate-400 dark:text-slate-500">
              {items.length} {items.length === 1 ? 'registro' : 'registros'} en lista negra
            </p>
          </div>
        </div>
        <button
          onClick={() => { setLoading(true); load() }}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <RefreshCw size={13} /> Actualizar
        </button>
      </header>

      <div className="shrink-0 border-b border-slate-100 px-6 py-3 dark:border-slate-800">
        <p className="text-[12px] text-slate-500 dark:text-slate-500">
          Estas vacantes fueron eliminadas manualmente. El scraper las omitirá permanentemente.
          Usa <span className="font-medium text-slate-700 dark:text-slate-300">Restaurar</span> para quitarlas de la lista negra.
        </p>
      </div>

      <main className="flex-1 overflow-y-auto px-6 py-4">
        {loading && (
          <div className="flex h-40 items-center justify-center">
            <Loader2 size={22} className="animate-spin text-slate-300 dark:text-slate-700" />
          </div>
        )}

        {error && (
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-center">
            <WifiOff size={28} className="text-slate-300 dark:text-slate-700" />
            <p className="text-[13px] text-slate-500">{error}</p>
            <button
              onClick={() => load()}
              className="text-[12px] text-rose-500 transition-colors hover:text-rose-400"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="flex h-48 flex-col items-center justify-center gap-3 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-800">
              <Trash2 size={20} className="text-slate-300 dark:text-slate-600" />
            </div>
            <p className="text-[13px] text-slate-400 dark:text-slate-600">No hay vacantes archivadas.</p>
          </div>
        )}

        {!loading && !error && items.length > 0 && (
          <div className="overflow-hidden rounded-2xl border border-slate-100 shadow-sm dark:border-slate-800">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 dark:border-slate-800 dark:bg-slate-900">
                  <th className="px-4 py-3 font-semibold text-slate-500">#</th>
                  <th className="px-4 py-3 font-semibold text-slate-500">Vacante</th>
                  <th className="px-4 py-3 font-semibold text-slate-500">Eliminada el</th>
                  <th className="px-4 py-3 font-semibold text-slate-500"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-slate-800/60">
                {items.map((item, i) => (
                  <tr
                    key={item.id}
                    className={`transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40 ${
                      i % 2 === 0 ? 'bg-white dark:bg-slate-900' : 'bg-slate-50/40 dark:bg-slate-900/60'
                    }`}
                  >
                    <td className="px-4 py-3 text-slate-400 dark:text-slate-600">#{item.id}</td>
                    <td className="px-4 py-3">
                      <p className="max-w-[280px] truncate font-medium text-slate-800 dark:text-slate-200">
                        {item.titulo || <span className="italic text-slate-400 dark:text-slate-600">Sin título</span>}
                      </p>
                      {item.enlace && (
                        <a
                          href={item.enlace}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-0.5 inline-flex max-w-[280px] items-center gap-1 truncate text-[11px] text-slate-400 transition-colors hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
                        >
                          {item.enlace.slice(0, 60)}{item.enlace.length > 60 ? '…' : ''}
                          <ExternalLink size={10} />
                        </a>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                      {item.fecha_eliminacion?.slice(0, 16).replace('T', ' ') ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleRestaurar(item)}
                        disabled={busy === item.id}
                        title="Quitar de la lista negra"
                        className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-[11px] font-medium text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-50 dark:border-indigo-700/30 dark:bg-indigo-950/20 dark:text-indigo-300 dark:hover:bg-indigo-950/40"
                      >
                        {busy === item.id
                          ? <Loader2 size={11} className="animate-spin" />
                          : <RotateCcw size={11} />}
                        Restaurar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
