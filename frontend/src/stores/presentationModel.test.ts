import { describe, expect, it } from 'vitest'

import {
  conversationDisplayTitle,
  filterConversationSummaries,
  groupConversationSummaries,
  projectStatusLabel,
  projectTypeLabel,
  type ConversationSummary,
} from './presentationModel'

describe('shared presentation model', () => {
  it('translates project types and statuses into stable Chinese labels', () => {
    expect(projectTypeLabel('research')).toBe('研究型')
    expect(projectTypeLabel('invention')).toBe('发明型')
    expect(projectTypeLabel('engineering')).toBe('工程型')
    expect(projectStatusLabel('active')).toBe('进行中')
    expect(projectStatusLabel('unclaimed')).toBe('待认领')
    expect(projectStatusLabel('completed')).toBe('已完成')
  })

  it('uses the first user prompt for generic conversation titles', () => {
    expect(conversationDisplayTitle({ title: '新对话', project_title: null }, '  我想研究校园雨水  ')).toBe('我想研究校园雨水')
    expect(conversationDisplayTitle({ title: '通用咨询', project_title: null }, '')).toBe('未命名对话')
    expect(conversationDisplayTitle({ title: '研究问题讨论', project_title: '校园雨水' }, '新的问题')).toBe('研究问题讨论')
  })

  it('filters conversation summaries without changing source records', () => {
    const items: ConversationSummary[] = [
      { id: 1, title: '问题讨论', project_title: '校园雨水', updated_at: '2026-08-22T10:00:00Z', is_archived: false },
      { id: 2, title: '开题', project_title: null, updated_at: '2026-08-21T10:00:00Z', is_archived: false },
      { id: 3, title: '旧对话', project_title: '校园雨水', updated_at: '2026-08-20T10:00:00Z', is_archived: true },
    ]

    expect(filterConversationSummaries(items, '雨水')).toEqual([items[0]])
    expect(filterConversationSummaries(items, '', false)).toEqual([items[0], items[1]])
    expect(items).toHaveLength(3)
  })

  it('groups repeated conversation titles into display-only history groups', () => {
    const items: ConversationSummary[] = [
      { id: 1, title: '通用咨询', project_title: null, updated_at: '2026-08-22T10:00:00Z', is_archived: false },
      { id: 2, title: '新对话', project_title: null, updated_at: '2026-08-22T09:00:00Z', is_archived: false },
      { id: 3, title: '通用咨询', project_title: '校园雨水', updated_at: '2026-08-22T08:00:00Z', is_archived: false },
    ]

    const groups = groupConversationSummaries(items, { 1: '研究校园雨水的积水问题' })

    expect(groups).toHaveLength(2)
    expect(groups[0].title).toBe('研究校园雨水的积水问题')
    expect(groups[0].items.map((item) => item.id)).toEqual([1, 2])
    expect(groups[0].count).toBe(2)
    expect(groups[1].project_title).toBe('校园雨水')
    expect(items).toHaveLength(3)
  })
})
