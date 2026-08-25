import { describe, expect, it } from 'vitest'

import { projectRiskLabel, projectTaskSummary, teacherProjectListMeta } from './teacherProjectModel'
import type { Project } from '../api'

const task = (status: 'locked' | 'available' | 'pending_review' | 'revision_required' | 'approved' | 'completed') => ({
  id: 1, project: 1, stage_name: '开题', stage_order: 1, title: '任务', description: '', evidence_requirements: [], order: 1, status, xp_reward: 100, due_at: null,
})

describe('teacher project guidance model', () => {
  it('summarizes progress and risks without duplicating student detail', () => {
    expect(projectTaskSummary([task('completed'), task('revision_required'), task('locked')])).toEqual({ total: 3, approved: 1, needsReview: 1, percent: 33 })
    expect(projectRiskLabel([task('revision_required')], [])).toBe('有材料需要修订')
    expect(projectRiskLabel([task('pending_review')], [])).toBe('有材料等待审核')
    expect(projectRiskLabel([], [])).toBe('等待任务材料生成')
  })

  it('builds a compact project-list row without copying the project problem', () => {
    const project = {
      id: 8,
      title: '校园雨水观察',
      problem: '这段内容只应该出现在详情页',
      project_type: 'research',
      status: 'active',
      leader: 12,
      members: [
        { id: 1, account: 12, username: '林同学', role: 'leader' },
        { id: 2, account: 13, username: '周同学', role: 'member' },
      ],
      created_at: '2026-08-22T08:30:00Z',
    } as unknown as Project

    expect(teacherProjectListMeta(project)).toEqual({
      title: '校园雨水观察',
      typeLabel: '研究型',
      status: 'active',
      leaderName: '林同学',
      memberCount: 2,
      createdDate: '2026-08-22',
    })
    expect(teacherProjectListMeta(project)).not.toHaveProperty('problem')
  })
})
