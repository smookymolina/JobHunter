'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import { signIn } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  AlertCircle, ChevronRight, Lock, Mail, Loader2, Zap,
  ShieldCheck, RotateCcw, CheckCircle2,
} from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

type Stage = 'login' | 'verifying'

const INPUT =
  'w-full rounded-xl border border-white/15 bg-white/8 py-[10px] text-[13px] text-white ' +
  'placeholder-white/30 outline-none transition focus:border-rose-500/60 focus:bg-white/12 ' +
  'focus:ring-2 focus:ring-rose-500/20'

function BrandPanel() {
  return (
    <div className="flex flex-col justify-between bg-rose-500/[0.06] px-9 py-10">
      <div>
        <div className="mb-10 flex items-center gap-2.5">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-rose-500 shadow-lg shadow-rose-500/30">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <p className="text-[16px] font-bold leading-none tracking-tight text-white">Job Hunter</p>
            <p className="mt-0.5 text-[11px] text-white/40">CV Automation</p>
          </div>
        </div>

        <h1 className="mb-3 text-[26px] font-extrabold leading-[1.3] tracking-tight text-white">
          Tu CV perfecto,<br />
          generado por <span className="text-rose-400">IA.</span>
        </h1>
        <p className="text-[13px] leading-[1.7] text-white/40 max-w-[240px]">
          Automatiza la creación de CVs personalizados para cada vacante. Más entrevistas, menos esfuerzo.
        </p>

        <div className="mt-8 grid grid-cols-2 gap-3">
          {[{ num: '8/8', label: 'CVS ENVIADOS' }, { num: '3x', label: 'MÁS ENTREVISTAS' }].map(({ num, label }) => (
            <div key={label} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
              <p className="text-[20px] font-bold leading-none text-rose-400">{num}</p>
              <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-white/30">{label}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3.5 backdrop-blur-sm">
        <p className="text-[11px] italic leading-[1.6] text-white/60">
          &ldquo;Conseguí 3 entrevistas en una semana usando Job Hunter. El CV se adapta solo a cada oferta.&rdquo;
        </p>
        <div className="mt-2.5 flex items-center gap-2">
          <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-rose-500/30 bg-rose-500/20 text-[9px] font-bold text-rose-400">
            JM
          </div>
          <p className="text-[10px] font-medium text-white/40">Jair M. · Ingeniero de Software</p>
        </div>
      </div>
    </div>
  )
}

function LoginPageContent() {
  const [stage,      setStage]     = useState<Stage>('login')
  const [email,      setEmail]     = useState('')
  const [password,   setPassword]  = useState('')
  const [otp,        setOtp]       = useState(['', '', '', '', '', ''])
  const [loading,    setLoading]   = useState(false)
  const [resending,  setResending] = useState(false)
  const [resent,     setResent]    = useState(false)
  const [countdown,  setCountdown] = useState(0)
  const [error,      setError]     = useState('')
  const inputRefs    = useRef<(HTMLInputElement | null)[]>([])
  const router       = useRouter()
  const searchParams = useSearchParams()
  const registered   = searchParams.get('registered') === 'true'

  useEffect(() => {
    if (stage === 'verifying') setTimeout(() => inputRefs.current[0]?.focus(), 80)
  }, [stage])

  useEffect(() => {
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    const result = await signIn('credentials', { email, password, redirect: false })
    setLoading(false)
    if (result?.error) {
      // Auth.js solo expone el `code` del CredentialsSignin al cliente; ahí viaja
      // el mensaje real del backend (ver CustomAuthError en auth.ts).
      const msg = result.code && result.code !== 'credentials'
        ? result.code
        : 'Credenciales incorrectas'
      if (
        msg === 'Cuenta pendiente de verificación de correo.' ||
        msg.toLowerCase().includes('verifica') ||
        msg.toLowerCase().includes('pendiente')
      ) {
        setStage('verifying')
        setCountdown(60)
        return
      }
      setError(msg)
    } else {
      router.push('/dashboard')
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    const code = otp.join('')
    if (code.length < 6) { setError('Ingresa el código completo de 6 dígitos.'); return }
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      })
      const data = await res.json() as { ok?: boolean; detail?: string }
      if (res.ok && data.ok) {
        const result = await signIn('credentials', { email, password, redirect: false })
        router.push(result?.error ? '/login?registered=true' : '/dashboard')
        return
      }
      setError(data.detail ?? 'Código incorrecto. Intenta de nuevo.')
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    if (countdown > 0) return
    setError('')
    setResending(true)
    setResent(false)
    try {
      await fetch(`${API}/auth/resend-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      setResent(true)
      setOtp(['', '', '', '', '', ''])
      setCountdown(60)
      setTimeout(() => inputRefs.current[0]?.focus(), 80)
    } catch {
      setError('No se pudo reenviar el código.')
    } finally {
      setResending(false)
    }
  }

  function handleOtpInput(i: number, val: string) {
    const digit = val.replace(/\D/g, '').slice(-1)
    const next = [...otp]; next[i] = digit; setOtp(next)
    if (digit && i < 5) inputRefs.current[i + 1]?.focus()
  }

  function handleOtpKeyDown(i: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !otp[i] && i > 0) inputRefs.current[i - 1]?.focus()
  }

  function handleOtpPaste(e: React.ClipboardEvent) {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!text) return
    e.preventDefault()
    const next = [...otp]
    text.split('').forEach((d, idx) => { next[idx] = d })
    setOtp(next)
    setTimeout(() => inputRefs.current[Math.min(text.length, 5)]?.focus(), 0)
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-slate-950">
      {/* ── Blobs animados (fondo global) ── */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -right-32 -top-32 h-[32rem] w-[32rem] animate-pulse rounded-full bg-rose-600/20 blur-3xl" />
        <div
          className="absolute -left-24 top-1/2 h-80 w-80 animate-pulse rounded-full bg-violet-600/15 blur-3xl"
          style={{ animationDelay: '1.5s' }}
        />
        <div
          className="absolute bottom-0 right-1/3 h-64 w-64 animate-pulse rounded-full bg-indigo-600/10 blur-3xl"
          style={{ animationDelay: '3s' }}
        />
      </div>

      {/* ── Card central ── */}
      <div className="relative z-10 flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-3xl overflow-hidden rounded-3xl border border-white/10 shadow-2xl shadow-black/60 backdrop-blur-md">
          <div className="grid grid-cols-1 md:grid-cols-2">
            <BrandPanel />

            {/* ── Columna derecha (formulario) ── */}
            <div className="flex flex-col justify-center border-t border-white/10 bg-white/[0.04] px-9 py-10 backdrop-blur-md md:border-l md:border-t-0">
              <div className="mx-auto w-full max-w-[320px]">

                {stage === 'login' ? (
                  <>
                    <div className="mb-7">
                      <h2 className="text-[20px] font-bold tracking-tight text-white">Bienvenido de vuelta</h2>
                      <p className="mt-1 text-[12px] text-white/40">Inicia sesión para continuar con tu búsqueda</p>
                    </div>

                    {registered && (
                      <div className="mb-4 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-[12px] text-emerald-300">
                        <CheckCircle2 size={14} /> Cuenta creada. Verifica tu correo antes de ingresar.
                      </div>
                    )}

                    {error && (
                      <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-300">
                        <AlertCircle size={14} /> {error}
                      </div>
                    )}

                    <form onSubmit={handleLogin} className="space-y-4">
                      <div>
                        <label className="mb-1.5 block text-[10px] font-medium uppercase tracking-widest text-white/50">
                          Correo electrónico
                        </label>
                        <div className="relative group">
                          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 transition group-focus-within:text-rose-400">
                            <Mail size={15} />
                          </div>
                          <input
                            type="email"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            placeholder="tu@email.com"
                            required
                            className={`${INPUT} pl-9`}
                          />
                        </div>
                      </div>

                      <div>
                        <label className="mb-1.5 block text-[10px] font-medium uppercase tracking-widest text-white/50">
                          Contraseña
                        </label>
                        <div className="relative group">
                          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30 transition group-focus-within:text-rose-400">
                            <Lock size={15} />
                          </div>
                          <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            placeholder="••••••••"
                            required
                            className={`${INPUT} pl-9`}
                          />
                        </div>
                      </div>

                      <a href="#" className="block text-right text-[11px] text-rose-400 transition hover:text-rose-300 hover:underline mt-1">
                        ¿Olvidaste tu contraseña?
                      </a>

                      <button
                        type="submit"
                        disabled={loading}
                        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-rose-600 py-[11px] text-[13px] font-bold tracking-wide text-white shadow-lg shadow-rose-600/25 transition hover:bg-rose-500 disabled:opacity-50"
                      >
                        {loading ? <Loader2 size={16} className="animate-spin" /> : <ChevronRight size={16} />}
                        {loading ? 'Entrando...' : 'Ingresar al sistema'}
                      </button>
                    </form>

                    <div className="my-6 flex items-center gap-3">
                      <div className="h-px flex-1 bg-white/10" />
                      <span className="text-[10px] font-medium uppercase tracking-widest text-white/25">o continúa con</span>
                      <div className="h-px flex-1 bg-white/10" />
                    </div>

                    <button
                      type="button"
                      onClick={() => signIn('google')}
                      className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/15 bg-white/8 py-2.5 text-[12px] font-semibold text-white/70 transition hover:bg-white/12 hover:text-white"
                    >
                      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                      </svg>
                      Continuar con Google
                    </button>

                    <p className="mt-8 text-center text-[12px] text-white/30">
                      ¿No tienes cuenta?{' '}
                      <Link href="/register" className="font-bold text-rose-400 transition hover:text-rose-300 hover:underline">
                        Regístrate gratis
                      </Link>
                    </p>
                  </>
                ) : (
                  <>
                    <div className="mb-7 text-center">
                      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-500/20 bg-emerald-500/10">
                        <ShieldCheck size={26} className="text-emerald-400" />
                      </div>
                      <h2 className="text-[20px] font-bold tracking-tight text-white">Verifica tu correo</h2>
                      <p className="mt-1.5 text-[12px] leading-relaxed text-white/40">
                        Enviamos un código de 6 dígitos a<br />
                        <span className="font-semibold text-white/70">{email}</span>
                      </p>
                    </div>

                    {error && (
                      <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-300">
                        <AlertCircle size={14} /> {error}
                      </div>
                    )}

                    {resent && (
                      <div className="mb-4 flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-[12px] text-emerald-300">
                        <ShieldCheck size={14} /> Nuevo código enviado. Revisa tu bandeja.
                      </div>
                    )}

                    <form onSubmit={handleVerify} className="space-y-5">
                      <div>
                        <label className="mb-3 block text-center text-[10px] font-medium uppercase tracking-widest text-white/50">
                          Código de verificación
                        </label>
                        <div className="flex justify-center gap-2" onPaste={handleOtpPaste}>
                          {otp.map((d, i) => (
                            <input
                              key={i}
                              ref={el => { inputRefs.current[i] = el }}
                              type="text"
                              inputMode="numeric"
                              maxLength={1}
                              value={d}
                              onChange={e => handleOtpInput(i, e.target.value)}
                              onKeyDown={e => handleOtpKeyDown(i, e)}
                              className="h-13 w-11 rounded-xl border border-white/15 bg-white/8 text-center text-[20px] font-bold text-white caret-emerald-400 outline-none transition focus:border-emerald-400/60 focus:ring-2 focus:ring-emerald-500/20"
                            />
                          ))}
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={loading || otp.join('').length < 6}
                        className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 py-[11px] text-[13px] font-bold tracking-wide text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-500 disabled:opacity-50"
                      >
                        {loading ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                        {loading ? 'Verificando...' : 'Activar y entrar'}
                      </button>
                    </form>

                    <div className="mt-5 flex flex-col items-center gap-2">
                      <button
                        onClick={handleResend}
                        disabled={resending || countdown > 0}
                        className="flex items-center gap-1.5 text-[12px] text-white/30 transition hover:text-white/60 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {resending ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                        {countdown > 0 ? `Reenviar en ${countdown}s` : 'Reenviar código'}
                      </button>
                      <button
                        onClick={() => { setStage('login'); setError(''); setOtp(['','','','','','']) }}
                        className="text-[12px] text-white/20 transition hover:text-white/40"
                      >
                        Volver al login
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
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
