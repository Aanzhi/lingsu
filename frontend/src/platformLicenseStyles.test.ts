import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = readFileSync(new URL('./styles/workspace.css', import.meta.url), 'utf8')

describe('platform license styles', () => {
  it('keeps authorization switches inside the shared moss-green system', () => {
    expect(styles).toContain('.license-table .el-switch.is-checked .el-switch__core')
    expect(styles).toContain('background: var(--moss) !important')
  })
})
