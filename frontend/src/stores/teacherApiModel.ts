export type ReviewDecision = 'approved' | 'revision_required'

export function reviewValidation(decision: ReviewDecision, comment: string) {
  return decision === 'revision_required' && !comment.trim() ? '打回材料必须填写明确、可执行的审核意见。' : null
}
