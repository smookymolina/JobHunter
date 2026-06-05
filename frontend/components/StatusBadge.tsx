import type { Status } from '@/lib/api'

const config: Record<Status, { label: string; dot: string; badge: string }> = {
  No_Creado: {
    label: 'Sin iniciar',
    dot:   'bg-slate-400 dark:bg-slate-500',
    badge: 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700/50',
  },
  En_Proceso: {
    label: 'En Proceso',
    dot:   'bg-blue-500',
    badge: 'bg-blue-50 text-blue-600 border-blue-100 dark:bg-blue-950/60 dark:text-blue-300 dark:border-blue-800/40',
  },
  Revisado_IA: {
    label: 'Revisado IA',
    dot:   'bg-amber-400',
    badge: 'bg-amber-50 text-amber-600 border-amber-100 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-700/40',
  },
  Requiere_Correccion: {
    label: 'Requiere corrección',
    dot:   'bg-rose-500 animate-pulse-badge',
    badge: 'bg-rose-50 text-rose-600 border-rose-100 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/40',
  },
  Listo_Manual: {
    label: 'Listo',
    dot:   'bg-emerald-500',
    badge: 'bg-emerald-50 text-emerald-700 border-emerald-100 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/40',
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
    Alta:  'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-400 dark:border-emerald-800/30',
    Media: 'bg-amber-50  text-amber-700  border-amber-200  dark:bg-amber-950/50  dark:text-amber-400  dark:border-amber-800/30',
    Baja:  'bg-slate-100 text-slate-500  border-slate-200  dark:bg-slate-800     dark:text-slate-400  dark:border-slate-700/30',
    Nula:  'bg-slate-50  text-slate-400  border-slate-200  dark:bg-slate-900     dark:text-slate-600  dark:border-slate-800/30',
  }
  return map[c] ?? map['Nula']
}
