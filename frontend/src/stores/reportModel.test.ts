import { describe, expect, it } from 'vitest'

import { exportStatusLabel, shouldPollExport } from './reportModel'

describe('report export model', () => {
  it('polls only unfinished exports and exposes honest status labels', () => {
    expect(shouldPollExport('queued')).toBe(true)
    expect(shouldPollExport('processing')).toBe(true)
    expect(shouldPollExport('completed')).toBe(false)
    expect(shouldPollExport('failed')).toBe(false)
    expect(exportStatusLabel('failed')).toBe('生成失败')
  })
})
