export interface ApiSchool {
  id: number
  name: string
  invite_code: string
  is_active: boolean
  license_expires_at: string | null
  is_authorized: boolean
  ai_quota: number
  storage_quota_mb: number
  student_count: number
  teacher_count: number
  project_count: number
}

export type LicenseStatus = 'active' | 'expiring' | 'expired' | 'disabled'

export function licenseStatus(school: ApiSchool, today = new Date()): LicenseStatus {
  if (!school.is_active) return 'disabled'
  if (!school.license_expires_at) return 'active'
  const expiry = new Date(`${school.license_expires_at}T23:59:59Z`).getTime()
  if (expiry < today.getTime()) return 'expired'
  return expiry - today.getTime() <= 90 * 86400000 ? 'expiring' : 'active'
}
