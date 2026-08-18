import { describe, expect, it } from 'vitest'

import { resolveNavigation, type AuthUser } from './authModel'

const teacher: AuthUser = {
  id: 2,
  username: 'chen',
  displayName: '陈老师',
  role: 'teacher',
  school: 1,
  schoolName: '灵川中学',
  authorized: true,
}

describe('real session routing', () => {
  it('sends anonymous users to login while retaining their target', () => {
    expect(resolveNavigation(null, '/student/projects/7')).toEqual({
      path: '/login',
      redirect: '/student/projects/7',
    })
  })

  it('sends an authenticated user to only their own portal', () => {
    expect(resolveNavigation(teacher, '/student/home')).toEqual({ path: '/teacher/home' })
    expect(resolveNavigation(teacher, '/teacher/reviews')).toBeNull()
  })

  it('routes authenticated visits to public entry pages into the role home', () => {
    expect(resolveNavigation(teacher, '/login')).toEqual({ path: '/teacher/home' })
    expect(resolveNavigation(teacher, '/')).toEqual({ path: '/teacher/home' })
  })

})
