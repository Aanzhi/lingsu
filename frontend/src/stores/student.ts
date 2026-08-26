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
type StudentResource = 'projects' | 'tasks' | 'materials' | 'competitions' | 'announcements' | 'archived' | 'trashed'
const resourceLoading = reactive<Record<StudentResource, boolean>>({
  projects: false,
  tasks: false,
  materials: false,
  competitions: false,
  announcements: false,
  archived: false,
  trashed: false,
})
const resourceErrors = reactive<Record<StudentResource, string | null>>({
  projects: null,
  tasks: null,
  materials: null,
  competitions: null,
  announcements: null,
  archived: null,
  trashed: null,
})
const loading = computed(() => Object.values(resourceLoading).some(Boolean))
const loaded = ref(false)
const backgroundLoaded = ref(false)
let projectsPromise: Promise<void> | null = null
let backgroundPromise: Promise<void> | null = null

function compatTaskStatus(task: ProjectTask): ApiTask['status'] {
  if (task.legacy_status === 'locked') return 'locked'
  return task.status === 'in_progress' ? 'available' : task.status
}

function asStudentTask(task: ProjectTask): ApiTask {
  return { ...task, status: compatTaskStatus(task) }
}

function readableError(reason: unknown) {
  return reason instanceof Error && reason.message ? reason.message : '这部分内容暂时没有加载完成。'
}

async function loadProjects(force = false) {
  if (!force && loaded.value) return
  if (projectsPromise) return projectsPromise
  resourceLoading.projects = true
  resourceErrors.projects = null
  const request = (async () => {
    const response = await getProjects()
    state.projects = response.data
    loaded.value = true
  })()
  projectsPromise = request.finally(() => {
    resourceLoading.projects = false
    projectsPromise = null
  })
  return projectsPromise
}

async function loadResource<T>(key: StudentResource, request: Promise<{ data: T }>, commit: (data: T) => void) {
  resourceLoading[key] = true
  resourceErrors[key] = null
  try {
    const response = await request
    commit(response.data)
  } catch (reason) {
    resourceErrors[key] = readableError(reason)
    throw reason
  } finally {
    resourceLoading[key] = false
  }
}

async function loadBackgroundResources() {
  if (backgroundLoaded.value) return
  if (backgroundPromise) return backgroundPromise
  const requests = [
    loadResource('tasks', getProjectTasks(), (data) => { state.tasks = data.map(asStudentTask) }),
    loadResource('materials', getMaterials(), (data) => { state.materials = data }),
    loadResource('competitions', getCompetitions(), (data) => { state.competitions = data }),
    loadResource('announcements', getAnnouncements(), (data) => { state.announcements = data }),
  ]
  backgroundPromise = Promise.allSettled(requests).then((results) => {
    backgroundLoaded.value = results.every((result) => result.status === 'fulfilled')
  }).finally(() => { backgroundPromise = null })
  return backgroundPromise
}

async function loadProjectShell() {
  // The project list is enough to paint the page header and project shell.
  // Tasks and materials are deliberately loaded by the page afterwards so
  // the first meaningful frame is not held up by secondary resources.
  await loadProjects()
}

async function loadProjectResources(projectId: number) {
  const tasksRequest = loadResource('tasks', getProjectTasks(projectId), (data) => {
    state.tasks = [...state.tasks.filter((item) => item.project !== projectId), ...data.map(asStudentTask)]
  })
  const materialsRequest = loadResource('materials', getMaterials(projectId), (data) => {
    state.materials = [...state.materials.filter((item) => item.project !== projectId), ...data]
  })
  await Promise.all([tasksRequest, materialsRequest])
}

async function load() {
  await loadProjects()
  void loadBackgroundResources()
}

export const student = {
  state, loading, loaded: computed(() => loaded.value), load,
  resourceLoading, resourceErrors, loadProjects, loadProjectShell, loadProjectResources,
  async createProject(payload: { title: string; problem: string; plan: string; project_type: Project['project_type'] }) {
    const project = (await createProject(payload)).data; state.projects.unshift(project); return project
  },
  async refreshProject(projectId: number) {
    await loadProjects(true)
    await loadProjectResources(projectId)
  },
  async loadArchived() {
    await loadResource('archived', getProjects({ include_archived: true }), (data) => {
      state.archivedProjects = data.filter((item) => item.is_archived)
    })
  },
  async loadTrashed() {
    await loadResource('trashed', getTrashedProjects(), (data) => {
      state.trashedProjects = data
    })
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
