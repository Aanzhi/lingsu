import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const page = read('./pages/shared/AICenter.vue')
const tabs = read('./components/ai/AIModeTabs.vue')
const picker = read('./components/ai/AIToolPicker.vue')
const composer = read('./components/ai/AIWorkbenchComposer.vue')

describe('action-first AI workbench layout', () => {
  it('uses a shared mode and action rail for opening, research and defense', () => {
    expect(page).toContain('ai-workbench-mode-region')
    expect(tabs).toContain('data-agent-rail')
    expect(tabs).toContain('查看前面的 Agent')
    expect(tabs).toContain('查看后面的 Agent')
    expect(tabs).toContain('更多能力')
    expect(tabs).toContain('开题')
    expect(tabs).toContain('研究')
    expect(tabs).toContain('成果表达')
  })

  it('mounts the agent picker as an overlay rather than an absolute child menu', () => {
    expect(picker).toContain('<Teleport')
    expect(picker).toContain('agent-picker-overlay')
    expect(picker).not.toContain('.agent-picker-drawer { position: absolute')
    expect(picker).not.toContain('overflow-y: auto')
  })

  it('mounts history, context and the backdrop at the document layer', () => {
    expect(page).toContain('<Teleport to="body">')
    expect(read('./components/ai/AIConversationHistory.vue')).toContain('<Teleport to="body">')
    expect(read('./components/ai/AIContextDrawer.vue')).toContain('<Teleport to="body">')
  })

  it('keeps direct-input language and explicit context permissions', () => {
    expect(page).toContain('直接输入你的研究目标')
    expect(page).not.toContain('填写后可让 AI 工具更准确')
    expect(composer).toContain('不读取项目材料')
    expect(composer).toContain('当前 Agent')
  })

  it('keeps an empty workbench focused on the next action', () => {
    const sessionHeader = 'v-if="hasConversationMessages" class="ai-session-bar"'
    expect(page).toContain('ai-workbench-context-strip')
    expect(page).toContain(sessionHeader)
    expect(page).toContain('ai-empty-state__prompt')
    expect(page).not.toContain('ai-workbench-agent-note')
    expect(page).not.toContain('margin: clamp(46px, 10vh, 104px) auto 0')
    expect(page).not.toContain('margin: auto auto 4px')
  })

  it('uses one compact mode control before the agent action rail', () => {
    expect(tabs).toContain('ai-mode-tabs__row--segmented')
    expect(tabs).toContain('data-agent-rail')
    expect(page.indexOf('ai-workbench-mode-region')).toBeLessThan(page.indexOf('ai-workbench-context-strip'))
    expect(page.indexOf('ai-workbench-context-strip')).toBeLessThan(page.indexOf('ai-workbench-composer-host'))
  })

  it('keeps material citation available for project-based consumers', () => {
    expect(composer).toContain("props.canCiteMaterials ?? props.mode !== 'opening'")
    expect(composer).toContain('class="composer-tool-button selected-material"')
  })
})
