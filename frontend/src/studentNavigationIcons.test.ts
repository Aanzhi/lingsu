import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

import { primaryNavigation, studentTopNavigation } from './stores/navigationRegistry'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const registry = read('./stores/navigationRegistry.ts')
const shell = read('./components/WorkspaceShell.vue')
const portal = read('./components/StudentPortalShell.vue')
const frame = read('./components/WorkspaceFrame.vue')

describe('student navigation icon consistency', () => {
  it('assigns a distinct semantic icon token to each student capability', () => {
    const expected = ['home', 'projects', 'ai', 'journey', 'members', 'cases', 'competitions', 'announcements']
    expect(primaryNavigation('student').map((item) => item.icon)).toEqual(expected)
    expect(studentTopNavigation(8).map((item) => item.icon)).toEqual(expected)
  })

  it('maps student icons to one consistent Element Plus line-icon family', () => {
    expect(shell).toContain("import { Bell, Briefcase, Collection, DocumentChecked, FolderOpened, House, MagicStick, MapLocation, Medal, Reading, Setting, Trophy, User } from '@element-plus/icons-vue'")
    expect(shell).toContain('journey: MapLocation')
    expect(shell).toContain("members: props.role === 'student' ? User : Briefcase")
    expect(shell).toContain('cases: Reading')
    expect(shell).toContain('competitions: Trophy')
    expect(shell).toContain('announcements: Bell')
    expect(portal).toContain('journey: MapLocation')
    expect(portal).toContain('members: User')
    expect(portal).toContain('cases: Reading')
    expect(portal).toContain('competitions: Trophy')
    expect(portal).toContain('announcements: Bell')
    expect(registry).toContain("icon: 'cases'")
    expect(registry).toContain("icon: 'competitions'")
    expect(registry).toContain("icon: 'announcements'")
  })

  it('uses line arrows for the collapsed sidebar control and keeps its labels', () => {
    expect(frame).toContain("import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'")
    expect(frame).toContain('ArrowLeft')
    expect(frame).toContain('ArrowRight')
    expect(frame).toContain('aria-expanded')
    expect(frame).toContain('aria-label')
    expect(frame).not.toContain("{{ sidebarCollapsed ? '›' : '‹' }}")
  })
})
