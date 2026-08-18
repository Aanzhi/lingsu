import { describe, expect, it } from 'vitest'
import { auditEventMessage, schoolConfigurationChanges } from './platformDetailModel'
import type { ApiSchool } from './platformApiModel'

const school: ApiSchool = { id: 1, name: '灵溯学校', invite_code: 'demo', is_active: true, license_expires_at: '2027-07-31', is_authorized: true, ai_quota: 100, storage_quota_mb: 10240, student_count: 10, teacher_count: 2, project_count: 3 }

describe('schoolConfigurationChanges', () => {
  it('only saves configuration fields that changed', () => {
    expect(schoolConfigurationChanges(school, { license_expires_at: '2027-07-31', ai_quota: 180, storage_quota_mb: 10240 })).toEqual({ ai_quota: 180 })
  })

  it('turns an audit event into a readable non-sensitive record', () => {
    expect(auditEventMessage({ id: 1, school: 1, actor: 1, actor_name: '平台管理员', action: 'school_updated', changes: { ai_quota: 180 }, created_at: '2026-08-13T10:00:00Z' })).toBe('AI 配额：180')
  })

  it('labels a report export request without exposing report contents', () => {
    expect(auditEventMessage({ id: 2, school: 1, actor: 1, actor_name: '林同学', action: 'report_export_requested', changes: { project_id: 8, export_id: 12, format: 'pdf' }, created_at: '2026-08-13T10:00:00Z' })).toBe('请求生成了一份 PDF 项目报告')
  })
})
