import { computed, reactive, ref } from 'vue'

import { completeUploadSession, createMaterialDraft, createMaterialRevision, createProject, createUploadSession, getAnnouncements, getCompetitions, getMaterialRevision, getMaterials, getProjects, getProjectTasks, getTrashedProjects, getUploadSession, restoreProject, setPrimaryProject, submitMaterialRevision, trashProject, unarchiveProject, archiveProject, uploadSessionPart, type Announcement, type Competition, type Material, type Project, type ProjectTask } from '../api'
import type { ApiTask } from './studentApiModel'
import { waitForAttachmentSecurity } from './attachmentPolling'
import { sha256, shouldUseChunkUpload, uploadFileInChunks } from './chunkedUploader'

const CHUNK_UPLOAD_THRESHOLD = Number(import.meta.env.VITE_CHUNK_UPLOAD_THRESHOLD_BYTES ?? 8 * 1024 * 1024)
const CHUNK_UPLOAD_SIZE = 4 * 1024 * 1024

const state = reactive({
  projects: [] as Project[],
  archivedProjects: [] as Project[],
  trashedProjects: [] as Project[],
  tasks: [] as ApiTask[],
  materials: [] as Material[],
  competitions: [] as Competition[],
  announcements: [] as Announcement[],
})
const loading = ref(false); const loaded = ref(false)

function compatTaskStatus(task: ProjectTask): ApiTask['status'] {
  if (task.legacy_status === 'locked') return 'locked'
  return task.status === 'in_progress' ? 'available' : task.status
}

function asStudentTask(task: ProjectTask): ApiTask {
  return { ...task, status: compatTaskStatus(task) }
}

async function load() {
  loading.value = true
  try {
    const [projects, tasks, materials, competitions, announcements] = await Promise.all([
      getProjects(), getProjectTasks(), getMaterials(), getCompetitions(), getAnnouncements(),
    ])
    state.projects = projects.data; state.tasks = tasks.data.map(asStudentTask); state.materials = materials.data
    state.competitions = competitions.data; state.announcements = announcements.data; loaded.value = true
  } finally { loading.value = false }
}

export const student = {
  state, loading: computed(() => loading.value), loaded: computed(() => loaded.value), load,
  async createProject(payload: { title: string; problem: string; plan: string; project_type: Project['project_type'] }) {
    const project = (await createProject(payload)).data; state.projects.unshift(project); return project
  },
  async refreshProject(projectId: number) {
    const [projects, tasks, materials] = await Promise.all([getProjects(), getProjectTasks(projectId), getMaterials(projectId)])
    state.projects = projects.data
    state.tasks = [...state.tasks.filter((item) => item.project !== projectId), ...tasks.data.map(asStudentTask)]
    state.materials = [...state.materials.filter((item) => item.project !== projectId), ...materials.data]
  },
  async loadArchived() {
    const response = await getProjects({ include_archived: true })
    state.archivedProjects = response.data.filter((item) => item.is_archived)
  },
  async loadTrashed() {
    const response = await getTrashedProjects()
    state.trashedProjects = response.data
  },
  async archive(projectId: number) {
    const project = (await archiveProject(projectId)).data
    state.projects = state.projects.filter((item) => item.id !== projectId)
    state.archivedProjects = [project, ...state.archivedProjects.filter((item) => item.id !== projectId)]
    return project
  },
  async unarchive(projectId: number) {
    const project = (await unarchiveProject(projectId)).data
    state.archivedProjects = state.archivedProjects.filter((item) => item.id !== projectId)
    state.projects = [project, ...state.projects]
    return project
  },
  async trash(projectId: number) {
    const project = (await trashProject(projectId)).data
    state.projects = state.projects.filter((item) => item.id !== projectId)
    state.archivedProjects = state.archivedProjects.filter((item) => item.id !== projectId)
    state.trashedProjects = [project, ...state.trashedProjects.filter((item) => item.id !== projectId)]
    return project
  },
  async restore(projectId: number) {
    const project = (await restoreProject(projectId)).data
    state.trashedProjects = state.trashedProjects.filter((item) => item.id !== projectId)
    state.projects = [project, ...state.projects]
    return project
  },
  async setPrimary(projectId: number) {
    const project = (await setPrimaryProject(projectId)).data
    state.projects = state.projects.map((item) => ({ ...item, is_primary: item.id === projectId }))
    state.archivedProjects = state.archivedProjects.map((item) => ({ ...item, is_primary: item.id === projectId }))
    return project
  },
  async submitMaterial(materialId: number, content: string, files: File[], revisionNote = '') {
    const useChunks = shouldUseChunkUpload(files, CHUNK_UPLOAD_THRESHOLD)
    const draft = (await (useChunks
      ? createMaterialDraft(materialId, content, revisionNote)
      : createMaterialRevision(materialId, content, files, revisionNote))).data
    if (useChunks) {
      for (const file of files) {
        const wholeHash = await sha256(file)
        const created = (await createUploadSession({
          revision: draft.id,
          original_name: file.name,
          content_type: file.type,
          total_size: file.size,
          chunk_size: CHUNK_UPLOAD_SIZE,
          expected_sha256: wholeHash,
        })).data
        const session = (await getUploadSession(created.id)).data
        await uploadFileInChunks(file, {
          chunkSize: session.chunk_size,
          uploadedParts: session.uploaded_parts,
          uploadPart: async (index, chunk, digest) => { await uploadSessionPart(session.id, index, chunk, digest) },
          complete: async () => (await completeUploadSession(session.id)).data,
        })
      }
    }
    const revision = useChunks ? (await getMaterialRevision(draft.id)).data : draft
    if (revision.attachments.length) {
      await waitForAttachmentSecurity(async () => (await getMaterialRevision(draft.id)).data.attachments)
    }
    await submitMaterialRevision(draft.id)
    const material = state.materials.find((item) => item.id === materialId)
    if (material) await this.refreshProject(material.project)
  },
  async saveMaterialDraft(materialId: number, content: string, files: File[], revisionNote = '') {
    const draft = (await createMaterialRevision(materialId, content, files, revisionNote)).data
    const material = state.materials.find((item) => item.id === materialId)
    if (material) await this.refreshProject(material.project)
    return draft
  },
  async formallySubmitDraft(materialId: number, revisionId: number) {
    await submitMaterialRevision(revisionId)
    const material = state.materials.find((item) => item.id === materialId)
    if (material) await this.refreshProject(material.project)
  },
  project(id: number) { return state.projects.find((item) => item.id === id) },
  task(id: number) { return state.tasks.find((item) => item.id === id) },
  materialForTask(id: number) { return state.materials.find((item) => item.task === id) },
}
