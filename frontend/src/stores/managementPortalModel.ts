import type { ManagementAgent, ManagementPoolProject, ManagementSchool } from '../fixtures/managementFixtures'

export type ReviewAction = 'approve' | 'revision_required'
export type CaseStatus = 'waiting_student' | 'pending_platform' | 'published'

export function reviewActions(input: { primaryTeacherId: number | null; currentTeacherId: number }): ReviewAction[] {
  return input.primaryTeacherId !== null && input.primaryTeacherId === input.currentTeacherId ? ['approve', 'revision_required'] : []
}

export function caseStatus(input: { teacherInvite: boolean; studentConsent: boolean; platformReview: boolean }): CaseStatus {
  if (!input.teacherInvite || !input.studentConsent) return 'waiting_student'
  return input.platformReview ? 'published' : 'pending_platform'
}

export function poolRows(projects: ManagementPoolProject[]) {
  return projects.map((project) => ({
    ...project,
    claimable: project.primaryTeacherId === null && project.status === 'unclaimed',
    statusLabel: project.primaryTeacherId === null ? '待认领' : '已被其他教师认领',
  }))
}

export function schoolOverview(schools: ManagementSchool[]) {
  return schools.reduce((summary, school) => ({
    activeSchools: summary.activeSchools + (school.isAuthorized ? 1 : 0),
    totalProjects: summary.totalProjects + school.projectCount,
    activeProjects: summary.activeProjects + school.activeProjectCount,
    needsAttention: summary.needsAttention + (school.isAuthorized ? 0 : 1),
  }), { activeSchools: 0, totalProjects: 0, activeProjects: 0, needsAttention: 0 })
}

export function agentTemplateRows(agents: ManagementAgent[]) {
  return agents.map((agent) => ({ key: agent.key, name: agent.name, category: agent.category || '其他', status: agent.isActive ? 'active' as const : 'inactive' as const }))
}
