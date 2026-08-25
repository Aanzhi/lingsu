import axios, { AxiosError, type AxiosResponse } from 'axios'

import type { AuthRole } from './stores/authModel'
import type { UnifiedStatus } from './stores/status'
import type { ApiSchool } from './stores/platformApiModel'
import type { ApiTask } from './stores/studentApiModel'
import { optionalAgentInputs, type ResearchQuestionCandidate } from './stores/aiConversationModel'
import type {
  AIWorkspaceMode,
  CurrentProjectContext,
  JourneyTaskState,
  ProjectLifecycleState,
} from './stores/productContracts'
export type { ApiTask }

export const api = axios.create({ baseURL: '/api/', withCredentials: true, xsrfCookieName: 'csrftoken', xsrfHeaderName: 'X-CSRFToken' })

export interface MeResponse {
  id: number; username: string; display_name: string; role: AuthRole; school: number | null; school_name: string | null
  must_change_password: boolean; authorized: boolean
  primary_project: number | null; primary_project_title: string | null
}
export interface AnonymousMeResponse { authenticated: false }
export type SessionMeResponse = MeResponse | AnonymousMeResponse
export interface ProjectMember { id: number; account: number; username: string; role: 'leader' | 'member' }
export interface Project {
  id: number; school: number; school_name: string; title: string; problem: string; plan: string; summary: string
  leader: number; primary_teacher: number | null
  project_type: 'research' | 'invention' | 'engineering'; status: ProjectLifecycleState
  members: ProjectMember[]
  growth: { experience: number; level: number; streak_days: number; achievements: string[]; title: string }
  is_archived: boolean; archived_at: string | null
  deleted_at: string | null; trashed_at: string | null; days_until_purge: number | null
  is_primary: boolean
  created_at: string
}
export interface MaterialAttachment {
  id: number; original_name: string; content_type: string; size: number; sha256: string
  scan_status: 'pending' | 'processing' | 'clean' | 'infected' | 'failed'; scan_detail: string
  download_url: string; created_at: string
}
export interface UploadSession {
  id: number; revision: number; original_name: string; content_type: string; total_size: number; chunk_size: number
  expected_sha256: string; status: 'active' | 'completed' | 'aborted' | 'expired'; expires_at: string
  part_count: number; uploaded_parts: number[]; attachment_id: number | null
}
export interface AIRevisionSource { ai_log_id: number; agent_key: string | null; purpose: string; paper_type: 'empirical' | 'case' | 'literature-review' | 'theoretical' | null; created_at: string }
export interface AIVerificationSummary { total: number; items: VerificationItem[] }
export interface MaterialRevision { id: number; material: number; material_title: string; project_title: string; author: number; author_name: string; primary_teacher_id?: number | null; content: string; truth_confirmed: boolean; revision_note: string; status: UnifiedStatus; reviewer: number | null; review_comment: string; created_at: string; attachments: MaterialAttachment[]; source_summary: AIRevisionSource | null; verification_summary: AIVerificationSummary | null }
export interface MaterialReference { url: string; original_name: string }
export interface Material { id: number; project: Project['id']; task: ProjectTask['id'] | null; template_material: number | null; title: string; kind: 'standard' | 'experiment_log'; status: UnifiedStatus; required: boolean; report_section: string; report_order: number; revisions: MaterialRevision[]; guidance: string; reference: MaterialReference | null }
export interface Competition { id: number; title: string; description: string; registration_deadline?: string; starts_at?: string; ends_at?: string; audience: string; status: string }
export interface Announcement { id: number; title: string; body: string; audience: string; published_at?: string; is_read?: boolean }
export interface AppNotification { id: number; kind: string; title: string; body: string; link: string; is_read: boolean; created_at?: string; actor_name?: string | null; project_id?: number | null }
export interface MemberInvitation { id: number; project: number; project_title: string; inviter: number; invitee: number; invitee_name: string; status: 'pending_student' | 'pending_teacher' | 'approved' | 'rejected'; created_at: string }
export interface StudentDirectoryEntry { id: number; username: string; display_name: string }
export interface ReportExport { id: number; project: number; requested_by: number; format: 'docx' | 'pdf'; status: 'queued' | 'processing' | 'completed' | 'failed'; project_version: string; material_manifest: { material_id: number; revision_id: number; title: string }[]; error_message: string; created_at: string; completed_at: string | null; download_url: string | null }
export interface PublicCase { id: number; project: Project['id']; project_title: string; school_name: string; applicant: number; request_type: 'student_school' | 'teacher_platform'; visibility_scope: 'school' | 'platform'; public_summary: string; tags: string[]; discipline: string; application_scene: string; outcome_form: string; cover: string | null; selected_materials: Material['id'][]; selected_material_summaries: { material_id: Material['id']; title: string; report_section: string; content: string }[]; status: 'pending_teacher' | 'waiting_student' | 'pending_platform' | 'published' | 'offline' | 'rejected'; review_comment: string; student_consent_at?: string | null; student_consent_by?: number | null; teacher_reviewer?: number | null; admin_reviewer?: number | null; platform_reviewer?: number | null; project_status?: ProjectLifecycleState | null }
export type AIContextScope = Record<string, boolean | string | number[]>
export interface PublicCase { student_consent?: boolean }
export interface AISource { kind: 'task' | 'material' | 'attachment'; id: number; title: string; project_id: number; material_id?: number | null }
export interface AIArtifactOutput { title?: string; draft?: string; next_action?: string; project_title?: string; project_type?: Project['project_type']; project_plan?: string; candidates?: ResearchQuestionCandidate[]; recommended_index?: number; missing_information?: string[]; [key: string]: unknown }
export interface VerificationItem { item: string; status: string; guidance?: string }
export interface AIGeneration { id: number; project: number | null; workspace_mode: AIWorkspaceMode; actor: number; actor_name: string; purpose: string; prompt: string; context_scope: AIContextScope; task: number | null; material: number | null; agent_key?: string | null; paper_type?: 'empirical' | 'case' | 'literature-review' | 'theoretical' | null; output: string; artifact_payload?: AIArtifactOutput; verification_items?: VerificationItem[]; saved_material_revision?: number | null; model_name: string; status: 'queued' | 'processing' | 'completed' | 'failed'; error_message: string; created_at: string; completed_at: string | null; referenced_sources: AISource[] }
export interface ProjectTask extends Omit<ApiTask, 'status'> { status: JourneyTaskState; legacy_status: 'locked' | null }
export interface ProjectTaskBrief extends ProjectTask {}
export interface ServiceStatus { database: string; task_queue: string; virus_scan: string; document_converter: string; storage: string; ai: string }
export interface AIAvailability { status: 'configured' | 'not_configured' | 'quota_exhausted' | 'unavailable'; remaining_quota: number }
export interface AIAgentInputField {
  key: string
  label: string
  placeholder?: string
  required: boolean
  type: 'text' | 'textarea' | 'select'
  options?: string[]
}
export interface AIAgent {
  id: number
  key: string
  name: string
  description: string
  role: 'student' | 'teacher' | 'both'
  category: string
  system_instruction: string
  prompt_template: string
  input_schema: AIAgentInputField[]
  context_scope_default: Record<string, boolean | string>
  is_active: boolean
  school: number | null
  order: number
  workflow?: string
  applicable_stages?: string[]
  quick_tasks?: string[]
  project_types?: string[]
  output_contract?: Record<string, unknown>
}
export interface AuditEvent { id: number; school: number; actor: number; actor_name: string; action: 'school_updated' | 'invite_code_reset' | 'project_claimed' | 'project_archived' | 'project_trashed' | 'project_restored' | 'member_invitation_decided' | 'material_submitted' | 'material_reviewed' | 'case_submitted' | 'case_reviewed' | 'case_visibility_changed' | 'report_export_requested'; changes: Record<string, string | number | boolean>; created_at: string }

export function errorMessage(error: unknown, fallback = '操作失败，请稍后重试') {
  if (!(error instanceof AxiosError)) return error instanceof Error ? error.message : fallback
  const status = error.response?.status
  if (status === 401) return '登录状态已失效，请重新登录。'
  if (status === 408 || error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') return 'AI 请求超时，请稍后重试。'
  if (status === 429) return 'AI 请求过于频繁或学校配额已用尽，请稍后重试。'
  const data = error.response?.data as { detail?: string | string[]; [key: string]: unknown } | undefined
  if (typeof data === 'string') return fallback
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.join('；')
  if (status === 502 || status === 503) return 'AI 服务暂时不可用，请稍后重试。'
  if (data) {
    const render = (value: unknown, field = ''): string => {
      if (typeof value === 'string') return field ? `${field}：${value}` : value
      if (Array.isArray(value)) return value.map((item) => render(item, field)).filter(Boolean).join('；')
      if (value && typeof value === 'object') {
        return Object.entries(value).map(([key, child]) => render(child, key === 'input_values' ? field : key)).filter(Boolean).join('；')
      }
      return ''
    }
    const detail = render(data)
    if (detail) return detail
  }
  return fallback
}

export const getMe = () => api.get<SessionMeResponse>('me/')
export const getServiceStatus = () => api.get<ServiceStatus>('service-status/')
export const getAIAvailability = () => api.get<AIAvailability>('ai-availability/')
export const getCsrf = () => api.get<{ detail: string }>('csrf/')
export const login = (username: string, password: string) => api.post<MeResponse>('login/', { username, password })
export const logout = () => api.post('logout/')
export const changePassword = (payload: { old_password: string; new_password: string; confirm_password: string }) => api.post<{ detail: string; must_change_password: boolean }>('change-password/', payload)
export const registerAccount = (payload: { invite_code: string; role: 'student' | 'teacher'; username: string; password: string; display_name: string }) => api.post<MeResponse>('register/', payload)
export const getProjects = (params?: { include_archived?: boolean; only_archived?: boolean }) => api.get<Project[]>('projects/', { params })
export const getTrashedProjects = () => api.get<Project[]>('projects/trashed/')
export const getProject = (id: number) => api.get<Project>(`projects/${id}/`)
export const createProject = (payload: Pick<Project, 'title' | 'problem' | 'plan' | 'project_type'>) => api.post<Project>('projects/', payload)
export const archiveProject = (id: number) => api.post<Project>(`projects/${id}/archive/`)
export const unarchiveProject = (id: number) => api.post<Project>(`projects/${id}/unarchive/`)
export const trashProject = (id: number) => api.post<Project>(`projects/${id}/trash/`)
export const restoreProject = (id: number) => api.post<Project>(`projects/${id}/restore/`)
export interface SetPrimaryProjectResponse extends Project { current_project?: CurrentProjectContext | null }
export const setPrimaryProject = (id: number) => api.post<SetPrimaryProjectResponse>(`projects/${id}/set_primary/`)
export const getMaterials = (project?: number) => api.get<Material[]>('materials/', { params: project ? { project } : undefined })
export const getMaterial = (id: number) => api.get<Material>(`materials/${id}/`)
export const createMaterialRevision = (material: number, content: string, files: File[], revisionNote = '') => {
  const body = new FormData()
  body.append('material', String(material)); body.append('content', content); body.append('revision_note', revisionNote)
  files.forEach((file) => body.append('uploaded_files', file))
  return api.post<MaterialRevision>('material-revisions/', body)
}
export const createMaterialDraft = (material: number, content: string, revisionNote = '') => createMaterialRevision(material, content, [], revisionNote)
export const createUploadSession = (payload: { revision: number; original_name: string; content_type: string; total_size: number; chunk_size: number; expected_sha256?: string }) => api.post<UploadSession>('upload-sessions/', payload)
export const getUploadSession = (id: number) => api.get<UploadSession>(`upload-sessions/${id}/`)
export const uploadSessionPart = (id: number, index: number, chunk: Blob, sha256: string) => {
  const body = new FormData(); body.append('chunk', chunk)
  return api.put(`upload-sessions/${id}/parts/${index}/`, body, { headers: { 'X-Chunk-Sha256': sha256 } })
}
export const completeUploadSession = (id: number) => api.post<{ attachment_id: number }>(`upload-sessions/${id}/complete/`)
export const abortUploadSession = (id: number) => api.post<UploadSession>(`upload-sessions/${id}/abort/`)
export const submitMaterialRevision = (id: number) => api.post<MaterialRevision>(`material-revisions/${id}/submit/`, { truth_confirmed: true })
export const getMaterialRevision = (id: number) => api.get<MaterialRevision>(`material-revisions/${id}/`)
export const getCompetitions = () => api.get<Competition[]>('competitions/')
export const getAnnouncements = () => api.get<Announcement[]>('announcements/')
export const markAnnouncementRead = (id: number) => api.post<Announcement>(`announcements/${id}/mark_read/`)
// ── 个人站内信（Phase 1 T3 后端端点，前端消息中心接入）──────────────
export interface NotificationReadReceipt { id: AppNotification['id']; is_read: boolean }
export interface NotificationReadSummary { detail?: string; unread_count?: number; updated_ids?: AppNotification['id'][] }
export const getNotifications = () => api.get<AppNotification[]>('notifications/')
export const markNotificationRead = (id: number) => api.post<AppNotification & NotificationReadReceipt>(`notifications/${id}/mark_read/`)
export const markAllNotificationsRead = () => api.post<NotificationReadSummary>('notifications/mark_all_read/')
export const getProjectPool = () => api.get<Project[]>('projects/pool/')
export const getGuidedProjects = () => api.get<Project[]>('projects/guided/')
export const claimProject = (id: number) => api.post<Project>(`projects/${id}/claim/`)
export const getPendingReviews = () => api.get<MaterialRevision[]>('material-revisions/pending_reviews/')
export const reviewMaterialRevision = (id: number, outcome: 'approved' | 'revision_required', comment: string) => api.post<MaterialRevision>(`material-revisions/${id}/review/`, { outcome, comment })
export const getPendingMemberInvitations = () => api.get<MemberInvitation[]>('member-invitations/pending_teacher/')
export const decideMemberInvitation = (id: number, approved: boolean) => api.post<MemberInvitation>(`member-invitations/${id}/decide/`, { approved })
export const searchStudents = (q: string) => api.get<StudentDirectoryEntry[]>('accounts/students/', { params: { q } })
export const createMemberInvitation = (project: number, invitee: number) => api.post<MemberInvitation>('member-invitations/', { project, invitee })
export const addProjectMember = (project: number, invitee: number) => api.post<ProjectMember>(`projects/${project}/add_member/`, { invitee })
export const getPendingStudentInvitations = () => api.get<MemberInvitation[]>('member-invitations/pending_student/')
export const acceptMemberInvitation = (id: number) => api.post<MemberInvitation>(`member-invitations/${id}/accept/`)
export const rejectMemberInvitation = (id: number) => api.post<MemberInvitation>(`member-invitations/${id}/reject/`)
export const createAnnouncement = (payload: Pick<Announcement, 'title' | 'body' | 'audience'> & { status: 'draft' | 'published' }) => api.post<Announcement>('announcements/', payload)
export const getSchools = () => api.get<ApiSchool[]>('schools/')
export const getSchool = (id: number) => api.get<ApiSchool>(`schools/${id}/`)
export const createSchool = (payload: { name: string; license_expires_at: string | null; is_active: boolean }) => api.post<ApiSchool>('schools/', payload)
export const updateSchool = (id: number, payload: Partial<Pick<ApiSchool, 'is_active' | 'license_expires_at' | 'ai_quota' | 'storage_quota_mb'>>) => api.patch<ApiSchool>(`schools/${id}/`, payload)
export const resetSchoolInvite = (id: number) => api.post<ApiSchool>(`schools/${id}/reset_invite_code/`)
export const getSchoolAuditEvents = (id: number) => api.get<AuditEvent[]>(`schools/${id}/audit-events/`)
export const createCompetition = (payload: Partial<Competition> & Pick<Competition, 'title'>) => api.post<Competition>('competitions/', payload)
export const updateCompetition = (id: number, payload: Partial<Competition>) => api.patch<Competition>(`competitions/${id}/`, payload)
export const getReportExports = (project: number) => api.get<ReportExport[]>('report-exports/', { params: { project } })
export const createReportExport = (project: number, format: 'docx' | 'pdf') => api.post<ReportExport>('report-exports/', { project, format })
export const getPublicCases = () => api.get<PublicCase[]>('public-case-requests/')
export const setCaseVisibility = (id: number, visible: boolean) => api.post<PublicCase>(`public-case-requests/${id}/set_visibility/`, { visible })
export const createPublicCase = (payload: { project: number; public_summary: string; tags: string[]; discipline: string; application_scene: string; outcome_form: string; selected_materials: number[]; request_type?: PublicCase['request_type']; visibility_scope?: PublicCase['visibility_scope'] }) => api.post<PublicCase>('public-case-requests/', payload)
export const resubmitPublicCase = (id: number, payload: Partial<{ public_summary: string; tags: string[]; discipline: string; application_scene: string; outcome_form: string; selected_materials: number[] }>) => api.post<PublicCase>(`public-case-requests/${id}/resubmit/`, payload)
export const approvePublicCase = (id: number) => api.post<PublicCase>(`public-case-requests/${id}/teacher_approve/`)
export const rejectPublicCase = (id: number, comment: string) => api.post<PublicCase>(`public-case-requests/${id}/teacher_reject/`, { comment })
export const teacherInvitePublicCase = (id: number) => api.post<PublicCase>(`public-case-requests/${id}/teacher_invite/`)
export const studentConsentPublicCase = (id: number) => api.post<PublicCase>(`public-case-requests/${id}/student_consent/`)
export const platformReviewPublicCase = (id: number, approved: boolean, comment = '') => api.post<PublicCase>(`public-case-requests/${id}/platform_review/`, { approved, comment })
export const getAIGenerations = (project?: number) => api.get<AIGeneration[]>('ai-logs/', { params: project ? { project } : undefined })
type ProjectTaskApiStatus = JourneyTaskState | 'locked'
type ProjectTaskApiResponse = Omit<ProjectTask, 'status' | 'legacy_status'> & { status: ProjectTaskApiStatus }

export function normalizeProjectTask(task: ProjectTaskApiResponse): ProjectTask {
  const { status, ...rest } = task
  if (status === 'locked') return { ...rest, status: 'available', legacy_status: 'locked' }
  return { ...rest, status, legacy_status: null }
}

function normalizeProjectTaskResponse(response: AxiosResponse<ProjectTaskApiResponse[]>): AxiosResponse<ProjectTask[]> {
  return { ...response, data: response.data.map(normalizeProjectTask) }
}

export const getProjectTasks = (project?: number) => api.get<ProjectTaskApiResponse[]>('project-tasks/', { params: project ? { project } : undefined }).then(normalizeProjectTaskResponse)
export const createAIGeneration = (payload: { project?: number | null; workspace_mode?: AIWorkspaceMode; purpose?: string; prompt: string; input_values?: Record<string, string>; context_scope: AIContextScope; agent_key?: string; task?: number; material?: number; paper_type?: 'empirical' | 'case' | 'literature-review' | 'theoretical' }) => api.post<AIGeneration>('ai-logs/', payload)
export interface AIConversation { id: number; title: string; project: Project['id'] | null; opening_project?: Project['id'] | null; project_title: string | null; paper_type: string | null; current_agent: string | null; workspace_mode?: AIWorkspaceMode | null; current_project?: CurrentProjectContext | null; is_archived: boolean; updated_at: string; created_at: string }
export interface AIConversationMessage { id: number; role: 'user' | 'assistant' | 'system'; content: string; status: 'queued' | 'streaming' | 'completed' | 'failed'; generation_log?: number | null; artifact_payload?: AIArtifactOutput | null; verification_items?: Array<VerificationItem | string>; error_message?: string; created_at: string }
export interface AIConversationMessageInput { content: string; agent_key?: string; project?: number | null; workspace_mode?: AIWorkspaceMode; task?: number; paper_type?: string; input_values?: Record<string, string>; context_scope?: AIContextScope }
export const getAIConversations = (params?: { project?: number; include_archived?: boolean }) => api.get<AIConversation[]>('ai-conversations/', { params })
export const createAIConversation = (payload: { title?: string; project?: number | null; workspace_mode?: AIWorkspaceMode; paper_type?: string | null; current_agent?: string | null }) => api.post<AIConversation>('ai-conversations/', payload)
export const updateAIConversation = (id: number, payload: Partial<Pick<AIConversation, 'title' | 'paper_type' | 'current_agent' | 'workspace_mode'>>) => api.patch<AIConversation>(`ai-conversations/${id}/`, payload)
export const archiveAIConversation = (id: number) => api.post<AIConversation>(`ai-conversations/${id}/archive/`)
export const getAIConversationMessages = (id: number) => api.get<AIConversationMessage[]>(`ai-conversations/${id}/messages/`)
export const createAIConversationMessage = (id: number, payload: AIConversationMessageInput) => api.post<AIConversationMessage>(`ai-conversations/${id}/messages/`, payload)
export const retryAIConversationMessage = (conversationId: number, messageId: number) => api.post<AIConversationMessage>(`ai-conversations/${conversationId}/messages/${messageId}/retry/`)
export interface CreateProjectFromOpeningPayload { confirm: true; message_id?: number; title: string; problem: string; plan?: string; project_type: Project['project_type']; candidate_index?: number }
export const createProjectFromOpening = (conversationId: number, payload: CreateProjectFromOpeningPayload) => api.post<Project>(`ai-conversations/${conversationId}/create_from_opening/`, payload)

function csrfToken() { return document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))?.split('=').slice(1).join('=') || '' }
export async function streamAIConversationMessage(id: number, messageId: number, onEvent: (event: { id?: string; event: string; data: Record<string, unknown> }) => void, signal?: AbortSignal, lastEventId?: string) {
  const response = await fetch(`/api/ai-conversations/${id}/messages/${messageId}/stream/${lastEventId ? `?last_event_id=${encodeURIComponent(lastEventId)}` : ''}`, { credentials: 'include', headers: { Accept: 'text/event-stream', 'X-CSRFToken': csrfToken(), ...(lastEventId ? { 'Last-Event-ID': lastEventId } : {}) }, signal })
  if (!response.ok || !response.body) throw new Error(`AI stream failed (${response.status})`)
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''
  while (true) {
    const { value, done } = await reader.read(); if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split(/\r?\n\r?\n/); buffer = blocks.pop() || ''
    blocks.forEach((block) => {
      let event = 'message'; let idValue: string | undefined; const data: string[] = []
      block.split(/\r?\n/).forEach((line) => { if (line.startsWith('id:')) idValue = line.slice(3).trim(); else if (line.startsWith('event:')) event = line.slice(6).trim(); else if (line.startsWith('data:')) data.push(line.slice(5).trim()) })
      if (data.length) { try { onEvent({ id: idValue, event, data: JSON.parse(data.join('\n')) }) } catch { onEvent({ id: idValue, event, data: { text: data.join('\n') } }) } }
    })
  }
}
export interface SaveAIGenerationAsMaterialPayload {
  material: Material['id']
  content: string
  revision_note: string
  workspace_mode?: AIWorkspaceMode
  current_project?: CurrentProjectContext | null
}
export const saveAIGenerationAsMaterial = (id: number, payload: SaveAIGenerationAsMaterialPayload) => api.post<MaterialRevision>(`ai-logs/${id}/save_as_material/`, payload)
// ── AI Agent 模板（平台/校本管理 + 学生/教师按角色拉取）──────────────
export const getAIAgents = () => api.get<AIAgent[]>('ai-agents/')
export const createAIAgent = (payload: Partial<AIAgent>) => api.post<AIAgent>('ai-agents/', payload)
export const updateAIAgent = (id: number, payload: Partial<AIAgent>) => api.patch<AIAgent>(`ai-agents/${id}/`, payload)
export const deleteAIAgent = (id: number) => api.delete(`ai-agents/${id}/`)

// ── 材料参考范本（指引 + 可下载模板）─────────────────────────────
// 学生端用于「需要上传什么」「参考模板」；教师端用于自定义覆盖。
export const getMaterialReference = (id: number) => api.get<{ guidance: string; reference: MaterialReference | null }>(`materials/${id}/reference/`)
export const setMaterialReference = (id: number, payload: { guidance?: string; reference_file?: File }) => {
  if (payload.reference_file) {
    const body = new FormData()
    if (payload.guidance !== undefined) body.append('guidance', payload.guidance)
    body.append('reference_file', payload.reference_file)
    return api.put<Material>(`materials/${id}/set_reference/`, body)
  }
  return api.put<Material>(`materials/${id}/set_reference/`, { guidance: payload.guidance ?? '' })
}
export const resetMaterialReference = (id: number) => api.delete<Material>(`materials/${id}/reset_reference/`)
