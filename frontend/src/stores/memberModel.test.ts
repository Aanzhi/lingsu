import { describe, expect, it } from 'vitest'

import { canInviteMember, invitationActionLabel } from './memberModel'

describe('member collaboration model', () => {
  it('requires the project leader and an active project before inviting', () => {
    expect(canInviteMember({ currentUserId: 2, leaderId: 2, projectStatus: 'active', authorized: true })).toBe(true)
    expect(canInviteMember({ currentUserId: 3, leaderId: 2, projectStatus: 'active', authorized: true })).toBe(false)
    expect(canInviteMember({ currentUserId: 2, leaderId: 2, projectStatus: 'unclaimed', authorized: true })).toBe(false)
    expect(canInviteMember({ currentUserId: 2, leaderId: 2, projectStatus: 'active', authorized: false })).toBe(false)
  })

  it('explains each invitation state without relying on color', () => {
    expect(invitationActionLabel('pending_student')).toBe('等待学生确认')
    expect(invitationActionLabel('pending_teacher')).toBe('等待教师确认')
    expect(invitationActionLabel('approved')).toBe('已加入项目')
    expect(invitationActionLabel('rejected')).toBe('已拒绝')
  })
})
