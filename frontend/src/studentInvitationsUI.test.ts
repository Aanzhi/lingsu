import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./pages/student/StudentInvitations.vue', import.meta.url), 'utf8')

describe('student invitations workspace', () => {
  it('shows received and sent invitations in aligned columns with a real cancel action', () => {
    expect(source).toContain('getMemberInvitations')
    expect(source).toContain('receivedInvitations')
    expect(source).toContain('sentInvitations')
    expect(source).toContain('invite-columns')
    expect(source).toContain('取消邀请')
    expect(source).toContain('cancelMemberInvitation')
  })
})
