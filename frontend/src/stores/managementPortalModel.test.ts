import { describe, expect, it } from 'vitest'
import { managementFixture } from '../fixtures/managementFixtures'
import { agentTemplateRows, caseStatus, poolRows, reviewActions, schoolOverview } from './managementPortalModel'

describe('management portal model', () => {
  it('hides review actions for projects not guided by the current teacher', () => {
    expect(reviewActions({ primaryTeacherId: 11, currentTeacherId: 12 })).toEqual([])
    expect(reviewActions({ primaryTeacherId: 12, currentTeacherId: 12 })).toEqual(['approve', 'revision_required'])
  })

  it('shows platform case review only after student consent', () => {
    expect(caseStatus({ teacherInvite: true, studentConsent: false, platformReview: false })).toBe('waiting_student')
    expect(caseStatus({ teacherInvite: true, studentConsent: true, platformReview: false })).toBe('pending_platform')
    expect(caseStatus({ teacherInvite: true, studentConsent: true, platformReview: true })).toBe('published')
  })

  it('keeps unclaimed projects available while marking claimed projects read-only', () => {
    const rows = poolRows(managementFixture.poolProjects)
    expect(rows.find((row) => row.id === 501)?.claimable).toBe(true)
    expect(rows.find((row) => row.id === 502)?.claimable).toBe(false)
  })

  it('summarizes school authorization separately from activity', () => {
    expect(schoolOverview(managementFixture.schools)).toMatchObject({ activeSchools: 1, totalProjects: 19, needsAttention: 1 })
  })

  it('exposes agent template status and management grouping', () => {
    expect(agentTemplateRows(managementFixture.agents)).toEqual([
      { key: 'opening-topic', name: '研究问题助手', category: '开题', status: 'active' },
      { key: 'defense-prep', name: '成果表达问答准备', category: '成果表达', status: 'inactive' },
    ])
  })
})
