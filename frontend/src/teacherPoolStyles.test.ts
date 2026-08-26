import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = ['foundations.css', 'workspace.css', 'responsive.css']
  .map((file) => readFileSync(new URL(`./styles/${file}`, import.meta.url), 'utf8'))
  .join('\n')

describe('teacher project pool styles', () => {
  it('keeps project type as a readable Chinese-friendly metadata pill', () => {
    expect(styles).toContain('.project-card__eyebrow')
    expect(styles).toContain('font-size: 11px')
  })

  it('keeps title, problem and plan rhythm compact inside a pool card', () => {
    expect(styles).toContain('.project-card__summary')
    expect(styles).toContain('.project-card__detail')
  })
})
