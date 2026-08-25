import { existsSync, readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

function source(path: string) {
  const url = new URL(path, import.meta.url)
  return existsSync(url) ? readFileSync(url, 'utf8') : ''
}

const studentLayout = readFileSync(new URL('./layouts/StudentLayout.vue', import.meta.url), 'utf8')
const studentShell = source('./components/StudentPortalShell.vue')
const heroShell = source('./components/HeroHomeShell.vue')
const workspaceShell = readFileSync(new URL('./components/WorkspaceShell.vue', import.meta.url), 'utf8')
const teacherLayout = readFileSync(new URL('./layouts/TeacherLayout.vue', import.meta.url), 'utf8')
const platformLayout = readFileSync(new URL('./layouts/PlatformLayout.vue', import.meta.url), 'utf8')
const router = readFileSync(new URL('./router.ts', import.meta.url), 'utf8')
const topbar = readFileSync(new URL('./components/AppTopbar.vue', import.meta.url), 'utf8')
const foundations = readFileSync(new URL('./styles/foundations.css', import.meta.url), 'utf8')
const responsive = readFileSync(new URL('./styles/responsive.css', import.meta.url), 'utf8')
const tokens = readFileSync(new URL('./styles/tokens.css', import.meta.url), 'utf8')
const navigationRegistry = readFileSync(new URL('./stores/navigationRegistry.ts', import.meta.url), 'utf8')

describe('shared Demo B workspace layout contract', () => {
  it('uses a full-screen hero shell only for student and teacher home pages', () => {
    expect(studentLayout).toContain('<HeroHomeShell')
    expect(studentLayout).toContain('<WorkspaceShell')
    expect(studentLayout).not.toContain('StudentPortalShell')
    expect(teacherLayout).toContain('<HeroHomeShell')
    expect(teacherLayout).toContain('<WorkspaceShell')
    expect(platformLayout).toContain('<WorkspaceShell')
    expect(studentLayout).not.toContain('student-top-navigation')
  })

  it('marks only the student and teacher home routes as hero layouts', () => {
    expect(router).toContain("name: 'student-home', component: () => import('./pages/student/StudentHome.vue'), meta: { layout: 'hero' }")
    expect(router).toContain("name: 'teacher-home', component: () => import('./pages/teacher/TeacherWorkbench.vue'), meta: { surface: 'home', layout: 'hero' }")
    expect(heroShell).toContain('layout="hero"')
    expect(heroShell).toContain(':show-sidebar="false"')
    expect(heroShell).toContain('home-mode')
    expect(topbar).toContain('homeMode')
  })

  it('keeps teacher and platform navigation in a 232px desktop sidebar', () => {
    expect(foundations).toContain('.workspace-shell')
    expect(foundations).toContain('grid-template-columns:232px minmax(0, 1fr)')
    expect(foundations).toContain('.workspace-sidebar')
    expect(foundations).toContain('.workspace-main')
    expect(responsive).not.toContain('.student-top-navigation::after')
  })

  it('keeps the shared navigation registry complete for the student workspace sidebar', () => {
    for (const label of ['首页', '我的项目', '灵思 AI', '研究旅程', '材料档案', '项目邀请', '成果申请', '通知']) {
      expect(navigationRegistry).toContain(`label: '${label}'`)
    }
    expect(workspaceShell).toContain('primaryNavigation(props.role)')
  })

  it('keeps shared secondary navigation inside the workspace sidebar', () => {
    expect(workspaceShell).toContain('utilityNavigation')
    expect(workspaceShell).toContain('更多页面')
    expect(studentLayout).not.toContain('更多页面')
  })

  it('sets a PC-only minimum width and the Demo B sans typography', () => {
    expect(tokens).toContain('--pc-min-width: 1280px')
    expect(foundations).toContain('.page-header h1')
    expect(foundations).toContain('font-family: var(--sans)')
    expect(foundations).toContain('.workspace-shell--hero .workspace-main')
  })
})
