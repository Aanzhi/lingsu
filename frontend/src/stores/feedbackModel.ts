export type FeedbackTone = 'success' | 'error' | 'info'

export interface FeedbackState {
  tone: FeedbackTone
  message: string
  detail?: string
  actionLabel?: string
  busy?: boolean
}

export function feedbackToneClass(tone: FeedbackTone) {
  return tone
}

export function feedbackTitle(tone: FeedbackTone) {
  return tone === 'success' ? '操作成功' : tone === 'error' ? '需要处理' : '提示'
}

export function makeFeedback(tone: FeedbackTone, message: string, detail?: string, actionLabel?: string): FeedbackState {
  return { tone, message, detail, actionLabel }
}
