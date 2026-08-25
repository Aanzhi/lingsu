import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = ['foundations.css', 'workspace.css', 'responsive.css']
  .map((file) => readFileSync(new URL(`./styles/${file}`, import.meta.url), 'utf8'))
  .join('\n')

describe('teacher project pool styles', () => {
  it('keeps project type as a readable Chinese-friendly metadata pill', () => {
    expect(styles).toContain('.pool-card header > span:last-child')
    expect(styles).toContain('text-transform: none')
  })

  it('keeps title, problem and plan rhythm compact inside a pool card', () => {
    expect(styles).toContain('.pool-card h2, .guided-card h2 { margin: 14px 0 6px;')
    expect(styles).toContain('.pool-plan { min-height: 72px;')
  })
})
