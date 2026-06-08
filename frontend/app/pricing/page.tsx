'use client'

import { Check, Zap, Package, Star, Sparkles, FileText, Briefcase } from 'lucide-react'

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: '$0',
    currency: '',
    period: 'gratis',
    description: 'Para explorar la plataforma',
    icon: Zap,
    iconBg: 'bg-slate-800 border-slate-700',
    iconColor: 'text-slate-400',
    highlight: false,
    badge: null,
    buttonLabel: 'Plan Actual',
    buttonClass: 'cursor-not-allowed border border-slate-700 bg-slate-800/50 text-slate-500',
    buttonDisabled: true,
    onBuy: null,
    features: [
      { label: '5 vacantes activas',         icon: Briefcase },
      { label: '3 generaciones de CV LaTeX',  icon: FileText },
      { label: 'Tablero Kanban',              icon: null },
      { label: 'Revisión básica IA',          icon: null },
    ],
  },
  {
    id: 'standard',
    name: 'Standard',
    price: '$200',
    currency: 'MXN',
    period: 'pago único',
    description: 'Una búsqueda enfocada y seria',
    icon: Package,
    iconBg: 'bg-blue-500/10 border-blue-500/30',
    iconColor: 'text-blue-400',
    highlight: false,
    badge: null,
    buttonLabel: 'Comprar Standard',
    buttonClass: 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/20 hover:scale-[1.02] active:scale-[0.98]',
    buttonDisabled: false,
    onBuy: () => alert('La pasarela de pago estará disponible muy pronto. ¡Gracias por tu interés!'),
    features: [
      { label: '20 vacantes activas',         icon: Briefcase },
      { label: '12 generaciones de CV LaTeX', icon: FileText },
      { label: 'Búsqueda autónoma (scraping)', icon: null },
      { label: 'Motor de compatibilidad IA',  icon: null },
      { label: 'Plantillas LaTeX personalizadas', icon: null },
    ],
  },
  {
    id: 'premium',
    name: 'Premium',
    price: '$500',
    currency: 'MXN',
    period: 'pago único',
    description: 'El arsenal completo del candidato',
    icon: Star,
    iconBg: 'bg-emerald-500/10 border-emerald-500/30',
    iconColor: 'text-emerald-400',
    highlight: true,
    badge: 'Mejor Valor',
    buttonLabel: 'Comprar Premium',
    buttonClass: 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-white shadow-lg shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98]',
    buttonDisabled: false,
    onBuy: () => alert('La pasarela de pago estará disponible muy pronto. ¡Gracias por tu interés!'),
    features: [
      { label: '50 vacantes activas',          icon: Briefcase },
      { label: '35 generaciones de CV LaTeX',  icon: FileText },
      { label: 'Búsqueda autónoma (scraping)', icon: null },
      { label: 'Motor de compatibilidad IA',   icon: null },
      { label: 'Plantillas LaTeX personalizadas', icon: null },
      { label: 'Inspector de CV automático',   icon: null },
      { label: 'Soporte prioritario',          icon: null },
    ],
  },
] as const

export default function PricingPage() {
  return (
    <div className="flex h-full flex-col overflow-auto bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-50">
      {/* Header */}
      <div className="mx-auto w-full max-w-4xl px-6 pb-8 pt-14 text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-1.5 text-[12px] font-medium text-emerald-600 dark:text-emerald-400">
          <Sparkles size={12} />
          Pago único — sin suscripciones, sin trampas.
        </div>
        <h1 className="text-[34px] font-bold leading-tight tracking-tight text-slate-900 dark:text-slate-100 md:text-[40px]">
          Invierte en tu carrera.
          <br />
          <span className="bg-gradient-to-r from-emerald-600 to-cyan-600 dark:from-emerald-400 dark:to-cyan-400 bg-clip-text text-transparent">
            Consigue más entrevistas.
          </span>
        </h1>
        <p className="mx-auto mt-4 max-w-lg text-[14px] leading-relaxed text-slate-600 dark:text-slate-400">
          No queremos cobrarte todos los meses — queremos que consigas trabajo este mes. Elige tu paquete, úsalo a tu ritmo.
        </p>
      </div>

      {/* Plans grid */}
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-6 pb-20 md:flex-row md:items-start">
        {PLANS.map(plan => {
          const PlanIcon = plan.icon
          return (
            <div
              key={plan.id}
              className={`relative flex flex-1 flex-col rounded-2xl p-6 transition-all border ${
                plan.highlight
                  ? 'border-emerald-500/40 bg-slate-50 dark:bg-slate-900 shadow-xl shadow-emerald-500/5'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950'
              }`}
            >
              {plan.badge && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
                  <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-50 dark:bg-emerald-950 px-3 py-1 text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 shadow-sm">
                    <Star size={9} fill="currentColor" />
                    {plan.badge}
                  </span>
                </div>
              )}

              {/* Plan header */}
              <div className="mb-5">
                <div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-xl border ${plan.iconBg}`}>
                  <PlanIcon size={16} className={plan.iconColor} />
                </div>
                <h2 className="text-[17px] font-semibold text-slate-900 dark:text-slate-100">{plan.name}</h2>
                <p className="mt-0.5 text-[12px] text-slate-500 dark:text-slate-400">{plan.description}</p>
                <div className="mt-3 flex items-end gap-1.5">
                  <span className="text-[38px] font-bold leading-none text-slate-900 dark:text-slate-100">{plan.price}</span>
                  {plan.currency && (
                    <span className="mb-1.5 text-[13px] font-medium text-slate-500 dark:text-slate-400">{plan.currency}</span>
                  )}
                </div>
                <p className="mt-0.5 text-[11px] text-slate-400 dark:text-slate-500">{plan.period}</p>
              </div>

              {/* Features */}
              <ul className="mb-6 flex-1 space-y-2.5">
                {plan.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-[13px] text-slate-600 dark:text-slate-300">
                    <Check
                      size={13}
                      className={`mt-0.5 shrink-0 ${plan.highlight ? 'text-emerald-500' : 'text-slate-400 dark:text-slate-500'}`}
                    />
                    {f.label}
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <button
                disabled={plan.buttonDisabled}
                onClick={plan.onBuy ?? undefined}
                className={`w-full rounded-xl py-2.5 text-[13px] font-semibold transition-all ${plan.buttonClass}`}
              >
                {plan.buttonLabel}
              </button>
            </div>
          )
        })}
      </div>

      {/* Comparison note */}
      <div className="pb-10 text-center">
        <p className="text-[12px] text-slate-500 dark:text-slate-400">
          ¿Dudas? Compara el costo unitario: Standard = $16.6 MXN/CV · Premium = $14.3 MXN/CV
        </p>
      </div>
    </div>
  )
}
