export function selectReviewById<T extends { id: number }>(reviews: T[], id: number) {
  return reviews.find((review) => review.id === id)
}
