import { describe, expect, it } from 'vitest'

import { reviewPageState } from './reviewPageState'

describe('review page state', () => {
  it('distinguishes a completed submission from an invalid review URL', () => {
    expect(reviewPageState(undefined)).toBe('missing')
    expect(reviewPageState(undefined, true)).toBe('completed')
    expect(reviewPageState({ id: 4 })).toBe('reviewing')
  })
})
