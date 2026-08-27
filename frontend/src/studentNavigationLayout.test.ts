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
const workspaceFrame = readFileSync(new URL('./components/WorkspaceFrame.vue', import.meta.url), 'utf8')
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
    for (const label of ['首页', '我的项目', '灵思 AI', '研究进程', '项目邀请', '成果申请', '工作通知', '公开内容']) {
      expect(navigationRegistry).toContain(`label: '${label}'`)
    }
    expect(navigationRegistry).not.toContain("label: '材料档案'")
    expect(workspaceShell).toContain('resolveStudentNavigationProject(auth.user.value?.primaryProject, student.state.projects, routeProjectId(route.params.id ?? route.query.projectId))')
    expect(workspaceShell).toContain('active-class=""')
    expect(foundations).toContain('.workspace-sidebar > a.workspace-router-active')
  })

  it('keeps shared secondary navigation inside the workspace sidebar', () => {
    expect(workspaceShell).toContain('utilityNavigation')
    expect(workspaceShell).toContain('更多页面')
    expect(studentLayout).not.toContain('更多页面')
  })

  it('enables a default-collapsed icon sidebar for students only', () => {
    expect(studentLayout).toContain('collapsible-sidebar')
    expect(workspaceShell).toContain('readSidebarPreference')
    expect(workspaceShell).toContain('writeSidebarPreference')
    expect(workspaceShell).toContain('aria-expanded')
    expect(foundations).toContain('.workspace-shell--sidebar-collapsed')
    expect(foundations).toContain('.workspace-sidebar--collapsed')
    expect(responsive).toContain('.workspace-shell--sidebar-collapsed .workspace-sidebar')
    expect(teacherLayout).not.toContain('collapsible-sidebar')
    expect(platformLayout).not.toContain('collapsible-sidebar')
  })

  it('keeps the collapsible student sidebar mobile-safe in every preference state', () => {
    expect(workspaceFrame).toContain('workspace-shell--sidebar-collapsible')
    expect(responsive).toContain('.workspace-shell--sidebar-collapsible { grid-template-columns: 1fr; }')
    expect(responsive).toContain('.workspace-shell--sidebar-collapsible .workspace-sidebar')
    expect(responsive).toContain('position: relative')
    expect(responsive).toContain('overflow-x: auto')
    expect(responsive).toContain('.workspace-shell--sidebar-collapsible .workspace-sidebar > a')
    expect(responsive).toContain('width: auto')
    expect(responsive).toContain('justify-content: flex-start')
    expect(responsive).toContain('font-size: 15px')
    expect(responsive).toContain('.workspace-shell--sidebar-collapsible .workspace-sidebar__toggle { display: none; }')
    expect(foundations).toContain('.workspace-sidebar__toggle:focus-visible')
    expect(foundations).toContain('outline: 3px solid var(--color-focus-ring)')
    expect(foundations.indexOf('.workspace-sidebar > a {')).toBeLessThan(foundations.indexOf('.workspace-sidebar--collapsed > a {'))
    expect(foundations.indexOf('.workspace-sidebar > a .el-icon {')).toBeLessThan(foundations.indexOf('.workspace-sidebar--collapsed > a .el-icon {'))
    expect(workspaceShell).toContain('sidebarPreferenceReady')
    expect(workspaceShell).toContain("flush: 'sync'")
  })

  it('keeps toggle focus styling separate from hover and sizes collapsed icons consistently', () => {
    expect(foundations).toContain('.workspace-sidebar__toggle:hover {')
    expect(foundations).toContain('.workspace-sidebar__toggle:focus-visible {')
    expect(foundations).toContain('outline-offset: 2px')
    expect(foundations).toContain('flex-basis: 20px')
  })

  it('uses the registry active state instead of RouterLink path-only matching', () => {
    expect(workspaceShell).toContain('active-class=""')
    expect(workspaceShell).toContain('exact-active-class=""')
  })

  it('sets a PC-only minimum width and the Demo B sans typography', () => {
    expect(tokens).toContain('--pc-min-width: 1280px')
    expect(foundations).toContain('.page-header h1')
    expect(foundations).toContain('font-family: var(--sans)')
    expect(foundations).toContain('.workspace-shell--hero .workspace-main')
  })
})
