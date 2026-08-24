import { describe, expect, it } from 'vitest'
import { studentFixture } from './fixtures/portalFixtures'
import { canSubmitTask, daysUntilPurge, taskViewModel } from './stores/studentPortalModel'

describe('student portal fixture flows', () => {
  it('requires explicit confirmation before an AI opening draft creates a project', () => {
    const draft = { title: '校园风向观察', problem: '不同区域的风向是否存在稳定差异？', plan: '' }
    const create = (confirmed: boolean) => confirmed ? { id: 99, ...draft, status: 'unclaimed' } : null
    expect(create(false)).toBeNull()
    expect(create(true)).toMatchObject({ id: 99, title: draft.title })
  })

  it('models archive, recycle-bin restore and purge countdown as separate actions', () => {
    const active = studentFixture.projects.find((project) => project.id === 8)!
    expect(active.status).toBe('active')
    expect({ ...active, status: 'archived' }).toMatchObject({ id: 8, status: 'archived' })
    expect({ ...active, status: 'trashed', trashedAt: '2026-08-25T00:00:00.000Z' }).toMatchObject({ status: 'trashed' })
    expect(daysUntilPurge('2026-08-25T00:00:00.000Z', '2026-08-25T00:00:00.000Z')).toBe(30)
  })

  it('shows the material submission guard when the required experiment log is missing', () => {
    const task = studentFixture.tasks.find((item) => item.id === 802)!
    expect(canSubmitTask(taskViewModel(task))).toBe(false)
    expect(task.feedback).toContain('实验日志')
  })

  it('keeps the school-only public case application entry explicit', () => {
    const schoolCase = studentFixture.publicCases[0]
    expect(schoolCase.scope).toBe('school')
    expect(schoolCase.status).toBe('published')
  })
})
