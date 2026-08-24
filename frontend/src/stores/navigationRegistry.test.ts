import { describe, expect, it } from 'vitest'

import { isNavigationActive, navigationChildren, primaryNavigation, utilityNavigation } from './navigationRegistry'

describe('primary navigation registry', () => {
  it('registers one primary entry per capability and role', () => {
    expect(primaryNavigation('student').map((item) => item.key))
      .toEqual(['home', 'projects', 'ai', 'journey', 'materials', 'invitations', 'public-applications'])
    expect(primaryNavigation('teacher').map((item) => item.key))
      .toEqual(['home', 'pool', 'projects', 'reviews', 'content'])
    expect(primaryNavigation('platform_admin').map((item) => item.key))
      .toEqual(['home', 'schools', 'ai-agents', 'content', 'settings'])
  })

  it('keeps the student portal capabilities flat for the top navigation', () => {
    const student = primaryNavigation('student')
    expect(student.every((item) => !item.children?.length)).toBe(true)
    expect(student.map((item) => item.label)).toEqual([
      '首页', '我的项目', '灵思 AI', '研究旅程', '材料档案', '项目邀请', '成果申请',
    ])
  })

  it('exposes content child pages from the same sidebar section', () => {
    const teacherContent = primaryNavigation('teacher').find((item) => item.key === 'content')!
    const platformContent = primaryNavigation('platform_admin').find((item) => item.key === 'content')!

    expect(navigationChildren('teacher', teacherContent).map((item) => item.to)).toEqual([
      '/teacher/competitions', '/teacher/announcements',
    ])
    expect(navigationChildren('platform_admin', platformContent).map((item) => item.to)).toEqual([
      '/platform/announcements', '/platform/cases',
    ])
  })

  it('never renders a child with the same route as its parent entry', () => {
    for (const role of ['student', 'teacher', 'platform_admin'] as const) {
      for (const item of primaryNavigation(role)) {
        expect(navigationChildren(role, item).map((child) => child.to)).not.toContain(item.to)
      }
    }
  })

  it('keeps a primary section active for nested routes without creating duplicate entries', () => {
    const student = primaryNavigation('student')
    const projects = student.find((item) => item.key === 'projects')!
    const settings = primaryNavigation('platform_admin').find((item) => item.key === 'settings')!

    expect(isNavigationActive('student', projects, '/student/projects/8/map')).toBe(true)
    expect(isNavigationActive('platform_admin', settings, '/platform/settings')).toBe(true)
  })

  it('keeps project work pages under the same primary project section', () => {
    const projects = primaryNavigation('student').find((item) => item.key === 'projects')!
    expect(isNavigationActive('student', projects, '/student/projects/8')).toBe(true)
    expect(isNavigationActive('student', projects, '/student/projects/8/map')).toBe(true)
  })

  it('does not register project detail tabs as duplicate global entries', () => {
    const routes = primaryNavigation('student').map((item) => item.to)
    expect(routes).not.toContain('/student/projects/:id/map')
    expect(routes).not.toContain('/student/projects/:id/materials')
    expect(routes).not.toContain('/student/projects/:id/report')
  })

  it('exposes remaining contextual pages in the secondary sidebar section', () => {
    expect(utilityNavigation('student', 8)).toEqual([])
    expect(utilityNavigation('student', null)).toEqual([])
    expect(utilityNavigation('teacher', null).map((item) => item.to)).toEqual(['/teacher/members'])
  })
})
