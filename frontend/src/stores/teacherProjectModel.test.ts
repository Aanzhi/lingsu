import { describe, expect, it } from 'vitest'

import { projectRiskLabel, projectTaskSummary } from './teacherProjectModel'

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
})
