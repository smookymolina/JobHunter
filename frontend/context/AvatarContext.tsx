'use client'

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface AvatarCtx {
  avatarUrl: string | null
  setAvatarUrl: (url: string | null) => void
}

const Ctx = createContext<AvatarCtx>({ avatarUrl: null, setAvatarUrl: () => {} })

export function AvatarProvider({ children }: { children: ReactNode }) {
  const [avatarUrl, setUrl] = useState<string | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem('avatarUrl')
    if (stored) setUrl(stored)
  }, [])

  const setAvatarUrl = (url: string | null) => {
    setUrl(url)
    url ? localStorage.setItem('avatarUrl', url) : localStorage.removeItem('avatarUrl')
  }

  return <Ctx.Provider value={{ avatarUrl, setAvatarUrl }}>{children}</Ctx.Provider>
}

export const useAvatar = () => useContext(Ctx)
