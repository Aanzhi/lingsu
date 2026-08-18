import { describe, expect, it } from 'vitest'

import { waitForAttachmentSecurity } from './attachmentPolling'

describe('attachment security polling', () => {
  it('waits until every attachment is clean', async () => {
    const states = [
      [{ scan_status: 'pending' as const }],
      [{ scan_status: 'processing' as const }],
      [{ scan_status: 'clean' as const }],
    ]
    let index = 0

    const result = await waitForAttachmentSecurity(
      async () => states[Math.min(index++, states.length - 1)],
      { intervalMs: 0, timeoutMs: 100 },
    )

    expect(result).toBe('clean')
    expect(index).toBe(3)
  })

  it('fails immediately when the scanner rejects a file', async () => {
    await expect(waitForAttachmentSecurity(
      async () => [{ scan_status: 'infected' as const }],
      { intervalMs: 0, timeoutMs: 100 },
    )).rejects.toThrow('未通过安全检查')
  })

  it('times out with an actionable message', async () => {
    await expect(waitForAttachmentSecurity(
      async () => [{ scan_status: 'pending' as const }],
      { intervalMs: 0, timeoutMs: 0 },
    )).rejects.toThrow('仍在进行安全检查')
  })
})
