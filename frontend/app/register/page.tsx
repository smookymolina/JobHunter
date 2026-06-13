'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { AlertCircle, ChevronRight, Lock, Mail, Loader2, Zap, ShieldCheck, RotateCcw } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

type Stage = 'idle' | 'verifying'

const INPUT =
  'w-full rounded-xl border border-white/15 bg-white/8 py-[10px] text-[13px] text-white ' +
  'placeholder-white/30 outline-none transition focus:border-rose-500/60 focus:bg-white/12 ' +
  'focus:ring-2 focus:ring-rose-500/20'

export default function RegisterPage() {
  const [stage,     setStage]    = useState<Stage>('idle')
  const [email,     setEmail]    = useState('')
  const [password,  setPassword] = useState('')
  const [otp,       setOtp]      = useState(['', '', '', '', '', ''])
  const [loading,   setLoading]  = useState(false)
  const [resending, setResending] = useState(false)
  const [error,     setError]    = useState('')
  const [resent,    setResent]   = useState(false)
  const [countdown, setCountdown] = useState(0)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])
  const router = useRouter()

  useEffect(() => {
    if (stage === 'verifying') setTimeout(() => inputRefs.current[0]?.focus(), 80)
  }, [stage])

  useEffect(() => {
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json() as { ok?: boolean; detail?: string }
      if (res.status === 201 && data.ok) {
        setStage('verifying')
        setCountdown(60)
        return
      }
      setError(data.detail ?? 'Error al crear la cuenta.')
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setLoading(false)
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    const code = otp.join('')
    if (code.length < 6) { setError('Ingresa el código completo de 6 dígitos.'); return }
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      })
      const data = await res.json() as { ok?: boolean; detail?: string }
      if (res.ok && data.ok) {
        router.push('/login?registered=true')
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
      {/* ── Blobs animados ── */}
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

      <div className="relative z-10 flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-3xl overflow-hidden rounded-3xl border border-white/10 shadow-2xl shadow-black/60 backdrop-blur-md">
          <div className="grid grid-cols-1 md:grid-cols-2">

            {/* ── Panel izquierdo (Brand) ── */}
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
                  Crea tu cuenta gratis y empieza a postularte con CVs personalizados en minutos.
                </p>

                <div className="mt-8 grid grid-cols-2 gap-3">
                  {[{ num: '8/8', label: 'CVS ENVIADOS' }, { num: '3x', label: 'MÁS ENTREVISTAS' }].map(({ num, label }) => (
                    <div key={label} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                      <p className="text-[20px] font-bold leading-none text-rose-400">{num}</p>
                      <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-white/30">{label}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3.5">
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

            {/* ── Panel derecho (Formulario) ── */}
            <div className="flex flex-col justify-center border-t border-white/10 bg-white/[0.04] px-9 py-10 backdrop-blur-md md:border-l md:border-t-0">
              <div className="mx-auto w-full max-w-[320px]">

                {stage === 'idle' ? (
                  <>
                    <div className="mb-7">
                      <h2 className="text-[20px] font-bold tracking-tight text-white">Registro de Cuenta</h2>
                      <p className="mt-1 text-[12px] text-white/40">Crea tu cuenta gratuita para empezar</p>
                    </div>

                    {error && (
                      <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-300">
                        <AlertCircle size={14} /> {error}
                      </div>
                    )}

                    <form onSubmit={handleRegister} className="space-y-4">
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
                            minLength={6}
                            className={`${INPUT} pl-9`}
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={loading}
                        className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-rose-600 py-[11px] text-[13px] font-bold tracking-wide text-white shadow-lg shadow-rose-600/25 transition hover:bg-rose-500 disabled:opacity-50"
                      >
                        {loading ? <Loader2 size={16} className="animate-spin" /> : <ChevronRight size={16} />}
                        {loading ? 'Creando cuenta...' : 'Registrarme'}
                      </button>
                    </form>

                    <p className="mt-8 text-center text-[12px] text-white/30">
                      ¿Ya tienes cuenta?{' '}
                      <Link href="/login" className="font-bold text-rose-400 transition hover:text-rose-300 hover:underline">
                        Inicia sesión
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
                        {loading ? 'Verificando...' : 'Activar cuenta'}
                      </button>
                    </form>

                    <div className="mt-6 flex flex-col items-center gap-2">
                      <button
                        onClick={handleResend}
                        disabled={resending || countdown > 0}
                        className="flex items-center gap-1.5 text-[12px] text-white/30 transition hover:text-white/60 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {resending ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                        {countdown > 0 ? `Reenviar en ${countdown}s` : 'Reenviar código'}
                      </button>
                      <button
                        onClick={() => { setStage('idle'); setError(''); setOtp(['','','','','','']) }}
                        className="text-[12px] text-white/20 transition hover:text-white/40"
                      >
                        Cambiar correo
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
