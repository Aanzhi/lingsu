import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const topbar = source('./components/AppTopbar.vue')
const shell = source('./components/WorkspaceShell.vue')
const entry = source('./pages/public/EntryPage.vue')
const studentLayout = source('./layouts/StudentLayout.vue')
const teacherLayout = source('./layouts/TeacherLayout.vue')
const platformLayout = source('./layouts/PlatformLayout.vue')
const studentHome = source('./pages/student/StudentHome.vue')
const teacherWorkbench = source('./pages/teacher/TeacherWorkbench.vue')
const platformConsole = source('./pages/platform/PlatformConsole.vue')
const aiCenter = source('./pages/shared/AICenter.vue')
const login = source('./pages/public/LoginPage.vue')
const register = source('./pages/public/RegisterPage.vue')
const platformLogin = source('./pages/public/PlatformLoginPage.vue')
const workspaceStyles = source('./styles/workspace.css')

describe('production chrome review hints', () => {
  it('does not render role chips in the shared topbar', () => {
    expect(topbar).not.toContain('class="role-chip"')
    expect(topbar).not.toContain('roleLabel')
  })

  it('does not expose demo guidance from the shared topbar', () => {
    expect(topbar).not.toContain('使用提示')
    expect(topbar).not.toContain('helpCopy')
    expect(topbar).not.toContain('help-popover')
    expect(topbar).not.toContain('aria-label="帮助中心"')
  })

  it('does not render sidebar guidance cards', () => {
    expect(shell).not.toContain('workspace-sidebar__note')
    expect(shell).not.toContain('noteTitle')
    expect(shell).not.toContain('noteBody')
    for (const layout of [studentLayout, teacherLayout, platformLayout]) {
      expect(layout).not.toContain('note-title=')
      expect(layout).not.toContain('note-body=')
    }
  })

  it('does not label the public page as 公共入口 above its title', () => {
    expect(entry).not.toContain('<p class="public-eyebrow">公共入口</p>')
  })

  it('does not prefix page eyebrows with endpoint names', () => {
    for (const page of [studentHome, teacherWorkbench, platformConsole, aiCenter, login]) {
      expect(page).not.toMatch(/(?:公共入口|学生端|教师端|平台端) ·/)
    }
    expect(register).not.toMatch(/<p class="eyebrow">(?:公共入口|学生端|教师端|平台端) ·/)
  })

  it('does not expose demo tips or credentials in production pages', () => {
    for (const page of [login, platformLogin]) {
      expect(page).not.toContain('demo-hint')
      expect(page).not.toContain('lingsu-demo-2026')
      expect(page).not.toContain('fillDemo')
    }
    expect(workspaceStyles).not.toContain('.demo-hint')
  })
})
