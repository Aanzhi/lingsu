import { describe, expect, it } from 'vitest'
import { AxiosError } from 'axios'

import { errorMessage } from './api'

describe('API error presentation', () => {
  it('does not render the first character of an HTML error page as user feedback', () => {
    const error = new AxiosError('Request failed')
    error.response = { data: '<!DOCTYPE html><html><body>Forbidden</body></html>' } as never

    expect(errorMessage(error)).toBe('操作失败，请稍后重试')
  })
})
