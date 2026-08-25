import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const foundations = readFileSync(new URL('./styles/foundations.css', import.meta.url), 'utf8')
const responsive = readFileSync(new URL('./styles/responsive.css', import.meta.url), 'utf8')
const agents = readFileSync(new URL('./pages/platform/PlatformAIAgents.vue', import.meta.url), 'utf8')
const draftActions = readFileSync(new URL('./components/ai/AIDraftActions.vue', import.meta.url), 'utf8')
const consoleHtml = readFileSync(new URL('../../scripts/console.html', import.meta.url), 'utf8')

describe('方案 B shared primitives', () => {
  it('styles native filters, chips, lists and tables from one global contract', () => {
    expect(foundations).toContain('.input, .select { min-height:36px;')
    expect(foundations).toContain('.chip, .status { display:inline-flex;')
    expect(foundations).toContain('.table-wrap { overflow-x:auto; }')
    expect(foundations).toContain('.list-row {')
    expect(foundations).toContain('.row-title {')
    expect(foundations).toContain('.row-meta {')
    expect(foundations).toContain('.row-actions {')
    expect(foundations).toContain('table { width:100%; border-collapse:collapse;')
  })

  it('keeps the 1280px desktop baseline outside the compression breakpoint', () => {
    expect(responsive).toContain('@media (max-width: 1279px)')
    expect(responsive).not.toContain('@media (max-width: 1280px)')
  })

  it('registers the platform status component and removes stale table selectors', () => {
    expect(agents).toContain("import StatusTag from '../../components/StatusTag.vue'")
    expect(agents).not.toContain('.agent-table-wrap')
    expect(agents).not.toContain('.agent-table .el-table__cell')
  })

  it('owns AI draft button styles in the component that renders them', () => {
    expect(draftActions).toContain('.save-draft {')
  })

  it('keeps console hash targets below the sticky topbar and syncs active navigation', () => {
    expect(consoleHtml).toContain('scroll-margin-top:')
    expect(consoleHtml).toContain("window.addEventListener('hashchange'")
    expect(consoleHtml).toContain('syncConsoleNav()')
  })
})
