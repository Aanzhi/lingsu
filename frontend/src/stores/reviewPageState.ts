export type ReviewPageState = 'reviewing' | 'completed' | 'missing'

export function reviewPageState(review: { id: number } | undefined, completed = false): ReviewPageState {
  if (review) return 'reviewing'
  return completed ? 'completed' : 'missing'
}
