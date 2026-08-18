import { describe, expect, it } from 'vitest'

import { licenseStatus, type ApiSchool } from './platformApiModel'

const school = (overrides: Partial<ApiSchool> = {}): ApiSchool => ({
  id: 1, name: '灵川中学', invite_code: 'LIVE', is_active: true,
  license_expires_at: '2027-01-01', is_authorized: true, ai_quota: 100,
  storage_quota_mb: 10240, student_count: 20, teacher_count: 3, project_count: 8,
  ...overrides,
})

describe('platform license model', () => {
  it('distinguishes active, expiring, expired and disabled authorization', () => {
    const today = new Date('2026-08-12T00:00:00Z')
    expect(licenseStatus(school(), today)).toBe('active')
    expect(licenseStatus(school({ license_expires_at: '2026-09-01' }), today)).toBe('expiring')
    expect(licenseStatus(school({ license_expires_at: '2026-08-01', is_authorized: false }), today)).toBe('expired')
    expect(licenseStatus(school({ is_active: false, is_authorized: false }), today)).toBe('disabled')
  })
})
