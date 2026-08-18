import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = readFileSync(new URL('./lingsu-system.css', import.meta.url), 'utf8')

describe('teacher review metadata', () => {
  it('stacks author and submitted time rather than allowing the two values to collide', () => {
    expect(styles).toContain('.version-rail > strong { display: block;')
    expect(styles).toContain('.version-rail > small { display: block;')
  })

  it('keeps a short submission from creating a large empty reading surface', () => {
    expect(styles).toContain('.submission-paper { padding: 35px 42px; min-height: 0; }')
  })
})
