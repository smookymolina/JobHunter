'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { Shield, Users, Crown, User, CheckCircle, XCircle, Loader2, ChevronUp } from 'lucide-react'
import { api } from '@/lib/api'

type AdminUser = {
  user_id: string
  email: string
  tier: string
  role: string
  fecha_creacion: string | null
}

type Toast = { id: number; message: string; ok: boolean }

export default function AdminPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState<string | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [denied, setDenied] = useState(false)

  const addToast = (message: string, ok: boolean) => {
    const id = Date.now()
    setToasts(t => [...t, { id, message, ok }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500)
  }

  const loadUsers = useCallback(async () => {
    try {
      const data = await api.adminUsers()
      setUsers(data)
    } catch (e: any) {
      if (e?.status === 403) setDenied(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (status === 'loading') return
    if (status !== 'authenticated') { router.replace('/login'); return }
    void loadUsers()
  }, [status, loadUsers, router])

  const updateTier = async (user_id: string, next: string) => {
    setUpdating(user_id)
    try {
      await api.adminUpdateTier(user_id, next as any)
      setUsers(prev => prev.map(u => u.user_id === user_id ? { ...u, tier: next } : u))
      addToast('Paquete asignado correctamente', true)
    } catch {
      addToast('Error al actualizar el plan', false)
    } finally {
      setUpdating(null)
    }
  }

  if (status === 'loading' || loading) {
    return (
      <div className="flex h-full items-center justify-center bg-white dark:bg-slate-950">
        <Loader2 size={28} className="animate-spin text-slate-500" />
      </div>
    )
  }

  if (denied) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 bg-white dark:bg-slate-950 text-center">
        <XCircle size={36} className="text-rose-500" />
        <p className="text-[15px] font-medium text-slate-900 dark:text-slate-200">Acceso denegado</p>
        <p className="text-[13px] text-slate-500">Solo los administradores pueden ver esta página.</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-50">
      {/* Toasts */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`flex items-center gap-2.5 rounded-xl border px-4 py-2.5 text-[13px] font-medium shadow-lg backdrop-blur-sm transition-all ${
              t.ok
                ? 'border-emerald-500/20 bg-emerald-50/90 text-emerald-800 dark:border-emerald-700/60 dark:bg-emerald-950/90 dark:text-emerald-300'
                : 'border-rose-500/20 bg-rose-50/90 text-rose-800 dark:border-rose-700/60 dark:bg-rose-950/90 dark:text-rose-300'
            }`}
          >
            {t.ok ? <CheckCircle size={14} className="text-emerald-500" /> : <XCircle size={14} className="text-rose-500" />}
            {t.message}
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="sticky top-0 z-40 flex shrink-0 items-center justify-between border-b border-slate-100 dark:border-slate-800 bg-white/95 dark:bg-slate-950/95 px-6 py-4 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-500/10 border border-rose-500/20">
            <Shield size={15} className="text-rose-500 dark:text-rose-400" />
          </div>
          <div>
            <h1 className="text-[17px] font-semibold text-slate-900 dark:text-slate-100">Panel de Administración</h1>
            <p className="text-[11px] text-slate-500">{users.length} usuario{users.length !== 1 ? 's' : ''} registrado{users.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 px-3 py-1.5">
          <Users size={13} className="text-slate-400 dark:text-slate-500" />
          <span className="text-[12px] text-slate-600 dark:text-slate-400">Gestión de usuarios</span>
        </div>
      </header>

      {/* Table */}
      <main className="flex-1 overflow-auto px-6 py-6">
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden bg-white dark:bg-slate-900/40">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60">
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px]">Usuario</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px]">Rol</th>
                <th className="px-4 py-3 text-left font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px]">Registro</th>
                <th className="px-4 py-3 text-center font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px]">Plan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {users.map(u => (
                <tr key={u.user_id} className="hover:bg-slate-50 dark:hover:bg-slate-900/60 transition-colors">
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-300 uppercase">
                        {u.email.charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-slate-900 dark:text-slate-200 font-medium">{u.email}</p>
                        <p className="truncate text-[10px] text-slate-400 dark:text-slate-600 font-mono">{u.user_id}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    {u.role === 'admin' ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-200 dark:border-rose-700/40 bg-rose-50 dark:bg-rose-950/50 px-2.5 py-0.5 text-[11px] font-medium text-rose-600 dark:text-rose-400">
                        <Crown size={10} />
                        Admin
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 dark:border-slate-700/40 bg-slate-50 dark:bg-slate-800/50 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 dark:text-slate-400">
                        <User size={10} />
                        User
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-slate-500 dark:text-slate-500">
                    {u.fecha_creacion
                      ? new Date(u.fecha_creacion).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
                      : '—'}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex justify-center">
                      <div className="relative">
                        <select
                          value={u.tier}
                          disabled={updating === u.user_id}
                          onChange={(e) => updateTier(u.user_id, e.target.value)}
                          className={`appearance-none h-7 pl-3 pr-8 rounded-lg border text-[12px] font-semibold transition-all outline-none focus:ring-2 focus:ring-rose-500/20 disabled:opacity-50 cursor-pointer ${
                            u.tier === 'ultimate'
                              ? 'border-purple-200 dark:border-purple-600/40 bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400'
                              : u.tier === 'pro'
                                ? 'border-amber-200 dark:border-amber-600/40 bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400'
                                : 'border-slate-200 dark:border-slate-700/40 bg-slate-50 dark:bg-slate-800/40 text-slate-600 dark:text-slate-400'
                          }`}
                        >
                          <option value="free">Free</option>
                          <option value="pro">Pro</option>
                          <option value="ultimate">Ultimate</option>
                        </select>
                        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
                          {updating === u.user_id ? (
                            <Loader2 size={11} className="animate-spin" />
                          ) : (
                            <ChevronUp size={11} className="rotate-180" />
                          )}
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {users.length === 0 && (
            <div className="py-16 text-center text-slate-600">
              <Users size={28} className="mx-auto mb-3 opacity-40" />
              <p>No hay usuarios registrados.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
