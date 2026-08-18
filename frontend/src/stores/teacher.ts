import { computed, reactive, ref } from 'vue'

import { addProjectMember, claimProject, decideMemberInvitation, getGuidedProjects, getMaterials, getPendingMemberInvitations, getPendingReviews, getProjectPool, getProjectTasks, getProjects, getTrashedProjects, archiveProject, unarchiveProject, trashProject, restoreProject, reviewMaterialRevision, type Material, type MaterialRevision, type MemberInvitation, type Project } from '../api'
import type { ReviewDecision } from './teacherApiModel'

const state = reactive({
  pool: [] as Project[],
  guided: [] as Project[],
  archived: [] as Project[],
  trashed: [] as Project[],
  reviews: [] as MaterialRevision[],
  invitations: [] as MemberInvitation[],
  detail: { projectId: null as number | null, tasks: [] as Awaited<ReturnType<typeof getProjectTasks>>['data'], materials: [] as Material[] },
})
const loading = ref(false)
async function load() {
  loading.value = true
  try {
    const [pool, guided, reviews, invitations] = await Promise.all([getProjectPool(), getGuidedProjects(), getPendingReviews(), getPendingMemberInvitations()])
    state.pool = pool.data; state.guided = guided.data; state.reviews = reviews.data; state.invitations = invitations.data
  } finally { loading.value = false }
}
export const teacherStore = {
  state, loading: computed(() => loading.value), load,
  async claim(id: number) { await claimProject(id); await load() },
  async review(id: number, outcome: ReviewDecision, comment: string) { await reviewMaterialRevision(id, outcome, comment); await load() },
  async decide(id: number, approved: boolean) { await decideMemberInvitation(id, approved); await load() },
  async addMember(projectId: number, inviteeId: number) { await addProjectMember(projectId, inviteeId); await load() },
  async loadArchived() {
    const response = await getProjects({ only_archived: true })
    state.archived = response.data
  },
  async loadTrashed() {
    const response = await getTrashedProjects()
    state.trashed = response.data
  },
  async archive(id: number) {
    const project = (await archiveProject(id)).data
    state.guided = state.guided.map((item) => (item.id === id ? project : item))
    return project
  },
  async unarchive(id: number) {
    const project = (await unarchiveProject(id)).data
    state.archived = state.archived.filter((item) => item.id !== id)
    state.guided = [project, ...state.guided.filter((item) => item.id !== id)]
    return project
  },
  async trash(id: number) {
    const project = (await trashProject(id)).data
    state.guided = state.guided.filter((item) => item.id !== id)
    state.archived = state.archived.filter((item) => item.id !== id)
    return project
  },
  async restore(id: number) {
    const project = (await restoreProject(id)).data
    state.trashed = state.trashed.filter((item) => item.id !== id)
    state.guided = [project, ...state.guided.filter((item) => item.id !== id)]
    return project
  },
  async loadProjectDetail(id: number) {
    const [tasks, materials] = await Promise.all([getProjectTasks(id), getMaterials(id)])
    state.detail.projectId = id; state.detail.tasks = tasks.data; state.detail.materials = materials.data
  },
}
