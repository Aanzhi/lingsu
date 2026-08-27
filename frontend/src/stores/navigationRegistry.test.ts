import { describe, expect, it } from 'vitest'

import { isNavigationActive, navigationChildren, primaryNavigation, resolveStudentNavigationProject, studentTopNavigation, utilityNavigation } from './navigationRegistry'

describe('primary navigation registry', () => {
  it('registers one primary entry per capability and role', () => {
    expect(primaryNavigation('student').map((item) => item.key))
      .toEqual(['home', 'projects', 'ai', 'journey', 'invitations', 'public-applications', 'notifications', 'content'])
    expect(primaryNavigation('teacher').map((item) => item.key))
      .toEqual(['home', 'pool', 'projects', 'ai', 'reviews', 'content'])
    expect(primaryNavigation('platform_admin').map((item) => item.key))
      .toEqual(['home', 'schools', 'ai-agents', 'content', 'settings'])
  })

  it('keeps the student primary entries stable and groups content pages in the sidebar', () => {
    const student = primaryNavigation('student')
    expect(student.filter((item) => item.key !== 'content').every((item) => !item.children?.length)).toBe(true)
    expect(student.map((item) => item.label)).toEqual([
      '首页', '我的项目', '灵思 AI', '研究进程', '项目邀请', '成果申请',
      '消息中心', '内容资源',
    ])
    expect(student.find((item) => item.key === 'content')?.children).toEqual(['cases', 'competitions', 'announcements'])
  })

  it('surfaces the notification center in the student top navigation', () => {
    expect(studentTopNavigation(8).find((item) => item.key === 'notifications')).toEqual({
      key: 'notifications', label: '消息中心', to: '/student/notifications', icon: 'bell',
    })
  })

  it('keeps project-dependent student entries distinct before a project exists', () => {
    const entries = primaryNavigation('student')
    expect(entries.find((item) => item.key === 'projects')?.to).toBe('/student/projects')
    expect(entries.find((item) => item.key === 'journey')?.to).toBe('/student/projects?focus=journey')
    expect(entries.find((item) => item.key === 'materials')).toBeUndefined()
    expect(entries.find((item) => item.key === 'public-applications')?.to).toBe('/student/projects?focus=apply')
    expect(new Set(entries.map((item) => item.to)).size).toBe(entries.length)
  })

  it('builds real project destinations when a primary project exists', () => {
    const entries = primaryNavigation('student', 8)
    expect(entries.find((item) => item.key === 'projects')?.to).toBe('/student/projects')
    expect(entries.find((item) => item.key === 'journey')?.to).toBe('/student/projects/8/map')
    expect(entries.find((item) => item.key === 'materials')).toBeUndefined()
    expect(entries.find((item) => item.key === 'public-applications')?.to).toBe('/student/public-applications?projectId=8')
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

  it('activates only the matching student project surface', () => {
    const student = primaryNavigation('student', 8)
    const projects = student.find((item) => item.key === 'projects')!
    const journey = student.find((item) => item.key === 'journey')!
    const applications = student.find((item) => item.key === 'public-applications')!
    const settings = primaryNavigation('platform_admin').find((item) => item.key === 'settings')!

    expect(isNavigationActive('student', projects, '/student/projects/8')).toBe(true)
    expect(isNavigationActive('student', projects, '/student/projects/8/map')).toBe(false)
    expect(isNavigationActive('student', journey, '/student/projects/8/map')).toBe(true)
    expect(isNavigationActive('student', journey, '/student/projects/8/tasks/21')).toBe(true)
    expect(isNavigationActive('student', journey, '/student/projects', { focus: 'journey' })).toBe(true)
    expect(isNavigationActive('student', journey, '/student/projects/8/materials')).toBe(true)
    expect(isNavigationActive('student', journey, '/student/projects/8/map')).toBe(true)
    expect(isNavigationActive('student', applications, '/student/public-applications', { projectId: 8 })).toBe(true)
    expect(isNavigationActive('student', applications, '/student/projects', { focus: 'apply' })).toBe(true)
    expect(isNavigationActive('student', projects, '/student/projects', { focus: 'journey' })).toBe(false)
    expect(isNavigationActive('student', projects, '/student/projects', { focus: 'materials' })).toBe(false)
    expect(isNavigationActive('student', projects, '/student/projects', { focus: 'apply' })).toBe(false)
    expect(isNavigationActive('platform_admin', settings, '/platform/settings')).toBe(true)
  })

  it('uses focus query destinations when no student project exists', () => {
    const student = primaryNavigation('student')
    const journey = student.find((item) => item.key === 'journey')!
    expect(isNavigationActive('student', journey, '/student/projects', { focus: 'journey' })).toBe(true)
    expect(isNavigationActive('student', journey, '/student/projects', { focus: 'materials' })).toBe(true)
  })

  it('uses the same active project fallback as the project page when no primary project is assigned', () => {
    expect(resolveStudentNavigationProject(null, [
      { id: 4, is_archived: true, deleted_at: null },
      { id: 8, is_primary: false, is_archived: false, deleted_at: null },
      { id: 9, is_primary: true, is_archived: false, deleted_at: null },
    ])).toBe(9)
    expect(resolveStudentNavigationProject(null, [
      { id: 8, is_primary: false, is_archived: false, deleted_at: null },
    ])).toBe(8)
    expect(resolveStudentNavigationProject(9, [
      { id: 9, is_primary: true, is_archived: false, deleted_at: null },
    ], 12)).toBe(12)
    expect(resolveStudentNavigationProject(null, [])).toBeNull()
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
    expect(utilityNavigation('teacher', null).map((item) => item.to)).toEqual(['/teacher/members', '/teacher/notifications'])
  })
})
