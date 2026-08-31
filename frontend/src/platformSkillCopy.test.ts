import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')

describe('Skill product language', () => {
  it('uses Skill terminology in platform management and student selection surfaces', () => {
    const platformPage = read('./pages/platform/PlatformAIAgents.vue')
    const navigation = read('./stores/navigationRegistry.ts')
    const contracts = read('./stores/pageContracts.ts')
    const picker = read('./components/ai/AIToolPicker.vue')

    expect(platformPage).toContain('Skill 管理')
    expect(platformPage).toContain('新建 Skill')
    expect(platformPage).not.toContain('AI 助手模板')
    expect(platformPage).not.toContain('删除 AI 助手')
    expect(navigation).toContain("label: 'Skills'")
    expect(contracts).toContain("title: 'Skills'")
    expect(picker).toContain('添加 Skill')
    expect(picker).not.toContain('平台模板')
  })
})
