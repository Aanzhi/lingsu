import { describe, expect, it } from 'vitest'
import { routeRecords } from './router'
import { resolveNavigation, routeForAuthRole } from './stores/authModel'

describe('application routes', () => {
  it('contains every agreed public and role route', () => {
    const paths = routeRecords.flatMap((route) => [route.path, ...(route.children ?? []).map((child) => `${route.path}/${child.path}`.replace(/\/+/g, '/'))])
    expect(paths).toEqual(expect.arrayContaining([
      '/', '/login', '/register', '/platform/login', '/student/home', '/student/projects', '/student/projects/:id/map',
      '/student/projects/:id/tasks/:taskId', '/student/projects/:id/materials', '/student/projects/:id/report',
      '/student/ai', '/student/notifications', '/teacher/home', '/teacher/pool', '/teacher/reviews/:submissionId', '/teacher/members',
      '/teacher/notifications',
      '/platform/home', '/platform/schools/:id', '/platform/settings',
    ]))
  })

  it('keeps the student portal defaulting to home', () => {
    const student = routeRecords.find((route) => route.path === '/student')!
    expect(student.redirect).toBe('/student/home')
  })

  it('keeps portal access bound to session role', () => {
    expect(routeForAuthRole('teacher')).toBe('/teacher/home')
    const teacher = { id: 1, username: 't', displayName: '教师', role: 'teacher' as const, school: 1, schoolName: '学校', authorized: true }
    expect(resolveNavigation(teacher, '/teacher/reviews')).toBeNull()
    expect(resolveNavigation(teacher, '/student/home')).toEqual({ path: '/teacher/home' })
  })

  it('keeps the public brand entry available before login', () => {
    expect(resolveNavigation(null, '/')).toBeNull()
  })

  it('keeps the legacy platform licenses URL pointed at the school list', () => {
    const platform = routeRecords.find((route) => route.path === '/platform')!
    const licenses = platform.children?.find((route) => route.path === 'licenses')!
    expect(licenses?.redirect).toBe('/platform/schools')
  })
})
