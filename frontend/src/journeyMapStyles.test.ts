import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = readFileSync(new URL('./lingsu-system.css', import.meta.url), 'utf8')

describe('journey map stage header styles', () => {
  it('styles only the chapter-number badge, not the direct StatusTag span', () => {
    expect(styles).toContain('.journey-stage > header > span:first-child')
    expect(styles).not.toContain('.journey-stage > header > span { width: 38px;')
  })

  it('uses a dedicated third column for status without narrowing the chapter title', () => {
    expect(styles).toContain('.journey-stage > header { padding: 18px 24px; border-right: 0; border-bottom: 1px dashed var(--line-dark); display: grid; grid-template-columns: 42px minmax(0, 1fr) auto;')
    expect(styles).toContain('.journey-stage > header .status-tag { grid-column: 3; grid-row: 1; justify-self: end;')
  })

  it('uses one shared chapter header rather than a narrow side column beside each task', () => {
    expect(styles).toContain('.journey-stage { display: block;')
    expect(styles).toContain('.journey-stage > header { padding: 18px 24px; border-right: 0; border-bottom: 1px dashed var(--line-dark); display: grid; grid-template-columns: 42px minmax(0, 1fr) auto;')
  })
})
