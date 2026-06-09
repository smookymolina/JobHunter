'use client'

import { useEffect, useRef, useState, type ElementType, type FormEvent, type ReactNode } from 'react'
import { useSession } from 'next-auth/react'
import {
  AlertCircle,
  Briefcase,
  Camera,
  CheckCircle,
  Copy,
  Eye,
  GraduationCap,
  LockKeyhole,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
  User,
  X,
  Zap,
} from 'lucide-react'
import Loader from '@/components/ui/Loader'
import { ApiError, api, type PerfilMaestro } from '@/lib/api'
import { useAvatar } from '@/context/AvatarContext'
import UserAvatar from '@/components/ui/UserAvatar'

const EMPTY: PerfilMaestro = {
  nombre: '', apellidos: '', titulo_profesional: '', email: '',
  telefono: '', ubicacion: '', linkedin: '', github: '', resumen: '',
  habilidades: { mecanica_manufactura: [], iot_embebidos: [], software_fullstack: [], idiomas: [] },
  experiencia: [], educacion: [], proyectos: [],
}

function toArr(csv: string): string[] {
  return csv.split(',').map(s => s.trim()).filter(Boolean)
}

function toCSV(arr: string[]): string {
  return arr.join(', ')
}

const INPUT = [
  'w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-4 py-2.5 text-sm text-slate-900 dark:text-slate-100',
  'placeholder:text-slate-400 dark:placeholder:text-slate-500 outline-none transition-colors duration-150',
  'focus:border-sky-400 focus:ring-2 focus:ring-sky-500/20',
].join(' ')

function Field({
  label, value, onChange, textarea = false, rows = 3,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  textarea?: boolean
  rows?: number
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="block text-xs font-medium tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </label>
      {textarea
        ? <textarea value={value} onChange={e => onChange(e.target.value)} rows={rows} className={`${INPUT} resize-none`} />
        : <input value={value} onChange={e => onChange(e.target.value)} className={INPUT} />}
    </div>
  )
}

function SectionCard({
  icon: Icon,
  title,
  children,
}: {
  icon: ElementType
  title: string
  children: ReactNode
}) {
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-2">
        <span className="h-4 w-1 shrink-0 rounded-full bg-sky-400" />
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          {title}
        </h2>
        <Icon size={13} className="ml-0.5 text-slate-400 dark:text-slate-500" />
      </div>
      {children}
    </div>
  )
}

function AvatarUploader({ initials }: { initials: string }) {
  const { avatarUrl, setAvatarUrl } = useAvatar()
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const handleFile = async (file: File) => {
    setUploading(true)
    const fd = new FormData()
    fd.append('avatar', file)
    const res = await fetch('/api/profile/avatar', { method: 'POST', body: fd })
    const data = await res.json() as { avatarUrl?: string }
    if (data.avatarUrl) setAvatarUrl(data.avatarUrl)
    setUploading(false)
  }

  const handleRemove = async () => {
    await fetch('/api/profile/avatar', { method: 'DELETE' })
    setAvatarUrl(null)
  }

  return (
    <div className="group relative w-fit">
      <UserAvatar initials={initials} size={64} shape="2xl" />
      <button
        onClick={() => !uploading && inputRef.current?.click()}
        className={`absolute inset-0 flex items-center justify-center rounded-2xl bg-black/50 transition-opacity duration-200 ${
          uploading ? 'cursor-wait opacity-100' : 'opacity-0 group-hover:opacity-100'
        }`}
        aria-label="Cambiar foto"
      >
        {uploading ? <Loader size={24} color="white" /> : <Camera size={18} className="text-white" />}
      </button>
      {avatarUrl && (
        <button
          onClick={handleRemove}
          className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-rose-500 text-white opacity-0 shadow-sm transition-opacity duration-200 group-hover:opacity-100"
          aria-label="Quitar foto"
        >
          <X size={10} />
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
    </div>
  )
}

export default function PerfilPage() {
  const [perfil, setPerfil] = useState<PerfilMaestro>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [hasTelegramBot, setHasTelegramBot] = useState(false)
  const [revealedToken, setRevealedToken] = useState<string | null>(null)
  const [securityAction, setSecurityAction] = useState<'set' | 'reveal' | null>(null)
  const [securityPassword, setSecurityPassword] = useState('')
  const [securityToken, setSecurityToken] = useState('')
  const [securityBusy, setSecurityBusy] = useState(false)
  const [securityError, setSecurityError] = useState<string | null>(null)
  const [copyHint, setCopyHint] = useState<string | null>(null)
  const { setInitials } = useAvatar()
  const { status } = useSession()

  useEffect(() => {
    // Wait for NextAuth to hydrate the session so _token is set before fetching
    if (status === 'loading') return
    let active = true
    Promise.allSettled([api.getPerfilMaestro(), api.me()]).then(([perfilRes, meRes]) => {
      if (!active) return
      if (perfilRes.status === 'fulfilled') {
        // Merge with EMPTY so partial profiles (from /register) never leave required fields undefined
        const p = { ...EMPTY, ...perfilRes.value }
        setPerfil(p)
        const ini = [p.nombre[0], p.apellidos?.[0]].filter(Boolean).join('').toUpperCase() || 'JM'
        setInitials(ini)
      } else {
        setPerfil(EMPTY)
      }
      setHasTelegramBot(meRes.status === 'fulfilled' ? !!meRes.value.has_telegram_bot : false)
      setLoading(false)
    })
    return () => { active = false }
  }, [status])

  // Auto-dismiss toast after 4 s
  useEffect(() => {
    if (!msg) return
    const t = window.setTimeout(() => setMsg(null), 4000)
    return () => window.clearTimeout(t)
  }, [msg])

  useEffect(() => {
    if (!revealedToken) return
    const timer = window.setTimeout(() => setRevealedToken(null), 60000)
    return () => window.clearTimeout(timer)
  }, [revealedToken])

  const set = (key: keyof PerfilMaestro, val: unknown) =>
    setPerfil(p => ({ ...p, [key]: val }))

  const setHab = (cat: keyof PerfilMaestro['habilidades'], csv: string) =>
    setPerfil(p => ({ ...p, habilidades: { ...p.habilidades, [cat]: toArr(csv) } }))

  const addExp = () => set('experiencia', [...perfil.experiencia, { puesto: '', empresa: '', periodo: '', logros: [] }])
  const delExp = (i: number) => set('experiencia', perfil.experiencia.filter((_, j) => j !== i))
  const setExp = (i: number, field: string, val: string) =>
    set('experiencia', perfil.experiencia.map((e, j) => (
      j === i ? { ...e, [field]: field === 'logros' ? toArr(val) : val } : e
    )))

  const addEdu = () => set('educacion', [...perfil.educacion, { titulo: '', institucion: '', anio: '' }])
  const delEdu = (i: number) => set('educacion', perfil.educacion.filter((_, j) => j !== i))
  const setEdu = (i: number, field: string, val: string) =>
    set('educacion', perfil.educacion.map((e, j) => (j === i ? { ...e, [field]: val } : e)))

  const addProj = () => set('proyectos', [...perfil.proyectos, { nombre: '', descripcion: '', tecnologias: [] }])
  const delProj = (i: number) => set('proyectos', perfil.proyectos.filter((_, j) => j !== i))
  const setProj = (i: number, field: string, val: string) =>
    set('proyectos', perfil.proyectos.map((p, j) => (
      j === i ? { ...p, [field]: field === 'tecnologias' ? toArr(val) : val } : p
    )))

  const handleSave = async () => {
    setSaving(true)
    setMsg(null)
    console.log('Guardando perfil...', perfil)
    try {
      const r = await api.savePerfilMaestro(perfil)
      console.log('Perfil guardado con éxito:', r)
      const ini = [perfil.nombre[0], perfil.apellidos?.[0]].filter(Boolean).join('').toUpperCase() || 'JM'
      setInitials(ini)
      setMsg({ ok: true, text: r.mensaje })
    } catch (err) {
      console.error('Error guardando perfil:', err)
      setMsg({ ok: false, text: err instanceof Error ? err.message : 'Error al guardar.' })
    } finally {
      setSaving(false)
    }
  }

  const openSecurityModal = (action: 'set' | 'reveal') => {
    setSecurityAction(action)
    setSecurityPassword('')
    setSecurityToken('')
    setSecurityError(null)
    setCopyHint(null)
  }

  const closeSecurityModal = () => {
    setSecurityAction(null)
    setSecurityPassword('')
    setSecurityToken('')
    setSecurityBusy(false)
    setSecurityError(null)
  }

  const handleSecuritySubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!securityAction) return
    // Frontend gate: block empty token before hitting the network
    if (securityAction === 'set' && !securityToken.trim()) {
      setSecurityError('El campo Token no puede estar vacío.')
      return
    }
    setSecurityBusy(true)
    setSecurityError(null)
    try {
      if (securityAction === 'set') {
        await api.setTelegramToken(securityPassword, securityToken.trim())
        setHasTelegramBot(true)
        setRevealedToken(null)
        setMsg({ ok: true, text: 'Token de Telegram guardado y cifrado.' })
      } else {
        const data = await api.revealTelegramToken(securityPassword)
        setRevealedToken(data.telegram_token)
        setMsg({ ok: true, text: 'Token de Telegram revelado temporalmente.' })
      }
      closeSecurityModal()
    } catch (err) {
      // Keep modal open on error — never auto-close on failure
      if (err instanceof ApiError) {
        setSecurityError(err.status === 401 ? 'Contraseña incorrecta.' : err.message)
      } else {
        setSecurityError('No se pudo completar la operación.')
      }
    } finally {
      setSecurityBusy(false)
    }
  }

  const handleCopyToken = async () => {
    if (!revealedToken) return
    try {
      await navigator.clipboard.writeText(revealedToken)
      setCopyHint('Copiado al portapapeles.')
      window.setTimeout(() => setCopyHint(null), 1500)
    } catch {
      setCopyHint('No se pudo copiar.')
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-white dark:bg-slate-950">
        <Loader size={40} label="Cargando perfil..." />
      </div>
    )
  }

  const addBtn = 'inline-flex items-center gap-1.5 text-xs font-medium text-sky-600 dark:text-sky-300 transition-colors hover:text-sky-500 dark:hover:text-sky-200'
  const delBtn = 'shrink-0 rounded-lg p-1 text-slate-400 transition-colors hover:bg-rose-500/10 hover:text-rose-400 dark:hover:text-rose-300'
  const subCard = 'rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 p-4 space-y-3'

  const initials = [perfil.nombre[0], perfil.apellidos?.[0]].filter(Boolean).join('').toUpperCase() || 'JM'
  const fullName = [perfil.nombre, perfil.apellidos].filter(Boolean).join(' ') || 'Tu nombre completo'

  return (
    <div className="flex h-full flex-col bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <header className="sticky top-0 z-30 shrink-0 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95 px-6 py-4 backdrop-blur-sm">
        <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">Perfil Maestro</h1>
        <p className="text-[12px] text-slate-500 dark:text-slate-400">
          Fuente de verdad para CV | datos guardados en perfil_maestro.json
        </p>
      </header>

      <main className="flex-1 space-y-4 overflow-y-auto bg-slate-50 dark:bg-slate-950 px-6 py-5">
        {msg && (
          <div className="fixed bottom-6 right-6 z-50 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div
              className={`flex items-center gap-2 rounded-2xl border px-5 py-3 shadow-xl backdrop-blur-md ${
                msg.ok
                  ? 'border-emerald-500/20 bg-emerald-50/90 text-emerald-800 dark:bg-emerald-950/90 dark:text-emerald-200'
                  : 'border-rose-500/20 bg-rose-50/90 text-rose-800 dark:bg-rose-950/90 dark:text-rose-200'
              }`}
            >
              {msg.ok ? <CheckCircle size={16} className="text-emerald-500" /> : <AlertCircle size={16} className="text-rose-500" />}
              <span className="text-sm font-semibold">{msg.text}</span>
            </div>
          </div>
        )}

        {revealedToken && (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-200">Token visible temporalmente</p>
                <p className="text-xs text-emerald-600/80 dark:text-emerald-100/70">Se oculta automaticamente en 60 segundos.</p>
              </div>
              <button
                onClick={() => setRevealedToken(null)}
                className="rounded-lg border border-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-100 transition-colors hover:bg-emerald-500/10"
              >
                Ocultar
              </button>
            </div>
            <div className="flex flex-col gap-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 p-4">
              <code className="break-all text-xs leading-6 text-slate-800 dark:text-slate-100">{revealedToken}</code>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyToken}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 px-4 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 transition-colors hover:border-sky-400/40 hover:text-slate-900 dark:hover:text-white"
                >
                  <Copy size={13} />
                  Copiar
                </button>
                {copyHint && <span className="text-xs text-slate-500 dark:text-slate-400">{copyHint}</span>}
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center gap-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 p-6 shadow-sm">
          <AvatarUploader initials={initials} />
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
              {fullName}
            </h2>
            <p className="mt-0.5 truncate text-sm text-slate-500 dark:text-slate-400">
              {perfil.titulo_profesional || 'Titulo profesional'}
            </p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              <span className="text-xs text-slate-500 dark:text-slate-400">perfil_maestro.json | guardado</span>
            </div>
          </div>
        </div>

        <SectionCard icon={ShieldCheck} title="Integracion de Telegram Bot">
          <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    hasTelegramBot ? 'bg-emerald-400 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]' : 'bg-slate-400 dark:bg-slate-500'
                  }`}
                />
                <p className="text-sm font-medium text-slate-700 dark:text-slate-100">
                  {hasTelegramBot ? 'Bot Conectado' : 'Sin configurar'}
                </p>
              </div>
              <p className="text-xs leading-5 text-slate-500 dark:text-slate-400">
                El token se guarda cifrado por usuario. La contraseña se exige para modificar o revelar el valor.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => openSecurityModal('set')}
                className="inline-flex items-center gap-2 rounded-xl border border-sky-400/20 bg-sky-500/10 px-4 py-2 text-xs font-semibold text-sky-600 dark:text-sky-200 transition-colors hover:bg-sky-500/15"
              >
                <LockKeyhole size={13} />
                Configurar Token
              </button>
              {hasTelegramBot && (
                <button
                  onClick={() => openSecurityModal('reveal')}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-200 transition-colors hover:border-sky-400/40 hover:text-slate-900 dark:hover:text-white"
                >
                  <Eye size={13} />
                  Ver Token
                </button>
              )}
            </div>
          </div>
        </SectionCard>

        <SectionCard icon={User} title="Datos Personales">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nombre" value={perfil.nombre} onChange={v => set('nombre', v)} />
            <Field label="Apellidos" value={perfil.apellidos} onChange={v => set('apellidos', v)} />
            <Field label="Titulo profesional" value={perfil.titulo_profesional} onChange={v => set('titulo_profesional', v)} />
            <Field label="Email" value={perfil.email} onChange={v => set('email', v)} />
            <Field label="Telefono" value={perfil.telefono} onChange={v => set('telefono', v)} />
            <Field label="Ubicacion" value={perfil.ubicacion} onChange={v => set('ubicacion', v)} />
            <Field label="LinkedIn" value={perfil.linkedin} onChange={v => set('linkedin', v)} />
            <Field label="GitHub" value={perfil.github} onChange={v => set('github', v)} />
          </div>
          <div className="mt-4">
            <Field label="Resumen profesional" value={perfil.resumen} onChange={v => set('resumen', v)} textarea rows={4} />
          </div>
        </SectionCard>

        <SectionCard icon={Zap} title="Habilidades">
          <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">Valores separados por coma</p>
          <div className="space-y-3">
            {(Object.keys(perfil.habilidades) as (keyof PerfilMaestro['habilidades'])[]).map(cat => (
              <Field
                key={cat}
                label={cat.replace(/_/g, ' ')}
                value={toCSV(perfil.habilidades[cat])}
                onChange={v => setHab(cat, v)}
              />
            ))}
          </div>
        </SectionCard>

        <SectionCard icon={Briefcase} title="Experiencia Laboral">
          <div className="space-y-3">
            {perfil.experiencia.map((e, i) => (
              <div key={i} className={subCard}>
                <div className="grid grid-cols-3 gap-3">
                  <Field label="Puesto" value={e.puesto} onChange={v => setExp(i, 'puesto', v)} />
                  <Field label="Empresa" value={e.empresa} onChange={v => setExp(i, 'empresa', v)} />
                  <Field label="Periodo" value={e.periodo} onChange={v => setExp(i, 'periodo', v)} />
                </div>
                <Field label="Logros (separados por coma)" value={toCSV(e.logros)} onChange={v => setExp(i, 'logros', v)} textarea />
                <button onClick={() => delExp(i)} className={delBtn}><Trash2 size={13} /></button>
              </div>
            ))}
          </div>
          <button onClick={addExp} className={`${addBtn} mt-3`}><Plus size={13} /> Agregar experiencia</button>
        </SectionCard>

        <SectionCard icon={GraduationCap} title="Educacion">
          <div className="space-y-3">
            {perfil.educacion.map((e, i) => (
              <div key={i} className="grid grid-cols-[1fr_1fr_80px_auto] items-end gap-3">
                <Field label="Titulo" value={e.titulo} onChange={v => setEdu(i, 'titulo', v)} />
                <Field label="Institucion" value={e.institucion} onChange={v => setEdu(i, 'institucion', v)} />
                <Field label="Anio" value={e.anio} onChange={v => setEdu(i, 'anio', v)} />
                <button onClick={() => delEdu(i)} className={`${delBtn} mb-0.5`}><Trash2 size={13} /></button>
              </div>
            ))}
          </div>
          <button onClick={addEdu} className={`${addBtn} mt-3`}><Plus size={13} /> Agregar educacion</button>
        </SectionCard>

        <SectionCard icon={Zap} title="Proyectos Destacados">
          <div className="space-y-3">
            {perfil.proyectos.map((p, i) => (
              <div key={i} className={subCard}>
                <Field label="Nombre" value={p.nombre} onChange={v => setProj(i, 'nombre', v)} />
                <Field label="Descripcion" value={p.descripcion} onChange={v => setProj(i, 'descripcion', v)} textarea />
                <Field label="Tecnologias (coma)" value={toCSV(p.tecnologias)} onChange={v => setProj(i, 'tecnologias', v)} />
                <button onClick={() => delProj(i)} className={delBtn}><Trash2 size={13} /></button>
              </div>
            ))}
          </div>
          <button onClick={addProj} className={`${addBtn} mt-3`}><Plus size={13} /> Agregar proyecto</button>
        </SectionCard>

        <div className="pb-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-sky-500/10 px-6 py-2.5 text-sm font-semibold text-sky-700 dark:text-sky-100 transition-all duration-200 hover:border-sky-400/40 hover:bg-sky-500/15 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
          >
            {saving
              ? <><Loader size={14} color="currentColor" /> Guardando...</>
              : <><Save size={14} /> Guardar cambios</>}
          </button>
        </div>
      </main>

      {securityAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 dark:bg-slate-950/80 px-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-2xl shadow-black/40">
            <form onSubmit={handleSecuritySubmit}>
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 px-5 py-4">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-50">Modal de Seguridad</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {securityAction === 'set'
                      ? 'Confirma tu contraseña para guardar el token.'
                      : 'Confirma tu contraseña para revelar el token.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closeSecurityModal}
                  className="rounded-lg border border-slate-200 dark:border-slate-800 p-2 text-slate-500 dark:text-slate-400 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100"
                  aria-label="Cerrar"
                >
                  <X size={14} />
                </button>
              </div>
              <div className="space-y-4 px-5 py-5">
                {securityError && (
                  <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm font-medium text-rose-600 dark:text-rose-200">
                    {securityError}
                  </div>
                )}
                <div className="grid gap-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Contraseña</label>
                    <input
                      type="password"
                      value={securityPassword}
                      onChange={e => setSecurityPassword(e.target.value)}
                      className={INPUT}
                      autoComplete="current-password"
                    />
                  </div>
                  {securityAction === 'set' && (
                    <div className="space-y-1.5">
                      <label className="text-xs font-medium text-slate-500 dark:text-slate-400">Nuevo Token</label>
                      <textarea
                        value={securityToken}
                        onChange={e => setSecurityToken(e.target.value)}
                        rows={4}
                        className={`${INPUT} resize-none font-mono text-xs`}
                        placeholder="1234567890:ABCDEF..."
                      />
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={closeSecurityModal}
                    className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 transition-colors hover:text-slate-900 dark:hover:text-white"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={securityBusy || !securityPassword || (securityAction === 'set' && !securityToken.trim())}
                    className="inline-flex items-center gap-2 rounded-xl border border-sky-400/20 bg-sky-500/10 px-4 py-2 text-xs font-semibold text-sky-600 dark:text-sky-100 transition-colors hover:bg-sky-500/15 disabled:opacity-50"
                  >
                    {securityBusy ? <Loader size={14} color="currentColor" /> : <LockKeyhole size={13} />}
                    {securityAction === 'set' ? 'Guardar' : 'Revelar'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
