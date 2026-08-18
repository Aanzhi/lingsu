import { describe, expect, it } from 'vitest'

import { reviewPageState } from './reviewPageState'

describe('review page state', () => {
  it('shows a completion state instead of a blank review desk after the submission leaves the queue', () => {
    expect(reviewPageState(undefined)).toBe('completed')
    expect(reviewPageState({ id: 4 })).toBe('reviewing')
  })
})
