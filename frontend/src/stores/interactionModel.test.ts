import { describe, expect, it } from 'vitest'

import { operationSuccess, reviewCompletionAction } from './interactionModel'

describe('operation feedback copy', () => {
  it('explains the result and next step for high-impact actions', () => {
    expect(operationSuccess('claim')).toContain('项目已认领')
    expect(operationSuccess('review_approved')).toContain('下一任务已解锁')
    expect(operationSuccess('review_returned')).toContain('修订意见已发送')
    expect(operationSuccess('school_disabled')).toContain('历史只读')
    expect(operationSuccess('competition_published')).toContain('已发布')
  })

  it('keeps a completed review visible until the teacher deliberately returns to the queue', () => {
    expect(reviewCompletionAction()).toBe('返回审核队列')
  })
})
