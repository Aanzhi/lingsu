export interface AIConversation {
  id: number
  title: string
  project: number | null
  project_title: string | null
  paper_type: string | null
  current_agent: string | null
  is_archived: boolean
  updated_at: string
  created_at: string
}

export interface AIConversationMessage {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  status: 'queued' | 'streaming' | 'completed' | 'failed'
  generation?: number | null
  artifact_payload?: { title?: string; draft?: string; next_action?: string } | null
  verification_items?: Array<{ item: string; status?: string; guidance?: string } | string>
  error_message?: string
  created_at: string
}

export interface ParsedSSEEvent { id?: string; event: string; data: Record<string, unknown> }

export function parseSSEChunk(chunk: string): { events: ParsedSSEEvent[]; rest: string } {
  const blocks = chunk.split(/\r?\n\r?\n/)
  const rest = blocks.pop() || ''
  const events = blocks.flatMap((block) => {
    let id: string | undefined
    let event = 'message'
    const dataLines: string[] = []
    block.split(/\r?\n/).forEach((line) => {
      if (line.startsWith('id:')) id = line.slice(3).trim()
      else if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    })
    if (!dataLines.length) return []
    try { return [{ id, event, data: JSON.parse(dataLines.join('\n')) as Record<string, unknown> }] }
    catch { return [{ id, event, data: { text: dataLines.join('\n') } }] }
  })
  return { events, rest }
}

export function conversationTitle(value: string): string {
  const compact = value.trim().replace(/\s+/g, ' ')
  return compact.slice(0, 24) || '新建科创对话'
}

export function filterConversations(conversations: AIConversation[], options: { project: number | null; includeArchived: boolean }): AIConversation[] {
  return conversations
    .filter((item) => options.includeArchived || !item.is_archived)
    .filter((item) => options.project === null || item.project === options.project)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
}
