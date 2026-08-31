import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const source = read('./pages/shared/AICenter.vue')
const modeTabs = read('./components/ai/AIModeTabs.vue')
const composer = read('./components/ai/AIWorkbenchComposer.vue')
const draftActions = read('./components/ai/AIDraftActions.vue')

describe('AI workbench information architecture', () => {
  it('keeps the student page as one Conversation Studio workbench', () => {
    expect(source).toContain('class="page ai-center-page ai-workbench-frame ai-workbench-main"')
    expect(source).toContain('class="ai-workbench-mode-region"')
    expect(source).toContain('class="ai-workbench-active-toolbar"')
    expect(source).toContain('class="ai-active-chat"')
    expect(source).toContain('isConversationStarted')
    expect(source).toContain('<AIModeTabs')
    expect(source).toContain('<AIWorkbenchComposer')
    expect(source).toContain('<AIResultCard')
    expect(source).toContain('AIConversationHistory')
    expect(source).not.toContain('AIContextDrawer')
    expect(source).toContain('AIToolPicker')
    expect(source).not.toContain('AIResearchWizard')
    expect(source).not.toContain('class="ai-workbench-agent-region"')
    expect(source).not.toContain('ai-assistant-bar')
    expect(source).not.toContain('ai-workbench-new-state')
    expect(source).not.toContain('ai-workbench-active-state')
  })

  it('keeps the new conversation canvas focused on chat and the composer', () => {
    expect(source).not.toContain('starterPrompts(workbenchMode.value)')
    expect(source).not.toContain('modeStarterPrompts')
    expect(source).not.toContain('class="ai-welcome"')
    expect(source).not.toContain('class="ai-starter-prompt"')
    expect(source).toContain('class="ai-conversation-stream"')
    expect(source).toContain('class="ai-workbench-composer-dock"')
    expect(source).not.toContain('class="ai-recent-conversations"')
    expect(source).not.toContain('recentConversations')
    expect(source).toContain('class="ai-workbench-header__actions"')
    expect(source).toContain('历史会话')
  })

  it('uses the empty state to explain the current workflow without canned prompt actions', () => {
    expect(source).toContain('emptyWorkflow')
    expect(source).toContain('type EmptyWorkflowField')
    expect(source).toContain('class="ai-workbench-empty__guide"')
    expect(source).toContain('v-for="step in emptyWorkflow"')
    expect(source).toContain('fields:')
    expect(source).toContain('startGuideStep(step)')
    expect(source).toContain('activeGuideStep')
    expect(source).toContain('guideDialogOpen')
    expect(source).toContain('guideDialogValues')
    expect(source).toContain('guideDialogComplete')
    expect(source).toContain('guideDialogPrompt')
    expect(source).toContain('generateGuideStep')
    expect(source).toContain('void sendMessage(content, { includeUserMessage: true })')
    expect(source).toContain('v-model="guideDialogValues[field.key]"')
    expect(source).toContain(':aria-required="field.required"')
    expect(source).toContain('不会自动发送')
    expect(source).not.toContain('starter:')
    expect(source).not.toContain('guideDialogDraft')
    expect(source).not.toContain('@click="sendMessage')
    expect(source).not.toContain('starterPrompts(workbenchMode.value)')
  })

  it('keeps the conversation stage and existing recovery/result contracts', () => {
    expect(source).toContain('ai-active-chat')
    expect(source).toContain('AIResultCard')
    expect(source).toContain('resumePendingMessage')
    expect(source).toContain("message.status === 'failed'")
  })

  it('gives an active conversation the full chat canvas', () => {
    expect(source).toContain('class="ai-workbench-active-toolbar"')
    expect(source).toContain('<template v-if="isNewConversation">')
    expect(source).toContain('.ai-active-chat')
    expect(source).toContain('.ai-workbench-page--active .ai-workbench-composer-dock')
  })

  it('keeps the new state focused on mode, read-only context and one composer', () => {
    expect(source).toContain('class="ai-workbench-content"')
    expect(source).toContain('workbenchDescription')
    expect(source).toContain('v-if="loading || projectsLoading || conversationLoading"')
    expect(source).not.toContain('class="ai-empty-state"')
    expect(source).not.toContain('class="ai-project-selector"')
  })

  it('renders the composer inside the active chat grid so only messages scroll', () => {
    expect(source).toContain('class="ai-active-chat"')
    expect(source).toContain('class="ai-active-chat__stream"')
    expect(source).toContain('class="ai-active-chat__composer"')
    expect(source).toContain('class="ai-active-chat__notices"')
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

  it('treats the three workbench tabs as primary Agents and exposes a Skill picker from the composer', () => {
    expect(modeTabs).toContain('data-agent-kind="primary"')
    expect(modeTabs).toContain('aria-label="选择主 Agent"')
    expect(source).toContain("import AIToolPicker from '../../components/ai/AIToolPicker.vue'")
    expect(source).toContain('skillPickerOpen')
    expect(source).toContain('@add-skill="openSkillPicker"')
    expect(source).toContain('<AIToolPicker')
    expect(composer).toContain('showSkillPicker')
    expect(composer).toContain('＋ 添加技能')
    expect(composer).toContain("(event: 'add-skill')")
  })

  it('uses one direct composer without exposing Agent or pre-chat form fields', () => {
    expect(source.match(/<AIWorkbenchComposer/g) ?? []).toHaveLength(1)
    expect(source).not.toContain('agent-name="currentAgent?.name"')
    expect(source).not.toContain('当前 Agent')
    expect(source).toContain(':show-meta="false"')
    expect(composer).toContain('写下你的问题或研究想法')
    expect(source).toContain(':show-material-citation="false"')
    expect(source).not.toContain('selected-material-ids="selectedMaterialIds"')
    expect(source).not.toContain('补充信息（可选）')
    expect(source).not.toContain('研究对象与场景')
    expect(source).not.toContain('你想弄清楚哪个方向')
  })

  it('keeps the new state compact and binds the working project read-only', () => {
    expect(source).not.toContain('ai-empty-state')
    expect(source).not.toContain('ai-welcome')
    expect(source).not.toContain('ai-starter-prompts')
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

  it('keeps the three workbench modes as the only empty-state entry point', () => {
    expect(source).toContain('class="ai-workbench-empty"')
    expect(source).not.toContain('class="ai-workbench-paths"')
    expect(source).not.toContain('workbenchPaths')
    expect(source).not.toContain('@click="selectWorkPath(path)"')
    expect(source).not.toContain('选择工作路径')
    expect(source).not.toContain('conversationIntents')
    expect(source).not.toContain('useConversationIntent')
    expect(source).toContain(':show-skill-picker="true"')
    expect(source).toContain('class="ai-active-toolbar__mode"')
    expect(source).not.toContain('data-result-actions="确认创建项目 / 保存为材料"')
  })

  it('renders an assistant result once as the editable confirmation surface', () => {
    expect(source).toContain('v-if="!hasResult(message)"')
    expect(source).toContain('<AIResultCard')
  })

  it('keeps a route-selected Skill while the Skill resource is loading', () => {
    expect(source).toContain('if (agentsLoading.value) return')
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

  it('keeps history available across new and active conversation states', () => {
    expect(source).toContain('历史会话')
    expect(source).toContain('historyOpen')
    expect(source).toContain('isNewConversation')
    expect(source).toContain('historyConversations')
    expect(source).toContain('conversationId')
    expect(source).toContain('openConversationFromHistory')
    expect(source).toContain('v-if="historyOpen"')
    expect(source).toContain('<button class="text-button" type="button" :disabled="sending" @click="startNewConversation">新建对话</button>')
    expect(source).not.toContain('查看上下文')
    expect(source).not.toContain('更多能力')
    expect(source).not.toContain('选择 AI 工具')
    expect(source).not.toContain('研究问题步骤')
    expect(source).not.toContain('researchStep')
    expect(source).not.toContain('selectedMaterialIds')
  })

  it('keeps history filtering to the three independent workbench modes', () => {
    expect(source).toContain('historyModeFilter = ref<AIWorkspaceMode>(routeModeValue())')
    expect(source).toContain('historyModeFilter.value = mode')
    expect(source).not.toContain("historyModeFilter.value === 'all'")
  })

  it('keeps paper type compatibility without blocking the simple chat surface', () => {
    expect(source).toContain("import { PAPER_TYPES, type PaperType } from '../../stores/aiModel'")
    expect(source).toContain('function paperTypeForRequest()')
    expect(source).toContain('paper_type: paperTypeForRequest()')
    expect(source).not.toContain('const paperTypeRequired = computed')
    expect(source).not.toContain('论文类型（必选）')
    expect(source).not.toContain('paperTypeRequired.value && !paperType.value')
  })

  it('does not keep a redundant assistant banner or stretch the new state', () => {
    expect(source).not.toContain('ai-assistant-bar')
    expect(source).not.toContain('assistantName')
    expect(source).not.toContain('assistantDescription')
    expect(source).not.toContain('assistantStage')
    expect(source).toContain('.ai-workbench-page--new { height: calc(100vh - var(--topbar-height) - 104px); min-height: 0;')
  })

  it('connects history deletion to page state and the delete API', () => {
    expect(source).toContain('deleteAIConversation')
    expect(source).toContain('deletingConversationId')
    expect(source).toContain('conversationDeleteError')
    expect(source).toContain('@delete="void deleteConversation($event)"')
    expect(source).toContain('historyConversations.value = historyConversations.value.filter')
    expect(source).toContain('resetConversationSelection()')
  })

  it('uses a mode-specific description without exposing technical Agent names', () => {
    expect(source).toContain('workspaceModeDescription')
    expect(source).toContain('{{ workbenchDescription }}')
    expect(source).not.toContain('当前模式的 Agent')
    expect(source).not.toContain('当前 Agent')
  })
})
