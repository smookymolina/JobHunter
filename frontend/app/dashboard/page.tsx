'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Plus, Radio, RefreshCw, TrendingUp, WifiOff } from 'lucide-react'
import { api, type Status, type SyncHealthReport, type Vacante } from '@/lib/api'
import AddVacanteModal from '@/components/AddVacanteModal'
import KanbanBoard from '@/components/KanbanBoard'

const STAT_COLS: { id: Status; label: string; color: string }[] = [
  { id: 'No_Creado', label: 'Sin iniciar', color: 'text-zinc-400' },
  { id: 'En_Proceso', label: 'En proceso', color: 'text-blue-400' },
  { id: 'Revisado_IA', label: 'Revisado IA', color: 'text-amber-400' },
  { id: 'Requiere_Correccion', label: 'Con error', color: 'text-rose-400' },
  { id: 'Listo_Manual', label: 'CV Enviado', color: 'text-emerald-400' },
]

export default function DashboardPage() {
  const [vacantes, setVacantes] = useState<Vacante[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [spinning, setSpinning] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [scrapeRunning, setScrapeRunning] = useState(false)
  const [health, setHealth] = useState<SyncHealthReport | null>(null)

  const fetchVacantes = useCallback(async (silent = false) => {
    try {
      const data = await api.vacantes()
      setVacantes(data)
      if (!silent) setError('')
    } catch {
      if (!silent) setError('No se pudo conectar con la API. Verifica http://127.0.0.1:8000.')
    } finally {
      if (!silent) {
        setLoading(false)
        setSpinning(false)
      }
    }
  }, [])

  useEffect(() => {
    const checkScrape = async () => {
      try {
        const s = await api.scrapeStatus()
        setScrapeRunning(s.running)
      } catch {
        setScrapeRunning(false)
      }
    }
    void checkScrape()
    const id = setInterval(checkScrape, 3000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const checkHealth = async () => {
      try {
        setHealth(await api.debugSyncHealth())
      } catch {
        setHealth(null)
      }
    }
    void checkHealth()
    const id = setInterval(checkHealth, 5000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    void fetchVacantes()
  }, [fetchVacantes])

  useEffect(() => {
    const id = setInterval(() => {
      void fetchVacantes(true)
    }, 2000)
    return () => clearInterval(id)
  }, [fetchVacantes])

  const handleRefresh = () => {
    setSpinning(true)
    void fetchVacantes()
  }

  const count = (s: Status) => vacantes.filter(v => v.status === s).length
  const healthState = health?.state ?? 'idle'
  const healthDot =
    healthState === 'healthy'
      ? 'bg-emerald-400 shadow-emerald-400/40'
      : healthState === 'degraded'
        ? 'bg-amber-400 shadow-amber-400/40'
        : 'bg-zinc-500 shadow-zinc-500/30'

  return (
    <div className="flex h-full flex-col overflow-hidden bg-radial-indigo">
      <header className="flex shrink-0 flex-col gap-2 border-b border-white/[0.06] px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight text-zinc-50">Dashboard</h1>
            <div className="mt-1 flex items-center gap-2 text-[12px] text-zinc-500">
              <span className={`h-2.5 w-2.5 rounded-full ${healthDot}`} />
              <span>
                {healthState === 'healthy'
                  ? 'Salud del sistema: estable'
                  : healthState === 'degraded'
                    ? `Salud del sistema: degradada (${health?.issues.length ?? 0} incidencias)`
                    : `Salud del sistema: sin telemetría · ${vacantes.length} vacantes totales`}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-[12px] text-zinc-300 transition-colors hover:bg-white/[0.06] hover:text-zinc-100"
            >
              <Plus size={13} />
              Añadir vacante
            </button>
            <button
              onClick={handleRefresh}
              disabled={spinning}
              className="inline-flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 py-1.5 text-[12px] text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-zinc-200 disabled:opacity-40"
            >
              <RefreshCw size={13} className={spinning ? 'animate-spin' : ''} />
              Actualizar
            </button>
          </div>
        </div>

        {scrapeRunning && (
          <div className="flex items-center gap-2 self-start rounded-lg border border-blue-800/40 bg-blue-950/30 px-3 py-1.5 text-[12px] text-blue-300">
            <Radio size={13} className="animate-pulse" />
            Buscando vacantes de forma autónoma...
            <Loader2 size={12} className="animate-spin opacity-70" />
          </div>
        )}
      </header>

      {!loading && !error && (
        <div className="flex shrink-0 gap-4 border-b border-white/[0.06] px-6 py-3">
          {STAT_COLS.map(({ id, label, color }) => (
            <div key={id} className="flex flex-col">
              <span className={`text-[22px] font-bold leading-none ${color}`}>{count(id)}</span>
              <span className="mt-0.5 text-[11px] text-zinc-600">{label}</span>
            </div>
          ))}
          <div className="ml-auto flex items-center gap-1.5 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-1.5">
            <TrendingUp size={13} className="text-indigo-400" />
            <span className="text-[12px] text-zinc-500">
              {count('Listo_Manual')} / {vacantes.length} enviados
            </span>
          </div>
        </div>
      )}

      <main className="flex-1 overflow-hidden px-4 py-4">
        {loading && (
          <div className="flex h-full items-center justify-center">
            <Loader2 size={24} className="animate-spin text-zinc-600" />
          </div>
        )}

        {error && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <WifiOff size={32} className="text-zinc-700" />
            <p className="max-w-sm text-[13px] text-zinc-500">{error}</p>
            <button
              onClick={handleRefresh}
              className="text-[12px] text-indigo-400 transition-colors hover:text-indigo-300"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            <KanbanBoard vacantes={vacantes} onRefresh={handleRefresh} />
            <button
              onClick={() => setAddOpen(true)}
              className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-full bg-white px-4 py-3 text-[13px] font-semibold text-zinc-950 shadow-lg shadow-black/40 transition-transform hover:scale-[1.02]"
            >
              <Plus size={16} />
              Añadir Vacante
            </button>
          </>
        )}
      </main>

      <AddVacanteModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSuccess={handleRefresh}
      />
    </div>
  )
}
