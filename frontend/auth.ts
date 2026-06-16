import NextAuth, { CredentialsSignin } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

// Importante: BACKEND debe ser la URL interna de Docker para llamadas server-side.
// Si no existe BACKEND_URL, usamos el nombre del servicio 'api' por defecto.
const BACKEND = process.env.BACKEND_URL || 'http://api:8000'

// Auth.js solo expone `code` (no el mensaje libre) al cliente para errores de
// Credentials provider, así que usamos `code` como transporte del mensaje real
// del backend en vez del genérico "credentials".
class CustomAuthError extends CredentialsSignin {
  constructor(message: string) {
    super()
    this.code = message
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email:    { label: 'Email',    type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null
        
        const maxRetries = 3
        let lastError: any = null

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
          try {
            console.log(`[AUTH] [Intento ${attempt}] Login en: ${BACKEND}/auth/login para ${credentials.email}`)
            
            const res = await fetch(`${BACKEND}/auth/login`, {
              method:  'POST',
              headers: { 'Content-Type': 'application/json' },
              body:    JSON.stringify({ 
                email: credentials.email, 
                password: credentials.password 
              }),
              // Añadimos un pequeño timeout para no quedar colgados
              signal: AbortSignal.timeout(10000)
            })

            if (!res.ok) {
              const errorText = await res.text()
              console.error(`[AUTH] Error del Backend (${res.status}):`, errorText)
              
              let errorMessage = "Credenciales incorrectas"
              try {
                const errorData = JSON.parse(errorText)
                errorMessage = errorData.detail || errorMessage
              } catch (e) {
                errorMessage = errorText || `Error ${res.status} en el servidor`
              }
              throw new CustomAuthError(errorMessage)
            }

            const data = await res.json() as { access_token: string; user_id: string }
            console.log(`[AUTH] Login exitoso para: ${credentials.email}`)
            
            return { 
              id: data.user_id, 
              email: credentials.email as string, 
              accessToken: data.access_token 
            }
          } catch (error: any) {
            lastError = error
            console.error(`[AUTH] Fallo en intento ${attempt}:`, error.message || error)
            
            // Si es un error de credenciales (401/403), no reintentamos
            if (error instanceof CustomAuthError) {
              throw error
            }

            // Si no es el último intento, esperamos un poco antes de reintentar
            if (attempt < maxRetries) {
              const delay = attempt * 1000
              console.log(`[AUTH] Reintentando en ${delay}ms...`)
              await new Promise(resolve => setTimeout(resolve, delay))
            }
          }
        }

        // Si llegamos aquí, todos los intentos fallaron
        throw lastError || new Error("No se pudo conectar con el servidor interno tras varios intentos.")
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.userId      = (user as any).id
        token.accessToken = (user as any).accessToken
      }
      return token
    },
    session({ session, token }) {
      if (session && token) {
        ;(session as any).userId      = token.userId
        ;(session as any).accessToken = token.accessToken
      }
      return session
    },
  },
  pages: { 
    signIn: '/login' 
  },
  // En Auth.js v5, AUTH_SECRET es detectado automáticamente del env,
  // pero lo explicitamos para asegurar compatibilidad y depuración.
  secret: process.env.AUTH_SECRET,
  trustHost: true,
})
