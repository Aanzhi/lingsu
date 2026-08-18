export type ExportStatus = 'queued' | 'processing' | 'completed' | 'failed'

export const shouldPollExport = (status: ExportStatus) => status === 'queued' || status === 'processing'
export const exportStatusLabel = (status: ExportStatus) => ({ queued: '排队中', processing: '生成中', completed: '已完成', failed: '生成失败' }[status])
