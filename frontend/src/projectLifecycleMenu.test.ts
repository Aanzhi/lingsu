import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const component = readFileSync(new URL('./components/ProjectLifecycleMenu.vue', import.meta.url), 'utf8')

describe('project lifecycle menu', () => {
  it('keeps the recovery action reachable for trashed projects', () => {
    expect(component).toContain("if (open.value) void nextTick(() => panel.value?.querySelector<HTMLButtonElement>('[role=\"menuitem\"]')?.focus())")
    expect(component).toContain('<strong>恢复项目</strong>')
    expect(component).not.toContain('if (props.project.deleted_at) return')
  })
})
