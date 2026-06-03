import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist-sans' })

export const metadata: Metadata = {
  title: 'Job Hunter — CV Automation',
  description: 'Automated job search and CV generation system',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${geist.variable} h-full`}>
      <body className="flex h-full bg-zinc-950 text-zinc-100 antialiased">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden pl-[220px]">
          {children}
        </div>
      </body>
    </html>
  )
}
