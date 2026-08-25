import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const component = readFileSync(new URL('./components/TeacherAIPreReview.vue', import.meta.url), 'utf8')
const workbench = readFileSync(new URL('./pages/teacher/TeacherWorkbench.vue', import.meta.url), 'utf8')
const templatePage = readFileSync(new URL('./pages/teacher/TeacherProjectTemplate.vue', import.meta.url), 'utf8')

describe('teacher AI pre-review entry', () => {
  it('keeps AI review contextual to the submitted material', () => {
    expect(component).toContain('AI 预审材料')
    expect(component).toContain("agent_key: 'material-feedback'")
    expect(component).toContain('当前提交材料')
    expect(component).toContain('仍由教师决定')
    expect(component).toContain('写入评语草稿')
    expect(component).toContain("emit('use-draft'")
  })

  it('does not turn AI output into an approval action', () => {
    expect(component).toContain('只提供核验清单和修改建议')
    expect(component).not.toContain('reviewMaterialRevision')
    expect(component).not.toContain('通过并解锁')
  })

  it('renders one pre-review module inside the teacher review desk', () => {
    expect(workbench).toContain('import TeacherAIPreReview from "../../components/TeacherAIPreReview.vue"')
    expect(workbench).toContain('<TeacherAIPreReview')
    expect(workbench).toContain('@use-draft="comment = $event"')
    expect(workbench).toContain(':material-id="selectedRevision.material"')
  })

  it('initializes material drafts defensively before async detail data renders', () => {
    expect(templatePage).toContain('function draftFor(material: Material)')
    expect(templatePage).toContain('v-model="draftFor(selectedTemplateEntry.material).guidance"')
  })
})
