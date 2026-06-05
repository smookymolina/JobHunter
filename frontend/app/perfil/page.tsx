'use client'

import { useEffect, useRef, useState } from 'react'
import {
  AlertCircle, Briefcase, Camera, CheckCircle, GraduationCap,
  Plus, Save, Trash2, User, X, Zap,
} from 'lucide-react'
import Loader from '@/components/ui/Loader'
import { api, type PerfilMaestro } from '@/lib/api'
import { useAvatar } from '@/context/AvatarContext'
import UserAvatar from '@/components/ui/UserAvatar'

const EMPTY: PerfilMaestro = {
  nombre: '', apellidos: '', titulo_profesional: '', email: '',
  telefono: '', ubicacion: '', linkedin: '', github: '', resumen: '',
  habilidades: { mecanica_manufactura: [], iot_embebidos: [], software_fullstack: [], idiomas: [] },
  experiencia: [], educacion: [], proyectos: [],
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function toArr(csv: string): string[] {
  return csv.split(',').map(s => s.trim()).filter(Boolean)
}
function toCSV(arr: string[]): string {
  return arr.join(', ')
}

const INPUT = [
  'w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900',
  'placeholder:text-slate-400 outline-none transition-colors duration-150',
  'focus:ring-2 focus:ring-rose-500/20 focus:border-rose-400',
  'dark:bg-slate-800/60 dark:border-slate-700 dark:text-slate-100',
  'dark:placeholder:text-slate-500 dark:focus:border-rose-500/50 dark:focus:ring-rose-500/10',
].join(' ')

function Field({ label, value, onChange, textarea = false, rows = 3 }: {
  label: string; value: string; onChange: (v: string) => void; textarea?: boolean; rows?: number
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="block text-xs font-medium tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </label>
      {textarea
        ? <textarea value={value} onChange={e => onChange(e.target.value)} rows={rows}
            className={`${INPUT} resize-none`} />
        : <input value={value} onChange={e => onChange(e.target.value)} className={INPUT} />}
    </div>
  )
}

function SectionCard({
  icon: Icon, title, children,
}: {
  icon: React.ElementType; title: string; children: React.ReactNode
}) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-5 flex items-center gap-2">
        <span className="h-4 w-1 shrink-0 rounded-full bg-rose-500" />
        <h2 className="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
          {title}
        </h2>
        <Icon size={13} className="ml-0.5 text-slate-300 dark:text-slate-600" />
      </div>
      {children}
    </div>
  )
}

// ── Avatar uploader ───────────────────────────────────────────────────────────

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
      <button onClick={() => !uploading && inputRef.current?.click()}
        className={`absolute inset-0 flex items-center justify-center rounded-2xl bg-black/50 transition-opacity duration-200 ${uploading ? 'opacity-100 cursor-wait' : 'opacity-0 group-hover:opacity-100'}`}
        aria-label="Cambiar foto">
        {uploading ? <Loader size={24} color="white" /> : <Camera size={18} className="text-white" />}
      </button>
      {avatarUrl && (
        <button onClick={handleRemove}
          className="absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-rose-500 text-white opacity-0 shadow-sm transition-opacity duration-200 group-hover:opacity-100"
          aria-label="Quitar foto">
          <X size={10} />
        </button>
      )}
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
    </div>
  )
}

// ── Página ────────────────────────────────────────────────────────────────────

export default function PerfilPage() {
  const [perfil, setPerfil]   = useState<PerfilMaestro>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [msg, setMsg]         = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    api.getPerfilMaestro()
      .then(setPerfil)
      .catch(() => setPerfil(EMPTY))
      .finally(() => setLoading(false))
  }, [])

  const set = (key: keyof PerfilMaestro, val: unknown) =>
    setPerfil(p => ({ ...p, [key]: val }))

  const setHab = (cat: keyof PerfilMaestro['habilidades'], csv: string) =>
    setPerfil(p => ({ ...p, habilidades: { ...p.habilidades, [cat]: toArr(csv) } }))

  const addExp = () => set('experiencia', [...perfil.experiencia, { puesto: '', empresa: '', periodo: '', logros: [] }])
  const delExp = (i: number) => set('experiencia', perfil.experiencia.filter((_, j) => j !== i))
  const setExp = (i: number, field: string, val: string) =>
    set('experiencia', perfil.experiencia.map((e, j) =>
      j === i ? { ...e, [field]: field === 'logros' ? toArr(val) : val } : e
    ))

  const addEdu = () => set('educacion', [...perfil.educacion, { titulo: '', institucion: '', anio: '' }])
  const delEdu = (i: number) => set('educacion', perfil.educacion.filter((_, j) => j !== i))
  const setEdu = (i: number, field: string, val: string) =>
    set('educacion', perfil.educacion.map((e, j) => j === i ? { ...e, [field]: val } : e))

  const addProj = () => set('proyectos', [...perfil.proyectos, { nombre: '', descripcion: '', tecnologias: [] }])
  const delProj = (i: number) => set('proyectos', perfil.proyectos.filter((_, j) => j !== i))
  const setProj = (i: number, field: string, val: string) =>
    set('proyectos', perfil.proyectos.map((p, j) =>
      j === i ? { ...p, [field]: field === 'tecnologias' ? toArr(val) : val } : p
    ))

  const handleSave = async () => {
    setSaving(true); setMsg(null)
    try {
      const r = await api.savePerfilMaestro(perfil)
      setMsg({ ok: true, text: r.mensaje })
    } catch (err) {
      setMsg({ ok: false, text: err instanceof Error ? err.message : 'Error al guardar.' })
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div className="flex h-full items-center justify-center">
      <Loader size={40} label="Cargando perfil..." />
    </div>
  )

  const addBtn = "inline-flex items-center gap-1.5 text-xs font-medium text-rose-500 transition-colors hover:text-rose-400"
  const delBtn = "shrink-0 rounded-lg p-1 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-500 dark:hover:bg-rose-900/20"
  const subCard = "rounded-xl border border-slate-100 bg-slate-50/60 p-4 space-y-3 dark:border-slate-800 dark:bg-slate-800/30"

  const initials = [perfil.nombre[0], perfil.apellidos[0]].filter(Boolean).join('').toUpperCase() || 'JM'
  const fullName = [perfil.nombre, perfil.apellidos].filter(Boolean).join(' ') || 'Tu nombre completo'

  return (
    <div className="flex h-full flex-col">
      <header className="sticky top-0 z-30 shrink-0 border-b border-slate-100 bg-white/90 px-6 py-4 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-950/90">
        <h1 className="text-[18px] font-semibold tracking-tight text-slate-900 dark:text-slate-50">Perfil Maestro</h1>
        <p className="text-[12px] text-slate-400 dark:text-slate-500">
          Fuente de verdad para CV · datos guardados en perfil_maestro.json
        </p>
      </header>

      <main className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

        {/* Feedback */}
        {msg && (
          <div className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm ${
            msg.ok
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-700/30 dark:bg-emerald-950/30 dark:text-emerald-300'
              : 'border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-700/30 dark:bg-rose-950/30 dark:text-rose-300'
          }`}>
            {msg.ok ? <CheckCircle size={14} /> : <AlertCircle size={14} />}
            {msg.text}
          </div>
        )}

        {/* Header card de identidad */}
        <div className="flex items-center gap-5 rounded-2xl border border-slate-100 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <AvatarUploader initials={initials} />
          <div className="min-w-0 flex-1">
            <h2 className="truncate text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
              {fullName}
            </h2>
            <p className="mt-0.5 truncate text-sm text-slate-500 dark:text-slate-400">
              {perfil.titulo_profesional || 'Título profesional'}
            </p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="text-xs text-slate-400">perfil_maestro.json · guardado</span>
            </div>
          </div>
        </div>

        {/* Datos personales */}
        <SectionCard icon={User} title="Datos Personales">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Nombre" value={perfil.nombre} onChange={v => set('nombre', v)} />
            <Field label="Apellidos" value={perfil.apellidos} onChange={v => set('apellidos', v)} />
            <Field label="Título profesional" value={perfil.titulo_profesional} onChange={v => set('titulo_profesional', v)} />
            <Field label="Email" value={perfil.email} onChange={v => set('email', v)} />
            <Field label="Teléfono" value={perfil.telefono} onChange={v => set('telefono', v)} />
            <Field label="Ubicación" value={perfil.ubicacion} onChange={v => set('ubicacion', v)} />
            <Field label="LinkedIn" value={perfil.linkedin} onChange={v => set('linkedin', v)} />
            <Field label="GitHub" value={perfil.github} onChange={v => set('github', v)} />
          </div>
          <div className="mt-4">
            <Field label="Resumen profesional" value={perfil.resumen} onChange={v => set('resumen', v)} textarea rows={4} />
          </div>
        </SectionCard>

        {/* Habilidades */}
        <SectionCard icon={Zap} title="Habilidades">
          <p className="mb-3 text-xs text-slate-400 dark:text-slate-500">Valores separados por coma</p>
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

        {/* Experiencia */}
        <SectionCard icon={Briefcase} title="Experiencia Laboral">
          <div className="space-y-3">
            {perfil.experiencia.map((e, i) => (
              <div key={i} className={subCard}>
                <div className="grid grid-cols-3 gap-3">
                  <Field label="Puesto"  value={e.puesto}  onChange={v => setExp(i, 'puesto', v)} />
                  <Field label="Empresa" value={e.empresa} onChange={v => setExp(i, 'empresa', v)} />
                  <Field label="Período" value={e.periodo} onChange={v => setExp(i, 'periodo', v)} />
                </div>
                <Field label="Logros (separados por coma)" value={toCSV(e.logros)} onChange={v => setExp(i, 'logros', v)} textarea />
                <button onClick={() => delExp(i)} className={delBtn}><Trash2 size={13} /></button>
              </div>
            ))}
          </div>
          <button onClick={addExp} className={`${addBtn} mt-3`}><Plus size={13} /> Agregar experiencia</button>
        </SectionCard>

        {/* Educación */}
        <SectionCard icon={GraduationCap} title="Educación">
          <div className="space-y-3">
            {perfil.educacion.map((e, i) => (
              <div key={i} className="grid grid-cols-[1fr_1fr_80px_auto] items-end gap-3">
                <Field label="Título"      value={e.titulo}      onChange={v => setEdu(i, 'titulo', v)} />
                <Field label="Institución" value={e.institucion} onChange={v => setEdu(i, 'institucion', v)} />
                <Field label="Año"         value={e.anio}        onChange={v => setEdu(i, 'anio', v)} />
                <button onClick={() => delEdu(i)} className={`${delBtn} mb-0.5`}><Trash2 size={13} /></button>
              </div>
            ))}
          </div>
          <button onClick={addEdu} className={`${addBtn} mt-3`}><Plus size={13} /> Agregar educación</button>
        </SectionCard>

        {/* Proyectos */}
        <SectionCard icon={Zap} title="Proyectos Destacados">
          <div className="space-y-3">
            {perfil.proyectos.map((p, i) => (
              <div key={i} className={subCard}>
                <Field label="Nombre" value={p.nombre} onChange={v => setProj(i, 'nombre', v)} />
                <Field label="Descripción" value={p.descripcion} onChange={v => setProj(i, 'descripcion', v)} textarea />
                <Field label="Tecnologías (coma)" value={toCSV(p.tecnologias)} onChange={v => setProj(i, 'tecnologias', v)} />
                <button onClick={() => delProj(i)} className={delBtn}><Trash2 size={13} /></button>
              </div>
            ))}
          </div>
          <button onClick={addProj} className={`${addBtn} mt-3`}><Plus size={13} /> Agregar proyecto</button>
        </SectionCard>

        {/* Guardar */}
        <div className="pb-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-6 py-2.5 text-sm font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-slate-700 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
          >
            {saving
              ? <><Loader size={14} color="currentColor" /> Guardando...</>
              : <><Save size={14} /> Guardar cambios</>}
          </button>
        </div>

      </main>
    </div>
  )
}
