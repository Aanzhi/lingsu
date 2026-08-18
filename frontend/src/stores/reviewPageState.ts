export function reviewPageState(review: { id: number } | undefined) {
  return review ? 'reviewing' : 'completed'
}
