import type { AIAgent } from '../api'

export type AIWorkspaceMode = 'opening' | 'research' | 'defense'

export const AI_WORKBENCH_MODES: Array<{ key: AIWorkspaceMode; label: string; description: string }> = [
  { key: 'opening', label: '开题', description: '从观察开始，形成研究问题和开题草稿' },
  { key: 'research', label: '研究', description: '围绕当前项目完善材料、实验和证据' },
  { key: 'defense', label: '成果表达', description: '整理成果、演练问答和表达项目价值' },
]

const AI_MODE_ASSISTANT_DESCRIPTIONS: Record<AIWorkspaceMode, string> = {
  opening: '整理观察和研究问题，形成可以确认的开题草稿。',
  research: '围绕当前项目的任务、材料和进度，推进下一步研究工作。',
  defense: '围绕已完成成果整理展示内容，练习清晰、可核验地表达研究结论。',
}

export function workspaceModeDescription(mode: AIWorkspaceMode): string {
  return AI_MODE_ASSISTANT_DESCRIPTIONS[mode]
}

const AI_STARTER_PROMPTS: Record<AIWorkspaceMode, readonly string[]> = {
  opening: ['把我的观察整理成研究问题', '哪些变量值得先记录？', '给我一个可执行的开题思路'],
  research: ['帮我拆解今天的研究任务', '如何设计下一步实验？', '怎样整理现有证据？'],
  defense: ['帮我提炼项目亮点', '给我一个展示提纲', '模拟一次答辩提问'],
}

export function starterPrompts(mode: AIWorkspaceMode): string[] {
  return [...AI_STARTER_PROMPTS[mode]]
}

export type AIContextScope = 'none' | 'current_project'

export function resolveAIContext(mode: AIWorkspaceMode, currentProjectId: number | null): { projectId: number | null; scope: AIContextScope } {
  if (mode === 'opening') return { projectId: null, scope: 'none' }
  return currentProjectId === null
    ? { projectId: null, scope: 'current_project' }
    : { projectId: currentProjectId, scope: 'current_project' }
}

function matchesMode(mode: AIWorkspaceMode, agent: AIAgent): boolean {
  const workflow = (agent.workflow || '').toLowerCase()
  const category = agent.category || ''
  const isDefense = /defense/.test(workflow) || /答辩|成果表达|展示|汇报/.test(category)
  const isOpening = /^(opening|proposal)/.test(workflow) || /开题|选题|申报/.test(category)
  if (mode === 'opening') return isOpening && !isDefense
  if (mode === 'defense') return isDefense
  return !isOpening && !isDefense && (/research|experiment|paper/.test(workflow) || /研究|实验|科创|写作/.test(category))
}

/**
 * Selects active, student-facing Agents for the visible workbench mode.
 * The API list is never mutated, so changing modes cannot reorder history data.
 */
export function visibleAgents(mode: AIWorkspaceMode, agents: AIAgent[], audience: 'student' | 'teacher' = 'student'): AIAgent[] {
  return agents
    .filter((agent) => agent.is_active !== false)
    .filter((agent) => agent.role === audience || agent.role === 'both')
    .filter((agent) => matchesMode(mode, agent))
    .sort((left, right) => left.order - right.order || left.name.localeCompare(right.name))
}

/** Resolve the internal student assistant without exposing platform template names in the UI. */
export function resolveStudentAgent(
  mode: AIWorkspaceMode,
  agents: AIAgent[],
  requestedKey?: string,
  conversationKey?: string | null,
): AIAgent | null {
  const available = visibleAgents(mode, agents, 'student')
  const conversationAgent = available.find((agent) => agent.key === conversationKey)
  if (conversationAgent) return conversationAgent
  const requestedAgent = available.find((agent) => agent.key === requestedKey)
  return requestedAgent || available[0] || null
}

export type DraftAction = 'save_material' | 'create_project_from_opening'

export function draftActions(status: string): DraftAction[] {
  return status === 'completed' ? ['save_material', 'create_project_from_opening'] : []
}

export function normalizeAIWorkspaceMode(value: unknown): AIWorkspaceMode {
  if (value === 'opening' || value === 'brainstorm') return 'opening'
  if (value === 'defense') return 'defense'
  return 'research'
}

export function modeAgentLabel(mode: AIWorkspaceMode): string {
  return AI_WORKBENCH_MODES.find((item) => item.key === mode)?.label || '研究'
}

/** The Composer only sends IDs deliberately selected in the current project. */
export function materialSelectionScope(mode: AIWorkspaceMode, materialIds: number[], allowedSelections: string[] = []): Record<string, number[]> {
  if (mode === 'opening' || !allowedSelections.includes('selected_materials')) return {}
  const selectedMaterials = [...new Set(materialIds.filter((id) => Number.isInteger(id) && id > 0))]
  return selectedMaterials.length ? { selected_materials: selectedMaterials } : {}
}
