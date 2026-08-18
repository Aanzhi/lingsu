import type { AuditEvent } from '../api'
import type { ApiSchool } from './platformApiModel'

export type SchoolConfigurationDraft = Pick<ApiSchool, 'license_expires_at' | 'ai_quota' | 'storage_quota_mb'>

export function makeSchoolConfigurationDraft(school: ApiSchool): SchoolConfigurationDraft {
  return {
    license_expires_at: school.license_expires_at,
    ai_quota: school.ai_quota,
    storage_quota_mb: school.storage_quota_mb,
  }
}

export function schoolConfigurationChanges(school: ApiSchool, draft: SchoolConfigurationDraft): Partial<SchoolConfigurationDraft> {
  const changes: Partial<SchoolConfigurationDraft> = {}
  if (school.license_expires_at !== draft.license_expires_at) changes.license_expires_at = draft.license_expires_at
  if (school.ai_quota !== draft.ai_quota) changes.ai_quota = draft.ai_quota
  if (school.storage_quota_mb !== draft.storage_quota_mb) changes.storage_quota_mb = draft.storage_quota_mb
  return changes
}

export function auditEventMessage(event: AuditEvent): string {
  if (event.action === 'invite_code_reset') return '重置了学校邀请码（旧邀请码已失效）'
  const workflowMessages: Partial<Record<AuditEvent['action'], string>> = {
    project_claimed: '认领并启动了一个项目',
    member_invitation_decided: '处理了一项项目成员邀请',
    material_submitted: '提交了一份项目材料审核',
    material_reviewed: event.changes.outcome === 'approved' ? '通过了一份项目材料' : '打回了一份项目材料',
    case_submitted: event.changes.resubmitted ? '重新提交了一项公开案例申请' : '提交了一项公开案例申请',
    case_reviewed: event.changes.outcome === 'published' ? '通过了一项公开案例申请' : '驳回了一项公开案例申请',
    case_visibility_changed: event.changes.visible ? '恢复了一项公开案例' : '下架了一项公开案例',
    report_export_requested: `请求生成了一份 ${event.changes.format === 'pdf' ? 'PDF' : 'Word'} 项目报告`,
  }
  if (workflowMessages[event.action]) return workflowMessages[event.action]!
  const labels: Record<string, string> = { is_active: '授权状态', license_expires_at: '授权到期日', ai_quota: 'AI 配额', storage_quota_mb: '存储配额' }
  return Object.entries(event.changes).map(([key, value]) => `${labels[key] ?? key}：${String(value)}`).join('；') || '更新了学校配置'
}
