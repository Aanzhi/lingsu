import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const taskPage = read('./pages/student/StudentTask.vue')
const projectPage = read('./pages/student/StudentProject.vue')
const projectsPage = read('./pages/student/StudentProjects.vue')
const aiPage = read('./pages/shared/AICenter.vue')
const aiResultCard = read('./components/ai/AIResultCard.vue')
const aiModel = read('./stores/aiModel.ts')
const studentLayout = read('./layouts/StudentLayout.vue')
const router = read('./router.ts')

describe('student AI center entries', () => {
  it('keeps task-scoped AI entry points real and project-bound', () => {
    expect(taskPage).not.toContain('MaterialAIAssistant')
    expect(taskPage).not.toContain('task-ai-quick')
    expect(taskPage).toContain('task-ai-options')
    expect(taskPage).toContain('aiQuickEntryLocation(projectId, taskId')
    expect(projectPage).toContain('const researchAILocation = computed(() => ({')
    expect(projectPage).toContain("mode: 'research'")
    expect(projectPage).toContain('projectId: String(projectId.value)')
  })

  it('uses canonical opening mode for new projects while keeping old links compatible', () => {
    expect(projectsPage).toContain('AI 开题')
    expect(projectsPage).toContain("mode: 'opening'")
    expect(projectsPage).not.toContain("mode: 'brainstorm'")
    expect(aiModel).toContain("agentKey: 'proposal-consistency'")
    expect(aiModel).toContain("workflow: 'proposal_consistency'")
    expect(aiPage).toContain("value === 'brainstorm'")
  })

  it('keeps the AI workbench inside the student project layout and sidebar', () => {
    expect(studentLayout).not.toContain("route.meta.layout === 'ai'")
    expect(router).not.toContain("path: 'ai', name: 'student-ai', component: () => import('./pages/shared/AICenter.vue'), meta: { layout: 'ai' }")
    expect(aiPage).not.toContain('AIWorkspaceShell')
    expect(aiPage).toContain('class="page ai-center-page ai-workbench-frame ai-workbench-main"')
  })

  it('keeps direct input without exposing technical Agent controls and preserves retry behavior', () => {
    expect(aiPage).not.toContain('当前 Agent')
    expect(aiPage).toContain(':show-agent-rail="false"')
    expect(aiPage).toContain(':show-meta="false"')
    expect(aiPage).not.toContain('ai-empty-state')
    expect(aiPage).not.toContain('ai-project-selector')
    expect(aiPage).toContain('retryAIConversationMessage(conversationId, message.id)')
    expect(aiPage).toContain('retryMessage')
    expect(aiPage).not.toContain('补充信息（可选）')
    expect(aiPage).not.toContain('补充信息（按 Agent 契约填写）')
  })

  it('creates a conversation only when the first message is sent', () => {
    expect(aiPage).toContain('async function ensureConversation()')
    expect(aiPage).toContain('const conversationId = await ensureConversation()')
    expect(aiPage).toContain('if (!selectedId.value) return')
    expect(aiPage).not.toContain('else if (!selectedId.value) await newConversation()')
    expect(aiPage).not.toContain('void newConversation()')
  })

  it('keeps opening creation and material saving confirmation-first', () => {
    expect(aiPage).toContain('createProjectFromOpening')
    expect(aiPage).toContain('saveAIGenerationAsMaterial')
    expect(aiResultCard).toContain('确认创建项目')
    expect(aiPage).toContain('保存为材料')
    expect(aiPage).not.toContain('AIResearchWizard')
    expect(aiPage).not.toContain('研究对象与场景')
    expect(aiPage).not.toContain('第 1 步 · 发现现象')
  })
})
