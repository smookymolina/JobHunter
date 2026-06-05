'use client'

import Image from 'next/image'
import { useAvatar } from '@/context/AvatarContext'

const R: Record<string, string> = {
  full: 'rounded-full', '2xl': 'rounded-2xl', xl: 'rounded-xl', lg: 'rounded-lg',
}

export default function UserAvatar({
  initials = 'JH',
  size = 32,
  shape = '2xl',
}: {
  initials?: string
  size?: number
  shape?: 'full' | '2xl' | 'xl' | 'lg'
}) {
  const { avatarUrl } = useAvatar()
  const r = R[shape] ?? 'rounded-xl'

  if (avatarUrl) return (
    <div className={`relative shrink-0 overflow-hidden ${r} ring-2 ring-white dark:ring-slate-800`}
      style={{ width: size, height: size }}>
      <Image src={avatarUrl} alt="Avatar" fill sizes={`${size}px`} className="object-cover" />
    </div>
  )

  return (
    <div className={`shrink-0 ${r} bg-rose-50 dark:bg-rose-900/20 flex items-center justify-center font-bold text-rose-500 dark:text-rose-400`}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }}>
      {initials}
    </div>
  )
}
