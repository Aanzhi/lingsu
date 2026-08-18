import type { MaterialAttachment } from '../api'

type SecurityAttachment = Pick<MaterialAttachment, 'scan_status'>

export async function waitForAttachmentSecurity(
  load: () => Promise<SecurityAttachment[]>,
  options: { intervalMs?: number; timeoutMs?: number } = {},
) {
  const intervalMs = options.intervalMs ?? 1000
  const timeoutMs = options.timeoutMs ?? 120_000
  const deadline = Date.now() + timeoutMs
  while (true) {
    const attachments = await load()
    if (attachments.some((item) => item.scan_status === 'infected' || item.scan_status === 'failed')) {
      throw new Error('附件未通过安全检查，请删除风险文件后重新提交。')
    }
    if (attachments.every((item) => item.scan_status === 'clean')) return 'clean' as const
    if (Date.now() >= deadline) throw new Error('附件仍在进行安全检查，请稍后回到该任务继续提交。')
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
}
