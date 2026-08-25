import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./components/JourneyTimeline.vue', import.meta.url), 'utf8')

describe('journey timeline layout', () => {
  it('allocates the desktop rail for the five research chapters', () => {
    expect(source).toContain('flex: 1 0 calc(100% / 5)')
    expect(source).not.toContain('calc(100% / 10)')
  })
})
