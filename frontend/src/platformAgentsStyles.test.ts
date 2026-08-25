import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./pages/platform/PlatformAIAgents.vue', import.meta.url), 'utf8')

describe('platform AI agent catalogue presentation', () => {
  it('keeps the desktop catalogue compact and the mobile catalogue readable', () => {
    expect(source).toContain('.agent-admin-panel { padding: 26px;')
    expect(source).toContain('.demo-agent-table table { min-width: 850px; }')
    expect(source).not.toContain('.agent-table .el-table__cell')
    expect(source).not.toContain('.agent-table-wrap')
    expect(source).toContain('.agent-card-list--mobile')
  })
})
