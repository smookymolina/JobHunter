'use client'
import { SessionProvider } from 'next-auth/react'
import { AvatarProvider } from '@/context/AvatarContext'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AvatarProvider>{children}</AvatarProvider>
    </SessionProvider>
  )
}
