import { describe, expect, it } from 'vitest'
import { routeRecords } from '../router'

import {
  PAGE_CONTRACTS,
  consoleSectionLocations,
  platformSchoolRoute,
  studentProjectRoute,
  studentProjectsLocation,
  studentTaskRoute,
  teacherMembersRoute,
  teacherReviewRoute,
  pageDescription,
} from './pageContracts'
import { navigationChildren, primaryNavigation, utilityNavigation } from './navigationRegistry'

describe('page contracts and route locations', () => {
  it('covers the canonical public and workspace pages with operational copy', () => {
    const keys = PAGE_CONTRACTS.map((contract) => contract.key)

    expect(keys).toEqual(expect.arrayContaining([
      'public.entry',
      'public.login',
      'public.register',
      'public.platform-login',
      'student.home',
      'student.projects',
      'student.project.map',
      'student.project.task',
      'student.project.report',
      'student.ai',
      'student.notifications',
      'student.invitations',
      'student.public-applications',
      'teacher.home',
      'teacher.pool',
      'teacher.projects',
      'teacher.ai',
      'teacher.reviews',
      'teacher.members',
      'teacher.notifications',
      'platform.home',
      'platform.schools',
      'platform.school',
      'platform.ai-agents',
      'platform.competitions',
      'platform.announcements',
      'platform.cases',
      'platform.settings',
      'console.overview',
      'console.checks',
      'console.services',
      'console.logs',
    ]))

    expect(PAGE_CONTRACTS.every((contract) => contract.title.trim() && pageDescription(contract.key).trim())).toBe(true)
    expect(PAGE_CONTRACTS.some((contract) => pageDescription(contract.key).includes('研究不是一次完成的答案'))).toBe(false)
  })

  it('registers every production page and navigation destination once', () => {
    const registeredPaths = routeRecords.flatMap((record) => record.children
      ? record.children.filter((child) => !child.redirect).map((child) => `${record.path}/${child.path}`.replace(/\/+/g, '/'))
      : record.redirect ? [] : [record.path])
    const contractPaths = PAGE_CONTRACTS.filter((contract) => contract.role !== 'console').map((contract) => contract.path)
    expect(new Set(PAGE_CONTRACTS.map((contract) => contract.key)).size).toBe(PAGE_CONTRACTS.length)
    for (const path of contractPaths) expect(registeredPaths).toContain(path)

    const navigationPaths = [
      ...primaryNavigation('student'), ...primaryNavigation('teacher'), ...primaryNavigation('platform_admin'),
    ].flatMap((item) => [item.to, ...navigationChildren('student', item), ...navigationChildren('teacher', item), ...navigationChildren('platform_admin', item)])
      .map((item) => typeof item === 'string' ? item : item.to)
      .map((path) => path.split('?')[0])
    for (const path of navigationPaths) expect(registeredPaths).toContain(path)
    for (const role of ['teacher', 'platform_admin'] as const) {
      for (const item of utilityNavigation(role, null)) expect(registeredPaths).toContain(item.to)
    }
  })

  it('builds canonical project and contextual locations without nested duplicates', () => {
    expect(studentProjectRoute(8)).toBe('/student/projects/8/map')
    expect(studentProjectRoute(8, 'map')).toBe('/student/projects/8/map')
    expect(studentProjectRoute(8, 'materials')).toBe('/student/projects/8/map')
    expect(studentProjectRoute(8, 'report')).toBe('/student/projects/8/report')
    expect(studentTaskRoute(8, 21)).toBe('/student/projects/8/tasks/21')
    expect(studentProjectsLocation('journey')).toEqual({ path: '/student/projects', query: { focus: 'journey' } })
    expect(studentProjectsLocation('materials')).toEqual({ path: '/student/projects', query: { focus: 'journey' } })
    expect(studentProjectsLocation('apply')).toEqual({ path: '/student/projects', query: { focus: 'apply' } })
  })

  it('keeps teacher and platform detail context in query parameters', () => {
    expect(teacherReviewRoute(undefined, 8)).toEqual({ path: '/teacher/reviews', query: { projectId: '8' } })
    expect(teacherReviewRoute(31, 8)).toEqual({ path: '/teacher/reviews/31', query: { projectId: '8' } })
    expect(teacherMembersRoute(8)).toEqual({ path: '/teacher/members', query: { projectId: '8' } })
    expect(platformSchoolRoute(4)).toBe('/platform/schools/4')
  })

  it('keeps the independent console on its four supported hash sections', () => {
    expect(consoleSectionLocations()).toEqual(['#overview', '#checks', '#services', '#logs'])
  })
})
