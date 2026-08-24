import { describe, expect, it } from 'vitest'
import { studentFixture } from '../fixtures/portalFixtures'
import { buildStudentPortalModel, canSubmitTask, daysUntilPurge, taskViewModel } from './studentPortalModel'

describe('student portal model', () => {
  it('uses the selected current project for hero and AI context', () => {
    const model = buildStudentPortalModel(studentFixture, '2026-08-25T00:00:00.000Z')
    expect(model.currentProject?.id).toBe(8)
    expect(model.aiContext.projectId).toBe(8)
    expect(model.aiContext.scope).toBe('current_project')
  })

  it('keeps archived and trashed projects out of the active shelf', () => {
    const model = buildStudentPortalModel(studentFixture, '2026-08-25T00:00:00.000Z')
    expect(model.activeProjects.map((project) => project.id)).toEqual([8, 9, 12])
    expect(model.archivedProjects.map((project) => project.id)).toEqual([10])
    expect(model.trashedProjects[0]).toMatchObject({ id: 11, daysUntilPurge: 15 })
  })

  it('blocks submission when an experimental step has no required log', () => {
    const task = taskViewModel(studentFixture.tasks.find((item) => item.id === 802)!)
    expect(canSubmitTask(task)).toBe(false)
    expect(canSubmitTask({ ...task, requiredMaterials: task.requiredMaterials.map((item) => ({ ...item, completed: true })) })).toBe(true)
  })

  it('calculates a deterministic 30-day recycle-bin countdown', () => {
    expect(daysUntilPurge('2026-08-10T00:00:00.000Z', '2026-08-25T00:00:00.000Z')).toBe(15)
    expect(daysUntilPurge('2026-07-01T00:00:00.000Z', '2026-08-25T00:00:00.000Z')).toBe(0)
  })
})
