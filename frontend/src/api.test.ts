import { describe, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'

import {
  api,
  createAIConversation,
  createAIConversationMessage,
  createProjectFromOpening,
  changePassword,
  errorMessage,
  markAllNotificationsRead,
  markNotificationRead,
  platformReviewPublicCase,
  saveAIGenerationAsMaterial,
  studentConsentPublicCase,
  teacherInvitePublicCase,
  updateAIConversation,
} from './api'

describe('API error presentation', () => {
  it('renders nested validation details instead of hiding them behind a generic error', () => {
    const error = new AxiosError('validation error')
    error.response = { status: 400, statusText: 'Bad Request', headers: {}, config: {}, data: { input_values: { topic: ['此字段为必填项。'] } } } as never

    expect(errorMessage(error)).toBe('topic：此字段为必填项。')
  })
  it('does not render the first character of an HTML error page as user feedback', () => {
    const error = new AxiosError('Request failed')
    error.response = { data: '<!DOCTYPE html><html><body>Forbidden</body></html>' } as never

    expect(errorMessage(error)).toBe('操作失败，请稍后重试')
  })

  it.each([
    [401, '登录状态已失效，请重新登录。'],
    [429, 'AI 请求过于频繁或学校配额已用尽，请稍后重试。'],
    [502, 'AI 服务暂时不可用，请稍后重试。'],
    [503, 'AI 服务暂时不可用，请稍后重试。'],
  ])('maps provider status %s to a user-facing message', (status, message) => {
    const error = new AxiosError('provider error')
    error.response = { status, statusText: 'error', headers: {}, config: {}, data: {} } as never
    expect(errorMessage(error)).toBe(message)
  })

  it('maps request timeouts to a retryable user-facing message', () => {
    const error = new AxiosError('timeout', 'ECONNABORTED')
    expect(errorMessage(error)).toBe('AI 请求超时，请稍后重试。')
  })
})

it('saves the edited AI draft as the material revision content', async () => {
  const post = vi.spyOn(api, 'post').mockResolvedValue({} as never)

  await saveAIGenerationAsMaterial(9, { material: 3, content: '已编辑的草稿', revision_note: 'AI 草稿，经学生编辑后保存' })

  expect(post).toHaveBeenCalledWith('ai-logs/9/save_as_material/', {
    material: 3, content: '已编辑的草稿', revision_note: 'AI 草稿，经学生编辑后保存',
  })
  post.mockRestore()
})

it('keeps null current_agent when creating a free AI conversation', async () => {
  const post = vi.spyOn(api, 'post').mockResolvedValue({} as never)

  await createAIConversation({ project: null, current_agent: null })

  expect(post).toHaveBeenCalledWith('ai-conversations/', { project: null, current_agent: null })
  post.mockRestore()
})

it('keeps null paper_type when updating an AI conversation', async () => {
  const patch = vi.spyOn(api, 'patch').mockResolvedValue({} as never)

  await updateAIConversation(4, { paper_type: null })

  expect(patch).toHaveBeenCalledWith('ai-conversations/4/', { paper_type: null })
  patch.mockRestore()
})

it('uses the existing password change endpoint', async () => {
  const post = vi.spyOn(api, 'post').mockResolvedValue({} as never)

  await changePassword({ old_password: 'old-pass-123', new_password: 'new-pass-456', confirm_password: 'new-pass-456' })

  expect(post).toHaveBeenCalledWith('change-password/', {
    old_password: 'old-pass-123', new_password: 'new-pass-456', confirm_password: 'new-pass-456',
  })
  post.mockRestore()
})

it('uses the explicit opening confirmation endpoint to create a project', async () => {
  const post = vi.spyOn(api, 'post').mockResolvedValue({} as never)

  await createProjectFromOpening(12, {
    confirm: true,
    message_id: 44,
    title: '校园雨水回收',
    problem: '如何降低校园绿地灌溉用水？',
    plan: '完成一轮对照实验',
    project_type: 'research',
    candidate_index: 0,
  })

  expect(post).toHaveBeenCalledWith('ai-conversations/12/create_from_opening/', {
    confirm: true,
    message_id: 44,
    title: '校园雨水回收',
    problem: '如何降低校园绿地灌溉用水？',
    plan: '完成一轮对照实验',
    project_type: 'research',
    candidate_index: 0,
  })
  post.mockRestore()
})

it('keeps the AI workspace mode in conversation and message payloads', async () => {
  const post = vi.spyOn(api, 'post').mockResolvedValue({} as never)

  await createAIConversation({ project: 8, workspace_mode: 'research', current_agent: 'science-agent' })
  await createAIConversationMessage(5, { content: '帮我检查实验设计', workspace_mode: 'research', project: 8 })

  expect(post).toHaveBeenNthCalledWith(1, 'ai-conversations/', { project: 8, workspace_mode: 'research', current_agent: 'science-agent' })
  expect(post).toHaveBeenNthCalledWith(2, 'ai-conversations/5/messages/', { content: '帮我检查实验设计', workspace_mode: 'research', project: 8 })
  post.mockRestore()
})

it('exposes notification read actions as explicit API calls', async () => {
  const post = vi.spyOn(api, 'post').mockResolvedValue({} as never)

  await markNotificationRead(21)
  await markAllNotificationsRead()
  await teacherInvitePublicCase(31)
  await studentConsentPublicCase(31)
  await platformReviewPublicCase(31, false, '请补充隐私脱敏说明')

  expect(post).toHaveBeenNthCalledWith(1, 'notifications/21/mark_read/')
  expect(post).toHaveBeenNthCalledWith(2, 'notifications/mark_all_read/')
  expect(post).toHaveBeenNthCalledWith(3, 'public-case-requests/31/teacher_invite/')
  expect(post).toHaveBeenNthCalledWith(4, 'public-case-requests/31/student_consent/')
  expect(post).toHaveBeenNthCalledWith(5, 'public-case-requests/31/platform_review/', { approved: false, comment: '请补充隐私脱敏说明' })
  post.mockRestore()
})
