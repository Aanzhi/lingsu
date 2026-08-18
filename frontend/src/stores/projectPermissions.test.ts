import { describe, expect, it } from 'vitest'

import { taskPermission } from './projectPermissions'

describe('task permission mapping', () => {
  it('lets a team member keep an evidence draft but reserves formal submission for the leader', () => {
    expect(taskPermission({ isLeader: false, taskStatus: 'available', materialStatus: 'draft' })).toEqual({
      canDraft: true,
      canSubmit: false,
      reason: '请由项目负责人确认真实性并正式提交。',
    })
  })

  it('uses one explicit read-only reason for waiting and completed material', () => {
    expect(taskPermission({ isLeader: true, taskStatus: 'pending_review', materialStatus: 'submitted' })).toEqual({
      canDraft: false,
      canSubmit: false,
      reason: '材料正在等待教师审核。',
    })
    expect(taskPermission({ isLeader: true, taskStatus: 'completed', materialStatus: 'approved' })).toEqual({
      canDraft: false,
      canSubmit: false,
      reason: '材料已通过审核，已作为项目成果归档。',
    })
  })
})
