import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const demo = readFileSync(new URL('../public/design-demo.html', import.meta.url), 'utf8')

describe('design demo AI workflows', () => {
  it('does not render review-only role switches or tips', () => {
    expect(demo).not.toContain('class="demo-badge"')
    expect(demo).not.toContain('class="role-switch"')
    expect(demo).not.toContain('class="side-note"')
    expect(demo).not.toContain('class="prototype-ribbon"')
    expect(demo).not.toContain('仅供评审')
    expect(demo).not.toContain('评审提示')
    expect(demo).not.toContain('本 Demo 的设计规则')
    expect(demo).not.toMatch(/pageHeader\('(?:公共入口|学生端|教师端|平台端)(?: · [^']+)?'/)
  })

  it('shows explicit existing-topic and no-topic student paths', () => {
    expect(demo).toContain('已有课题')
    expect(demo).toContain('还没有课题')
    expect(demo).toContain('creation:brainstorm')
    expect(demo).toContain('data-context="existing"')
    expect(demo).toContain('data-context="no-project"')
    expect(demo).toContain('发现现象')
    expect(demo).toContain('头脑风暴')
    expect(demo).toContain('先比较几个可研究方向')
    expect(demo).toContain('选择一个你愿意继续观察的方向')
    expect(demo).toContain('我不会先替你给出一个项目题目')
    expect(demo).toContain('确认并生成项目')
    expect(demo).toContain('确认生成项目')
    expect(demo).toContain('确认前不会创建项目')
  })

  it('includes a teacher AI review module with human approval boundary', () => {
    expect(demo).toContain("['review', '✓', '材料审核']")
    expect(demo).toContain("page:aiReview")
    expect(demo).toContain('function teacherAIReview()')
    expect(demo).toContain('审核边界')
    expect(demo).toContain('不自动通过')
    expect(demo).toContain('教师下一步')
    expect(demo).toContain('AI 预审材料')
  })
})
