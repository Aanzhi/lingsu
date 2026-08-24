import { describe, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'

import { api, createAIConversation, errorMessage, saveAIGenerationAsMaterial, updateAIConversation } from './api'

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
