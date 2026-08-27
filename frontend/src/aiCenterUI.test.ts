import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const source = read('./pages/shared/AICenter.vue')
const modeTabs = read('./components/ai/AIModeTabs.vue')
const composer = read('./components/ai/AIWorkbenchComposer.vue')
const draftActions = read('./components/ai/AIDraftActions.vue')

describe('AI workbench information architecture', () => {
  it('keeps the student page as one Conversation Studio workbench', () => {
    expect(source).toContain('class="page ai-center-page ai-workbench-frame"')
    expect(source).toContain('class="ai-workbench-mode-region"')
    expect(source).toContain('class="ai-conversation-stage"')
    expect(source).toContain('class="ai-assistant-bar"')
    expect(source).toContain('isConversationStarted')
    expect(source).toContain('<AIModeTabs')
    expect(source).toContain('<AIWorkbenchComposer')
    expect(source).toContain('<AIResultCard')
    expect(source).toContain('AIConversationHistory')
    expect(source).not.toContain('AIContextDrawer')
    expect(source).not.toContain('AIToolPicker')
    expect(source).not.toContain('AIResearchWizard')
    expect(source).not.toContain('class="ai-workbench-agent-region"')
    expect(source).not.toContain('ai-workbench-new-state')
    expect(source).not.toContain('ai-workbench-active-state')
    expect(source).not.toContain('class="ai-active-chat"')
  })

  it('renders the assistant identity and starter prompts in the new conversation canvas', () => {
    expect(source).toContain('starterPrompts(workbenchMode.value)')
    expect(source).toContain('currentAgent.value?.name')
    expect(source).toContain('<span class="ai-assistant-avatar" aria-hidden="true">灵思</span>')
    expect(source).toContain('class="ai-welcome"')
    expect(source).toContain('class="ai-starter-prompt"')
    expect(source).toContain('@click="void sendMessage(prompt)"')
  })

  it('keeps the conversation stage and existing recovery/result contracts', () => {
    expect(source).toContain('ai-conversation-stage')
    expect(source).toContain('AIResultCard')
    expect(source).toContain('resumePendingMessage')
    expect(source).toContain("message.status === 'failed'")
  })

  it('shows only the three student modes and hides the technical Agent rail', () => {
    expect(modeTabs).toContain('开题')
    expect(modeTabs).toContain('研究')
    expect(modeTabs).toContain('成果表达')
    expect(modeTabs).toContain('showAgentRail')
    expect(modeTabs).toContain('v-if="props.showAgentRail"')
    expect(source).toContain(':show-agent-rail="false"')
    expect(source).not.toContain('当前模式的 Agent')
    expect(source).not.toContain('show-more-agents')
  })

  it('uses one direct composer without exposing Agent or pre-chat form fields', () => {
    expect(source.match(/<AIWorkbenchComposer/g) ?? []).toHaveLength(1)
    expect(source).not.toContain('agent-name="currentAgent?.name"')
    expect(source).not.toContain('当前 Agent')
    expect(source).toContain(':show-meta="false"')
    expect(composer).toContain('写下你的观察或研究想法')
    expect(source).toContain(':show-material-citation="false"')
    expect(source).not.toContain('selected-material-ids="selectedMaterialIds"')
    expect(source).not.toContain('补充信息（可选）')
    expect(source).not.toContain('研究对象与场景')
    expect(source).not.toContain('你想弄清楚哪个方向')
  })

  it('keeps the new state compact and binds the working project read-only', () => {
    expect(source).not.toContain('ai-empty-state')
    expect(source).not.toContain('ai-new-conversation-body')
    expect(source).not.toContain('ai-project-selector')
    expect(source).not.toContain('当前项目选择')
    expect(source).not.toContain('student-ai-project')
    expect(source).not.toContain('请选择一个项目')
    expect(source).toContain('workspaceContextLabel')
  })

  it('keeps the new conversation hierarchy single-layered', () => {
    expect(source).not.toContain('ai-workbench-mode-heading')
    expect(source).not.toContain('modeDescription')
    expect(source).not.toContain('aiPageDescription')
    expect(source).not.toContain('围绕当前项目直接聊天，处理任务、材料和研究推进')
    expect(source).toContain(':show-mode-descriptions="true"')
    expect(source).not.toContain(':project-label="workspaceContextLabel"')
  })

  it('uses a compact result surface only for confirmed writes', () => {
    expect(source).toContain('AIResultCard')
    expect(source).toContain('createProjectFromOpening')
    expect(source).toContain('saveAIGenerationAsMaterial')
    expect(source).toContain('ensureConversation')
    expect(draftActions).toContain('保存为材料')
    expect(draftActions).toContain('用此报告创建项目')
    expect(source).not.toContain('自动保存到材料')
    expect(source).not.toContain('自动创建项目')
  })

  it('only exposes history from the new-conversation state', () => {
    expect(source).toContain('历史会话')
    expect(source).toContain('historyOpen')
    expect(source).toContain('isNewConversation')
    expect(source).toContain('<button v-if="isNewConversation"')
    expect(source).toContain('<button v-else class="text-button" type="button" :disabled="sending" @click="startNewConversation">新建对话</button>')
    expect(source).not.toContain('查看上下文')
    expect(source).not.toContain('更多能力')
    expect(source).not.toContain('选择 AI 工具')
    expect(source).not.toContain('研究问题步骤')
    expect(source).not.toContain('researchStep')
    expect(source).not.toContain('selectedMaterialIds')
  })

  it('keeps paper type compatibility without blocking the simple chat surface', () => {
    expect(source).toContain("import { PAPER_TYPES, type PaperType } from '../../stores/aiModel'")
    expect(source).toContain('function paperTypeForRequest()')
    expect(source).toContain('paper_type: paperTypeForRequest()')
    expect(source).not.toContain('const paperTypeRequired = computed')
    expect(source).not.toContain('论文类型（必选）')
    expect(source).not.toContain('paperTypeRequired.value && !paperType.value')
  })
})
