'use client'

import { useCallback, useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  AlertCircle, Bot, Clock, Loader2,
  Plus, Radio, RefreshCw, Send, Sparkles, WifiOff,
} from 'lucide-react'
import Loader from '@/components/ui/Loader'
import { api, type Status, type SyncHealthReport, type Vacante } from '@/lib/api'
import AddVacanteModal from '@/components/AddVacanteModal'
import KanbanBoard from '@/components/KanbanBoard'

const STAT_COLS: {
  id: Status
  label: string
  numberColor: string
  icon: React.ElementType
  cardClass: string
}[] = [
  {
    id: 'No_Creado',
    label: 'Sin Iniciar',
    numberColor: 'text-slate-600 dark:text-slate-300',
    icon: Clock,
    cardClass: '',
  },
  {
    id: 'En_Proceso',
    label: 'En Proceso',
    numberColor: 'text-blue-500',
    icon: Loader2,
    cardClass: '',
  },
  {
    id: 'Revisado_IA',
    label: 'Revisado IA',
    numberColor: 'text-amber-500',
    icon: Bot,
    cardClass: '',
  },
  {
    id: 'Requiere_Correccion',
    label: 'Con Error',
    numberColor: 'text-rose-500',
    icon: AlertCircle,
    cardClass: '',
  },
  {
    id: 'Listo_Manual',
    label: 'CV Enviado',
    numberColor: 'text-emerald-500',
    icon: Send,
    cardClass: 'border-emerald-100 bg-emerald-50/60 dark:border-emerald-800/50 dark:bg-emerald-900/10',
  },
]

export default function DashboardPage() {
  const { status } = useSession()
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
    if (status === 'loading') {
      setLoading(true)
      return
    }
    if (status !== 'authenticated') {
      setLoading(false)
      setError('Sesión no autenticada.')
      return
    }
    void fetchVacantes()
  }, [fetchVacantes, status])

  useEffect(() => {
    if (status !== 'authenticated') return
    const id = setInterval(() => {
      void fetchVacantes(true)
    }, 2000)
    return () => clearInterval(id)
  }, [fetchVacantes, status])

  const handleRefresh = () => {
    setSpinning(true)
    void fetchVacantes()
  }

  const count = (s: Status) => vacantes.filter(v => v.status === s).length
  const healthState = health?.state ?? 'idle'

  const healthBadge =
    healthState === 'healthy'
      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800'
      : healthState === 'degraded'
        ? 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800'
        : 'bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-800/50 dark:text-slate-400 dark:border-slate-700'

  const healthDotColor =
    healthState === 'healthy'
      ? 'bg-emerald-500'
      : healthState === 'degraded'
        ? 'bg-amber-400'
        : 'bg-slate-400 dark:bg-slate-500'

  return (
    <div className="flex h-full flex-col overflow-hidden bg-radial-indigo">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 flex shrink-0 flex-col gap-2 border-b border-slate-100 bg-white/90 px-6 py-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">
              Dashboard
            </h1>
            <div className="mt-1.5 flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${healthBadge}`}>
                <span className={`h-1.5 w-1.5 animate-pulse rounded-full ${healthDotColor}`} />
                {healthState === 'healthy'
                  ? 'Salud del sistema: estable'
                  : healthState === 'degraded'
                    ? `Degradada · ${health?.issues.length ?? 0} incidencias`
                    : `Sin telemetría · ${vacantes.length} vacantes`}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={spinning}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900 disabled:opacity-40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            >
              <RefreshCw
                size={13}
                className={`transition-transform duration-500 ${spinning ? 'animate-spin' : 'hover:rotate-180'}`}
              />
              Actualizar
            </button>
            <button
              onClick={() => setAddOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-1.5 text-[12px] font-semibold text-white shadow-sm transition-all duration-200 hover:scale-105 hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
            >
              <Plus size={14} />
              Añadir Vacante
            </button>
          </div>
        </div>

        {scrapeRunning && (
          <div className="flex items-center gap-2 self-start rounded-xl border border-blue-200 bg-blue-50 px-3 py-1.5 text-[12px] text-blue-700 dark:border-blue-800/40 dark:bg-blue-950/30 dark:text-blue-300">
            <Radio size={13} className="animate-pulse" />
            Buscando vacantes de forma autónoma...
            <Loader2 size={12} className="animate-spin opacity-70" />
          </div>
        )}
      </header>

      {/* ── Stat Cards ─────────────────────────────────────────────── */}
      {!loading && !error && (
        <div className="shrink-0 border-b border-slate-100 px-6 py-4 dark:border-slate-800">
          <div className="grid grid-cols-5 gap-3">
            {STAT_COLS.map(({ id, label, numberColor, icon: Icon, cardClass }) => (
              <div
                key={id}
                className={`rounded-2xl border border-slate-100 bg-white p-4 shadow-sm transition-shadow duration-200 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 ${cardClass}`}
              >
                <div className="flex items-start justify-between">
                  <span className={`text-3xl font-bold leading-none ${numberColor}`}>
                    {count(id)}
                  </span>
                  <Icon size={16} className="mt-0.5 text-slate-300 dark:text-slate-600" />
                </div>
                <p className="mt-2 text-[11px] font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                  {label}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Main ───────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden px-4 py-4">
        {loading && (
          <div className="flex h-full items-center justify-center">
            <Loader size={36} label="Cargando vacantes..." />
          </div>
        )}

        {error && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <WifiOff size={32} className="text-slate-300 dark:text-slate-700" />
            <p className="max-w-sm text-[13px] text-slate-500">{error}</p>
            <button
              onClick={handleRefresh}
              className="text-[12px] text-rose-500 transition-colors hover:text-rose-400"
            >
              Reintentar
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            <KanbanBoard vacantes={vacantes} onRefresh={handleRefresh} />

            {/* FAB */}
            <button
              onClick={() => setAddOpen(true)}
              className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-5 py-3 text-[13px] font-semibold text-white shadow-lg shadow-slate-900/20 transition-transform duration-200 hover:scale-105 active:scale-95 dark:bg-white dark:text-slate-900 dark:shadow-white/10"
            >
              <Sparkles size={15} />
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
