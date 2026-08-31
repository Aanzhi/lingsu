import type { Project } from '../api'

export const PROJECT_TYPE_LABELS: Record<Project['project_type'], string> = {
  research: '研究型',
  invention: '发明型',
  engineering: '工程型',
}

export const PROJECT_STATUS_LABELS: Record<Project['status'], string> = {
  unclaimed: '待认领',
  active: '进行中',
  completed: '已完成',
  archived: '已归档',
  trashed: '回收站',
}

export interface ConversationSummary {
  id: number
  title: string
  preview?: string
  message_count?: number
  project_title: string | null
  updated_at: string
  is_archived: boolean
}

export interface ConversationDisplayGroup<T extends ConversationSummary = ConversationSummary> {
  key: string
  title: string
  project_title: string | null
  is_archived: boolean
  updated_at: string
  count: number
  items: T[]
}

export function projectTypeLabel(type: Project['project_type'] | string | null | undefined) {
  return type && type in PROJECT_TYPE_LABELS ? PROJECT_TYPE_LABELS[type as Project['project_type']] : '研究型'
}

export function projectStatusLabel(status: Project['status'] | string | null | undefined) {
  return status && status in PROJECT_STATUS_LABELS ? PROJECT_STATUS_LABELS[status as Project['status']] : '项目状态'
}

export function conversationDisplayTitle(conversation: Pick<ConversationSummary, 'title' | 'project_title' | 'preview'>, firstPrompt = '') {
  const title = conversation.title.trim()
  const generic = !title || ['新对话', '新建科创对话', '通用咨询', '未命名对话'].includes(title)
  if (!generic) return title
  const prompt = (firstPrompt.trim() || conversation.preview?.trim() || '').replace(/\s+/g, ' ')
  return prompt ? `${prompt.slice(0, 32)}${prompt.length > 32 ? '…' : ''}` : '未命名对话'
}

export function hasConversationMessages(conversation: Pick<ConversationSummary, 'message_count' | 'preview'>) {
  if (typeof conversation.message_count === 'number') return conversation.message_count > 0
  return Boolean(conversation.preview?.trim())
}

export function filterConversationSummaries<T extends ConversationSummary>(items: T[], keyword: string, includeArchived = false): T[] {
  const normalized = keyword.trim().toLowerCase()
  return items.filter((item) => {
    if (!includeArchived && item.is_archived) return false
    if (!normalized) return true
    return `${item.title} ${item.preview ?? ''} ${item.project_title ?? ''}`.toLowerCase().includes(normalized)
  })
}

export function groupConversationSummaries<T extends ConversationSummary>(items: T[], previews: Record<number, string> = {}): ConversationDisplayGroup<T>[] {
  return [...items]
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at) || right.id - left.id)
    .map((item) => ({
      key: String(item.id),
      title: conversationDisplayTitle(item, previews[item.id] || ''),
      project_title: item.project_title,
      is_archived: item.is_archived,
      updated_at: item.updated_at,
      count: 1,
      items: [item],
    }))
}
