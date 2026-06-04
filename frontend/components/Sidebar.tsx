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
  ChevronRight,
} from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

function StatusDot({ active }: { active: boolean | null }) {
  if (active === null)
    return <div className="flex h-1.5 w-1.5 rounded-full bg-zinc-600 animate-pulse" />
  return (
    <div
      className={`flex h-1.5 w-1.5 rounded-full ${
        active
          ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50'
          : 'bg-zinc-500'
      }`}
    />
  )
}

function SystemStatus() {
  const [apiOk, setApiOk]   = useState<boolean | null>(null)
  const [botOk, setBotOk]   = useState<boolean | null>(null)

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(`${API}/debug/sync-health`, { cache: 'no-store' })
        if (r.ok) {
          const d = await r.json()
          setApiOk(true)
          setBotOk(!!d.bot_active)
        } else {
          setApiOk(false); setBotOk(false)
        }
      } catch {
        setApiOk(false); setBotOk(false)
      }
    }
    check()
    const id = setInterval(check, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <>
      <div className="flex items-center gap-2.5 rounded-md px-2.5 py-[7px] text-[13px] text-zinc-600">
        <StatusDot active={apiOk} />
        {apiOk === null ? 'Comprobando API…' : apiOk ? 'API conectada' : 'API desconectada'}
      </div>
      <div className="flex items-center gap-2.5 rounded-md px-2.5 py-[7px] text-[13px] text-zinc-600">
        <StatusDot active={botOk} />
        {botOk === null ? 'Comprobando bot…' : botOk ? 'Bot conectado' : 'Bot desconectado'}
      </div>
    </>
  )
}

const nav = [
  { href: '/dashboard',  label: 'Dashboard',        icon: LayoutDashboard },
  { href: '/vacantes',   label: 'Mis Vacantes',      icon: Briefcase },
  { href: '/plantillas', label: 'Plantillas LaTeX',  icon: FileCode2 },
  { href: '/perfil',     label: 'Perfil & Settings', icon: UserCircle },
]

export default function Sidebar() {
  const path = usePathname()

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-[220px] flex-col border-r border-white/[0.06] bg-zinc-950">
      {/* Brand */}
      <div className="flex items-center gap-2.5 border-b border-white/[0.06] px-4 py-[18px]">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
          <Zap size={13} className="text-white" />
        </div>
        <div>
          <p className="text-[13px] font-semibold leading-none text-zinc-100">Job Hunter</p>
          <p className="mt-0.5 text-[10px] leading-none text-zinc-500">CV Automation</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3">
        <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
          Main
        </p>
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={`group flex items-center justify-between gap-2.5 rounded-md px-2.5 py-[7px] text-[13px] transition-colors duration-100 ${
                active
                  ? 'bg-white/[0.07] text-white'
                  : 'text-zinc-500 hover:bg-white/[0.04] hover:text-zinc-300'
              }`}
            >
              <span className="flex items-center gap-2.5">
                <Icon
                  size={14}
                  className={active ? 'text-indigo-400' : 'text-zinc-600 group-hover:text-zinc-500'}
                />
                {label}
              </span>
              {active && <ChevronRight size={11} className="text-zinc-600" />}
            </Link>
          )
        })}

        <div className="my-2 border-t border-white/[0.06]" />
        <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-zinc-600">
          Sistema
        </p>
        <SystemStatus />
      </nav>

      {/* User mock */}
      <div className="border-t border-white/[0.06] p-2.5">
        <button className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 transition-colors hover:bg-white/[0.04]">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-indigo-500 text-[11px] font-bold text-white">
            JH
          </div>
          <div className="min-w-0 flex-1 text-left">
            <p className="truncate text-[12px] font-medium text-zinc-300">Mi Cuenta</p>
            <p className="truncate text-[10px] text-zinc-600">Personal Plan</p>
          </div>
          <Settings size={13} className="shrink-0 text-zinc-600" />
        </button>
      </div>
    </aside>
  )
}
