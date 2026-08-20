import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const taskPage = readFileSync(new URL('./pages/student/StudentTask.vue', import.meta.url), 'utf8')
const projectPage = readFileSync(new URL('./pages/student/StudentProject.vue', import.meta.url), 'utf8')
const aiPage = readFileSync(new URL('./pages/shared/AICenter.vue', import.meta.url), 'utf8')

describe('student AI center entries', () => {
  it('removes the retired material assistant in favor of task-scoped AI center links', () => {
    expect(taskPage).not.toContain('MaterialAIAssistant')
    expect(taskPage).toContain('任务 AI 快捷入口')
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
})
