'use client'

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

interface AvatarCtx {
  avatarUrl: string | null
  setAvatarUrl: (url: string | null) => void
  initials: string
  setInitials: (i: string) => void
}

const Ctx = createContext<AvatarCtx>({
  avatarUrl: null, setAvatarUrl: () => {},
  initials: 'JM', setInitials: () => {},
})

export function AvatarProvider({ children }: { children: ReactNode }) {
  const [avatarUrl, setUrl] = useState<string | null>(null)
  const [initials, setInitialsState] = useState('JM')

  useEffect(() => {
    fetch('/api/profile/avatar')
      .then(r => r.json())
      .then((d: { avatarUrl: string | null }) => {
        if (d.avatarUrl) {
          setUrl(d.avatarUrl)
          localStorage.setItem('avatarUrl', d.avatarUrl)
        } else {
          const stored = localStorage.getItem('avatarUrl')
          if (stored) setUrl(stored)
        }
      })
      .catch(() => {
        const stored = localStorage.getItem('avatarUrl')
        if (stored) setUrl(stored)
      })

    const stored = localStorage.getItem('avatarInitials')
    if (stored) setInitialsState(stored)
  }, [])

  const setAvatarUrl = useCallback((url: string | null) => {
    setUrl(url)
    url ? localStorage.setItem('avatarUrl', url) : localStorage.removeItem('avatarUrl')
  }, [])

  const setInitials = useCallback((i: string) => {
    setInitialsState(i)
    localStorage.setItem('avatarInitials', i)
  }, [])

  return (
    <Ctx.Provider value={{ avatarUrl, setAvatarUrl, initials, setInitials }}>
      {children}
    </Ctx.Provider>
  )
}

export const useAvatar = () => useContext(Ctx)
