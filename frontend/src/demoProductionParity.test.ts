import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const router = readFileSync(new URL('./router.ts', import.meta.url), 'utf8')
const aiCenter = readFileSync(new URL('./pages/shared/AICenter.vue', import.meta.url), 'utf8')
const aiContextChooser = readFileSync(new URL('./components/ai/AIContextChooser.vue', import.meta.url), 'utf8')
const aiResearchWizard = readFileSync(new URL('./components/ai/AIResearchWizard.vue', import.meta.url), 'utf8')
const entry = readFileSync(new URL('./pages/public/EntryPage.vue', import.meta.url), 'utf8')
const teacherReview = readFileSync(new URL('./pages/teacher/TeacherWorkbench.vue', import.meta.url), 'utf8')
const teacherAI = readFileSync(new URL('./components/TeacherAIPreReview.vue', import.meta.url), 'utf8')

describe('design demo production parity', () => {
  it('keeps every approved surface on a real production route', () => {
    for (const routeName of [
      'student-projects', 'student-ai', 'teacher-projects',
      'teacher-reviews', 'platform-schools', 'platform-ai-agents',
    ]) expect(router).toContain(`name: '${routeName}'`)
  })

  it('exposes the three student AI modes without creating an empty project', () => {
    const aiProduction = `${aiCenter}\n${aiContextChooser}\n${aiResearchWizard}`
    expect(aiProduction).toContain('开题与选题')
    expect(aiProduction).toContain('AI 对话完善材料')
    expect(aiProduction).toContain('科创 Agent')
    expect(aiProduction).toContain('确认并生成项目前不会创建空项目')
  })

  it('gives anonymous users a real brand entry', () => {
    expect(entry).toContain('从项目创建、材料提交到教师审核')
    expect(entry).toContain('登录工作台')
    expect(entry).toContain('public-hero-card')
    expect(entry).toContain('public-next-card')
    expect(entry).toContain('public-three-col')
    expect(entry).toContain('平台如何协作')
    expect(entry).not.toContain('从一个好问题开始')
    expect(entry).not.toContain('public-entry__journey')
    expect(entry).not.toContain('clamp(40px, 6vw, 78px)')
  })

  it('keeps teacher AI review advisory', () => {
    expect(teacherReview).toContain('TeacherAIPreReview')
    expect(teacherAI).toContain('仍由教师决定')
  })
})
