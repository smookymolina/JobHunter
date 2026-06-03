'use client'

import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, RefreshCw, Loader2, WifiOff, Search } from 'lucide-react'
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
      <header className="flex shrink-0 items-center justify-between border-b border-white/[0.06] px-6 py-4">
        <div>
          <h1 className="text-[18px] font-semibold tracking-tight text-zinc-50">Mis Vacantes</h1>
          <p className="text-[12px] text-zinc-500">{vacantes.length} registros en total</p>
        </div>
        <button
          onClick={() => { setLoading(true); load() }}
          className="inline-flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-zinc-200"
        >
          <RefreshCw size={13} /> Actualizar
        </button>
      </header>

      {/* Search */}
      <div className="shrink-0 border-b border-white/[0.06] px-6 py-3">
        <div className="relative max-w-sm">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-600" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Buscar por título o empresa…"
            className="w-full rounded-lg border border-white/[0.06] bg-white/[0.03] py-2 pl-8 pr-3 text-[13px] text-zinc-300 placeholder-zinc-600 outline-none transition-colors focus:border-white/[0.12] focus:bg-white/[0.05]"
          />
        </div>
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
          </div>
        )}

        {!loading && !error && (
          <div className="overflow-hidden rounded-xl border border-white/[0.06]">
            <table className="w-full text-left text-[12px]">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">ID</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">Puesto</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">Empresa</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">Compat.</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">Status</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500">Fecha</th>
                  <th className="px-4 py-2.5 font-semibold text-zinc-500"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((v, i) => (
                  <tr
                    key={v.id}
                    className={`border-b border-white/[0.04] transition-colors hover:bg-white/[0.03] ${
                      i % 2 === 0 ? '' : 'bg-white/[0.01]'
                    }`}
                  >
                    <td className="px-4 py-3 text-zinc-600">#{v.id}</td>
                    <td className="max-w-[220px] px-4 py-3">
                      <p className="truncate font-medium text-zinc-200">{v.titulo}</p>
                    </td>
                    <td className="px-4 py-3 text-zinc-500">{v.empresa}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${compatBadge(v.compatibilidad)}`}>
                        {v.compatibilidad}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={v.status} />
                    </td>
                    <td className="px-4 py-3 text-zinc-600">{v.fecha_registro?.slice(0, 10)}</td>
                    <td className="px-4 py-3">
                      {v.enlace && (
                        <a href={v.enlace} target="_blank" rel="noopener noreferrer"
                          className="text-zinc-600 transition-colors hover:text-zinc-400">
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-zinc-600">
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
