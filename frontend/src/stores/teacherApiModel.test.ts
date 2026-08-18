import { describe, expect, it } from 'vitest'

import { reviewValidation, type ReviewDecision } from './teacherApiModel'

describe('teacher review model', () => {
  it('requires executable feedback when returning a submission', () => {
    expect(reviewValidation('revision_required', '')).toContain('审核意见')
    expect(reviewValidation('revision_required', '请补充三组对照数据')).toBeNull()
    expect(reviewValidation('approved', '')).toBeNull()
  })

  it('accepts only the two workflow decisions at compile/runtime boundary', () => {
    const decisions: ReviewDecision[] = ['approved', 'revision_required']
    expect(decisions).toHaveLength(2)
  })
})
