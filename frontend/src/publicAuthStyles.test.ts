import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const login = readFileSync(new URL('./pages/public/LoginPage.vue', import.meta.url), 'utf8')
const register = readFileSync(new URL('./pages/public/RegisterPage.vue', import.meta.url), 'utf8')
const platformLogin = readFileSync(new URL('./pages/public/PlatformLoginPage.vue', import.meta.url), 'utf8')
const entry = readFileSync(new URL('./pages/public/EntryPage.vue', import.meta.url), 'utf8')
const styles = readFileSync(new URL('./styles/workspace.css', import.meta.url), 'utf8')

describe('public authentication surfaces', () => {
  it('uses the Demo B public shell without changing auth form responsibilities', () => {
    for (const source of [login, register, platformLogin]) {
      expect(source).toContain('public-auth-page')
      expect(source).toContain('auth-topbar')
      expect(source).toContain('auth-page-header')
      expect(source).not.toContain('auth-story--hero')
      expect(source).not.toContain('demo-hint')
    }
    expect(login).not.toContain('demo-platform')
    expect(platformLogin).toContain('data-workspace-theme="management"')
    expect(register).not.toContain('role-segment')
    expect(register).toContain('route.query.role')
    expect(styles).toContain('.public-auth-page {')
    expect(styles).toContain('.auth-two-col {')
    expect(styles).toContain('.auth-register-grid {')
  })

  it('keeps exactly one anonymous workspace entry and distinct public role destinations', () => {
    const topbarActions = entry.match(/<div class="public-entry__actions">([\s\S]*?)<\/div>/)?.[1] ?? ''
    expect(topbarActions.match(/<RouterLink/g)?.length ?? 0).toBe(1)
    expect(topbarActions).toContain(':to="workspacePath"')
    expect(topbarActions).toContain('{{ workspaceLabel }}')
    expect(entry).toContain("auth.user.value ? '进入我的工作台' : '登录工作台'")
    expect(topbarActions).not.toContain('>登录</RouterLink>')

    expect(entry).toContain('public-role-card public-role-card--student')
    expect(entry).toContain('data-role="student"')
    expect(entry).toContain('学生端 · 注册')
    expect(entry).toContain('to="/register?role=student"')
    expect(entry).toContain('public-role-card public-role-card--teacher')
    expect(entry).toContain('data-role="teacher"')
    expect(entry).toContain('教师端 · 登录')
    expect(entry).toContain('to="/login"')
  })

  it('shares role markers and visible selection feedback on registration cards', () => {
    expect(register).toContain('role-badge role-badge--student')
    expect(register).toContain('role-badge role-badge--teacher')
    expect(register).toContain('当前选择')
    expect(register).toContain('auth-role-card--student')
    expect(register).toContain('auth-role-card--teacher')
    expect(styles).toContain('.role-badge--student')
    expect(styles).toContain('.role-badge--teacher')
    expect(styles).toContain('.auth-role-card--student.active')
    expect(styles).toContain('.auth-role-card--teacher.active')
  })
})
