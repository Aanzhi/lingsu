export type OperationKind = 'claim' | 'review_approved' | 'review_returned' | 'member_approved' | 'member_rejected' | 'school_enabled' | 'school_disabled' | 'invite_reset' | 'competition_published' | 'competition_withdrawn' | 'search'

const messages: Record<OperationKind, string> = {
  claim: '项目已认领，研究任务地图已生成。',
  review_approved: '材料已通过，下一任务已解锁。',
  review_returned: '修订意见已发送，学生会在任务台看到优先修复任务。',
  member_approved: '成员已加入项目团队。',
  member_rejected: '成员邀请已拒绝。',
  school_enabled: '学校授权已恢复，可以继续写入。',
  school_disabled: '学校已停用，师生保留历史只读访问。',
  invite_reset: '邀请码已重置，请将新邀请码安全交给学校。',
  competition_published: '赛事已发布到全平台。',
  competition_withdrawn: '赛事已撤回，不再对师生展示。',
  search: '筛选结果已更新。',
}

export function operationSuccess(kind: OperationKind) {
  return messages[kind]
}

export function reviewCompletionAction() {
  return '返回审核队列'
}
