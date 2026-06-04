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
      <header className="flex shrink-0 items-center justify-between border-b border-white/[0.06] px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.06] bg-white/[0.03]">
            <Archive size={14} className="text-zinc-400" />
          </div>
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight text-zinc-50">Vacantes Archivadas</h1>
            <p className="text-[12px] text-zinc-500">
              {items.length} {items.length === 1 ? 'registro' : 'registros'} en lista negra
            </p>
          </div>
        </div>
        <button
          onClick={() => { setLoading(true); load() }}
          className="inline-flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-zinc-200"
        >
          <RefreshCw size={13} /> Actualizar
        </button>
      </header>

      <div className="shrink-0 border-b border-white/[0.06] px-6 py-3">
        <p className="text-[12px] text-zinc-600">
          Estas vacantes fueron eliminadas manualmente. El scraper las omitirá permanentemente.
          Usa <span className="text-zinc-400">Restaurar</span> para quitarlas de la lista negra y que puedan reaparecer en búsquedas futuras.
        </p>
      </div>

      <main className="flex-1 overflow-auto px-6 py-4">
        {loading && (
          <div className="flex h-40 items-center justify-center">
            <Loader2 size={22} className="animate-spin text-zinc-700" />
          </div>
        )}

        {error && (
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-center">
            <WifiOff size={28} className="text-zinc-700" />
            <p className="text-[13px] text-zinc-500">{error}</p>
            <button
              onClick={() => load()}
              className="text-[12px] text-indigo-400 transition-colors hover:text-indigo-300"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="flex h-48 flex-col items-center justify-center gap-3 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/[0.06] bg-white/[0.02]">
              <Trash2 size={20} className="text-zinc-700" />
            </div>
            <p className="text-[13px] text-zinc-600">No hay vacantes archivadas.</p>
          </div>
        )}

        {!loading && !error && items.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-white/[0.06]">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">#</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">Vacante</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">Eliminada el</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr
                    key={item.id}
                    className={`border-b border-white/[0.04] transition-colors hover:bg-white/[0.02] ${
                      i % 2 === 0 ? '' : 'bg-white/[0.01]'
                    }`}
                  >
                    <td className="px-4 py-3 text-zinc-600">#{item.id}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-zinc-200 truncate max-w-[280px]">
                        {item.titulo || <span className="text-zinc-600 italic">Sin título</span>}
                      </p>
                      {item.enlace && (
                        <a
                          href={item.enlace}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[11px] text-zinc-500 transition-colors hover:text-zinc-300 mt-0.5 truncate max-w-[280px]"
                        >
                          {item.enlace.slice(0, 60)}{item.enlace.length > 60 ? '…' : ''}
                          <ExternalLink size={10} />
                        </a>
                      )}
                    </td>
                    <td className="px-4 py-3 text-zinc-500 whitespace-nowrap">
                      {item.fecha_eliminacion?.slice(0, 16).replace('T', ' ') ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleRestaurar(item)}
                        disabled={busy === item.id}
                        title="Quitar de la lista negra"
                        className="inline-flex items-center gap-1.5 rounded-md border border-indigo-700/30 bg-indigo-950/20 px-2.5 py-1 text-[11px] font-medium text-indigo-300 transition-colors hover:bg-indigo-950/40 disabled:opacity-50"
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
