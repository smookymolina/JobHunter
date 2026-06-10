import { auth } from '@/auth'
import { NextResponse } from 'next/server'

export default auth((req) => {
  const isAuthenticated = !!req.auth
  const { pathname } = req.nextUrl

  if (!isAuthenticated && pathname !== '/login' && pathname !== '/register') {
    const url = req.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }
  if (isAuthenticated && pathname === '/login') {
    const url = req.nextUrl.clone()
    url.pathname = '/dashboard'
    return NextResponse.redirect(url)
  }
})

export const config = {
  matcher: ['/((?!api/auth|_next/static|_next/image|favicon\\.ico).*)'],
}
