'use client'

import { Suspense, useState } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { AlertCircle, ChevronRight, Lock, Mail, Loader2, Zap } from 'lucide-react'

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

  return (
    <div className="min-h-screen w-full bg-slate-50 dark:bg-slate-950 p-0 md:p-4 lg:p-8 transition-colors duration-300">
      <div className="w-full min-h-screen md:min-h-[calc(100vh-4rem)] grid grid-cols-1 md:grid-cols-2 md:rounded-2xl overflow-hidden border-y md:border border-slate-200 dark:border-slate-800 shadow-sm transition-colors duration-300">

        {/* ── Columna Izquierda (Brand/Hero) ── */}
        <div className="bg-slate-900 dark:bg-slate-900 px-9 py-10 flex flex-col justify-between relative overflow-hidden transition-colors duration-300">
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            <div className="absolute rounded-full bg-rose-500 w-48 h-48 -top-10 -right-10 opacity-20 blur-3xl animate-pulse" />
            <div className="absolute rounded-full bg-rose-400 w-40 h-40 bottom-10 -left-10 opacity-15 blur-3xl" />
          </div>

          <div className="relative z-10">
            <div className="flex items-center gap-2.5 mb-10">
              <div className="w-9 h-9 rounded-xl bg-rose-500 flex items-center justify-center shrink-0 shadow-lg shadow-rose-500/20">
                <Zap size={18} className="text-white" />
              </div>
              <div>
                <p className="text-[16px] font-bold tracking-tight text-white leading-none">Job Hunter</p>
                <p className="text-[11px] text-slate-400 mt-0.5">CV Automation</p>
              </div>
            </div>

            <h1 className="text-[26px] font-extrabold text-white leading-[1.3] tracking-tight mb-3">
              Tu CV perfecto,<br />
              generado por <span className="text-rose-400">IA.</span>
            </h1>
            <p className="text-[13px] text-slate-400 leading-[1.7] max-w-[240px]">
              Automatiza la creación de CVs personalizados para cada vacante. Más entrevistas, menos esfuerzo.
            </p>

            <div className="grid grid-cols-2 gap-3 mt-8">
              {[
                { num: '8/8',   label: 'CVS ENVIADOS'    },
                { num: '3x',    label: 'MÁS ENTREVISTAS' },
              ].map(({ num, label }) => (
                <div key={label} className="rounded-xl px-4 py-3 bg-white/5 border border-white/10 backdrop-blur-sm">
                  <p className="text-[20px] font-bold text-rose-400 leading-none">{num}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5 tracking-wider uppercase font-semibold">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="relative z-10">
            <div className="rounded-xl px-4 py-3.5 bg-white/5 border border-white/10 backdrop-blur-sm">
              <p className="text-[11px] italic leading-[1.6] text-slate-300">
                &ldquo;Conseguí 3 entrevistas en una semana usando Job Hunter. El CV se adapta solo a cada oferta.&rdquo;
              </p>
              <div className="flex items-center gap-2 mt-2.5">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-rose-400 shrink-0 bg-rose-500/20 border border-rose-500/30">
                  JM
                </div>
                <p className="text-[10px] font-medium text-slate-400">Jair M. · Ingeniero de Software</p>
              </div>
            </div>
          </div>
        </div>

        {/* ── Columna Derecha (Formulario) ── */}
        <div className="bg-white dark:bg-slate-950 flex flex-col justify-center px-9 py-10 transition-colors duration-300">
          <div className="max-w-[320px] w-full mx-auto">
            <div className="mb-7">
              <h2 className="text-[20px] font-bold tracking-tight text-slate-900 dark:text-slate-50">Bienvenido de vuelta</h2>
              <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-1">Inicia sesión para continuar con tu búsqueda</p>
            </div>

            {registered && (
              <div className="mb-4 rounded-xl border border-emerald-100 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-900/50 px-4 py-3 text-[12px] text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
                <ChevronRight size={14} className="text-emerald-500" />
                Cuenta creada correctamente.
              </div>
            )}

            {error && (
              <div className="mb-4 rounded-xl border border-rose-100 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900/50 px-4 py-3 text-[12px] text-rose-600 dark:text-rose-400 flex items-center gap-2">
                <AlertCircle size={14} />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1.5 tracking-wide">
                  Correo electrónico
                </label>
                <div className="relative group">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 group-focus-within:text-rose-500 transition-colors">
                    <Mail size={15} />
                  </div>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="tu@email.com"
                    required
                    className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 placeholder-slate-400 dark:placeholder-slate-600 rounded-xl pl-9 pr-3 py-[10px] text-[13px] outline-none transition-all duration-150 focus:ring-2 focus:ring-rose-500/10 focus:border-rose-500/50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1.5 tracking-wide">
                  Contraseña
                </label>
                <div className="relative group">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 group-focus-within:text-rose-500 transition-colors">
                    <Lock size={15} />
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 placeholder-slate-400 dark:placeholder-slate-600 rounded-xl pl-9 pr-3 py-[10px] text-[13px] outline-none transition-all duration-150 focus:ring-2 focus:ring-rose-500/10 focus:border-rose-500/50"
                  />
                </div>
              </div>

              <a href="#" className="block text-right text-[11px] mt-1 text-rose-500 dark:text-rose-400 hover:underline">
                ¿Olvidaste tu contraseña?
              </a>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-4 flex items-center justify-center gap-2 rounded-xl text-white py-[11px] text-[13px] font-bold tracking-wide transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed bg-slate-900 dark:bg-slate-50 dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-white shadow-lg shadow-slate-900/10 dark:shadow-none"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <ChevronRight size={16} />}
                {loading ? 'Entrando...' : 'Ingresar al sistema'}
              </button>
            </form>

            <div className="flex items-center gap-3 my-6">
              <div className="flex-1 h-px bg-slate-100 dark:bg-slate-800" />
              <span className="text-[10px] text-slate-400 font-medium uppercase tracking-widest">o continúa con</span>
              <div className="flex-1 h-px bg-slate-100 dark:bg-slate-800" />
            </div>

            <button
              type="button"
              onClick={() => signIn('google')}
              className="w-full flex items-center justify-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 py-2.5 text-[12px] font-semibold transition-all hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              <svg viewBox="0 0 24 24" className="w-3.5 h-3.5">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
              </svg>
              Continuar con Google
            </button>

            <p className="mt-8 text-center text-[12px] text-slate-500 dark:text-slate-400">
              ¿No tienes cuenta?{' '}
              <Link href="/register" className="font-bold text-rose-500 dark:text-rose-400 hover:underline">
                Regístrate gratis
              </Link>
            </p>
          </div>
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
