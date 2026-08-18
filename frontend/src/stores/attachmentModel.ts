export type AttachmentScanStatus = 'pending' | 'processing' | 'clean' | 'infected' | 'failed'

export function attachmentSecurity(status: AttachmentScanStatus) {
  if (status === 'clean') return { label: '安全', tone: 'success', downloadable: true } as const
  if (status === 'infected') return { label: '发现威胁', tone: 'danger', downloadable: false } as const
  if (status === 'failed') return { label: '检查失败', tone: 'danger', downloadable: false } as const
  return { label: status === 'processing' ? '检查中' : '等待检查', tone: 'warning', downloadable: false } as const
}
