import { PORTAL_FIXTURE_DATE, type StudentFixture, type StudentFixtureProject, type StudentFixtureTask } from '../fixtures/portalFixtures'

export interface StudentTaskViewModel {
  status: string
  requiredMaterials: Array<{ kind: 'standard' | 'experiment_log'; completed: boolean }>
}

export interface StudentPortalModel {
  school: StudentFixture['school']
  currentProject: StudentFixtureProject | null
  activeProjects: StudentFixtureProject[]
  archivedProjects: StudentFixtureProject[]
  trashedProjects: Array<StudentFixtureProject & { daysUntilPurge: number }>
  currentTasks: StudentFixtureTask[]
  currentMaterials: StudentFixture['materials']
  notifications: StudentFixture['notifications']
  aiContext: { projectId: number | null; scope: 'none' | 'current_project' }
}

const PURGE_DAYS = 30
const DAY_MS = 24 * 60 * 60 * 1000

export function daysUntilPurge(trashedAt: string, now: string): number {
  const trashedTime = Date.parse(trashedAt)
  const nowTime = Date.parse(now)
  if (!Number.isFinite(trashedTime) || !Number.isFinite(nowTime)) return 0
  return Math.max(0, Math.ceil((trashedTime + PURGE_DAYS * DAY_MS - nowTime) / DAY_MS))
}

export function canSubmitTask(task: StudentTaskViewModel): boolean {
  const editable = task.status === 'in_progress' || task.status === 'revision_required'
  if (!editable) return false
  return task.requiredMaterials.every((material) => material.kind !== 'experiment_log' || material.completed)
}

export function buildStudentPortalModel(input: StudentFixture, now = PORTAL_FIXTURE_DATE): StudentPortalModel {
  const currentProject = input.projects.find((project) => project.id === input.currentProjectId && project.status !== 'trashed') ?? null
  const activeProjects = input.projects.filter((project) => project.status !== 'archived' && project.status !== 'trashed')
  const archivedProjects = input.projects.filter((project) => project.status === 'archived')
  const trashedProjects = input.projects
    .filter((project) => project.status === 'trashed')
    .map((project) => ({ ...project, daysUntilPurge: daysUntilPurge(project.trashedAt ?? '', now) }))
  const projectId = currentProject?.id ?? null
  return {
    school: input.school,
    currentProject,
    activeProjects,
    archivedProjects,
    trashedProjects,
    currentTasks: projectId === null ? [] : input.tasks.filter((task) => task.projectId === projectId),
    currentMaterials: projectId === null ? [] : input.materials.filter((material) => material.projectId === projectId),
    notifications: input.notifications,
    aiContext: { projectId, scope: projectId === null ? 'none' : 'current_project' },
  }
}

export function taskViewModel(task: StudentFixtureTask): StudentTaskViewModel {
  return { status: task.status, requiredMaterials: task.requiredMaterials }
}
