import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const frame = readFileSync(new URL('./components/WorkspaceFrame.vue', import.meta.url), 'utf8')
const shell = readFileSync(new URL('./components/WorkspaceShell.vue', import.meta.url), 'utf8')
const entry = readFileSync(new URL('./pages/public/EntryPage.vue', import.meta.url), 'utf8')
const studentHome = readFileSync(new URL('./pages/student/StudentHome.vue', import.meta.url), 'utf8')
const teacherHome = readFileSync(new URL('./pages/teacher/TeacherWorkbench.vue', import.meta.url), 'utf8')
const platformHome = readFileSync(new URL('./pages/platform/PlatformConsole.vue', import.meta.url), 'utf8')
const tokens = readFileSync(new URL('./styles/tokens.css', import.meta.url), 'utf8')
const foundations = readFileSync(new URL('./styles/foundations.css', import.meta.url), 'utf8')

describe('five-page UI pilot contract', () => {
  it('provides one frame for public and authenticated workspaces', () => {
    expect(frame).toContain('class="workspace-frame"')
    expect(frame).toContain('class="workspace-shell"')
    expect(frame).toContain('class="workspace-sidebar"')
    expect(frame).toContain('class="workspace-main"')
    expect(shell).toContain('<WorkspaceFrame')
    expect(entry).toContain('<WorkspaceFrame')
  })

  it('renders the public entry edge to edge without workspace navigation', () => {
    expect(entry).toContain(':show-sidebar="false"')
    expect(entry).toContain('edge-to-edge')
    expect(entry).not.toContain('<template #sidebar>')
    expect(entry).not.toContain('workspace-sidebar__note')
    expect(frame).toContain('workspace-shell--full')
    expect(frame).toContain('workspace-main--edge')
    expect(foundations).toContain('.workspace-shell--full')
    expect(foundations).toContain('.workspace-main--edge')
  })

  it('keeps the public product content operational while retaining the shared layout', () => {
    expect(entry).toContain('class="public-entry__content"')
    expect(entry).toContain('class="public-page-header"')
    expect(entry).toContain('class="public-hero-grid"')
    expect(entry).toContain('class="public-card public-hero-card"')
    expect(entry).toContain('class="public-card public-next-card"')
    expect(entry).toContain('class="public-three-col"')
    expect(entry).toContain('把想法变成可以验证的发现。')
    expect(entry).toContain('先看看研究旅程')
    expect(entry).toContain('注册学生账号')
    expect(entry).toContain('登录教师工作台')
    expect(entry).toContain('href="#platform"')
    expect(entry).toContain('了解平台如何协作')
    expect(entry).not.toContain('class="public-entry__journey"')
  })

  it('keeps management geometry identical and changes only brand tokens', () => {
    expect(tokens).toContain('--management-brand: #3d6c6a')
    expect(tokens).toContain('--management-brand-deep: #285250')
    expect(foundations).toContain('[data-workspace-theme="management"]')
    expect(foundations).toContain('--moss: var(--management-brand)')
    expect(foundations).toContain('--moss-dark: var(--management-brand-deep)')
  })

  it('uses the B system sans family for visible pilot headings and branding', () => {
    expect(foundations).toContain('.brand-lockup strong, .auth-brand strong')
    expect(foundations).toContain('.page-header h1')
    expect(foundations).not.toContain('.page-header h1 { margin: 2px 0 9px; font: 700 clamp(26px, 3vw, 36px)/1.25 var(--serif)')
  })

  it('transplants the Demo B student home composition around real project data', () => {
    expect(studentHome).toContain('eyebrow="当前项目"')
    expect(studentHome).toContain('title="继续当前研究"')
    expect(studentHome).toContain('从当前项目的待办开始，查看进度、材料状态和下一项可完成任务。')
    expect(studentHome).not.toContain('打开研究旅程 →')
    expect(studentHome).toContain('class="pilot-hero-grid"')
    expect(studentHome).toContain('class="pilot-card pilot-hero-card"')
    expect(studentHome).toContain('class="pilot-card pilot-next-card"')
    expect(studentHome).toContain('class="pilot-chapter-grid"')
    expect(studentHome).toContain('class="pilot-two-col student-home-support"')
    expect(studentHome).not.toContain('var(--serif)')
  })

  it('makes the current project name the student hero focus', () => {
    expect(studentHome).toContain('<p class="eyebrow">当前项目</p>')
    expect(studentHome).toContain('<h2>{{ project.title }}</h2>')
    expect(studentHome).toContain('class="pilot-hero-question"')
    expect(studentHome).toContain('研究问题')
    expect(studentHome).not.toContain('当前项目 · {{ project.title }}')
    expect(studentHome).not.toContain('预计用时 20 分钟')
  })

  it('uses the same Demo B metric and list primitives for teacher and platform homes', () => {
    expect(teacherHome).toContain('"工作台"')
    expect(teacherHome).toContain('查看本校项目、待审核材料和成员事项，优先处理需要你决定的记录。')
    expect(teacherHome).toContain('查看待审核材料')
    expect(teacherHome).toContain('class="pilot-metric-grid"')
    expect(teacherHome).toContain('class="pilot-card pilot-list-card"')
    expect(teacherHome).toContain('teacherStore.state')
    expect(teacherHome).not.toContain('teacherHomeFixtures')

    expect(platformHome).toContain("home: ['概览'")
    expect(platformHome).toContain('平台概览')
    expect(platformHome).toContain('查看学校空间')
    expect(platformHome).toContain('class="pilot-metric-grid"')
    expect(platformHome).toContain('class="pilot-two-col pilot-platform-detail"')
  })

  it('defines one shared set of Demo B pilot primitives', () => {
    for (const selector of [
      '.pilot-hero-grid', '.pilot-card', '.pilot-metric-grid', '.pilot-metric',
      '.pilot-two-col', '.pilot-chapter-grid', '.pilot-section-head', '.pilot-list-row',
    ]) expect(foundations).toContain(selector)
    expect(foundations).toContain('min-height: 250px')
    expect(foundations).toContain('grid-template-columns: minmax(0, 1.35fr) minmax(280px, .65fr)')
  })
})
