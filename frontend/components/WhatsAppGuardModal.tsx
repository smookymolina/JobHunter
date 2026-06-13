'use client'

import { useEffect, useRef, useState } from 'react'
import { AlertCircle, Loader2, MessageCircle, Phone, RotateCcw, ShieldCheck } from 'lucide-react'
import { api } from '@/lib/api'

type Step = 'phone' | 'otp'

const INPUT =
  'w-full rounded-xl border border-white/15 bg-white/8 px-4 py-[10px] text-[13px] text-white placeholder-white/30 outline-none transition focus:border-green-400/60 focus:bg-white/12 focus:ring-2 focus:ring-green-500/20'

export default function WhatsAppGuardModal({ onVerified }: { onVerified: () => void }) {
  const [step, setStep]       = useState<Step>('phone')
  const [phone, setPhone]     = useState('+52')
  const [otp, setOtp]         = useState(['', '', '', '', '', ''])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [countdown, setCountdown] = useState(0)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    if (step === 'otp') setTimeout(() => inputRefs.current[0]?.focus(), 80)
  }, [step])

  useEffect(() => {
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.sendWhatsappOtp(phone)
      setStep('otp')
      setCountdown(60)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo enviar el código.')
    } finally {
      setLoading(false)
    }
  }

  async function handleResend() {
    if (countdown > 0) return
    setError('')
    setLoading(true)
    try {
      await api.sendWhatsappOtp(phone)
      setOtp(['', '', '', '', '', ''])
      setCountdown(60)
      setTimeout(() => inputRefs.current[0]?.focus(), 80)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo reenviar.')
    } finally {
      setLoading(false)
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    const code = otp.join('')
    if (code.length < 6) { setError('Ingresa el código completo de 6 dígitos.'); return }
    setError('')
    setLoading(true)
    try {
      await api.verifyWhatsappOtp(code)
      onVerified()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Código incorrecto. Intenta de nuevo.')
    } finally {
      setLoading(false)
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm px-4">
      {/* Blobs detrás del modal */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -bottom-20 -left-20 h-72 w-72 animate-pulse rounded-full bg-green-600/10 blur-3xl" />
        <div className="absolute -right-20 -top-20 h-72 w-72 animate-pulse rounded-full bg-emerald-500/10 blur-3xl" style={{ animationDelay: '2s' }} />
      </div>

      <div className="relative w-full max-w-md rounded-3xl border border-white/10 bg-slate-900/90 p-8 shadow-2xl shadow-black/60 backdrop-blur-xl">
        {step === 'phone' ? (
          <>
            <div className="mb-6 flex flex-col items-center text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-green-500/20 bg-green-500/10">
                <MessageCircle size={26} className="text-green-400" />
              </div>
              <h2 className="text-[20px] font-bold text-white">Verificación WhatsApp</h2>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-400">
                Antes de continuar, verifica tu número de WhatsApp para proteger tu cuenta.
              </p>
            </div>

            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-300">
                <AlertCircle size={14} className="shrink-0" /> {error}
              </div>
            )}

            <form onSubmit={handleSend} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-[10px] font-medium uppercase tracking-widest text-white/50">
                  Número WhatsApp (E.164)
                </label>
                <div className="relative">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/30">
                    <Phone size={15} />
                  </div>
                  <input
                    type="tel"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    placeholder="+5215512345678"
                    required
                    className={`${INPUT} pl-9`}
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-600 py-[11px] text-[13px] font-bold tracking-wide text-white shadow-lg shadow-green-600/20 transition hover:bg-green-500 disabled:opacity-50"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <MessageCircle size={16} />}
                {loading ? 'Enviando...' : 'Enviar código por WhatsApp'}
              </button>
            </form>
          </>
        ) : (
          <>
            <div className="mb-6 flex flex-col items-center text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-green-500/20 bg-green-500/10">
                <ShieldCheck size={26} className="text-green-400" />
              </div>
              <h2 className="text-[20px] font-bold text-white">Código enviado</h2>
              <p className="mt-2 text-[13px] leading-relaxed text-slate-400">
                Revisa WhatsApp en{' '}
                <span className="font-semibold text-slate-200">{phone}</span>
              </p>
            </div>

            {error && (
              <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-[12px] text-rose-300">
                <AlertCircle size={14} className="shrink-0" /> {error}
              </div>
            )}

            <form onSubmit={handleVerify} className="space-y-5">
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
                    className="h-13 w-11 rounded-xl border border-white/15 bg-white/8 text-center text-[20px] font-bold text-white caret-green-400 outline-none transition focus:border-green-400/60 focus:ring-2 focus:ring-green-500/20"
                  />
                ))}
              </div>

              <button
                type="submit"
                disabled={loading || otp.join('').length < 6}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-600 py-[11px] text-[13px] font-bold tracking-wide text-white shadow-lg shadow-green-600/20 transition hover:bg-green-500 disabled:opacity-50"
              >
                {loading ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
                {loading ? 'Verificando...' : 'Verificar y entrar'}
              </button>
            </form>

            <div className="mt-5 flex flex-col items-center gap-2">
              <button
                onClick={handleResend}
                disabled={loading || countdown > 0}
                className="flex items-center gap-1.5 text-[12px] text-slate-500 transition hover:text-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                {countdown > 0 ? `Reenviar en ${countdown}s` : 'Reenviar código'}
              </button>
              <button
                onClick={() => { setStep('phone'); setOtp(['','','','','','']); setError('') }}
                className="text-[12px] text-slate-600 transition hover:text-slate-400"
              >
                Cambiar número
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
