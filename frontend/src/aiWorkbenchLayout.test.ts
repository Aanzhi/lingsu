import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const page = read('./pages/shared/AICenter.vue')
const tabs = read('./components/ai/AIModeTabs.vue')
const composer = read('./components/ai/AIWorkbenchComposer.vue')

describe('simple AI workbench layout', () => {
  it('uses one shared mode selector for opening, research and defense', () => {
    expect(page).toContain('ai-workbench-mode-region')
    expect(page).not.toContain('ai-workbench-agent-region')
    expect(tabs).toContain('showAgentRail')
    expect(tabs).toContain('showModeDescriptions')
    expect(tabs).toContain('v-if="props.showModeDescriptions"')
    expect(tabs).toContain('开题')
    expect(tabs).toContain('研究')
    expect(tabs).toContain('成果表达')
  })

  it('keeps history behind the new-conversation state and removes other drawers', () => {
    expect(page).toContain('historyOpen')
    expect(page).toContain('isNewConversation')
    expect(page).not.toContain('contextOpen')
    expect(page).not.toContain('agentOpen')
    expect(page).toContain('AIConversationHistory')
    expect(page).not.toContain('AIContextDrawer')
    expect(page).not.toContain('AIToolPicker')
    expect(page).not.toContain('AIResearchWizard')
  })

  it('keeps the page shell visible while resources load and focuses the composer on direct input', () => {
    expect(page).toContain('ai-workbench-skeleton')
    expect(page).toContain('aria-label="正在准备灵思 AI"')
    expect(composer).toContain('写下你的观察或研究想法')
    expect(page).not.toContain('ai-empty-state')
    expect(page).not.toContain('ai-project-selector')
    expect(page).not.toContain('ai-workbench-context-strip')
    expect(page).not.toContain('先选择研究方式')
    expect(page).not.toContain('填写后可让 AI 工具更准确')
  })

  it('does not duplicate project context between the header and composer', () => {
    expect(page).not.toContain(':project-label="workspaceContextLabel"')
    expect(page).not.toContain('ai-workbench-mode-heading')
    expect(page).toContain('class="ai-workbench-context-pill"')
  })

  it('places the new-state mode selector before one composer and active chat before its composer', () => {
    expect(page.indexOf('ai-workbench-mode-region')).toBeLessThan(page.indexOf('ai-workbench-composer-host'))
    expect(page).toContain('ai-active-chat')
    expect(page).toContain('grid-template-rows: minmax(0, 1fr) auto')
    expect(page.match(/<AIWorkbenchComposer/g) ?? []).toHaveLength(1)
  })

  it('keeps material citation available to other shared consumers but hides it for students', () => {
    expect(composer).toContain('showMaterialCitation')
    expect(composer).toContain('class="composer-tool-button selected-material"')
    expect(page).toContain(':show-material-citation="false"')
    expect(page).not.toContain('@cite-material="citeProjectMaterial"')
    expect(composer).toContain('showMeta')
  })

  it('keeps the active conversation stream as the only scrolling region', () => {
    expect(page).toContain('ai-workbench-active-state')
    expect(page).toContain('ai-conversation-stream')
    expect(page).toContain('overflow-y: auto')
    expect(page).toContain('position: sticky')
    expect(page).toContain('ai-workbench-page--active')
  })

  it('reconnects a queued or streaming message after a conversation is restored', () => {
    expect(page).toContain('resumePendingMessage')
    expect(page).toContain("message.status === 'queued' || message.status === 'streaming'")
    expect(page).toContain('await streamAssistant(conversationId, pendingMessage.id')
  })
})
