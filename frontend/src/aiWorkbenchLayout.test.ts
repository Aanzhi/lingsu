import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const page = read('./pages/shared/AICenter.vue')
const tabs = read('./components/ai/AIModeTabs.vue')
const composer = read('./components/ai/AIWorkbenchComposer.vue')
const workbenchModel = read('./stores/aiWorkbenchModel.ts')

const cssRuleBody = (source: string, selector: string) => {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return source.match(new RegExp(`[^{}]*${escapedSelector}[^{}]*\\{([^{}]*)\\}`))?.[1] ?? ''
}

describe('simple AI workbench layout', () => {
  it('uses one shared mode selector for opening, research and defense', () => {
    expect(page).toContain('ai-workbench-mode-region')
    expect(page).toContain('ai-active-chat')
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
    expect(page).toContain('AIToolPicker')
    expect(page).not.toContain('AIResearchWizard')
  })

  it('keeps the page shell visible while resources load and focuses the composer on direct input', () => {
    expect(page).toContain('ai-workbench-skeleton')
    expect(page).toContain('aria-label="正在准备灵思 AI"')
    expect(composer).toContain('写下你的问题或研究想法')
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

  it('keeps the current context primary and history as a secondary header action', () => {
    expect(page).toContain('class="ai-workbench-header__actions"')
    expect(page).toContain('class="ai-workbench-context-pill"')
    expect(page).toContain('class="text-button ai-workbench-history-button"')
    expect(page.indexOf('class="ai-workbench-header__actions"')).toBeLessThan(page.indexOf('class="ai-workbench-context-pill"'))
    expect(page.indexOf('class="ai-workbench-context-pill"')).toBeLessThan(page.indexOf('class="text-button ai-workbench-history-button"'))
    expect(cssRuleBody(page, '.ai-workbench-header__actions')).toContain('align-items: center;')
    expect(cssRuleBody(page, '.ai-workbench-header__actions')).toContain('gap: 14px;')
    expect(cssRuleBody(page, '.ai-workbench-context-pill')).toContain('flex: 0 1 360px;')
  })

  it('places the shared mode selector before one conversation stage and composer', () => {
    expect(page.indexOf('ai-workbench-mode-region')).toBeLessThan(page.indexOf('ai-workbench-composer-dock'))
    expect(page.indexOf('ai-conversation-stream')).toBeLessThan(page.indexOf('ai-workbench-composer-dock'))
    expect(page).toContain('ai-active-chat')
    expect(page.match(/<AIWorkbenchComposer/g) ?? []).toHaveLength(1)
  })

  it('keeps the new state focused without duplicating the Skill picker', () => {
    expect(page).toContain('ai-workbench-empty')
    expect(page).not.toContain('ai-workbench-paths')
    expect(page).not.toContain('workbenchPaths')
    expect(page).not.toContain('selectWorkPath')
    expect(page).not.toContain('ai-workbench-prompts')
    expect(page).not.toContain('ai-agent-rail')
    expect(page).not.toContain('更多能力')
  })

  it('matches the reference main-area composition for the new opening state', () => {
    expect(page).toContain('ai-workbench-main')
    expect(page).toContain('ai-workbench-empty')
    expect(page).toContain('ai-workbench-composer-dock--new')
    expect(page).toContain('ai-workbench-content--opening')
    expect(workbenchModel).toContain('整理观察，形成研究问题')
    expect(workbenchModel).toContain('推进当前项目的研究任务')
    expect(workbenchModel).toContain('整理摘要和答辩表达')
  })

  it('keeps material citation available to other shared consumers but hides it for students', () => {
    expect(composer).toContain('showMaterialCitation')
    expect(composer).toContain('class="composer-tool-button selected-material"')
    expect(page).toContain(':show-material-citation="false"')
    expect(page).not.toContain('@cite-material="citeProjectMaterial"')
    expect(composer).toContain('showMeta')
  })

  it('keeps Composer actions in a stable tools-hint-send row', () => {
    expect(composer).toContain('class="ai-workbench-composer__tools"')
    expect(composer).toContain('class="ai-workbench-composer__action"')
    expect(composer.indexOf('class="ai-workbench-composer__footer"')).toBeLessThan(composer.indexOf('class="ai-workbench-composer__tools"'))
    expect(composer.indexOf('class="ai-workbench-composer__tools"')).toBeLessThan(composer.indexOf('class="composer-hint"'))
    expect(composer.indexOf('class="composer-hint"')).toBeLessThan(composer.indexOf('class="ai-workbench-composer__action"'))
    expect(cssRuleBody(composer, '.ai-workbench-composer__footer')).toContain('display: flex;')
    expect(cssRuleBody(composer, '.ai-workbench-composer__tools')).toContain('display: flex;')
    expect(cssRuleBody(composer, '.composer-hint')).toContain('flex: 1 1 auto;')
    expect(cssRuleBody(composer, '.composer-hint')).toContain('text-overflow: ellipsis;')
    expect(cssRuleBody(composer, '.composer-hint')).toContain('white-space: nowrap;')
    expect(cssRuleBody(composer, '.send-button')).toContain('width: 70px;')
  })

  it('supports the reference send button arrow without changing other composer consumers', () => {
    expect(composer).toContain('showSendIcon')
    expect(composer).toContain('ArrowRight')
    expect(page).toContain(':show-send-icon="true"')
  })

  it('uses the reference opening placeholder copy', () => {
    expect(composer).toContain("return '写下你的问题或研究想法...'")
  })

  it('keeps the reference treatment coherent and scoped to the new main area', () => {
    expect(page).toContain('.ai-workbench-main {')
    expect(page).toContain('background: var(--paper);')
    const newPageHintRule = cssRuleBody(page, '.ai-workbench-page--new :deep(.composer-hint)')
    expect(newPageHintRule).toContain('margin: 0;')
    expect(newPageHintRule).not.toContain('margin-left: auto;')
    expect(newPageHintRule).not.toContain('margin-right: auto;')
    expect(page).toContain('.ai-workbench-page--active .ai-workbench-composer-dock')
  })

  it('keeps the active conversation stream as the only scrolling region', () => {
    expect(page).toContain('ai-active-chat')
    expect(page).toContain('ai-conversation-stream')
    expect(page).toContain('overflow-y: auto')
    expect(page).toContain('position: sticky')
    expect(page).toContain('ai-workbench-page--active')
  })

  it('uses one content canvas with shared empty and composer surfaces', () => {
    expect(page).toContain('<div class="ai-workbench-canvas">')
    expect(page).toContain('class="ai-workbench-content"')
    expect(page).toContain('class="ai-workbench-empty"')
    expect(page).toContain('class="ai-workbench-composer-dock"')
    expect(page).toContain('ai-workbench-composer-dock--new')
  })

  it('reflows the workbench when the shell leaves a narrow content column', () => {
    expect(page).toContain('@media (max-width: 1024px)')
    expect(page).toContain('.ai-workbench-page--new :deep(.ai-mode-tab small) { white-space: normal;')
    expect(page).toContain('.ai-workbench-page--new :deep(.ai-workbench-composer) { min-height: 140px;')
  })

  it('uses the shared project visual language instead of an AI-only landing treatment', () => {
    expect(page).toContain('.ai-workbench-main { background: var(--color-bg-canvas);')
    expect(page).toContain('border-radius: var(--radius-md);')
    expect(page).toContain('box-shadow: var(--shadow-soft);')
    expect(page).toContain('font-size: clamp(24px, 2.4vw, 30px);')
    expect(page).toContain('.ai-workbench-page--new :deep(.ai-workbench-composer) { min-height: 148px;')
    expect(page).not.toContain('--ai-radius-card: 22px')
    expect(page).not.toContain('clamp(44px, 5.6vw, 64px)')
    expect(page).not.toContain('border: 2px solid var(--moss-dark)')
  })

  it('keeps the guidance module visible for every new workbench mode at a smaller scale', () => {
    expect(page).toContain('<section v-else class="ai-workbench-empty" aria-label="开始对话">')
    expect(page).toContain('.ai-workbench-heading h1 { margin: 2px 0 7px;')
    expect(page).toContain('font-size: clamp(24px, 2.4vw, 30px);')
    expect(page).toContain('.ai-workbench-page--new :deep(.ai-mode-tab) { min-height: 68px;')
    expect(page).toContain('.ai-workbench-page--new :deep(.ai-workbench-composer) { min-height: 148px;')
    expect(page).not.toContain('v-else-if="workbenchMode === \'opening\'" class="ai-workbench-empty"')
  })

  it('uses one shared vertical grid so each workbench mode keeps the same spacing', () => {
    expect(page).toContain('.ai-workbench-content { display: grid; flex: 1 1 auto;')
    expect(page).toContain('grid-template-rows: auto minmax(260px, 1fr);')
    expect(page).not.toContain('.ai-workbench-content--opening { flex: 1 1 auto;')
  })

  it('reconnects a queued or streaming message after a conversation is restored', () => {
    expect(page).toContain('resumePendingMessage')
    expect(page).toContain("message.status === 'queued' || message.status === 'streaming'")
    expect(page).toContain('await streamAssistant(conversationId, pendingMessage.id')
  })
})
