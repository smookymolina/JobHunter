'use client'
import { usePathname } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { useEffect } from 'react'
import Sidebar from './Sidebar'
import { setAuthToken } from '@/lib/api'

export default function ConditionalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { data: session, status } = useSession()

  useEffect(() => {
    setAuthToken((session as any)?.accessToken ?? null)
  }, [session])

  if (pathname === '/login' || pathname === '/register') return <>{children}</>

  if (status === 'loading') return (
    <div className="flex h-screen items-center justify-center bg-white dark:bg-slate-950">
      <div className="flex items-center gap-2 text-slate-400">
        <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span className="text-[13px]">Iniciando sesión...</span>
      </div>
    </div>
  )

  return (
    <div className="flex h-full">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden pl-[220px]">
        {children}
      </div>
    </div>
  )
}
