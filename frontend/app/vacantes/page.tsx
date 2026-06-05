'use client'

import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, RefreshCw, WifiOff, Search } from 'lucide-react'
import Loader from '@/components/ui/Loader'
import { api, type Vacante } from '@/lib/api'
import StatusBadge, { compatBadge } from '@/components/StatusBadge'

export default function VacantesPage() {
  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [query, setQuery]       = useState('')
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  const load = useCallback(async () => {
    try {
      setError('')
      setVacantes(await api.vacantes())
    } catch {
      setError('Sin conexión con la API.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = vacantes.filter(v =>
    !query || `${v.titulo} ${v.empresa}`.toLowerCase().includes(query.toLowerCase())
  )

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-30 flex shrink-0 items-center justify-between border-b border-slate-100 bg-white/90 px-6 py-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90">
        <div>
          <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">Mis Vacantes</h1>
          <p className="text-[12px] text-slate-400 dark:text-slate-500">{vacantes.length} registros en total</p>
        </div>
        <button
          onClick={() => { setLoading(true); load() }}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <RefreshCw size={13} /> Actualizar
        </button>
      </header>

      {/* Search */}
      <div className="shrink-0 border-b border-slate-100 px-6 py-3 dark:border-slate-800">
        <div className="relative max-w-sm">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Buscar por título o empresa…"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-8 pr-3 text-[13px] text-slate-700 placeholder-slate-400 outline-none transition-colors focus:border-indigo-400 focus:bg-white dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:placeholder-slate-500 dark:focus:border-slate-600 dark:focus:bg-slate-900"
          />
        </div>
      </div>

      <main className="flex-1 overflow-auto px-6 py-4">
        {loading && (
          <div className="flex h-full items-center justify-center">
            <Loader size={36} label="Cargando vacantes..." />
          </div>
        )}

        {error && (
          <div className="flex h-40 flex-col items-center justify-center gap-2 text-center">
            <WifiOff size={28} className="text-slate-300 dark:text-slate-700" />
            <p className="text-[13px] text-slate-500">{error}</p>
          </div>
        )}

        {!loading && !error && (
          <div className="overflow-hidden rounded-2xl border border-slate-100 shadow-sm dark:border-slate-800">
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
                {filtered.map((v, i) => (
                  <tr
                    key={v.id}
                    className={`transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/40 ${
                      i % 2 === 0 ? 'bg-white dark:bg-slate-900' : 'bg-slate-50/40 dark:bg-slate-900/60'
                    }`}
                  >
                    <td className="px-4 py-3 text-slate-400 dark:text-slate-600">#{v.id}</td>
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
                        <a href={v.enlace} target="_blank" rel="noopener noreferrer"
                          className="text-slate-400 transition-colors hover:text-slate-600 dark:text-slate-600 dark:hover:text-slate-400">
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-slate-400 dark:text-slate-600">
                      No hay vacantes con ese filtro.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
