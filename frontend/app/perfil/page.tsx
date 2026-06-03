'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle, Loader2, Plus, Save, Trash2 } from 'lucide-react'
import { api, type PerfilMaestro } from '@/lib/api'

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

function Field({ label, value, onChange, textarea = false }: {
  label: string; value: string; onChange: (v: string) => void; textarea?: boolean
}) {
  const cls = "w-full rounded-lg border border-white/[0.07] bg-zinc-950/60 px-3 py-1.5 text-[12px] text-zinc-200 outline-none placeholder-zinc-600 focus:border-indigo-500/50"
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">{label}</label>
      {textarea
        ? <textarea value={value} onChange={e => onChange(e.target.value)} rows={3} className={`${cls} resize-none`} />
        : <input  value={value} onChange={e => onChange(e.target.value)} className={cls} />}
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

  // ── Experiencia helpers
  const addExp = () => set('experiencia', [...perfil.experiencia, { puesto: '', empresa: '', periodo: '', logros: [] }])
  const delExp = (i: number) => set('experiencia', perfil.experiencia.filter((_, j) => j !== i))
  const setExp = (i: number, field: string, val: string) =>
    set('experiencia', perfil.experiencia.map((e, j) =>
      j === i ? { ...e, [field]: field === 'logros' ? toArr(val) : val } : e
    ))

  // ── Educación helpers
  const addEdu = () => set('educacion', [...perfil.educacion, { titulo: '', institucion: '', anio: '' }])
  const delEdu = (i: number) => set('educacion', perfil.educacion.filter((_, j) => j !== i))
  const setEdu = (i: number, field: string, val: string) =>
    set('educacion', perfil.educacion.map((e, j) => j === i ? { ...e, [field]: val } : e))

  // ── Proyectos helpers
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
      <Loader2 size={22} className="animate-spin text-zinc-600" />
    </div>
  )

  const sectionCls = "rounded-xl border border-white/[0.06] bg-zinc-900/50 p-4 space-y-3"
  const sectionTitle = "text-[11px] font-semibold uppercase tracking-widest text-zinc-500 mb-3"
  const addBtn = "inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-200 transition-colors"
  const delBtn = "shrink-0 rounded p-0.5 text-zinc-600 hover:text-rose-400 transition-colors"

  return (
    <div className="flex h-full flex-col">
      <header className="shrink-0 border-b border-white/[0.06] px-6 py-4">
        <h1 className="text-[18px] font-semibold tracking-tight text-zinc-50">Perfil Maestro</h1>
        <p className="text-[12px] text-zinc-500">Fuente de verdad para CV · datos guardados en perfil_maestro.json</p>
      </header>

      <main className="flex-1 overflow-auto px-6 py-5 space-y-4">

        {/* Feedback */}
        {msg && (
          <div className={`flex items-center gap-2 rounded-md px-3 py-2 text-[12px] ${
            msg.ok ? 'border border-emerald-700/30 bg-emerald-950/30 text-emerald-300'
                   : 'border border-rose-700/30 bg-rose-950/30 text-rose-300'
          }`}>
            {msg.ok ? <CheckCircle size={13} /> : <AlertCircle size={13} />}
            {msg.text}
          </div>
        )}

        {/* Datos personales */}
        <div className={sectionCls}>
          <p className={sectionTitle}>Datos personales</p>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nombre" value={perfil.nombre} onChange={v => set('nombre', v)} />
            <Field label="Apellidos" value={perfil.apellidos} onChange={v => set('apellidos', v)} />
            <Field label="Título profesional" value={perfil.titulo_profesional} onChange={v => set('titulo_profesional', v)} />
            <Field label="Email" value={perfil.email} onChange={v => set('email', v)} />
            <Field label="Teléfono" value={perfil.telefono} onChange={v => set('telefono', v)} />
            <Field label="Ubicación" value={perfil.ubicacion} onChange={v => set('ubicacion', v)} />
            <Field label="LinkedIn" value={perfil.linkedin} onChange={v => set('linkedin', v)} />
            <Field label="GitHub" value={perfil.github} onChange={v => set('github', v)} />
          </div>
          <Field label="Resumen profesional" value={perfil.resumen} onChange={v => set('resumen', v)} textarea />
        </div>

        {/* Habilidades */}
        <div className={sectionCls}>
          <p className={sectionTitle}>Habilidades (separadas por coma)</p>
          <div className="space-y-2">
            {(Object.keys(perfil.habilidades) as (keyof PerfilMaestro['habilidades'])[]).map(cat => (
              <Field
                key={cat}
                label={cat.replace(/_/g, ' ')}
                value={toCSV(perfil.habilidades[cat])}
                onChange={v => setHab(cat, v)}
              />
            ))}
          </div>
        </div>

        {/* Experiencia */}
        <div className={sectionCls}>
          <p className={sectionTitle}>Experiencia laboral</p>
          {perfil.experiencia.map((e, i) => (
            <div key={i} className="rounded-lg border border-white/[0.05] bg-zinc-950/30 p-3 space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <Field label="Puesto"   value={e.puesto}   onChange={v => setExp(i, 'puesto', v)} />
                <Field label="Empresa"  value={e.empresa}  onChange={v => setExp(i, 'empresa', v)} />
                <Field label="Período"  value={e.periodo}  onChange={v => setExp(i, 'periodo', v)} />
              </div>
              <Field label="Logros (separados por coma)" value={toCSV(e.logros)} onChange={v => setExp(i, 'logros', v)} textarea />
              <button onClick={() => delExp(i)} className={delBtn}><Trash2 size={12} /></button>
            </div>
          ))}
          <button onClick={addExp} className={addBtn}><Plus size={12} /> Agregar experiencia</button>
        </div>

        {/* Educación */}
        <div className={sectionCls}>
          <p className={sectionTitle}>Educación</p>
          {perfil.educacion.map((e, i) => (
            <div key={i} className="grid grid-cols-[1fr_1fr_80px_auto] gap-2 items-end">
              <Field label="Título"       value={e.titulo}      onChange={v => setEdu(i, 'titulo', v)} />
              <Field label="Institución"  value={e.institucion} onChange={v => setEdu(i, 'institucion', v)} />
              <Field label="Año"          value={e.anio}        onChange={v => setEdu(i, 'anio', v)} />
              <button onClick={() => delEdu(i)} className={`${delBtn} mb-0.5`}><Trash2 size={12} /></button>
            </div>
          ))}
          <button onClick={addEdu} className={addBtn}><Plus size={12} /> Agregar educación</button>
        </div>

        {/* Proyectos */}
        <div className={sectionCls}>
          <p className={sectionTitle}>Proyectos destacados</p>
          {perfil.proyectos.map((p, i) => (
            <div key={i} className="rounded-lg border border-white/[0.05] bg-zinc-950/30 p-3 space-y-2">
              <Field label="Nombre"          value={p.nombre}       onChange={v => setProj(i, 'nombre', v)} />
              <Field label="Descripción"     value={p.descripcion}  onChange={v => setProj(i, 'descripcion', v)} textarea />
              <Field label="Tecnologías (coma)" value={toCSV(p.tecnologias)} onChange={v => setProj(i, 'tecnologias', v)} />
              <button onClick={() => delProj(i)} className={delBtn}><Trash2 size={12} /></button>
            </div>
          ))}
          <button onClick={addProj} className={addBtn}><Plus size={12} /> Agregar proyecto</button>
        </div>

        {/* Guardar */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
        >
          {saving ? <><Loader2 size={14} className="animate-spin" /> Guardando...</> : <><Save size={14} /> Guardar perfil maestro</>}
        </button>

      </main>
    </div>
  )
}
