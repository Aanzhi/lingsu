import { describe, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'

import { api, errorMessage, saveAIGenerationAsMaterial } from './api'

describe('API error presentation', () => {
  it('does not render the first character of an HTML error page as user feedback', () => {
    const error = new AxiosError('Request failed')
    error.response = { data: '<!DOCTYPE html><html><body>Forbidden</body></html>' } as never

    expect(errorMessage(error)).toBe('操作失败，请稍后重试')
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
