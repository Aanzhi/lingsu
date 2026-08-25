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

  it('sends anonymous platform traffic to the independent platform login', () => {
    expect(resolveNavigation(null, '/platform/schools')).toEqual({
      path: '/platform/login',
      redirect: '/platform/schools',
    })
    expect(resolveNavigation(null, '/platform/login')).toBeNull()
  })

  it('keeps anonymous users on the branded public entry', () => {
    expect(resolveNavigation(null, '/')).toBeNull()
  })

  it('sends an authenticated user to only their own portal', () => {
    expect(resolveNavigation(teacher, '/student/home')).toEqual({ path: '/teacher/home' })
    expect(resolveNavigation(teacher, '/teacher/reviews')).toBeNull()
  })

  it('keeps the branded entry available after login while protecting auth pages', () => {
    expect(resolveNavigation(teacher, '/login')).toEqual({ path: '/teacher/home' })
    expect(resolveNavigation(teacher, '/')).toBeNull()
  })

})
