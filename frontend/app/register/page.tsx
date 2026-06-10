'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { AlertCircle, ChevronRight, Lock, Mail, Loader2, Zap, ShieldCheck, RotateCcw } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

type Stage = 'idle' | 'verifying'

export default function RegisterPage() {
  const [stage,    setStage]    = useState<Stage>('idle')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [otp,      setOtp]      = useState(['', '', '', '', '', ''])
  const [loading,  setLoading]  = useState(false)
  const [resending, setResending] = useState(false)
  const [error,    setError]    = useState('')
  const [resent,   setResent]   = useState(false)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])
  const router = useRouter()

  useEffect(() => {
    if (stage === 'verifying') {
      setTimeout(() => inputRefs.current[0]?.focus(), 80)
    }
  }, [stage])

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
      const res = await fetch(`${API}/auth/verify`, {
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
    setError('')
    setResending(true)
    setResent(false)
    try {
      await fetch(`${API}/auth/resend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      setResent(true)
      setOtp(['', '', '', '', '', ''])
      setTimeout(() => inputRefs.current[0]?.focus(), 80)
    } catch {
      setError('No se pudo reenviar el código.')
    } finally {
      setResending(false)
    }
  }

  function handleOtpInput(i: number, val: string) {
    const digit = val.replace(/\D/g, '').slice(-1)
    const next = [...otp]
    next[i] = digit
    setOtp(next)
    if (digit && i < 5) inputRefs.current[i + 1]?.focus()
  }

  function handleOtpKeyDown(i: number, e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Backspace' && !otp[i] && i > 0) {
      inputRefs.current[i - 1]?.focus()
    }
  }

  function handleOtpPaste(e: React.ClipboardEvent) {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
    if (!text) return
    e.preventDefault()
    const next = [...otp]
    text.split('').forEach((d, idx) => { next[idx] = d })
    setOtp(next)
    const focus = Math.min(text.length, 5)
    setTimeout(() => inputRefs.current[focus]?.focus(), 0)
  }

  const Brand = () => (
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
  )

  return (
    <div className="min-h-screen w-full bg-slate-50 dark:bg-slate-950 p-0 md:p-4 lg:p-8 transition-colors duration-300">
      <div className="w-full min-h-screen md:min-h-[calc(100vh-4rem)] grid grid-cols-1 md:grid-cols-2 md:rounded-2xl overflow-hidden border-y md:border border-slate-200 dark:border-slate-800 shadow-sm transition-colors duration-300">

        <Brand />

        {/* ── Columna Derecha ── */}
        <div className="bg-white dark:bg-slate-950 flex flex-col justify-center px-9 py-10 transition-colors duration-300">
          <div className="max-w-[320px] w-full mx-auto">

            {stage === 'idle' ? (
              <>
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

                <form onSubmit={handleRegister} className="space-y-4">
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
              </>
            ) : (
              <>
                <div className="mb-7 text-center">
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-700/40">
                    <ShieldCheck size={26} className="text-emerald-500" />
                  </div>
                  <h2 className="text-[20px] font-bold tracking-tight text-slate-900 dark:text-slate-50">Verifica tu correo</h2>
                  <p className="text-[12px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                    Enviamos un código de 6 dígitos a<br />
                    <span className="font-semibold text-slate-700 dark:text-slate-300">{email}</span>
                  </p>
                </div>

                {error && (
                  <div className="mb-4 rounded-xl border border-rose-100 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900/50 px-4 py-3 text-[12px] text-rose-600 dark:text-rose-400 flex items-center gap-2">
                    <AlertCircle size={14} />
                    {error}
                  </div>
                )}

                {resent && (
                  <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-800/50 px-4 py-3 text-[12px] text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                    <ShieldCheck size={14} />
                    Nuevo código enviado. Revisa tu bandeja.
                  </div>
                )}

                <form onSubmit={handleVerify} className="space-y-5">
                  <div>
                    <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-3 tracking-wide text-center">
                      Código de verificación
                    </label>
                    <div className="flex gap-2 justify-center" onPaste={handleOtpPaste}>
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
                          className="w-11 h-13 text-center text-[20px] font-bold bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-50 rounded-xl outline-none transition-all focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500/50 caret-rose-500"
                        />
                      ))}
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || otp.join('').length < 6}
                    className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white py-[11px] text-[13px] font-bold tracking-wide transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-600/20"
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                    {loading ? 'Verificando...' : 'Activar cuenta'}
                  </button>
                </form>

                <div className="mt-6 flex flex-col items-center gap-3">
                  <button
                    onClick={handleResend}
                    disabled={resending}
                    className="flex items-center gap-1.5 text-[12px] text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors disabled:opacity-50"
                  >
                    {resending ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                    Reenviar código
                  </button>
                  <button
                    onClick={() => { setStage('idle'); setError(''); setOtp(['','','','','','']) }}
                    className="text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
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
  )
}
