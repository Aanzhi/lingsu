export function canInviteMember(input: {
  currentUserId: number | undefined
  leaderId: number
  projectStatus: string
  authorized: boolean
}) {
  return input.currentUserId === input.leaderId && input.projectStatus === 'active' && input.authorized
}

export function invitationActionLabel(status: 'pending_student' | 'pending_teacher' | 'approved' | 'rejected') {
  return {
    pending_student: '等待学生确认',
    pending_teacher: '等待教师确认',
    approved: '已加入项目',
    rejected: '已拒绝',
  }[status]
}
