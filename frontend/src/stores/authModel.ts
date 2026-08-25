export type AuthRole = 'student' | 'teacher' | 'platform_admin'

export interface AuthUser {
  id: number
  username: string
  displayName: string
  role: AuthRole
  school: number | null
  schoolName: string | null
  authorized: boolean
  mustChangePassword?: boolean
  primaryProject?: number | null
  primaryProjectTitle?: string | null
}

export const routeForAuthRole = (role: AuthRole) => `/${role === 'platform_admin' ? 'platform' : role}/home`

export function roleForPath(path: string): AuthRole | null {
  if (path.startsWith('/student')) return 'student'
  if (path.startsWith('/teacher')) return 'teacher'
  if (path.startsWith('/platform')) return 'platform_admin'
  return null
}


export function resolveNavigation(user: AuthUser | null, path: string) {
  const isPublicEntry = path === '/'
  const isAuthEntry = path === '/login' || path === '/register' || path === '/platform/login'
  if (!user) {
    if (isPublicEntry || isAuthEntry) return null
    return { path: path.startsWith('/platform') ? '/platform/login' : '/login', redirect: path }
  }
  const home = routeForAuthRole(user.role)
  if (isPublicEntry) return null
  if (isAuthEntry) return { path: home }
  const required = roleForPath(path)
  if (required && required !== user.role) return { path: home }
  return null
}
