import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

const BACKEND = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email:    { label: 'Email',    type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null
        const res = await fetch(`${BACKEND}/auth/login`, {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ email: credentials.email, password: credentials.password }),
        })
        if (!res.ok) {
          let detail = 'Credenciales inválidas'
          try {
            const data = await res.json() as { detail?: string }
            detail = data.detail ?? detail
          } catch {
            try { detail = (await res.text()) || detail } catch { /* ignore */ }
          }
          throw new Error(detail)
        }
        const data = await res.json() as { access_token: string; user_id: string }
        return { id: data.user_id, email: credentials.email as string, accessToken: data.access_token }
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.userId      = user.id
        token.accessToken = (user as any).accessToken
      }
      return token
    },
    session({ session, token }) {
      ;(session as any).userId      = token.userId
      ;(session as any).accessToken = token.accessToken
      return session
    },
  },
  pages:     { signIn: '/login' },
  secret:    process.env.AUTH_SECRET,
  trustHost: true,
})
