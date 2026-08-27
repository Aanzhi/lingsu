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

export function conversationDisplayTitle(conversation: Pick<ConversationSummary, 'title' | 'project_title'>, firstPrompt = '') {
  const title = conversation.title.trim()
  const generic = !title || ['新对话', '通用咨询'].includes(title)
  if (!generic) return title
  const prompt = firstPrompt.trim().replace(/\s+/g, ' ')
  return prompt ? `${prompt.slice(0, 32)}${prompt.length > 32 ? '…' : ''}` : '未命名对话'
}

export function filterConversationSummaries<T extends ConversationSummary>(items: T[], keyword: string, includeArchived = false): T[] {
  const normalized = keyword.trim().toLowerCase()
  return items.filter((item) => {
    if (!includeArchived && item.is_archived) return false
    if (!normalized) return true
    return `${item.title} ${item.project_title ?? ''}`.toLowerCase().includes(normalized)
  })
}

export function groupConversationSummaries<T extends ConversationSummary>(items: T[], previews: Record<number, string> = {}): ConversationDisplayGroup<T>[] {
  const groups = new Map<string, ConversationDisplayGroup<T>>()
  const sorted = [...items].sort((left, right) => right.updated_at.localeCompare(left.updated_at))
  sorted.forEach((item) => {
    const rawTitle = item.title.trim()
    const genericTitle = !rawTitle || ['新对话', '新建科创对话', '通用咨询'].includes(rawTitle)
    const titleKey = genericTitle ? '__generic__' : rawTitle.toLowerCase()
    const projectKey = item.project_title?.trim().toLowerCase() || '__unbound__'
    const key = `${item.is_archived ? 'archived' : 'active'}:${projectKey}:${titleKey}`
    const existing = groups.get(key)
    if (existing) {
      existing.items.push(item)
      existing.count += 1
      return
    }
    const firstPreviewItem = genericTitle ? sorted.find((candidate) => {
      const candidateTitle = candidate.title.trim()
      const candidateGeneric = !candidateTitle || ['新对话', '新建科创对话', '通用咨询'].includes(candidateTitle)
      return candidateGeneric && (candidate.project_title?.trim().toLowerCase() || '__unbound__') === projectKey && candidate.is_archived === item.is_archived && Boolean(previews[candidate.id]?.trim())
    }) : undefined
    const displayItem = firstPreviewItem || item
    groups.set(key, {
      key,
      title: conversationDisplayTitle(displayItem, previews[displayItem.id] || ''),
      project_title: item.project_title,
      is_archived: item.is_archived,
      updated_at: item.updated_at,
      count: 1,
      items: [item],
    })
  })
  return Array.from(groups.values())
}
