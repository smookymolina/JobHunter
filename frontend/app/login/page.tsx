'use client'

import { useState } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const router = useRouter()

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

  return (
    <div 
      className="min-h-screen w-full flex items-center justify-center bg-[#020617] m-0 p-4"
      style={{ backgroundColor: '#020617' }}
    >
      <div className="w-full max-w-[900px] bg-[#0f172a] border border-[#1e293b] rounded-2xl overflow-hidden grid grid-cols-1 md:grid-cols-2 shadow-2xl">

        {/* ── Columna Izquierda: Brand ── */}
        <div className="bg-[#020617] p-10 flex flex-col justify-between relative min-h-[500px]">
          {/* Blobs decorativos */}
          <div className="absolute top-0 right-0 w-48 h-48 rounded-full bg-[#e11d48] opacity-15 blur-2xl -translate-y-1/3 translate-x-1/3 pointer-events-none" />
          <div className="absolute bottom-20 left-0 w-40 h-40 rounded-full bg-[#fb7185] opacity-15 blur-2xl -translate-x-1/3 pointer-events-none" />
          <div className="absolute bottom-0 right-12 w-28 h-28 rounded-full bg-[#e11d48] opacity-10 blur-xl pointer-events-none" />

          {/* Logo + copy */}
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-10">
              <div className="w-9 h-9 rounded-[10px] bg-[#e11d48] flex items-center justify-center shrink-0">
                <svg viewBox="0 0 20 20" className="w-4 h-4 fill-white">
                  <path d="M10 2a8 8 0 100 16A8 8 0 0010 2zm0 2a6 6 0 110 12A6 6 0 0110 4zm-1 2v5l4 2-1 1.7L8 13V6h1z" />
                </svg>
              </div>
              <div>
                <p className="text-[15px] font-bold tracking-tight text-white leading-none">Job Hunter</p>
                <p className="text-[11px] text-slate-500 mt-0.5">CV Automation</p>
              </div>
            </div>

            <h1 className="text-[26px] font-bold text-white leading-tight tracking-tight mb-3">
              Tu CV perfecto,<br />
              generado por <span className="text-[#fb7185]">IA.</span>
            </h1>
            <p className="text-[13px] text-slate-400 leading-relaxed max-w-[240px]">
              CVs personalizados para cada vacante. Más entrevistas, menos esfuerzo.
            </p>

            <div className="grid grid-cols-2 gap-2.5 mt-8">
              {[
                { num: '8/8',   label: 'CVS ENVIADOS'    },
                { num: '3x',    label: 'MÁS ENTREVISTAS' },
                { num: 'IA',    label: 'REVISIÓN AUTO'   },
                { num: 'LaTeX', label: 'PLANTILLAS PRO'  },
              ].map(({ num, label }) => (
                <div key={label} className="rounded-xl border border-white/[0.08] bg-white/[0.05] px-3.5 py-3">
                  <p className="text-[20px] font-bold text-[#fb7185] leading-none">{num}</p>
                  <p className="text-[10px] text-slate-500 mt-1 tracking-widest uppercase">{label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Testimonio */}
          <div className="relative z-10 mt-8">
            <div className="rounded-xl border border-white/[0.07] bg-white/[0.04] p-4">
              <p className="text-[11px] italic leading-relaxed text-slate-400">
                &ldquo;Conseguí 3 entrevistas en una semana. El CV se adapta solo a cada oferta.&rdquo;
              </p>
              <div className="flex items-center gap-2 mt-2.5">
                <div className="w-6 h-6 rounded-full bg-[#e11d48]/20 flex items-center justify-center text-[9px] font-bold text-[#fb7185] shrink-0">
                  JM
                </div>
                <p className="text-[10px] font-medium text-slate-500">Jair M. · Ingeniero de Software</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Columna Derecha: Formulario ── */}
        <div className="bg-[#0f172a] flex flex-col justify-center p-8 md:p-12">
          <div className="mb-8">
            <h2 className="text-[20px] font-bold tracking-tight text-[#f1f5f9]">Bienvenido de vuelta</h2>
            <p className="text-[12px] text-slate-400 mt-1">Inicia sesión para continuar con tu búsqueda</p>
          </div>

          {error && (
            <div className="mb-5 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Email */}
            <div>
              <label className="block text-[11px] font-semibold tracking-widest text-slate-400 uppercase mb-1.5">
                Correo electrónico
              </label>
              <div className="relative">
                <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 stroke-slate-500 fill-none" strokeWidth="1.8" viewBox="0 0 24 24">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="tu@email.com"
                  required
                  className="w-full bg-[#1e293b] border border-[#334155] text-white placeholder-slate-600 rounded-xl pl-10 pr-4 py-3 text-[13px] outline-none transition focus:border-[#fb7185]/50 focus:ring-2 focus:ring-[#fb7185]/10"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-[11px] font-semibold tracking-widest text-slate-400 uppercase mb-1.5">
                Contraseña
              </label>
              <div className="relative">
                <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 stroke-slate-500 fill-none" strokeWidth="1.8" viewBox="0 0 24 24">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-[#1e293b] border border-[#334155] text-white placeholder-slate-600 rounded-xl pl-10 pr-4 py-3 text-[13px] outline-none transition focus:border-[#fb7185]/50 focus:ring-2 focus:ring-[#fb7185]/10"
                />
              </div>
            </div>

            {/* Forgot password */}
            <div className="flex justify-end -mt-1">
              <a href="#" className="text-[11px] text-slate-500 hover:text-[#fb7185] transition-colors">
                ¿Olvidaste tu contraseña?
              </a>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="mt-2 w-full flex items-center justify-center gap-2 rounded-xl bg-[#f1f5f9] hover:bg-white text-[#0f172a] py-3 text-[13px] font-bold tracking-wide transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
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

          {/* Divider */}
          <div className="flex items-center gap-3 mt-5">
            <div className="flex-1 border-t border-[#1e293b]" />
            <span className="text-[11px] text-slate-600">o continúa con</span>
            <div className="flex-1 border-t border-[#1e293b]" />
          </div>

          {/* Google button */}
          <button
            type="button"
            onClick={() => signIn('google')}
            className="mt-3 w-full flex items-center justify-center gap-2.5 rounded-xl border border-[#334155] bg-transparent py-2.5 text-[13px] font-medium text-slate-300 transition-all hover:bg-white/[0.05] hover:border-[#475569] active:scale-[0.98]"
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continuar con Google
          </button>

          {/* Footer */}
          <p className="mt-6 text-center text-[11px] text-slate-600">
            ¿No tienes cuenta?{' '}
            <a href="#" className="text-[#fb7185] hover:text-rose-400 font-medium transition-colors">
              Regístrate gratis
            </a>
          </p>
        </div>

      </div>
    </div>
  )
}
