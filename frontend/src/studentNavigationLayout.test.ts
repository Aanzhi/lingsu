import { existsSync, readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

function source(path: string) {
  const url = new URL(path, import.meta.url)
  return existsSync(url) ? readFileSync(url, 'utf8') : ''
}

const studentLayout = readFileSync(new URL('./layouts/StudentLayout.vue', import.meta.url), 'utf8')
const studentShell = source('./components/StudentPortalShell.vue')
const workspaceShell = readFileSync(new URL('./components/WorkspaceShell.vue', import.meta.url), 'utf8')
const teacherLayout = readFileSync(new URL('./layouts/TeacherLayout.vue', import.meta.url), 'utf8')
const platformLayout = readFileSync(new URL('./layouts/PlatformLayout.vue', import.meta.url), 'utf8')
const foundations = readFileSync(new URL('./styles/foundations.css', import.meta.url), 'utf8')
const responsive = readFileSync(new URL('./styles/responsive.css', import.meta.url), 'utf8')
const tokens = readFileSync(new URL('./styles/tokens.css', import.meta.url), 'utf8')
const navigationRegistry = readFileSync(new URL('./stores/navigationRegistry.ts', import.meta.url), 'utf8')

describe('shared Demo B workspace layout contract', () => {
  it('uses a top-navigation shell for students and the management shell for teachers and platform administrators', () => {
    expect(studentLayout).toContain('<StudentPortalShell')
    expect(studentLayout).not.toContain('<WorkspaceShell')
    expect(studentShell).not.toContain('workspace-sidebar')
    expect(studentShell).toContain('student-top-navigation')
    expect(teacherLayout).toContain('<WorkspaceShell')
    expect(platformLayout).toContain('<WorkspaceShell')
    expect(studentShell).toContain('aria-label="学生顶部导航"')
  })

  it('keeps teacher and platform navigation in a 232px desktop sidebar', () => {
    expect(foundations).toContain('.workspace-shell')
    expect(foundations).toContain('grid-template-columns:232px minmax(0, 1fr)')
    expect(foundations).toContain('.workspace-sidebar')
    expect(foundations).toContain('.workspace-main')
    expect(responsive).not.toContain('.student-top-navigation::after')
  })

  it('renders student navigation as a complete flat top nav', () => {
    for (const label of ['首页', '我的项目', '灵思 AI', '研究旅程', '材料档案', '项目邀请', '成果申请']) {
      expect(studentShell).toContain(label)
    }
    expect(navigationRegistry).toContain("label: '首页'")
    expect(navigationRegistry).toContain("label: '研究旅程'")
  })

  it('keeps shared secondary navigation only inside the management sidebar', () => {
    expect(workspaceShell).toContain('utilityNavigation')
    expect(workspaceShell).toContain('更多页面')
    expect(studentShell).not.toContain('更多页面')
  })

  it('sets a PC-only minimum width and the Demo B sans typography', () => {
    expect(tokens).toContain('--pc-min-width: 1280px')
    expect(foundations).toContain('.page-header h1')
    expect(foundations).toContain('font-family: var(--sans)')
  })
})
