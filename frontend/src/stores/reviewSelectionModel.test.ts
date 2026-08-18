import { describe, expect, it } from 'vitest'

import { selectReviewById } from './reviewSelectionModel'

describe('review selection', () => {
  it('does not substitute another submission after the current submission has been reviewed', () => {
    const reviews = [{ id: 4, material_title: '观察记录' }, { id: 5, material_title: '访谈纪要' }]

    expect(selectReviewById(reviews, 3)).toBeUndefined()
    expect(selectReviewById(reviews, 4)).toEqual(reviews[0])
  })
})
