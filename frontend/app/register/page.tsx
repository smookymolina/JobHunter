'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

export default function RegisterPage() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const router = useRouter()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (res.status === 201) {
        router.push('/login?registered=true')
        return
      }
      const data = await res.json() as { detail?: string }
      setError(data.detail ?? 'Error al crear la cuenta.')
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setLoading(false)
    }
  }

  const INPUT = [
    'w-full bg-white border border-[#e2e8f0]',
    'text-[#0f172a] placeholder-slate-300 rounded-[10px]',
    'pl-9 pr-3 py-[10px] text-[13px] outline-none transition-[border-color,box-shadow] duration-150',
  ].join(' ')

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#f8fafc] py-4 px-4"
         style={{ fontFamily: "'DM Sans', system-ui, sans-serif" }}>

      <div className="w-full max-w-[900px] min-h-[560px] grid grid-cols-1 md:grid-cols-2 rounded-2xl overflow-hidden border border-[#e2e8f0]">

        {/* ── Columna Izquierda (dark) ── */}
        <div className="bg-[#0f172a] px-9 py-10 flex flex-col justify-between relative overflow-hidden">

          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute rounded-full bg-[#e11d48]"
                 style={{ width: 200, height: 200, top: -40, right: -40, opacity: .15 }} />
            <div className="absolute rounded-full bg-[#fb7185]"
                 style={{ width: 150, height: 150, bottom: 60, left: -30, opacity: .15 }} />
            <div className="absolute rounded-full bg-[#e11d48]"
                 style={{ width: 100, height: 100, bottom: -20, right: 60, opacity: .08 }} />
          </div>

          <div className="relative z-10">
            <div className="flex items-center gap-2.5 mb-10">
              <div className="w-9 h-9 rounded-[10px] bg-[#e11d48] flex items-center justify-center shrink-0">
                <svg viewBox="0 0 20 20" className="w-[18px] h-[18px] fill-white">
                  <path d="M10 2a8 8 0 100 16A8 8 0 0010 2zm0 2a6 6 0 110 12A6 6 0 0110 4zm-1 2v5l4 2-1 1.7L8 13V6h1z" />
                </svg>
              </div>
              <div>
                <p className="text-[16px] font-bold tracking-tight text-[#f1f5f9] leading-none">Job Hunter</p>
                <p className="text-[11px] text-[#64748b] mt-0.5">CV Automation</p>
              </div>
            </div>

            <h1 className="text-[26px] font-extrabold text-[#f1f5f9] leading-[1.3] tracking-tight mb-3">
              Tu CV perfecto,<br />
              generado por <span className="text-[#fb7185]">IA.</span>
            </h1>
            <p className="text-[13px] text-[#64748b] leading-[1.7] max-w-[240px]">
              Automatiza la creación de CVs personalizados para cada vacante. Más entrevistas, menos esfuerzo.
            </p>

            <div className="grid grid-cols-2 gap-2.5 mt-8">
              {[
                { num: '8/8',   label: 'CVS ENVIADOS'    },
                { num: '3x',    label: 'MÁS ENTREVISTAS' },
                { num: 'IA',    label: 'REVISIÓN AUTO'   },
                { num: 'LaTeX', label: 'PLANTILLAS PRO'  },
              ].map(({ num, label }) => (
                <div key={label}
                     className="rounded-[10px] px-3.5 py-3"
                     style={{ background: 'rgba(255,255,255,.05)', border: '1px solid rgba(255,255,255,.08)' }}>
                  <p className="text-[20px] font-bold text-[#fb7185] leading-none">{num}</p>
                  <p className="text-[10px] text-[#475569] mt-0.5 tracking-[.04em] uppercase">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative z-10">
            <div className="rounded-xl px-4 py-3.5"
                 style={{ background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.07)' }}>
              <p className="text-[11px] italic leading-[1.6] text-[#94a3b8]">
                &ldquo;Conseguí 3 entrevistas en una semana usando Job Hunter. El CV se adapta solo a cada oferta.&rdquo;
              </p>
              <div className="flex items-center gap-2 mt-2.5">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-[#fb7185] shrink-0"
                     style={{ background: 'rgba(225,29,72,.2)' }}>
                  JM
                </div>
                <p className="text-[10px] font-medium text-[#475569]">Jair M. · Ingeniero de Software</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Columna Derecha (light) ── */}
        <div className="bg-white flex flex-col justify-center px-9 py-10">

          <div className="mb-7">
            <h2 className="text-[20px] font-bold tracking-tight text-[#0f172a]">Registro de Cuenta</h2>
            <p className="text-[12px] text-[#94a3b8] mt-1">Crea tu cuenta gratuita para empezar</p>
          </div>

          {error && (
            <div className="mb-4 rounded-[10px] border border-red-200 bg-red-50 px-4 py-3 text-[12px] text-red-600">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>

            <div className="mb-3.5">
              <label className="block text-[11px] font-medium text-[#64748b] mb-1.5 tracking-[.02em]">
                Correo electrónico
              </label>
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                     style={{ width: 15, height: 15, stroke: '#cbd5e1', fill: 'none', strokeWidth: 1.8 }}
                     viewBox="0 0 24 24">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="tu@email.com"
                  required
                  className={INPUT}
                  onFocus={e => { e.target.style.borderColor = 'rgba(225,29,72,.5)'; e.target.style.boxShadow = '0 0 0 3px rgba(225,29,72,.08)' }}
                  onBlur={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.boxShadow = '' }}
                />
              </div>
            </div>

            <div className="mb-6">
              <label className="block text-[11px] font-medium text-[#64748b] mb-1.5 tracking-[.02em]">
                Contraseña
              </label>
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                     style={{ width: 15, height: 15, stroke: '#cbd5e1', fill: 'none', strokeWidth: 1.8 }}
                     viewBox="0 0 24 24">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                  className={INPUT}
                  onFocus={e => { e.target.style.borderColor = 'rgba(225,29,72,.5)'; e.target.style.boxShadow = '0 0 0 3px rgba(225,29,72,.08)' }}
                  onBlur={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.boxShadow = '' }}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-[10px] text-white py-[11px] text-[13px] font-semibold tracking-[.01em] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: '#0f172a' }}
              onMouseOver={e => { if (!loading) { e.currentTarget.style.background = '#1e293b'; e.currentTarget.style.transform = 'scale(1.015)' } }}
              onMouseOut={e => { e.currentTarget.style.background = '#0f172a'; e.currentTarget.style.transform = '' }}
            >
              {loading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Creando cuenta...
                </>
              ) : 'Crear cuenta'}
            </button>
          </form>

          <p className="mt-6 text-center text-[11px] text-[#94a3b8]">
            ¿Ya tienes cuenta?{' '}
            <Link href="/login" className="font-medium" style={{ color: '#e11d48', textDecoration: 'none' }}>
              Inicia sesión
            </Link>
          </p>
        </div>

      </div>
    </div>
  )
}
