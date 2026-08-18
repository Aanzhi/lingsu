import { describe, expect, it } from 'vitest'

import { attachmentSecurity } from './attachmentModel'

describe('attachment security presentation', () => {
  it('only allows clean attachments to be downloaded', () => {
    expect(attachmentSecurity('clean')).toEqual({ label: '安全', tone: 'success', downloadable: true })
    expect(attachmentSecurity('pending').downloadable).toBe(false)
    expect(attachmentSecurity('processing').downloadable).toBe(false)
    expect(attachmentSecurity('failed').downloadable).toBe(false)
    expect(attachmentSecurity('infected')).toEqual({ label: '发现威胁', tone: 'danger', downloadable: false })
  })
})
