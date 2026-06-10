'use client'

import { Inbox, X } from 'lucide-react'
import { type Vacante, type Status } from '@/lib/api'
import VacanteCard from './VacanteCard'

interface Column {
  id: Status
  label: string
  headerClass: string
  borderAccent: string
  emptyText: string
}

const COLUMNS: Column[] = [
  {
    id: 'No_Creado',
    label: 'Sin iniciar',
    headerClass: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
    borderAccent: 'border-t-slate-300 dark:border-t-slate-600',
    emptyText: 'Nuevas vacantes aparecerán aquí.',
  },
  {
    id: 'En_Proceso',
    label: 'En Proceso',
    headerClass: 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
    borderAccent: 'border-t-blue-400 dark:border-t-blue-500',
    emptyText: 'CVs en generación activa.',
  },
  {
    id: 'Requiere_Correccion',
    label: 'Requiere Corrección',
    headerClass: 'bg-rose-50 text-rose-600 dark:bg-rose-900/20 dark:text-rose-400',
    borderAccent: 'border-t-rose-400 dark:border-t-rose-500',
    emptyText: 'CVs que necesitan ajuste.',
  },
  {
    id: 'Revisado_IA',
    label: 'Revisado por IA',
    headerClass: 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400',
    borderAccent: 'border-t-amber-400 dark:border-t-amber-500',
    emptyText: 'CVs aprobados pendientes de revisión.',
  },
  {
    id: 'Listo_Manual',
    label: 'CV Enviado',
    headerClass: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',
    borderAccent: 'border-t-emerald-400 dark:border-t-emerald-500',
    emptyText: 'CVs enviados, esperando respuesta.',
  },
  {
    id: 'Entrevista',
    label: 'Entrevista',
    headerClass: 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
    borderAccent: 'border-t-purple-500 dark:border-t-purple-500',
    emptyText: 'Vacantes que llegaron a entrevista.',
  },
]

interface Props {
  vacantes: Vacante[]
  onRefresh: () => void
  activeFilter: Status | null
  setActiveFilter: (s: Status | null) => void
}

const DYNAMIC_COLS = new Set<Status>(['En_Proceso', 'Requiere_Correccion'])
const COMPAT_RANK: Record<string, number> = { Alta: 3, Media: 2, Baja: 1, Nula: 0 }

function sortColumn(items: Vacante[]): Vacante[] {
  return [...items].sort((a, b) => {
    if (b.favorito !== a.favorito) return b.favorito - a.favorito
    const ca = COMPAT_RANK[a.compatibilidad] ?? 0
    const cb = COMPAT_RANK[b.compatibilidad] ?? 0
    if (cb !== ca) return cb - ca
    return b.id - a.id
  })
}

export default function KanbanBoard({ vacantes, onRefresh, activeFilter, setActiveFilter }: Props) {
  const byStatus = (status: Status) => sortColumn(vacantes.filter(v => v.status === status))

  const visibleColumns = activeFilter
    ? COLUMNS.filter(c => c.id === activeFilter)
    : COLUMNS.filter(col => !DYNAMIC_COLS.has(col.id) || byStatus(col.id).length > 0)

  return (
    <div className={`flex h-full gap-3 ${activeFilter ? 'flex-col overflow-y-auto' : 'overflow-x-auto'} pb-4`}>
      {visibleColumns.map(col => {
        const items = byStatus(col.id)
        const isExpanded = activeFilter !== null

        return (
          <div
            key={col.id}
            className={`flex shrink-0 flex-col rounded-2xl border border-t-2 border-slate-200/50 bg-slate-100/60 backdrop-blur-sm dark:border-slate-800/50 dark:bg-slate-900/50 ${
              col.borderAccent
            } ${isExpanded ? 'w-full flex-1' : 'w-[268px]'}`}
          >
            {/* Column header */}
            <div className="flex items-center justify-between px-3 pt-3 pb-2">
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${col.headerClass}`}>
                  {col.label}
                </span>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${col.headerClass}`}>
                  {items.length}
                </span>
              </div>
              {isExpanded && (
                <button
                  onClick={() => setActiveFilter(null)}
                  className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-medium text-slate-500 transition-colors hover:bg-slate-200 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                >
                  <X size={14} />
                  Ver todo el tablero
                </button>
              )}
            </div>

            <div className="mx-3 mb-2 border-t border-slate-200/70 dark:border-slate-800/70" />

            {/* Cards */}
            <div className={`flex flex-1 flex-col gap-2 overflow-y-auto px-2 pb-3 ${
              isExpanded ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4' : ''
            }`}>
              {items.length === 0 ? (
                <div className={`flex flex-1 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-200 py-8 text-center dark:border-slate-800 ${
                  isExpanded ? 'col-span-full py-20' : ''
                }`}>
                  <Inbox size={20} className="text-slate-200 dark:text-slate-700" />
                  <p className="max-w-[160px] text-[11px] italic leading-relaxed text-slate-300 dark:text-slate-600">
                    {col.emptyText}
                  </p>
                </div>
              ) : (
                items.map(v => (
                  <VacanteCard key={v.id} vacante={v} onStatusChange={onRefresh} />
                ))
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
