export type ReviewDecision = 'approved' | 'revision_required'

export function reviewValidation(decision: ReviewDecision, comment: string) {
  return decision === 'revision_required' && !comment.trim() ? '打回材料必须填写明确、可执行的审核意见。' : null
}

export function reviewAIProvenance(revision: {
  source_summary?: { ai_log_id: number; purpose: string; [key: string]: unknown } | null
  verification_summary?: { total?: number; items?: Array<{ item: string; guidance?: string; [key: string]: unknown }> } | null
}) {
  if (!revision.source_summary) return null
  return {
    source: `AI 生成记录 #${revision.source_summary.ai_log_id} · ${revision.source_summary.purpose}`,
    items: (revision.verification_summary?.items ?? []).map((item) => ({ item: item.item, guidance: item.guidance || '' })),
  }
}
