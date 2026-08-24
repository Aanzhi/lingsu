import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const taskPage = readFileSync(new URL('./pages/student/StudentTask.vue', import.meta.url), 'utf8')
const projectPage = readFileSync(new URL('./pages/student/StudentProject.vue', import.meta.url), 'utf8')
const aiPage = readFileSync(new URL('./pages/shared/AICenter.vue', import.meta.url), 'utf8')
const aiHistory = readFileSync(new URL('./components/ai/AIConversationHistory.vue', import.meta.url), 'utf8')
const aiTools = readFileSync(new URL('./components/ai/AIToolPicker.vue', import.meta.url), 'utf8')
const aiWizard = readFileSync(new URL('./components/ai/AIResearchWizard.vue', import.meta.url), 'utf8')

describe('student AI center entries', () => {
  it('removes the retired material assistant in favor of task-scoped AI center links', () => {
    expect(taskPage).not.toContain('MaterialAIAssistant')
    expect(taskPage).not.toContain('task-ai-quick')
    expect(taskPage).toContain('task-ai-options')
    expect(taskPage).toContain('aiQuickEntryLocation(projectId, taskId')
  })

  it('routes material consistency checks to the new proposal-consistency agent', () => {
    expect(projectPage).not.toContain('ConsistencyCheckCard')
    expect(projectPage).toContain("agent: 'proposal-consistency'")
    expect(projectPage).toContain("workflow: 'proposal_consistency'")
  })

  it('requires an explicit target material and exposes conversation rename in the MVP AI workflow', () => {
    expect(aiPage).toContain('targetMaterialId')
    expect(aiPage).toContain('保存到指定材料')
    expect(aiPage).toContain('重命名对话')
    expect(aiPage).toContain('updateAIConversation')
  })

  it('exposes opening, material-dialogue, and science-agent modes as first-class entries', () => {
    const chooser = readFileSync(new URL('./components/ai/AIContextChooser.vue', import.meta.url), 'utf8')
    expect(chooser).toContain('开题与选题')
    expect(chooser).toContain('AI 对话完善材料')
    expect(chooser).toContain('科创 Agent')
    expect(aiPage).toContain('@agent="openScienceAgentPicker"')
    expect(aiPage).toContain('保存到指定材料')
  })

  it('keeps the message stream as the only scrollable chat surface', () => {
    expect(aiPage).toContain('chatStreamRef')
    expect(aiPage).toContain('scrollToLatest')
    expect(aiPage).toContain('跳到最新消息')
    expect(aiPage).toContain('.chat-main {')
    expect(aiPage).toContain('min-height: 0;')
    expect(aiPage).toContain('.chat-stream {')
    expect(aiPage).toContain('overflow-y: auto;')
  })

  it('does not nest a second main landmark inside the role layout', () => {
    expect(aiPage).not.toContain('<main class="chat-main">')
    expect(aiPage).toContain('<section class="chat-main ai-main-panel">')
  })

  it('exposes an in-place retry action for failed assistant messages', () => {
    expect(aiPage).toContain("ai-conversations/${conversationId}/messages/${message.id}/retry/")
    expect(aiPage).toContain('重试')
    expect(aiPage).toContain('retryMessage')
  })

  it('keeps project-free AI conversations from silently inheriting a project context', () => {
    expect(aiPage).toContain('const matchesContext = (item: AIConversation) => projectFilter.value === null ? item.project === null : item.project === projectFilter.value')
    expect(aiPage).toContain('async function reloadForProjectFilter()')
    expect(aiPage).not.toContain('projectFilter.value === null ? response.data[0] : null')
  })

  it('labels AI tool supplement fields as optional and explains the direct-chat fallback', () => {
    expect(aiPage).toContain('补充信息（可选）')
    expect(aiPage).toContain('填写后可让 AI 工具更准确；不填写也可以直接提问。')
    expect(aiPage).not.toContain('补充信息（按 Agent 契约填写）')
  })

  it('renders categorized AI tools in a counted, independently scrollable menu', () => {
    expect(aiPage).toContain('groupAgentsByCategory')
    expect(aiTools).toContain('选择 AI 工具')
    expect(aiTools).toContain('agent-group')
    expect(aiTools).toContain('.agent-menu')
    expect(aiTools).toContain('overflow-y: auto')
    expect(aiTools).toContain('agent-menu__filters')
    expect(aiTools).toContain('没有匹配的 AI 工具')
    expect(aiHistory).toContain('conversation-search')
  })

  it('collapses repeated history while keeping each source conversation selectable', () => {
    expect(aiPage).toContain('groupConversationSummaries')
    expect(aiHistory).toContain('conversation-group')
    expect(aiHistory).toContain('conversation-group__items')
    expect(aiHistory).toContain('itemTitle')
  })

  it('exposes the guided research-question workbench without exposing technical tool keys', () => {
    expect(aiPage).toContain('一步一步把问题想清楚')
    expect(aiWizard).toContain('发现现象')
    expect(aiWizard).toContain('研究对象与场景')
    expect(aiWizard).toContain('头脑风暴')
    expect(aiWizard).toContain('确认并生成项目')
    expect(aiPage).toContain("projects/${currentProject.value.id}/update_basics/")
    expect(aiPage).toContain('researchQuestion')
  })

  it('offers the research-question workbench from new and existing project surfaces', () => {
    const projectsPage = readFileSync(new URL('./pages/student/StudentProjects.vue', import.meta.url), 'utf8')
    expect(projectsPage).toContain('用 AI 一步步梳理研究课题')
    expect(projectsPage).toContain('已有课题路径需要填写项目题目和研究问题')
    expect(projectsPage).toContain("mode: 'brainstorm'")
    expect(projectsPage).not.toContain('create(true)')
    expect(projectPage).toContain('生成/完善研究问题')
  })

  it('keeps stage-level AI recommendations bound to the current project', () => {
    expect(projectPage).toContain("query: { projectId: String(project.id), stage: currentChapter?.index }")
  })
})
