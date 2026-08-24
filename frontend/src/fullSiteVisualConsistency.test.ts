import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const srcRoot = fileURLToPath(new URL('.', import.meta.url))

function source(path: string) {
  const url = new URL(path, import.meta.url)
  return existsSync(url) ? readFileSync(url, 'utf8') : ''
}

function collect(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? collect(path) : /\.(vue|css)$/.test(name) ? [path] : []
  })
}

const visualSources = collect(srcRoot).map((path) => ({ path, content: readFileSync(path, 'utf8') }))

describe('full-site Demo B visual consistency', () => {
  it('uses the approved system sans typography on every production surface', () => {
    const offenders = visualSources
      .filter(({ content }) => /var\(--serif\)|font(?:-family)?\s*:[^;]*(?:Georgia|STSong|SimSun|\bserif\b)/.test(content))
      .map(({ path }) => path.replace(srcRoot, ''))
    expect(offenders).toEqual([])
  })

  it('keeps the approved PC shell geometry and shared card radius in tokens', () => {
    const tokens = readFileSync(new URL('./styles/tokens.css', import.meta.url), 'utf8')
    const foundations = readFileSync(new URL('./styles/foundations.css', import.meta.url), 'utf8')
    expect(tokens).toContain('--topbar-height: 66px')
    expect(tokens).toContain('--sidebar-width: 232px')
    expect(tokens).toContain('--content-max: 1120px')
    expect(tokens).toContain('--radius-md: 12px')
    expect(foundations).toContain('grid-template-columns:232px minmax(0, 1fr)')
  })

  it('keeps the public shell full-screen without management affordances', () => {
    const publicShell = source('./components/PublicShell.vue')
    const entry = readFileSync(new URL('./pages/public/EntryPage.vue', import.meta.url), 'utf8')
    const publicHtml = `${publicShell}\n${entry}`
    expect(publicHtml).not.toContain('workspace-sidebar')
    expect(publicHtml).not.toContain('sidebar-note')
    expect(publicHtml).not.toContain('workspace-sidebar__note')
    expect(publicHtml).not.toContain('Demo tips')
  })

  it('keeps teacher and platform shells on the management sidebar contract', () => {
    const workspaceShell = readFileSync(new URL('./components/WorkspaceShell.vue', import.meta.url), 'utf8')
    const teacherLayout = readFileSync(new URL('./layouts/TeacherLayout.vue', import.meta.url), 'utf8')
    const platformLayout = readFileSync(new URL('./layouts/PlatformLayout.vue', import.meta.url), 'utf8')
    const teacherCss = readFileSync(new URL('./styles/foundations.css', import.meta.url), 'utf8')
    expect(teacherLayout).toContain('<WorkspaceShell')
    expect(platformLayout).toContain('<WorkspaceShell')
    expect(workspaceShell).toContain('workspace-sidebar')
    expect(teacherCss).toContain('grid-template-columns:232px')
  })
})
