'use client'

import { Suspense, useState } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'

function LoginPageContent() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const router       = useRouter()
  const searchParams = useSearchParams()
  const registered   = searchParams.get('registered') === 'true'

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    const result = await signIn('credentials', { email, password, redirect: false })
    setLoading(false)
    if (result?.error) {
      setError('Credenciales inválidas. Intenta de nuevo.')
    } else {
      router.push('/dashboard')
    }
  }

  const INPUT = [
    'w-full bg-white border border-[#e2e8f0]',
    'text-[#0f172a] placeholder-slate-300 rounded-[10px]',
    'pl-9 pr-3 py-[10px] text-[13px] outline-none transition-[border-color,box-shadow] duration-150',
  ].join(' ')

  return (
    <div className="min-h-screen w-full bg-[#f8fafc] dark:bg-[#020617] p-0 md:p-4 lg:p-8 transition-colors duration-300"
         style={{ fontFamily: "'DM Sans', system-ui, sans-serif" }}>

      <div className="w-full min-h-screen md:min-h-[calc(100vh-4rem)] grid grid-cols-1 md:grid-cols-2 md:rounded-2xl overflow-hidden border-y md:border border-[#e2e8f0] dark:border-[#1e293b] shadow-sm transition-colors duration-300">

        {/* ── Columna Izquierda (dark) ── */}
        <div className="bg-[#0f172a] dark:bg-[#020617] px-9 py-10 flex flex-col justify-between relative overflow-hidden transition-colors duration-300">

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
        <div className="bg-white dark:bg-[#0f172a] flex flex-col justify-center px-9 py-10 transition-colors duration-300">

          <div className="mb-7">
            <h2 className="text-[20px] font-bold tracking-tight text-[#0f172a] dark:text-[#f1f5f9]">Bienvenido de vuelta</h2>
            <p className="text-[12px] text-[#94a3b8] mt-1">Inicia sesión para continuar con tu búsqueda</p>
          </div>

          {registered && (
            <div className="mb-4 rounded-[10px] border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-800/50 px-4 py-3 text-[12px] text-emerald-700 dark:text-emerald-400">
              Cuenta creada correctamente. Inicia sesión para continuar.
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-[10px] border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-800/50 px-4 py-3 text-[12px] text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>

            <div className="mb-3.5">
              <label className="block text-[11px] font-medium text-[#64748b] dark:text-[#94a3b8] mb-1.5 tracking-[.02em]">
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
                  className="w-full bg-white dark:bg-[#1e293b] border border-[#e2e8f0] dark:border-[#334155] text-[#0f172a] dark:text-[#f1f5f9] placeholder-slate-300 dark:placeholder-slate-500 rounded-[10px] pl-9 pr-3 py-[10px] text-[13px] outline-none transition-all duration-150"
                  onFocus={e => { e.target.style.borderColor = 'rgba(225,29,72,.5)'; e.target.style.boxShadow = '0 0 0 3px rgba(225,29,72,.08)' }}
                  onBlur={e => { e.target.style.borderColor = ''; e.target.style.boxShadow = '' }}
                />
              </div>
            </div>

            <div className="mb-1">
              <label className="block text-[11px] font-medium text-[#64748b] dark:text-[#94a3b8] mb-1.5 tracking-[.02em]">
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
                  className="w-full bg-white dark:bg-[#1e293b] border border-[#e2e8f0] dark:border-[#334155] text-[#0f172a] dark:text-[#f1f5f9] placeholder-slate-300 dark:placeholder-slate-500 rounded-[10px] pl-9 pr-3 py-[10px] text-[13px] outline-none transition-all duration-150"
                  onFocus={e => { e.target.style.borderColor = 'rgba(225,29,72,.5)'; e.target.style.boxShadow = '0 0 0 3px rgba(225,29,72,.08)' }}
                  onBlur={e => { e.target.style.borderColor = ''; e.target.style.boxShadow = '' }}
                />
              </div>
            </div>

            <a href="#"
               className="block text-right text-[11px] mt-1.5 mb-4 cursor-pointer text-[#e11d48] dark:text-[#fb7185] no-underline">
              ¿Olvidaste tu contraseña?
            </a>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-[10px] text-white dark:text-[#0f172a] py-[11px] text-[13px] font-semibold tracking-[.01em] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed bg-[#0f172a] dark:bg-[#f1f5f9] hover:bg-[#1e293b] dark:hover:bg-white"
              onMouseOver={e => { e.currentTarget.style.transform = 'scale(1.015)' }}
              onMouseOut={e => { e.currentTarget.style.transform = '' }}
            >
              {loading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Entrando...
                </>
              ) : 'Iniciar sesión'}
            </button>
          </form>

          <div className="flex items-center gap-2.5 my-4">
            <div className="flex-1 h-px bg-[#f1f5f9] dark:bg-[#1e293b]" />
            <span className="text-[10px] text-[#cbd5e1]">o continúa con</span>
            <div className="flex-1 h-px bg-[#f1f5f9] dark:bg-[#1e293b]" />
          </div>

          <button
            type="button"
            onClick={() => signIn('google')}
            className="w-full flex items-center justify-center gap-2 rounded-[10px] border border-[#e2e8f0] dark:border-[#334155] bg-white dark:bg-[#1e293b] text-[#374151] dark:text-[#f1f5f9] py-2.5 text-[12px] font-medium transition-all hover:bg-[#f8fafc] dark:hover:bg-[#334155] hover:border-[#d1d5db]"
          >
            <svg viewBox="0 0 24 24" className="w-3.5 h-3.5">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continuar con Google
          </button>

          <p className="mt-5 text-center text-[11px] text-[#94a3b8]">
            ¿No tienes cuenta?{' '}
            <Link href="/register" className="font-medium text-[#e11d48] dark:text-[#fb7185] no-underline">
              Regístrate gratis
            </Link>
          </p>
        </div>

      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageContent />
    </Suspense>
  )
}
