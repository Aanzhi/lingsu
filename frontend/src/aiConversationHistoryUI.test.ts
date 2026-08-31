import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./components/ai/AIConversationHistory.vue', import.meta.url), 'utf8')
const aiCenter = readFileSync(new URL('./pages/shared/AICenter.vue', import.meta.url), 'utf8')

describe('AI conversation history presentation', () => {
  it('uses a focused overlay drawer without shrinking the workbench canvas', () => {
    expect(source).toContain('conversation-history-backdrop')
    expect(source).toContain('history-drawer__header')
    expect(source).toContain('history-drawer__section')
    expect(source).toContain('position: fixed')
    expect(source).toContain('z-index: 100')
    expect(source).toContain('当前模式会话')
    expect(source).toContain('conversation-list__section')
    expect(source).toContain('historySections')
    expect(source).toContain('formatHistoryDate')
    expect(source).not.toContain('groupIndex === 4')
    expect(source).not.toContain('较早对话')
    expect(source).toContain('class="conversation-item__current">当前</span>')
  })

  it('keeps search, new conversation, selection and archived conversation actions', () => {
    expect(source).toContain('type="search"')
    expect(source).toContain('＋ 新建对话')
    expect(source).toContain("emit('select'")
    expect(source).toContain("emit('toggle-archived')")
    expect(source).toContain("emit('close')")
    expect(source).toContain('查看已归档')
  })

  it('provides an explicit permanent delete confirmation for each history item', () => {
    expect(source).toContain("(event: 'delete', item: AIConversation): void")
    expect(source).toContain("emit('delete', pendingDelete.value)")
    expect(source).toContain('@click.stop="requestDelete(item)"')
    expect(source).toContain('永久删除会话')
    expect(source).toContain('删除后对话和消息不可恢复')
    expect(source).toContain('永久删除')
    expect(source).toContain('role="dialog"')
    expect(source).toContain(':disabled="deletingId === pendingDelete.id"')
    expect(source).toContain("import { Delete } from '@element-plus/icons-vue'")
    expect(source).toContain('<el-icon class="conversation-item__delete-icon"')
  })

  it('uses the active mode as list context instead of repeating it in every row', () => {
    expect(source).toContain('class="history-drawer__list-header"')
      expect(source).toContain('historyModeLabel')
      expect(source).toContain('class="conversation-item__title-row"')
      expect(source).toContain('formatTime(item.updated_at)')
      expect(source).toContain('class="conversation-item__meta-project"')
      expect(source).not.toContain('class="conversation-item__status"')
      expect(source).not.toContain('modeLabel(item)')
  })

  it('keeps history rows compact with a quiet contextual delete action', () => {
    expect(source).toContain('class="conversation-item__content"')
    expect(source).toContain('class="conversation-item__delete-icon"')
    expect(source).toContain('class="sr-only">{{ deletingId === item.id ? \'删除中…\' : \'删除\' }}</span>')
    expect(source).toContain('class="conversation-item__meta"')
    expect(source).toContain(':title="itemTitle(item)"')
    expect(source).not.toContain('class="conversation-item__actions"')
    expect(source).toContain('position: relative')
    expect(source).toContain('padding: 10px 42px 10px 12px')
    expect(source).toContain('opacity: 0')
    expect(source).toContain('visibility: hidden')
    expect(source).toContain('.conversation-item:hover .conversation-item__delete')
    expect(source).toContain('.conversation-item:focus-within .conversation-item__delete')
    expect(source).toContain('color: var(--muted)')
    expect(source).toContain('border-radius: 8px')
    expect(source).toContain('-webkit-line-clamp: 2')
    expect(source).toContain('white-space: nowrap')
  })

  it('shows a flat, mode-filterable history instead of merging generic conversations', () => {
    expect(source).toContain('modeFilter')
    expect(source).toContain('group.items')
    expect(source).toContain("{ key: 'opening', label: '开题' }")
    expect(source).toContain("{ key: 'research', label: '研究' }")
    expect(source).toContain("{ key: 'defense', label: '成果表达' }")
    expect(source).not.toContain('全部模式')
    expect(source).not.toContain("HistoryModeFilter | 'all'")
    expect(source).toContain('grid-template-columns: repeat(3, minmax(0, 1fr))')
    expect(source).not.toContain('<details')
    expect(source).not.toContain('已合并')
    expect(source).not.toContain('只在新建对话时打开')
  })

  it('exposes an accessible history trigger from the new conversation state', () => {
    expect(aiCenter).toContain('aria-controls="conversation-history"')
    expect(aiCenter).toContain(':aria-expanded="historyOpen"')
    expect(aiCenter).toContain("historyOpen.value")
  })
  it('keeps empty drafts out of history until the first message is sent', () => {
    expect(aiCenter).toContain('hasConversationMessages')
    expect(aiCenter).toContain('.filter(hasConversationMessages)')
    expect(aiCenter).not.toContain('historyConversations.value = [item, ...historyConversations.value.filter((conversation) => conversation.id !== item.id)]')
  })
})
