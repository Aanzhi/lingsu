import { describe, expect, it } from 'vitest'

import { reviewAIProvenance, reviewValidation, type ReviewDecision } from './teacherApiModel'

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

  it('makes AI origin and verification items reviewable without treating them as evidence', () => {
    expect(reviewAIProvenance({
      source_summary: { ai_log_id: 18, agent_key: 'proposal-plan', purpose: '实施方案', paper_type: null, created_at: '2026-08-20T10:00:00Z' },
      verification_summary: { total: 1, items: [{ item: '核对样本量', status: 'needs_verification', guidance: '查看原始记录' }] },
    })).toEqual({
      source: 'AI 生成记录 #18 · 实施方案',
      items: [{ item: '核对样本量', guidance: '查看原始记录' }],
    })
  })
})
