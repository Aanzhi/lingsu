import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const router = readFileSync(new URL('./router.ts', import.meta.url), 'utf8')
const layout = readFileSync(new URL('./layouts/TeacherLayout.vue', import.meta.url), 'utf8')
const navigation = readFileSync(new URL('./stores/navigationRegistry.ts', import.meta.url), 'utf8')

describe('teacher AI guidance studio', () => {
  it('has an independent full-screen guidance-studio route and sidebar entry', () => {
    expect(router).toContain("name: 'teacher-ai'")
    expect(router).toContain("meta: { layout: 'ai' }")
    expect(layout).toContain("route.meta.layout === 'ai'")
    expect(navigation).toContain("label: '灵思 AI'")
    expect(navigation).toContain("to: '/teacher/ai'")
  })
})
