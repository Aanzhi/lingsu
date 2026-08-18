import { describe, expect, it } from 'vitest'

import { feedbackToneClass, feedbackTitle } from './feedbackModel'

describe('interaction feedback model', () => {
  it('maps feedback tones to stable semantic classes and titles', () => {
    expect(feedbackToneClass('success')).toBe('success')
    expect(feedbackToneClass('error')).toBe('error')
    expect(feedbackToneClass('info')).toBe('info')
    expect(feedbackTitle('success')).toBe('操作成功')
    expect(feedbackTitle('error')).toBe('需要处理')
  })
})
