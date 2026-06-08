'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { AlertCircle, ChevronRight, Lock, Mail, Loader2, Zap } from 'lucide-react'

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
              <h2 className="text-[20px] font-bold tracking-tight text-slate-900 dark:text-slate-50">Registro de Cuenta</h2>
              <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-1">Crea tu cuenta gratuita para empezar</p>
            </div>

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
                    minLength={6}
                    className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 placeholder-slate-400 dark:placeholder-slate-600 rounded-xl pl-9 pr-3 py-[10px] text-[13px] outline-none transition-all duration-150 focus:ring-2 focus:ring-rose-500/10 focus:border-rose-500/50"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-6 flex items-center justify-center gap-2 rounded-xl text-white py-[11px] text-[13px] font-bold tracking-wide transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed bg-slate-900 dark:bg-slate-50 dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-white shadow-lg shadow-slate-900/10 dark:shadow-none"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <ChevronRight size={16} />}
                {loading ? 'Creando cuenta...' : 'Registrarme'}
              </button>
            </form>

            <p className="mt-8 text-center text-[12px] text-slate-500 dark:text-slate-400">
              ¿Ya tienes cuenta?{' '}
              <Link href="/login" className="font-bold text-rose-500 dark:text-rose-400 hover:underline">
                Inicia sesión
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
