import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = [
  'styles/tokens.css',
  'styles/foundations.css',
  'styles/workspace.css',
  'styles/element-plus.css',
  'styles/responsive.css',
].map((file) => readFileSync(new URL(`./${file}`, import.meta.url), 'utf8')).join('\n')
const researchWizardStyles = readFileSync(new URL('./components/ai/AIResearchWizard.vue', import.meta.url), 'utf8')

describe('global SaaS design system', () => {
  it('exposes semantic UI tokens and maps them into Element Plus', () => {
    for (const token of [
      '--color-bg-canvas', '--color-bg-surface', '--color-border-default',
      '--color-text-primary', '--color-text-secondary', '--color-primary',
      '--color-text-muted', '--color-success', '--color-warning', '--color-danger', '--color-info',
      '--color-focus-ring', '--el-color-primary', '--el-border-radius-base',
    ]) expect(styles).toContain(token)
  })

  it('keeps the primary action solid and respects reduced motion', () => {
    expect(styles).toContain('.primary-button { color: #fff; border: 1px solid var(--moss); background: var(--moss);')
    expect(styles).toContain('@media (prefers-reduced-motion: reduce)')
  })

  it('uses plain, reusable surfaces instead of decorative texture or gradient treatments', () => {
    expect(styles).toContain('--sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;')
    expect(styles).toContain('--serif: var(--sans);')
    expect(styles).toContain('--color-bg-canvas: var(--ivory);')
    expect(styles).toContain('--moss: #4f6f59;')
    expect(styles).toContain('body { background: var(--color-bg-canvas);')
    expect(styles).not.toContain('body { background: radial-gradient')
    expect(styles).toContain('.paper-card { background: var(--color-bg-surface);')
    expect(styles).toContain('.public-auth-page {')
    expect(styles).toContain('.auth-page-header {')
    expect(styles).toContain('.auth-two-col {')
    expect(styles).not.toContain('.auth-story { padding: 70px 9vw;')
    expect(styles).not.toContain('.auth-story--hero {')
    expect(researchWizardStyles).toContain('.research-workbench { margin: 0 26px 24px;')
  })

  it('gives Element Plus inputs, tables and dialogs the same shared interaction treatment', () => {
    expect(styles).toContain('.el-input__wrapper, .el-textarea__inner, .el-select__wrapper')
    expect(styles).toContain('.el-table th.el-table__cell')
    expect(styles).toContain('.el-dialog__header')
  })

  it('exposes one semantic surface, spacing and control contract', () => {
    for (const token of [
      '--surface-page', '--surface-card', '--surface-float',
      '--space-page', '--space-section', '--space-card', '--control-height',
      '--radius-sm', '--radius-md', '--color-primary-strong',
    ]) expect(styles).toContain(token)
    expect(styles).toContain('--line-strong: var(--line-dark);')
  })

  it('provides one shared workspace page shell and primary action treatment', () => {
    expect(styles).toContain('.workspace-page')
    expect(styles).toContain('.workspace-page__header')
    expect(styles).toContain('.workspace-page__primary-action')
  })
})
