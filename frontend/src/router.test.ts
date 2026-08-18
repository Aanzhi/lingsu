import { describe, expect, it } from 'vitest'
import { routeRecords } from './router'
import { resolveNavigation, routeForAuthRole } from './stores/authModel'

describe('application routes', () => {
  it('contains every agreed public and role route', () => {
    const paths = routeRecords.flatMap((route) => [route.path, ...(route.children ?? []).map((child) => `${route.path}/${child.path}`.replace(/\/+/g, '/'))])
    expect(paths).toEqual(expect.arrayContaining([
      '/login', '/register', '/student/home', '/student/projects', '/student/projects/:id/map',
      '/student/projects/:id/tasks/:taskId', '/student/projects/:id/materials', '/student/projects/:id/report',
      '/student/ai', '/teacher/home', '/teacher/pool', '/teacher/reviews/:submissionId', '/teacher/members',
      '/platform/home', '/platform/schools/:id', '/platform/settings',
    ]))
  })

  it('keeps portal access bound to session role', () => {
    expect(routeForAuthRole('teacher')).toBe('/teacher/home')
    const teacher = { id: 1, username: 't', displayName: '教师', role: 'teacher' as const, school: 1, schoolName: '学校', authorized: true }
    expect(resolveNavigation(teacher, '/teacher/reviews')).toBeNull()
    expect(resolveNavigation(teacher, '/student/home')).toEqual({ path: '/teacher/home' })
  })

  it('does not leave an unauthenticated visitor on the loading-only root entry', () => {
    expect(resolveNavigation(null, '/')).toEqual({ path: '/login' })
  })
})
