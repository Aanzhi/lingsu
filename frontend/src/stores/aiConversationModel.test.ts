import { describe, expect, it } from 'vitest'
import { parseSSEChunk, conversationTitle, filterConversations, type AIConversation } from './aiConversationModel'

describe('ai conversation model', () => {
  it('parses complete SSE events and keeps incomplete tail for the next chunk', () => {
    const first = parseSSEChunk('id: 7\nevent: message.delta\ndata: {"delta":"你好"}\n\npartial')
    expect(first.events).toEqual([{ id: '7', event: 'message.delta', data: { delta: '你好' } }])
    expect(first.rest).toBe('partial')
    const second = parseSSEChunk(`${first.rest}\n\nevent: message.done\ndata: {"message_id":9}\n\n`)
    expect(second.events[0]).toEqual({ id: undefined, event: 'message.done', data: { message_id: 9 } })
  })

  it('creates a useful title and filters archived/project conversations', () => {
    expect(conversationTitle('研究校园雨水花园的可行性')).toBe('研究校园雨水花园的可行性')
    expect(conversationTitle('这是一个非常长的对话标题，应该被截断为适合侧栏展示的简短标题')).toHaveLength(24)
    const conversations: AIConversation[] = [
      { id: 1, title: '项目一', project: 10, project_title: '项目一', paper_type: null, current_agent: null, is_archived: false, updated_at: '2026-08-20T09:00:00Z', created_at: '2026-08-20T09:00:00Z' },
      { id: 2, title: '归档', project: 10, project_title: '项目一', paper_type: null, current_agent: null, is_archived: true, updated_at: '2026-08-20T10:00:00Z', created_at: '2026-08-20T10:00:00Z' },
    ]
    expect(filterConversations(conversations, { project: 10, includeArchived: false })).toHaveLength(1)
    expect(filterConversations(conversations, { project: null, includeArchived: true })).toHaveLength(2)
  })
})
