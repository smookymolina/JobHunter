'use client'

import type { Vacante, Status } from '@/lib/api'
import VacanteCard from './VacanteCard'

interface Column {
  id: Status
  label: string
  accent: string
  headerBg: string
  countBg: string
  emptyText: string
}

const COLUMNS: Column[] = [
  {
    id: 'No_Creado',
    label: 'Sin iniciar',
    accent: 'border-t-zinc-700',
    headerBg: 'bg-zinc-900',
    countBg: 'bg-zinc-800 text-zinc-400',
    emptyText: 'Nuevas vacantes aparecerán aquí.',
  },
  {
    id: 'En_Proceso',
    label: 'En Proceso',
    accent: 'border-t-blue-600',
    headerBg: 'bg-zinc-900',
    countBg: 'bg-blue-950 text-blue-400',
    emptyText: 'CVs en generación activa.',
  },
  {
    id: 'Requiere_Correccion',
    label: 'Requiere Corrección',
    accent: 'border-t-rose-600',
    headerBg: 'bg-zinc-900',
    countBg: 'bg-rose-950 text-rose-400',
    emptyText: 'CVs que necesitan ajuste.',
  },
  {
    id: 'Revisado_IA',
    label: 'Revisado por IA',
    accent: 'border-t-amber-500',
    headerBg: 'bg-zinc-900',
    countBg: 'bg-amber-950 text-amber-400',
    emptyText: 'CVs aprobados pendientes de tu revisión.',
  },
  {
    id: 'Listo_Manual',
    label: 'CV Enviado',
    accent: 'border-t-emerald-500',
    headerBg: 'bg-zinc-900',
    countBg: 'bg-emerald-950 text-emerald-400',
    emptyText: 'CVs enviados, esperando respuesta de empresa.',
  },
]

interface Props {
  vacantes: Vacante[]
  onRefresh: () => void
}

export default function KanbanBoard({ vacantes, onRefresh }: Props) {
  const byStatus = (status: Status) => vacantes.filter(v => v.status === status)

  return (
    <div className="flex h-full gap-3 overflow-x-auto pb-4">
      {COLUMNS.map(col => {
        const items = byStatus(col.id)
        return (
          <div
            key={col.id}
            className={`flex w-[268px] shrink-0 flex-col rounded-xl border border-white/[0.06] border-t-2 ${col.accent} ${col.headerBg}`}
          >
            {/* Column header */}
            <div className="flex items-center justify-between px-3 py-2.5">
              <p className="text-[12px] font-semibold text-zinc-300">{col.label}</p>
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${col.countBg}`}>
                {items.length}
              </span>
            </div>

            <div className="mx-3 mb-2 border-t border-white/[0.05]" />

            {/* Cards */}
            <div className="flex flex-1 flex-col gap-2 overflow-y-auto px-2 pb-3">
              {items.length === 0 ? (
                <div className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-white/[0.06] py-8 text-center">
                  <p className="max-w-[180px] text-[11px] leading-relaxed text-zinc-600">
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
