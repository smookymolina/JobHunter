'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import {
  LayoutDashboard,
  Briefcase,
  FileCode2,
  UserCircle,
  Zap,
  Settings,
  Archive,
} from 'lucide-react'
import ThemeToggle from '@/components/ui/ThemeToggle'
import UserAvatar from '@/components/ui/UserAvatar'

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

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-[220px] flex-col border-r border-slate-100 bg-white dark:border-slate-800 dark:bg-slate-950">
      {/* Brand */}
      <div className="flex items-center gap-2.5 border-b border-slate-100 px-4 py-[18px] dark:border-slate-800">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-rose-500 to-rose-600 shadow-md shadow-rose-500/25">
          <Zap size={13} className="text-white" />
        </div>
        <div>
          <p className="text-[13px] font-semibold leading-none text-slate-900 dark:text-slate-100">Job Hunter</p>
          <p className="mt-0.5 text-[10px] leading-none text-slate-400 dark:text-slate-500">CV Automation</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3">
        <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-600">
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
                  ? 'bg-slate-100 font-medium text-slate-900 dark:bg-slate-800 dark:text-white'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800/60 dark:hover:text-slate-200'
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

        <div className="my-2 border-t border-slate-100 dark:border-slate-800" />
        <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-600">
          Sistema
        </p>
        <SystemStatus />
      </nav>

      {/* Theme toggle + User */}
      <div className="border-t border-slate-100 p-2.5 dark:border-slate-800">
        <div className="mb-2 flex justify-center">
          <ThemeToggle />
        </div>
        <button className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800/60">
          <UserAvatar initials="JH" size={28} shape="full" />
          <div className="min-w-0 flex-1 text-left">
            <p className="truncate text-[12px] font-medium text-slate-700 dark:text-slate-300">Mi Cuenta</p>
            <p className="truncate text-[10px] text-slate-400 dark:text-slate-600">Personal Plan</p>
          </div>
          <Settings size={13} className="shrink-0 text-slate-400 dark:text-slate-600" />
        </button>
      </div>
    </aside>
  )
}
