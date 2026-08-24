export const AI_WORKSPACE_MODES = [
  { key: 'opening', label: '开题' },
  { key: 'research', label: '研究' },
  { key: 'defense', label: '答辩' },
] as const

export type AIWorkspaceMode = typeof AI_WORKSPACE_MODES[number]['key']
export const PROJECT_LIFECYCLE_STATES = ['unclaimed', 'active', 'completed', 'archived', 'trashed'] as const
export const JOURNEY_TASK_STATES = ['available', 'in_progress', 'pending_review', 'revision_required', 'approved', 'completed'] as const
export type ProjectLifecycleState = typeof PROJECT_LIFECYCLE_STATES[number]
export type JourneyTaskState = typeof JOURNEY_TASK_STATES[number]

export interface CurrentProjectContext {
  id: number | null
  title: string | null
  status: ProjectLifecycleState | null
  materialCount: number
  unreadReviewCount: number
}
