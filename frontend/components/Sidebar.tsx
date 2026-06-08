'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import {
  LayoutDashboard,
  Briefcase,
  FileCode2,
  UserCircle,
  Zap,
  Archive,
  LogOut,
  ChevronUp,
  Shield,
  Sparkles,
} from 'lucide-react'
import { signOut, useSession } from 'next-auth/react'
import ThemeToggle from '@/components/ui/ThemeToggle'
import UserAvatar from '@/components/ui/UserAvatar'
import { useAvatar } from '@/context/AvatarContext'
import { api } from '@/lib/api'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

function StatusDot({ active }: { active: boolean | null }) {
  if (active === null)
    return <span className="flex h-1.5 w-1.5 rounded-full bg-slate-300 dark:bg-slate-600 animate-pulse" />
  return (
    <span className="relative flex h-1.5 w-1.5">
      {active && (
        <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
      )}
      <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${
        active ? 'bg-emerald-500' : 'bg-slate-400 dark:bg-slate-600'
      }`} />
    </span>
  )
}

function SystemStatus() {
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [botOk, setBotOk] = useState<boolean | null>(null)
  const [mcpOk, setMcpOk] = useState<boolean | null>(null)

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API}/debug/sync-health`, { cache: 'no-store' })
        if (r.ok) {
          const d = await r.json()
          setApiOk(true)
          setBotOk(!!d.bot_active)
          setMcpOk(!!d.mcp_active)
        } else {
          setApiOk(false); setBotOk(false); setMcpOk(false)
        }
      } catch {
        setApiOk(false); setBotOk(false); setMcpOk(false)
      }
    }
    check()
    const id = setInterval(check, 5000)
    return () => clearInterval(id)
  }, [])

  const rows = [
    { active: apiOk, label: apiOk === null ? 'Comprobando API…' : apiOk ? 'API conectada' : 'API desconectada' },
    { active: botOk, label: botOk === null ? 'Comprobando bot…' : botOk ? 'Bot conectado' : 'Bot desconectado' },
    { active: mcpOk, label: mcpOk === null ? 'Comprobando MCP…' : mcpOk ? 'MCP conectado' : 'MCP desconectado' },
  ]

  return (
    <>
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-2.5 rounded-lg px-2.5 py-[7px] text-[13px] text-slate-400 dark:text-slate-500">
          <StatusDot active={r.active} />
          {r.label}
        </div>
      ))}
    </>
  )
}

const nav = [
  { href: '/dashboard',  label: 'Dashboard',        icon: LayoutDashboard },
  { href: '/vacantes',   label: 'Mis Vacantes',      icon: Briefcase },
  { href: '/archivo',    label: 'Archivadas',        icon: Archive },
  { href: '/plantillas', label: 'Plantillas LaTeX',  icon: FileCode2 },
  { href: '/perfil',     label: 'Perfil & Settings', icon: UserCircle },
]

export default function Sidebar() {
  const path = usePathname()
  const { initials } = useAvatar()
  const { data: session } = useSession()
  const [isProfileOpen, setIsProfileOpen] = useState(false)
  const profileRef = useRef<HTMLDivElement>(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [credits, setCredits] = useState<{ generados: number; limite: number } | null>(null)

  useEffect(() => {
    if (!(session as any)?.accessToken) return
    api.me().then(u => {
      setIsAdmin(u.role === 'admin')
      if (u.latex_limite < 9999) {
        setCredits({ generados: u.latex_generados, limite: u.latex_limite })
      }
    }).catch(() => {})
  }, [(session as any)?.accessToken])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setIsProfileOpen(false)
      }
    }
    if (isProfileOpen) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [isProfileOpen])

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-[220px] flex-col border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 transition-colors">
      {/* Brand */}
      <div className="flex items-center gap-2.5 border-b border-slate-200 dark:border-slate-800 px-4 py-[18px]">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-rose-500 to-rose-600 shadow-md shadow-rose-500/25">
          <Zap size={13} className="text-white" />
        </div>
        <div>
          <p className="text-[13px] font-semibold leading-none text-slate-900 dark:text-slate-100">Job Hunter</p>
          <p className="mt-0.5 text-[10px] leading-none text-slate-500 dark:text-slate-400">CV Automation</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3">
        <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
          Main
        </p>
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={`group relative flex items-center gap-2.5 rounded-lg px-2.5 py-[7px] text-[13px] transition-colors duration-150 ${
                active
                  ? 'bg-white dark:bg-slate-800 font-semibold text-slate-900 dark:text-white shadow-sm ring-1 ring-slate-200 dark:ring-white/10'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-white/50 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {active && (
                <span className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full bg-rose-500" />
              )}
              <Icon
                size={14}
                className={active ? 'text-rose-500 dark:text-rose-400' : 'text-slate-400 dark:text-slate-500'}
              />
              {label}
            </Link>
          )
        })}

        {isAdmin && (
          <>
            <div className="my-2 border-t border-slate-100 dark:border-slate-800" />
            <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-600">
              Admin
            </p>
            <Link
              href="/admin"
              className={`group relative flex items-center gap-2.5 rounded-lg px-2.5 py-[7px] text-[13px] transition-colors duration-150 ${
                path === '/admin'
                  ? 'bg-slate-100 dark:bg-slate-800 font-medium text-slate-900 dark:text-white'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-700 dark:hover:text-slate-200'
              }`}
            >
              {path === '/admin' && (
                <span className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full bg-rose-500" />
              )}
              <Shield
                size={14}
                className={path === '/admin' ? 'text-rose-500 dark:text-rose-400' : 'text-slate-400 dark:text-slate-500'}
              />
              Administración
            </Link>
          </>
        )}

        <div className="my-2 border-t border-slate-100 dark:border-slate-800" />
        <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-600">
          Sistema
        </p>
        <SystemStatus />
      </nav>

      {/* Theme toggle + User */}
      <div className="border-t border-slate-100 dark:border-slate-800 p-2.5">
        {credits !== null && (
          <Link
            href="/pricing"
            className="mb-2 flex flex-col gap-1.5 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 transition-colors hover:bg-emerald-500/15"
          >
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                <Sparkles size={11} />
                CVs generados
              </span>
              <span className="text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                {credits.generados}/{credits.limite}
              </span>
            </div>
            <div className="h-1 w-full overflow-hidden rounded-full bg-emerald-200 dark:bg-emerald-900/50">
              <div
                className="h-full rounded-full bg-emerald-500 dark:bg-emerald-400 transition-all"
                style={{ width: `${Math.min(100, (credits.generados / credits.limite) * 100)}%` }}
              />
            </div>
            <span className="text-[10px] text-emerald-600/70 dark:text-emerald-500/70">Ver paquetes →</span>
          </Link>
        )}
        <div className="mb-2 flex justify-center">
          <ThemeToggle />
        </div>
        <div ref={profileRef} className="relative">
          {/* Dropdown menu (floats above) */}
          {isProfileOpen && (
            <div className="absolute bottom-full left-0 right-0 mb-1 overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-lg shadow-black/5 dark:shadow-black/40">
              <Link
                href="/perfil"
                onClick={() => setIsProfileOpen(false)}
                className="flex items-center gap-2.5 px-3 py-2.5 text-[12px] text-slate-600 dark:text-slate-400 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200"
              >
                <UserCircle size={13} className="text-slate-400 dark:text-slate-500" />
                Perfil &amp; Settings
              </Link>
              <div className="mx-2 border-t border-slate-100 dark:border-slate-800" />
              <button
                onClick={() => signOut({ callbackUrl: '/login' })}
                className="flex w-full items-center gap-2.5 px-3 py-2.5 text-[12px] text-rose-500 dark:text-rose-400 transition-colors hover:bg-rose-50 dark:hover:bg-rose-950/30"
              >
                <LogOut size={13} />
                Cerrar sesión
              </button>
            </div>
          )}
          <button
            onClick={() => setIsProfileOpen(v => !v)}
            className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800/60"
          >
            <UserAvatar initials={initials} size={28} shape="full" />
            <div className="min-w-0 flex-1 text-left">
              <p className="truncate text-[12px] font-medium text-slate-700 dark:text-slate-300">Mi Cuenta</p>
              <p className="truncate text-[10px] text-slate-400 dark:text-slate-500">Personal Plan</p>
            </div>
            <ChevronUp
              size={13}
              className={`shrink-0 text-slate-400 transition-transform duration-150 dark:text-slate-600 ${isProfileOpen ? 'rotate-180' : ''}`}
            />
          </button>
        </div>
      </div>
    </aside>
  )
}
