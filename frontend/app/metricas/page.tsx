'use client'

import { useEffect, useState } from 'react'
import { useSession } from 'next-auth/react'
import { BarChart2, MessageCircle, Send, Target, TrendingUp, Zap } from 'lucide-react'
import Loader from '@/components/ui/Loader'
import { api, type MetricasData } from '@/lib/api'

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
}: {
  label: string
  value: string | number
  sub?: string
  icon: React.ElementType
  accent: string
}) {
  return (
    <div className={`rounded-2xl border bg-white p-5 shadow-sm dark:bg-slate-900 ${accent}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
            {label}
          </p>
          <p className="mt-2 text-4xl font-bold leading-none text-slate-900 dark:text-slate-50">
            {value}
          </p>
          {sub && (
            <p className="mt-1.5 text-[12px] text-slate-400 dark:text-slate-500">{sub}</p>
          )}
        </div>
        <span className={`rounded-xl p-2.5 ${accent}`}>
          <Icon size={20} className="text-current opacity-70" />
        </span>
      </div>
    </div>
  )
}

export default function MetricasPage() {
  const { status } = useSession()
  const [data, setData] = useState<MetricasData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (status === 'loading') return
    if (status !== 'authenticated') {
      setLoading(false)
      setError('Sesión no autenticada.')
      return
    }
    api.metricas()
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError('No se pudo cargar las métricas.'); setLoading(false) })
  }, [status])

  const maxSkillCount = data?.top_skills_entrevistas?.[0]?.count ?? 1

  return (
    <div className="min-h-full bg-white dark:bg-slate-950">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-slate-100 bg-white/90 px-6 py-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-100 dark:bg-purple-900/30">
            <BarChart2 size={16} className="text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">
              Métricas y Rendimiento del Perfil
            </h1>
            <p className="text-[12px] text-slate-400 dark:text-slate-500">
              KPIs de tu proceso de búsqueda de empleo
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-8">
        {loading && (
          <div className="flex h-64 items-center justify-center">
            <Loader size={36} label="Calculando métricas..." />
          </div>
        )}

        {error && (
          <div className="flex h-64 items-center justify-center">
            <p className="text-[13px] text-rose-500">{error}</p>
          </div>
        )}

        {!loading && !error && data && (
          <div className="space-y-8">
            {/* KPI Grid */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <KpiCard
                label="Total Aplicadas"
                value={data.total_aplicadas}
                sub="Vacantes con CV iniciado"
                icon={Target}
                accent="border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50"
              />
              <KpiCard
                label="Entrevistas Logradas"
                value={data.total_entrevistas}
                sub="Llamadas o entrevistas confirmadas"
                icon={MessageCircle}
                accent="border-purple-200 dark:border-purple-800/50 text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20"
              />
              <KpiCard
                label="Tasa de Conversión"
                value={`${data.tasa_conversion}%`}
                sub="Entrevistas / Aplicadas"
                icon={TrendingUp}
                accent="border-emerald-200 dark:border-emerald-800/50 text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20"
              />
            </div>

            {/* Secondary stat */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                  CVs Enviados
                </p>
                <div className="mt-3 flex items-end gap-3">
                  <p className="text-4xl font-bold text-slate-900 dark:text-slate-50">{data.total_enviados}</p>
                  <Send size={18} className="mb-1 text-emerald-500" />
                </div>
                <p className="mt-1.5 text-[12px] text-slate-400 dark:text-slate-500">
                  Vacantes marcadas como Listo_Manual
                </p>
              </div>

              {/* Conversion bar */}
              <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                  Embudo de Conversión
                </p>
                <div className="mt-4 space-y-3">
                  <div>
                    <div className="mb-1 flex justify-between text-[12px] text-slate-500 dark:text-slate-400">
                      <span>Aplicadas</span>
                      <span className="font-semibold">{data.total_aplicadas}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div className="h-full rounded-full bg-slate-400 dark:bg-slate-500" style={{ width: '100%' }} />
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 flex justify-between text-[12px] text-slate-500 dark:text-slate-400">
                      <span>CV Enviado</span>
                      <span className="font-semibold">{data.total_enviados}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full bg-emerald-500 dark:bg-emerald-400 transition-all"
                        style={{ width: `${data.total_aplicadas > 0 ? Math.min(100, (data.total_enviados / data.total_aplicadas) * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="mb-1 flex justify-between text-[12px] text-slate-500 dark:text-slate-400">
                      <span>Entrevistas</span>
                      <span className="font-semibold text-purple-600 dark:text-purple-400">{data.total_entrevistas}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full bg-purple-500 dark:bg-purple-400 transition-all"
                        style={{ width: `${data.total_aplicadas > 0 ? Math.min(100, (data.total_entrevistas / data.total_aplicadas) * 100) : 0}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Insights: Top skills */}
            <div className="rounded-2xl border border-purple-200/60 bg-gradient-to-br from-purple-50 to-white p-6 shadow-sm dark:border-purple-800/30 dark:from-purple-950/20 dark:to-slate-900">
              <div className="mb-5 flex items-center gap-2">
                <Zap size={15} className="text-purple-500 dark:text-purple-400" />
                <h2 className="text-[14px] font-semibold text-slate-800 dark:text-slate-100">
                  Habilidades de Alta Conversión
                </h2>
                <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-600 dark:bg-purple-900/40 dark:text-purple-300">
                  IA Insight
                </span>
              </div>

              {data.top_skills_entrevistas.length === 0 ? (
                <div className="rounded-xl border border-dashed border-purple-200 py-8 text-center dark:border-purple-800/30">
                  <MessageCircle size={24} className="mx-auto mb-2 text-purple-200 dark:text-purple-800" />
                  <p className="text-[12px] text-slate-400 dark:text-slate-500">
                    Mueve vacantes al estado &quot;Entrevista&quot; para descubrir qué habilidades generan más conversiones.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {data.top_skills_entrevistas.map(({ skill, count }) => (
                    <div key={skill}>
                      <div className="mb-1 flex items-center justify-between">
                        <span className="text-[13px] font-medium text-slate-700 dark:text-slate-300">{skill}</span>
                        <span className="text-[11px] text-slate-400 dark:text-slate-500">
                          {count} {count === 1 ? 'vacante' : 'vacantes'}
                        </span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-purple-100 dark:bg-purple-900/30">
                        <div
                          className="h-full rounded-full bg-purple-500 dark:bg-purple-400 transition-all duration-500"
                          style={{ width: `${Math.max(8, (count / maxSkillCount) * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  <p className="mt-4 rounded-xl border border-purple-100 bg-white/60 px-3 py-2 text-[11px] leading-relaxed text-slate-500 dark:border-purple-800/20 dark:bg-slate-900/60 dark:text-slate-400">
                    La IA priorizará estas habilidades al generar tu próximo CV para maximizar la tasa de conversión.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
