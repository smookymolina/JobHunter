import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import { AvatarProvider } from '@/context/AvatarContext'

const geist = Geist({ subsets: ['latin'], variable: '--font-geist' })
const geistMono = Geist_Mono({ subsets: ['latin'], variable: '--font-geist-mono' })

export const metadata: Metadata = {
  title: 'Job Hunter — CV Automation',
  description: 'Automated job search and CV generation system',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="es"
      className={`${geist.variable} ${geistMono.variable} h-full dark`}
      suppressHydrationWarning
    >
      <body className="flex h-full font-sans antialiased">
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem('theme');if(t==='light')document.documentElement.classList.remove('dark');}catch(e){}`,
          }}
        />
        <AvatarProvider>
          <Sidebar />
          <div className="flex flex-1 flex-col overflow-hidden pl-[220px]">
            {children}
          </div>
        </AvatarProvider>
      </body>
    </html>
  )
}
