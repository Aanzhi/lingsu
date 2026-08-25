import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = readFileSync(new URL('./styles/workspace.css', import.meta.url), 'utf8')
const contentLibrary = readFileSync(new URL('./pages/shared/ContentLibrary.vue', import.meta.url), 'utf8')
const invitations = readFileSync(new URL('./pages/student/StudentInvitations.vue', import.meta.url), 'utf8')

describe('shared content surfaces', () => {
  it('gives empty states the full content width and avoids duplicate error copy', () => {
    expect(styles).toContain('.case-grid > .empty-state, .competition-list > .empty-state { grid-column: 1 / -1; }')
    expect(styles).toContain('.announcement-timeline > .empty-state { width: 100%; }')
    expect(contentLibrary).toContain('v-if="error && !feedback"')
    expect(invitations).toContain('v-if="error && !feedback"')
  })
})
