import type { Status } from '@/lib/api'

const config: Record<
  Status,
  { label: string; dot: string; badge: string }
> = {
  No_Creado: {
    label: 'Sin iniciar',
    dot:   'bg-zinc-600',
    badge: 'bg-zinc-800 text-zinc-400 border-zinc-700/50',
  },
  En_Proceso: {
    label: 'En Proceso',
    dot:   'bg-blue-500',
    badge: 'bg-blue-950/60 text-blue-300 border-blue-800/40',
  },
  Revisado_IA: {
    label: 'Revisado IA',
    dot:   'bg-amber-400',
    badge: 'bg-amber-950/60 text-amber-300 border-amber-700/40',
  },
  Requiere_Correccion: {
    label: 'Requiere corrección',
    dot:   'bg-rose-500 animate-pulse-badge',
    badge: 'bg-rose-950/60 text-rose-300 border-rose-800/40',
  },
  Listo_Manual: {
    label: 'Listo',
    dot:   'bg-emerald-400',
    badge: 'bg-emerald-950/60 text-emerald-300 border-emerald-800/40',
  },
}

export default function StatusBadge({ status }: { status: Status }) {
  const c = config[status] ?? config['No_Creado']
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${c.badge}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

export function compatBadge(c: string) {
  const map: Record<string, string> = {
    Alta:  'bg-emerald-950/50 text-emerald-400 border-emerald-800/30',
    Media: 'bg-amber-950/50  text-amber-400  border-amber-800/30',
    Baja:  'bg-zinc-800      text-zinc-400   border-zinc-700/30',
    Nula:  'bg-zinc-900      text-zinc-600   border-zinc-800/30',
  }
  return map[c] ?? map['Nula']
}
