import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const page = readFileSync(new URL('./pages/student/StudentTask.vue', import.meta.url), 'utf8')

describe('student task submission state', () => {
  it('uses one clear waiting state and retains the submitted draft for read-only review', () => {
    expect(page).toContain("v-if=\"material.status !== 'submitted' && !['approved', 'completed'].includes(task.status)\"")
    expect(page).not.toContain("body.value = ''; truth.value = false; files.value = []")
    expect(page).toContain(":class=\"{ 'task-paper--read-only': !canEdit }\"")
  })
})
