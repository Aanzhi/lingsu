<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createAIConversation, createAIConversationMessage, createProjectFromOpening, errorMessage, getAIAgents, getAIConversationMessages, getAIConversations, getMaterials, getProjects, retryAIConversationMessage, saveAIGenerationAsMaterial, streamAIConversationMessage, type AIAgent, type AIConversation, type AIConversationMessage, type Material, type Project } from '../../api'
import { auth } from '../../stores/auth'
import { isNearBottom, isTerminalSSEEvent, normalizeResearchQuestionArtifact, researchProjectDraftFromArtifact } from '../../stores/aiConversationModel'
import { normalizeAIWorkspaceMode, resolveStudentAgent, visibleAgents, type AIWorkspaceMode } from '../../stores/aiWorkbenchModel'
import { PAPER_TYPES, type PaperType } from '../../stores/aiModel'
import { studentProjectRoute } from '../../stores/pageContracts'
import { filterConversationSummaries, groupConversationSummaries } from '../../stores/presentationModel'
import AIConversationHistory from '../../components/ai/AIConversationHistory.vue'
import AIModeTabs from '../../components/ai/AIModeTabs.vue'
import AIResultCard from '../../components/ai/AIResultCard.vue'
import AIWorkbenchComposer from '../../components/ai/AIWorkbenchComposer.vue'

const route = useRoute()
const router = useRouter()

type ProjectDraft = {
  title: string
  problem: string
  plan: string
  project_type: Project['project_type']
}

function queryNumber(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function routeModeValue(): AIWorkspaceMode {
  const value = route.query.mode
  if (value === 'brainstorm') return 'opening'
  return normalizeAIWorkspaceMode(value)
}

function routeAgentValue(): string | undefined {
  // Keep the legacy brainstorm link pointed at the opening assistant, but let
  // an explicit agent query select a valid platform template for all other
  // opening links. The resolver below still rejects templates outside the
  // current mode and falls back to the first enabled template.
  if (route.query.mode === 'brainstorm' || route.query.researchQuestion === '1') return 'proposal-topic'
  return typeof route.query.agent === 'string' ? route.query.agent : undefined
}

function defaultProjectId(mode: AIWorkspaceMode, availableProjects: Project[]): number | null {
  if (mode === 'opening') return null
  const requested = queryNumber(route.query.projectId)
  if (requested && availableProjects.some((project) => project.id === requested)) return requested
  const primary = auth.user.value?.primaryProject
  if (primary && availableProjects.some((project) => project.id === primary)) return primary
  const eligible = mode === 'defense'
    ? availableProjects.filter((project) => project.status === 'completed' || project.status === 'active')
    : availableProjects.filter((project) => project.status === 'active' || project.status === 'completed')
  return eligible[0]?.id ?? availableProjects[0]?.id ?? null
}

const conversations = ref<AIConversation[]>([])
const messages = ref<AIConversationMessage[]>([])
const projects = ref<Project[]>([])
const agents = ref<AIAgent[]>([])
const selectedId = ref<number | null>(null)
const historyOpen = ref(false)
const historySearch = ref('')
const showArchivedConversations = ref(false)
const projectFilter = ref<number | null>(routeModeValue() === 'opening' ? null : queryNumber(route.query.projectId) ?? auth.user.value?.primaryProject ?? null)
const selectedAgent = ref<string | undefined>(routeAgentValue())
const paperType = ref<PaperType | ''>('')
const taskId = ref<number | undefined>(queryNumber(route.query.taskId) ?? undefined)
const draft = ref('')
const loading = ref(true)
const conversationLoading = ref(false)
const projectsLoading = ref(true)
const agentsLoading = ref(true)
const projectResourceError = ref('')
const agentResourceError = ref('')
const sending = ref(false)
const error = ref('')
const streamNotice = ref('')
const streamController = ref<AbortController | null>(null)
const requestVersion = ref(0)
const selectionVersion = ref(0)
const chatStreamRef = ref<HTMLElement | null>(null)
const showJumpLatest = ref(false)
const artifactDrafts = ref<Record<number, string>>({})
const savingMessage = ref<number | null>(null)
const pendingMaterialMessageId = ref<number | null>(null)
const materialDialogOpen = ref(false)
const materialDialogLoading = ref(false)
const materialDialogError = ref('')
const materials = ref<Material[]>([])
const targetMaterialId = ref<number | null>(null)
const openingDraft = ref<ProjectDraft>({ title: '', problem: '', plan: '', project_type: 'research' })
const creatingProject = ref(false)
const copyNotice = ref('')
const skipConversationRestore = ref(false)
let pendingResumeTimer: number | null = null

const workbenchMode = computed<AIWorkspaceMode>(() => routeModeValue())
const current = computed(() => conversations.value.find((item) => item.id === selectedId.value) || null)
const currentProject = computed(() => projects.value.find((item) => item.id === (current.value?.project ?? projectFilter.value)) || null)
const modeAgents = computed(() => visibleAgents(workbenchMode.value, agents.value, 'student'))
const currentAgent = computed(() => resolveStudentAgent(workbenchMode.value, agents.value, selectedAgent.value, current.value?.current_agent))
const projectRequired = computed(() => workbenchMode.value !== 'opening')
const isConversationStarted = computed(() => messages.value.some((message) => Boolean(message.content?.trim()) || message.status === 'queued' || message.status === 'streaming'))
const isNewConversation = computed(() => !isConversationStarted.value)
const resourceErrorMessage = computed(() => [projectResourceError.value, agentResourceError.value].filter(Boolean).join('；'))
const historyGroups = computed(() => groupConversationSummaries(filterConversationSummaries(conversations.value, historySearch.value, showArchivedConversations.value)))
const workspaceContextLabel = computed(() => {
  if (workbenchMode.value === 'opening') return '开题 · 不绑定项目'
  const modeLabel = workbenchMode.value === 'defense' ? '成果表达' : '研究'
  return currentProject.value ? `当前项目 · ${currentProject.value.title}` : `${modeLabel} · 尚未选择项目`
})
const composerDisabled = computed(() => loading.value || conversationLoading.value || sending.value || Boolean(current.value?.is_archived) || !currentAgent.value || (projectRequired.value && !currentProject.value))
const composerCanSend = computed(() => Boolean(draft.value.trim() && !composerDisabled.value))
const pendingMaterialMessage = computed(() => messages.value.find((message) => message.id === pendingMaterialMessageId.value) || null)

function normalizePaperType(value: unknown): PaperType | '' {
  return PAPER_TYPES.some((item) => item.key === value) ? value as PaperType : ''
}

function paperTypeForRequest(): PaperType | undefined {
  if (paperType.value) return paperType.value
  // Paper templates still have a backend paper_type contract. Keep that
  // compatibility internal so the simplified student chat never asks users
  // to fill in a technical field before they can send a message.
  return currentAgent.value?.key.startsWith('paper-') ? PAPER_TYPES[0].key : undefined
}

function messageBlocks(content: string | undefined): string[] {
  const normalized = String(content || '').replace(/\r\n?/g, '\n').trim()
  if (!normalized) return []
  return normalized
    .split(/\n{2,}/)
    .map((block) => block
      .replace(/^#{1,6}\s+/gm, '')
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/__(.*?)__/g, '$1')
      .trim())
    .filter(Boolean)
}

function scrollToLatest(behavior: ScrollBehavior = 'smooth') {
  const stream = chatStreamRef.value
  if (!stream) return
  stream.scrollTo({ top: stream.scrollHeight, behavior })
  showJumpLatest.value = false
}

function updateScrollAffordance() {
  const stream = chatStreamRef.value
  if (!stream) return
  showJumpLatest.value = !isNearBottom({ scrollTop: stream.scrollTop, clientHeight: stream.clientHeight, scrollHeight: stream.scrollHeight })
}

function maybeScrollLatest(force = false) {
  const stream = chatStreamRef.value
  if (!stream || force || isNearBottom({ scrollTop: stream.scrollTop, clientHeight: stream.clientHeight, scrollHeight: stream.scrollHeight })) {
    void nextTick(() => scrollToLatest(force ? 'smooth' : 'auto'))
  }
}

function abortActiveStream() {
  if (pendingResumeTimer !== null) {
    window.clearTimeout(pendingResumeTimer)
    pendingResumeTimer = null
  }
  streamController.value?.abort()
  streamController.value = null
}

function resetConversationSelection() {
  abortActiveStream()
  requestVersion.value += 1
  selectionVersion.value += 1
  selectedId.value = null
  messages.value = []
  paperType.value = ''
  conversationLoading.value = false
  streamNotice.value = ''
  error.value = ''
  copyNotice.value = ''
  artifactDrafts.value = {}
  openingDraft.value = { title: '', problem: '', plan: '', project_type: 'research' }
  materialDialogOpen.value = false
  pendingMaterialMessageId.value = null
  targetMaterialId.value = null
  materials.value = []
}

function replaceMessage(next: AIConversationMessage) {
  const index = messages.value.findIndex((item) => item.id === next.id)
  if (index >= 0) messages.value[index] = next
}

function scopedConversation(item: AIConversation) {
  if ((!showArchivedConversations.value && item.is_archived) || item.workspace_mode !== workbenchMode.value) return false
  return workbenchMode.value === 'opening' ? item.project === null : item.project === projectFilter.value
}

async function loadConversations(restoreConversation = true) {
  const response = projectFilter.value === null || workbenchMode.value === 'opening'
    ? await getAIConversations({ include_archived: showArchivedConversations.value })
    : await getAIConversations({ project: projectFilter.value, include_archived: showArchivedConversations.value })
  const scoped = response.data.filter(scopedConversation)
  conversations.value = scoped
  if (!restoreConversation) return
  const preferred = scoped.find((item) => item.id === selectedId.value) || scoped[0]
  if (preferred) await selectConversation(preferred)
}

async function refreshConversationList() {
  const response = projectFilter.value === null || workbenchMode.value === 'opening'
    ? await getAIConversations({ include_archived: showArchivedConversations.value })
    : await getAIConversations({ project: projectFilter.value, include_archived: showArchivedConversations.value })
  conversations.value = response.data.filter(scopedConversation)
}

function syncOpeningDraft(message?: AIConversationMessage) {
  if (!message?.artifact_payload) return
  let artifact = normalizeResearchQuestionArtifact(message.artifact_payload)
  if (!artifact && message.content?.trim()) {
    try { artifact = normalizeResearchQuestionArtifact(JSON.parse(message.content)) } catch { /* editable fields remain available when the response is plain text */ }
  }
  if (artifact) {
    openingDraft.value = researchProjectDraftFromArtifact(artifact, artifact.recommended_index)
    return
  }
  const payload = message.artifact_payload
  openingDraft.value = {
    title: String(payload.project_title || payload.title || '').trim(),
    problem: String(payload.draft || '').trim(),
    plan: String(payload.project_plan || '').trim(),
    project_type: payload.project_type === 'invention' || payload.project_type === 'engineering' ? payload.project_type : 'research',
  }
}

async function selectConversation(item: AIConversation) {
  if (sending.value) return
  const version = ++selectionVersion.value
  selectedId.value = item.id
  const modeAgent = modeAgents.value.find((agent) => agent.key === item.current_agent)
  if (modeAgent) selectedAgent.value = modeAgent.key
  paperType.value = normalizePaperType(item.paper_type)
  conversationLoading.value = true
  try {
    const response = await getAIConversationMessages(item.id)
    if (version !== selectionVersion.value || selectedId.value !== item.id) return
    messages.value = response.data
    const latestAssistant = [...messages.value].reverse().find((message) => message.role === 'assistant' && message.artifact_payload)
    if (workbenchMode.value === 'opening') syncOpeningDraft(latestAssistant)
    await nextTick()
    scrollToLatest('auto')
    const pendingMessage = [...messages.value].reverse().find((message) => isPendingAssistantMessage(message))
    if (pendingMessage) void resumePendingMessage(item.id, pendingMessage)
  } catch (reason) {
    if (version === selectionVersion.value) error.value = errorMessage(reason, '对话加载失败，请稍后重试。')
  } finally {
    if (version === selectionVersion.value) conversationLoading.value = false
  }
}

function isPendingAssistantMessage(message: AIConversationMessage): boolean {
  return message.role === 'assistant' && (message.status === 'queued' || message.status === 'streaming')
}

function schedulePendingResume(conversationId: number, messageId: number) {
  if (pendingResumeTimer !== null) window.clearTimeout(pendingResumeTimer)
  pendingResumeTimer = window.setTimeout(() => {
    pendingResumeTimer = null
    const pendingMessage = messages.value.find((message) => message.id === messageId)
    if (selectedId.value === conversationId && pendingMessage && isPendingAssistantMessage(pendingMessage)) {
      void resumePendingMessage(conversationId, pendingMessage)
    }
  }, 2500)
}

async function resumePendingMessage(conversationId: number, pendingMessage: AIConversationMessage) {
  if (sending.value || selectedId.value !== conversationId || !isPendingAssistantMessage(pendingMessage)) return
  const version = ++requestVersion.value
  const controller = new AbortController()
  streamController.value = controller
  sending.value = true
  streamNotice.value = '正在恢复后台生成状态…'
  try {
    await streamAssistant(conversationId, pendingMessage.id, version, controller)
    if (version !== requestVersion.value || controller.signal.aborted || selectedId.value !== conversationId) return
    const latest = messages.value.find((message) => message.id === pendingMessage.id)
    if (latest && isPendingAssistantMessage(latest)) {
      streamNotice.value = '生成仍在后台，页面会继续等待结果。'
      schedulePendingResume(conversationId, pendingMessage.id)
    } else {
      streamNotice.value = ''
    }
  } catch (reason) {
    if (controller.signal.aborted || version !== requestVersion.value) return
    try {
      const latest = (await getAIConversationMessages(conversationId)).data.find((message) => message.id === pendingMessage.id)
      if (latest) {
        replaceMessage(latest)
        if (isPendingAssistantMessage(latest)) {
          streamNotice.value = '生成仍在后台，页面会继续等待结果。'
          schedulePendingResume(conversationId, pendingMessage.id)
        } else {
          streamNotice.value = ''
        }
      }
    } catch (refreshReason) {
      error.value = errorMessage(refreshReason || reason, '生成状态恢复失败，请稍后重试。')
    }
  } finally {
    if (version === requestVersion.value) {
      sending.value = false
      streamController.value = null
    }
  }
}

async function ensureConversation() {
  if (selectedId.value && current.value && !current.value.is_archived) return selectedId.value
  if (projectRequired.value && !projectFilter.value) {
    error.value = '请先选择一个项目，再开始研究对话。'
    return null
  }
  const response = await createAIConversation({
    project: workbenchMode.value === 'opening' ? null : projectFilter.value,
    workspace_mode: workbenchMode.value,
    current_agent: currentAgent.value?.key || null,
    paper_type: paperTypeForRequest() || null,
  })
  const item = response.data
  conversations.value = [item, ...conversations.value]
  selectedId.value = item.id
  messages.value = []
  return item.id
}

async function conversationForSend() {
  const conversationId = await ensureConversation()
  return conversationId
}

async function sendMessage(contentOverride?: string) {
  const content = (contentOverride ?? draft.value).trim()
  if (!content || sending.value) return
  if (projectRequired.value && !currentProject.value) {
    error.value = '请先选择一个项目，再开始研究对话。'
    return
  }
  if (!currentAgent.value) {
    error.value = '当前模式暂未配置助手，请联系平台管理员。'
    return
  }
  const previousDraft = draft.value
  let conversationId: number | null = null
  // Lock the first-send path while the lazy conversation is being created.
  // This prevents a double click from creating two empty conversations.
  sending.value = true
  try {
    conversationId = await conversationForSend()
  } catch (reason) {
    error.value = errorMessage(reason, '创建对话失败，请稍后重试。')
    draft.value = previousDraft
    sending.value = false
    return
  }
  if (!conversationId) {
    sending.value = false
    return
  }
  const version = ++requestVersion.value
  const controller = new AbortController()
  streamController.value = controller
  error.value = ''
  streamNotice.value = ''
  const shouldClearDraft = contentOverride === undefined
  if (shouldClearDraft) draft.value = ''
  let assistantId: number | undefined
  try {
    const response = await createAIConversationMessage(conversationId, {
      content,
      agent_key: currentAgent.value.key,
      project: workbenchMode.value === 'opening' ? null : currentProject.value?.id,
      workspace_mode: workbenchMode.value,
      task: taskId.value,
      paper_type: paperTypeForRequest(),
      context_scope: {},
    })
    if (version !== requestVersion.value || controller.signal.aborted) return
    if (shouldClearDraft) messages.value.push({ id: -Date.now(), role: 'user', content, status: 'completed', created_at: new Date().toISOString() })
    messages.value.push(response.data)
    assistantId = response.data.id
    maybeScrollLatest(true)
    if ((response.data.status === 'queued' || response.data.status === 'streaming') && response.data.id) {
      await streamAssistant(conversationId, response.data.id, version, controller)
    }
    if (workbenchMode.value === 'opening' && assistantId) syncOpeningDraft(messages.value.find((item) => item.id === assistantId))
    await refreshConversationList()
  } catch (reason) {
    if (controller.signal.aborted) return
    const assistant = assistantId ? messages.value.find((item) => item.id === assistantId) : undefined
    if (assistant) {
      assistant.status = 'failed'
      assistant.error_message = errorMessage(reason, '生成失败，请点击重试。')
    }
    error.value = errorMessage(reason, '消息发送失败，请重试。')
    if (shouldClearDraft) draft.value = previousDraft
  } finally {
    if (version === requestVersion.value) {
      sending.value = false
      streamController.value = null
    }
  }
}

function regenerateMessage(message: AIConversationMessage) {
  if (sending.value || current.value?.is_archived) return
  const messageIndex = messages.value.findIndex((item) => item.id === message.id)
  const previousUserMessage = [...messages.value.slice(0, messageIndex)].reverse().find((item) => item.role === 'user' && item.content.trim())
  if (!previousUserMessage) {
    error.value = '找不到这条结果对应的问题，请直接在下方重新输入。'
    return
  }
  void sendMessage(previousUserMessage.content)
}

async function streamAssistant(conversationId: number, assistantId: number, version: number, controller: AbortController) {
  let terminal = false
  await streamAIConversationMessage(conversationId, assistantId, (event) => {
    if (version !== requestVersion.value || selectedId.value !== conversationId) return
    const assistant = messages.value.find((item) => item.id === assistantId)
    if (!assistant) return
    if (event.event === 'message.started') assistant.status = 'streaming'
    if (event.event === 'message.delta') {
      assistant.status = 'streaming'
      assistant.content += String(event.data.delta || event.data.text || '')
    }
    if (event.event === 'message.artifact') {
      assistant.artifact_payload = (event.data.artifact_payload as AIConversationMessage['artifact_payload']) || assistant.artifact_payload
      assistant.verification_items = (event.data.verification_items as AIConversationMessage['verification_items']) || assistant.verification_items
    }
    if (event.event === 'message.error') {
      assistant.status = 'failed'
      assistant.error_message = String(event.data.error || '生成失败')
    }
    if (event.event === 'message.done') assistant.status = 'completed'
    if (isTerminalSSEEvent(event.event)) terminal = true
    maybeScrollLatest()
  }, controller.signal)
  const streamedMessage = messages.value.find((item) => item.id === assistantId)
  if (workbenchMode.value === 'opening') syncOpeningDraft(streamedMessage)
  if (version !== requestVersion.value || selectedId.value !== conversationId || controller.signal.aborted || terminal) return
  const latest = (await getAIConversationMessages(conversationId)).data.find((item) => item.id === assistantId)
  if (!latest || version !== requestVersion.value || selectedId.value !== conversationId) return
  replaceMessage(latest)
  if (workbenchMode.value === 'opening') syncOpeningDraft(latest)
  if (latest.status === 'queued' || latest.status === 'streaming') streamNotice.value = '生成仍在后台，刷新页面可以继续查看。'
  maybeScrollLatest()
}

async function retryMessage(message: AIConversationMessage) {
  if (!selectedId.value) return
  if (sending.value || message.status !== 'failed' || current.value?.is_archived) return
  const conversationId = selectedId.value
  const version = ++requestVersion.value
  const controller = new AbortController()
  streamController.value = controller
  sending.value = true
  error.value = ''
  streamNotice.value = ''
  message.content = ''
  message.error_message = undefined
  message.status = 'queued'
  try {
    const response = await retryAIConversationMessage(conversationId, message.id)
    if (version !== requestVersion.value || controller.signal.aborted) return
    replaceMessage(response.data)
    maybeScrollLatest(true)
    if ((response.data.status === 'queued' || response.data.status === 'streaming') && response.data.id) await streamAssistant(conversationId, response.data.id, version, controller)
    await refreshConversationList()
  } catch (reason) {
    if (controller.signal.aborted) return
    const failedMessage = messages.value.find((item) => item.id === message.id) || message
    failedMessage.status = 'failed'
    failedMessage.error_message = errorMessage(reason, '重试失败，请稍后再试。')
  } finally {
    if (version === requestVersion.value) {
      sending.value = false
      streamController.value = null
    }
  }
}

function selectWorkbenchMode(mode: AIWorkspaceMode) {
  abortActiveStream()
  skipConversationRestore.value = true
  const projectId = mode === 'opening' ? null : currentProject.value?.id ?? projectFilter.value ?? auth.user.value?.primaryProject ?? projects.value.find((project) => project.status === 'active')?.id ?? null
  const query: Record<string, string> = { mode }
  if (projectId) query.projectId = String(projectId)
  if (mode === 'research' && taskId.value) query.taskId = String(taskId.value)
  void router.push({ path: '/student/ai', query })
}

function startNewConversation() {
  if (sending.value) return
  historyOpen.value = false
  skipConversationRestore.value = true
  resetConversationSelection()
  selectedAgent.value = routeAgentValue()
  normalizeSelectedAgent()
}

function openHistory() {
  if (!isNewConversation.value || sending.value) return
  historyOpen.value = true
}

function closeHistory() {
  historyOpen.value = false
}

async function toggleHistoryArchived() {
  if (sending.value) return
  showArchivedConversations.value = !showArchivedConversations.value
  await loadConversations(false)
}

function hasResult(message: AIConversationMessage) {
  if (message.role !== 'assistant' || message.status !== 'completed' || !message.artifact_payload) return false
  const artifact = message.artifact_payload
  return workbenchMode.value === 'opening'
    ? Boolean(artifact.candidates?.length || artifact.project_title || artifact.project_plan || artifact.project_type)
    : Boolean(artifact.draft?.trim())
}

function artifactDraftFor(message: AIConversationMessage) {
  return artifactDrafts.value[message.id] ?? message.artifact_payload?.draft ?? message.content
}

function copyMessage(message: AIConversationMessage) {
  const content = artifactDraftFor(message).trim()
  if (!content) return
  void navigator.clipboard?.writeText(content)
  copyNotice.value = '已复制结果内容。'
  window.setTimeout(() => { copyNotice.value = '' }, 1800)
}

async function openMaterialSave(message: AIConversationMessage) {
  if (workbenchMode.value === 'opening' || !currentProject.value) return
  pendingMaterialMessageId.value = message.id
  targetMaterialId.value = null
  materialDialogError.value = ''
  materialDialogOpen.value = true
  materialDialogLoading.value = true
  try {
    materials.value = (await getMaterials(currentProject.value.id)).data
  } catch (reason) {
    materialDialogError.value = errorMessage(reason, '材料列表加载失败，请稍后重试。')
  } finally {
    materialDialogLoading.value = false
  }
}

function closeMaterialDialog() {
  if (savingMessage.value !== null) return
  materialDialogOpen.value = false
  pendingMaterialMessageId.value = null
  targetMaterialId.value = null
  materialDialogError.value = ''
}

async function saveArtifact() {
  const message = pendingMaterialMessage.value
  const material = materials.value.find((item) => item.id === targetMaterialId.value)
  if (!message || !material) {
    materialDialogError.value = '请选择要保存到的目标材料。'
    return
  }
  const logId = Number(message.generation_log)
  const content = artifactDraftFor(message).trim()
  if (!logId || !content) {
    materialDialogError.value = '这份结果还没有可保存的内容。'
    return
  }
  savingMessage.value = message.id
  materialDialogError.value = ''
  try {
    await saveAIGenerationAsMaterial(logId, {
      material: material.id,
      content,
      workspace_mode: workbenchMode.value,
      revision_note: '由灵思 AI 生成结果保存为材料草稿',
    })
    streamNotice.value = `草稿已保存到“${material.title}”，请在任务页继续确认。`
    closeMaterialDialog()
  } catch (reason) {
    materialDialogError.value = errorMessage(reason, '保存材料草稿失败，请稍后重试。')
  } finally {
    savingMessage.value = null
  }
}

async function createProjectFromArtifact(message: AIConversationMessage) {
  if (workbenchMode.value !== 'opening' || !selectedId.value) return
  const payload = {
    title: openingDraft.value.title.trim(),
    problem: openingDraft.value.problem.trim(),
    plan: openingDraft.value.plan.trim(),
    project_type: openingDraft.value.project_type,
  }
  if (!payload.title || !payload.problem) {
    error.value = '请先补充项目标题和研究问题。'
    return
  }
  const artifact = normalizeResearchQuestionArtifact(message.artifact_payload)
  creatingProject.value = true
  error.value = ''
  try {
    const response = await createProjectFromOpening(selectedId.value, {
      confirm: true,
      message_id: message.id,
      candidate_index: artifact?.recommended_index ?? 0,
      ...payload,
    })
    projects.value.unshift(response.data)
    await router.push(studentProjectRoute(response.data.id, 'map'))
  } catch (reason) {
    error.value = errorMessage(reason, '项目创建失败，当前草稿已保留，请重试。')
  } finally {
    creatingProject.value = false
  }
}

function chooseProject() {
  void router.push('/student/projects')
}

function onGlobalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && materialDialogOpen.value) closeMaterialDialog()
}

function normalizeSelectedAgent() {
  selectedAgent.value = resolveStudentAgent(workbenchMode.value, agents.value, selectedAgent.value, current.value?.current_agent)?.key
}

async function loadProjectsResource() {
  projectsLoading.value = true
  projectResourceError.value = ''
  try {
    projects.value = (await getProjects()).data
    projectFilter.value = defaultProjectId(workbenchMode.value, projects.value)
  } catch (reason) {
    projectResourceError.value = errorMessage(reason, '项目加载失败，请重试。')
  } finally {
    projectsLoading.value = false
  }
}

async function loadAgentsResource() {
  agentsLoading.value = true
  agentResourceError.value = ''
  try {
    agents.value = (await getAIAgents()).data
    normalizeSelectedAgent()
  } catch (reason) {
    agentResourceError.value = errorMessage(reason, '当前模式的助手加载失败，请重试。')
  } finally {
    agentsLoading.value = false
  }
}

async function bootstrapWorkbench() {
  loading.value = true
  error.value = ''
  try {
    const projectsPromise = loadProjectsResource()
    const agentsPromise = loadAgentsResource()
    await projectsPromise
    // The shell and the direct input can render as soon as project context is
    // known. Agent templates continue loading in the background and only
    // affect send availability, so a slow template request does not blank the
    // workbench.
    loading.value = false
    normalizeSelectedAgent()
    await loadConversations()
    await agentsPromise
    normalizeSelectedAgent()
  } catch (reason) {
    error.value = errorMessage(reason, '工作台资源加载失败，请重试。')
  } finally {
    loading.value = false
    await nextTick()
    scrollToLatest('auto')
  }
}

let applyingRouteContext = false
async function reloadForRouteContext() {
  if (applyingRouteContext) return
  applyingRouteContext = true
  try {
    const restoreConversation = !skipConversationRestore.value
    skipConversationRestore.value = false
    projectFilter.value = workbenchMode.value === 'opening' ? null : queryNumber(route.query.projectId) ?? defaultProjectId(workbenchMode.value, projects.value)
    taskId.value = queryNumber(route.query.taskId) ?? undefined
    selectedAgent.value = routeAgentValue()
    resetConversationSelection()
    normalizeSelectedAgent()
    await loadConversations(restoreConversation)
  } catch (reason) {
    error.value = errorMessage(reason, '工作台上下文切换失败，请重试。')
  } finally {
    applyingRouteContext = false
  }
}

watch([workbenchMode, () => modeAgents.value.map((agent) => agent.key).join('|')], normalizeSelectedAgent, { immediate: true })
watch(() => [route.query.mode, route.query.projectId, route.query.taskId, route.query.researchQuestion] as const, (next, previous) => {
  if (!previous || next.every((value, index) => value === previous[index])) return
  void reloadForRouteContext()
})

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
  void bootstrapWorkbench()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  requestVersion.value += 1
  abortActiveStream()
})
</script>

<template>
  <div class="page ai-center-page ai-workbench-frame" :class="{ 'ai-workbench-page--new': isNewConversation, 'ai-workbench-page--active': isConversationStarted }">
    <template v-if="isNewConversation">
      <div class="ai-workbench-new-state">
        <header class="ai-workbench-header ai-workbench-header--new" aria-labelledby="ai-workbench-title">
          <div class="ai-workbench-heading">
            <span class="eyebrow">研究工作台</span>
            <h1 id="ai-workbench-title">灵思 AI</h1>
          </div>
          <div class="ai-workbench-header__actions">
            <span class="ai-workbench-context-pill">{{ workspaceContextLabel }}</span>
            <button class="text-button" type="button" :disabled="sending || loading || !conversations.length" @click="openHistory">历史会话</button>
          </div>
        </header>

        <section class="ai-workbench-mode-region" aria-label="灵思 AI 模式">
          <AIModeTabs :model-value="workbenchMode" :disabled="sending" :show-agent-rail="false" :show-mode-descriptions="false" @update:model-value="selectWorkbenchMode" />
        </section>

        <section v-if="loading || projectsLoading" class="ai-workbench-skeleton" role="status" aria-label="正在准备灵思 AI"><i /><i /><i /></section>
        <section v-else-if="(projectRequired && !currentProject) || (!agentsLoading && !currentAgent)" class="ai-workbench-context-note" role="status">
          <span v-if="projectRequired && !currentProject">研究和成果表达默认绑定你的主项目，请先在“我的项目”创建或设置主项目。</span>
          <span v-else>当前模式暂未配置 AI 助手，请联系平台管理员。</span>
          <button v-if="projectRequired && !currentProject" class="secondary-button" type="button" @click="chooseProject">去我的项目</button>
        </section>
      </div>
    </template>

    <template v-else>
      <header class="ai-workbench-active-state" aria-label="当前灵思 AI 对话">
        <div class="ai-active-context">
          <span class="eyebrow">灵思 AI</span>
          <span>{{ workspaceContextLabel }}</span>
        </div>
        <button class="text-button" type="button" :disabled="sending" @click="startNewConversation">新建对话</button>
      </header>

      <section class="ai-active-chat" aria-label="灵思 AI 消息记录">
        <section ref="chatStreamRef" class="ai-conversation-stream" aria-live="polite" :aria-busy="sending" @scroll="updateScrollAffordance">
          <div v-if="conversationLoading" class="ai-stream-loading"><span class="ai-loading-dot" />正在恢复对话…</div>
          <article v-for="message in messages" :key="message.id" class="ai-message" :class="message.role">
            <div class="ai-message__label">{{ message.role === 'user' ? '你' : '灵思 AI' }}</div>
            <div class="ai-message__body">
              <p v-for="(block, blockIndex) in messageBlocks(message.content)" :key="`${message.id}-${blockIndex}`">{{ block }}</p>
              <p v-if="!message.content && (message.status === 'queued' || message.status === 'streaming')" class="ai-message__pending">{{ message.status === 'queued' ? '正在排队…' : '正在生成…' }}</p>
              <div v-if="message.status === 'failed'" class="ai-message__error"><span>{{ message.error_message || '生成失败' }}</span><button type="button" :disabled="sending" @click="retryMessage(message)">{{ sending ? '重试中…' : '重试' }}</button></div>
              <AIResultCard
                v-if="hasResult(message)"
                data-result-actions="确认创建项目 / 保存为材料"
                :mode="workbenchMode"
                :message="message"
                :draft="artifactDraftFor(message)"
                :opening-draft="openingDraft"
                :saving="savingMessage === message.id"
                :creating-project="creatingProject"
                :can-save-material="Boolean(currentProject && message.generation_log)"
                :can-create-project="workbenchMode === 'opening' && Boolean(selectedId)"
                @update:draft="artifactDrafts[message.id] = $event"
                @update:opening-draft="openingDraft = $event"
                @save-material="void openMaterialSave(message)"
                @create-project="void createProjectFromArtifact(message)"
                @retry="regenerateMessage(message)"
                @copy="copyMessage(message)"
              />
            </div>
          </article>
        </section>
        <button v-if="showJumpLatest" type="button" class="jump-latest" @click="scrollToLatest()">↓ 跳到最新消息</button>
      </section>
    </template>

    <div v-if="resourceErrorMessage || error || streamNotice || copyNotice" class="ai-workbench-notices">
      <div v-if="resourceErrorMessage" class="ai-resource-notice" role="status"><span>{{ resourceErrorMessage }}</span><button type="button" :disabled="loading" @click="void bootstrapWorkbench()">重试加载</button></div>
      <div v-if="error" class="error-banner" role="alert"><span>{{ error }}</span><button type="button" :disabled="loading || sending" @click="void bootstrapWorkbench()">重试</button></div>
      <div v-if="streamNotice || copyNotice" class="stream-notice" role="status">{{ streamNotice || copyNotice }}</div>
    </div>

    <div class="ai-workbench-composer-host">
      <AIWorkbenchComposer
        :draft="draft"
        :mode="workbenchMode"
        :disabled="composerDisabled"
        :can-send="composerCanSend"
        :sending="sending"
        :show-meta="false"
        :show-material-citation="false"
        @update:draft="draft = $event"
        @send="void sendMessage()"
        @stop="abortActiveStream()"
      />
    </div>

    <AIConversationHistory
      v-if="isNewConversation && historyOpen"
      :groups="historyGroups"
      :selected-id="selectedId"
      :sending="sending"
      :search="historySearch"
      :show-archived="showArchivedConversations"
      @update:search="historySearch = $event"
      @new="startNewConversation"
      @select="historyOpen = false; void selectConversation($event)"
      @toggle-archived="void toggleHistoryArchived()"
      @close="closeHistory"
    />

    <div v-if="materialDialogOpen" class="ai-confirm-backdrop" role="presentation" @click.self="closeMaterialDialog">
      <section class="ai-material-dialog" role="dialog" aria-modal="true" aria-labelledby="save-material-title">
        <header><div><span class="eyebrow">结果确认</span><h2 id="save-material-title">保存为材料</h2></div><button class="ai-dialog-close" type="button" aria-label="关闭" @click="closeMaterialDialog">×</button></header>
        <p>选择当前项目中的目标材料，AI 内容会作为草稿写入，不会自动提交审核。</p>
        <div v-if="materialDialogError" class="ai-dialog-error" role="alert">{{ materialDialogError }}</div>
        <div v-if="materialDialogLoading" class="ai-dialog-loading">正在加载当前项目材料…</div>
        <label v-else class="ai-material-target"><span>目标材料</span><select v-model="targetMaterialId"><option :value="null">请选择目标材料</option><option v-for="material in materials" :key="material.id" :value="material.id">{{ material.title }}</option></select></label>
        <div v-if="!materialDialogLoading && !materials.length" class="ai-dialog-empty">当前项目还没有可保存的材料。</div>
        <footer><button class="secondary-button" type="button" @click="closeMaterialDialog">取消</button><button class="primary-button" type="button" :disabled="materialDialogLoading || savingMessage !== null || !materials.length" @click="void saveArtifact()">{{ savingMessage !== null ? '保存中…' : '保存为材料' }}</button></footer>
      </section>
    </div>
  </div>
</template>

<style scoped>
.ai-center-page { display: flex; width: 100%; max-width: var(--content-max); min-width: 0; min-height: calc(100vh - var(--topbar-height)); flex-direction: column; box-sizing: border-box; margin: 0 auto; padding: 28px 0 24px; overflow: visible; }
.ai-workbench-page--new { min-height: calc(100vh - var(--topbar-height) - 52px); }
.ai-workbench-new-state { display: flex; min-width: 0; min-height: 0; flex: 0 0 auto; flex-direction: column; }
.ai-workbench-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding-bottom: 17px; border-bottom: 1px solid var(--line); }
.ai-workbench-heading { min-width: 0; }
.ai-workbench-heading h1 { margin: 3px 0 5px; color: var(--ink); font: 700 clamp(32px, 4vw, 48px)/1.08 var(--sans); letter-spacing: -.045em; }
.ai-workbench-heading p { max-width: 740px; margin: 0; color: var(--muted); font-size: 13px; line-height: 1.65; }
.ai-workbench-header__actions { display: flex; align-items: center; justify-content: flex-end; gap: 9px; min-width: 0; padding-top: 4px; }
.ai-workbench-context-pill { flex: 0 1 auto; max-width: 420px; overflow: hidden; padding: 8px 12px; border: 1px solid var(--sage-line); border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); font-size: 11px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.text-button { min-height: 32px; padding: 6px 10px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); background: var(--paper); color: var(--moss-dark); font: inherit; font-size: 11px; font-weight: 700; cursor: pointer; }
.text-button:hover:not(:disabled), .text-button:focus-visible { border-color: var(--moss); background: var(--sage-soft); }
.text-button:disabled { cursor: not-allowed; opacity: .48; }
.ai-workbench-mode-region { width: min(100%, 900px); margin: 22px auto 0; }
.ai-workbench-skeleton { display: grid; gap: 10px; width: min(100%, 900px); margin: 28px auto 0; }
.ai-workbench-skeleton i { display: block; height: 10px; border-radius: 999px; background: var(--paper-muted); animation: ai-workbench-pulse 1.2s ease-in-out infinite alternate; }
.ai-workbench-skeleton i:nth-child(1) { width: 42%; }.ai-workbench-skeleton i:nth-child(2) { width: 68%; animation-delay: .12s; }.ai-workbench-skeleton i:nth-child(3) { width: 54%; animation-delay: .24s; }
@keyframes ai-workbench-pulse { from { opacity: .45; } to { opacity: 1; } }
.ai-workbench-context-note { display: flex; align-items: center; justify-content: space-between; gap: 14px; width: min(100%, 900px); box-sizing: border-box; margin: 18px auto 0; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--muted); font-size: 11px; line-height: 1.55; }
.ai-workbench-context-note .secondary-button { flex: 0 0 auto; }
.ai-workbench-page--active { height: calc(100vh - var(--topbar-height) - 104px); min-height: 0; overflow: hidden; display: grid; grid-template-rows: auto minmax(0, 1fr) auto auto; }
.ai-workbench-active-state { display: flex; align-items: center; justify-content: space-between; gap: 18px; min-width: 0; padding-bottom: 12px; border-bottom: 1px solid var(--line); }
.ai-active-context { display: flex; align-items: center; gap: 10px; min-width: 0; color: var(--moss-dark); font-size: 12px; font-weight: 700; }
.ai-active-context .eyebrow { flex: 0 0 auto; margin: 0; }
.ai-active-context > span:last-child { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-active-chat { display: grid; grid-template-rows: minmax(0, 1fr) auto; gap: 8px; min-width: 0; min-height: 0; overflow: hidden; }
.ai-conversation-stream { display: grid; align-content: start; gap: 22px; width: min(100%, 900px); min-height: 0; height: 100%; overflow-y: auto; box-sizing: border-box; margin: 0 auto; padding: 22px 8px 26px; scrollbar-width: thin; }
.ai-message { display: grid; gap: 7px; width: min(100%, 800px); min-width: 0; color: var(--ink); line-height: 1.75; }
.ai-message.user { justify-self: end; width: min(72%, 640px); }
.ai-message__label { color: var(--muted); font-size: 10px; }
.ai-message.user .ai-message__label { text-align: right; }
.ai-message__body { display: grid; gap: 10px; min-width: 0; color: var(--ink); font-size: 13px; line-height: 1.8; overflow-wrap: anywhere; }
.ai-message__body p { margin: 0; white-space: pre-wrap; }
.ai-message.user .ai-message__body { display: block; padding: 11px 14px; border: 1px solid var(--sage-line); border-radius: 14px 14px 4px 14px; background: var(--sage-soft); }
.ai-message__pending { color: var(--muted-light); }
.ai-message__error { display: flex; align-items: center; gap: 10px; margin-top: 8px; color: var(--danger); font-size: 11px; }
.ai-message__error button { border: 1px solid currentColor; border-radius: 999px; padding: 4px 9px; background: transparent; color: inherit; font: inherit; cursor: pointer; }
.ai-stream-loading { display: flex; align-items: center; gap: 8px; color: var(--muted); font-size: 11px; }
.ai-loading-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--moss); animation: ai-workbench-pulse 1s ease-in-out infinite alternate; }
.jump-latest { justify-self: center; border: 1px solid var(--line-dark); border-radius: 999px; padding: 6px 11px; background: var(--paper); color: var(--moss-dark); font: inherit; font-size: 10px; cursor: pointer; }
.ai-workbench-composer-host { width: min(100%, 900px); min-width: 0; margin: 24px auto 0; }
.ai-workbench-page--new .ai-workbench-composer-host { margin-top: clamp(48px, 8vh, 88px); }
.ai-workbench-page--active .ai-workbench-composer-host { position: sticky; bottom: 0; z-index: 2; padding-top: 8px; background: linear-gradient(to bottom, rgba(243, 244, 240, 0), var(--ivory) 26%); }
.ai-center-page :deep(.ai-workbench-composer) { width: 100%; box-sizing: border-box; border-color: var(--line-dark); box-shadow: 0 12px 30px rgba(42, 70, 47, .09); }
.ai-center-page :deep(.ai-workbench-composer__textarea) { min-height: 78px; }
.ai-workbench-notices { display: grid; gap: 8px; min-width: 0; margin-top: 9px; }
.ai-resource-notice, .error-banner, .stream-notice { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 11px; border: 1px solid var(--line); border-radius: var(--radius-sm); font-size: 11px; line-height: 1.5; }
.ai-resource-notice { background: var(--paper-soft); color: var(--muted); }.error-banner { border-color: #e5c8c0; background: #fff7f4; color: #8e4438; }.stream-notice { background: var(--sage-soft); color: var(--moss-dark); }
.ai-resource-notice button, .error-banner button { flex: 0 0 auto; border: 0; background: transparent; color: var(--moss-dark); font: inherit; font-weight: 700; cursor: pointer; }
.primary-button, .secondary-button { min-height: 34px; padding: 7px 13px; border-radius: var(--radius-sm); font: inherit; font-size: 11px; cursor: pointer; }.primary-button { border: 1px solid var(--moss-dark); background: var(--moss); color: #fff; font-weight: 700; }.primary-button:hover:not(:disabled), .primary-button:focus-visible { background: var(--moss-dark); }.secondary-button { border: 1px solid var(--line-dark); background: var(--paper); color: var(--moss-dark); }.secondary-button:hover:not(:disabled), .secondary-button:focus-visible { border-color: var(--moss); background: var(--paper-soft); }.primary-button:disabled, .secondary-button:disabled { cursor: wait; opacity: .55; }
.ai-confirm-backdrop { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; padding: 24px; background: rgba(32, 47, 38, .22); }.ai-material-dialog { display: grid; gap: 14px; width: min(100%, 480px); box-sizing: border-box; padding: 22px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-hover); }.ai-material-dialog header, .ai-material-dialog footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.ai-material-dialog h2 { margin: 4px 0 0; color: var(--ink); font: 700 22px/1.2 var(--sans); }.ai-material-dialog > p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.65; }.ai-dialog-close { width: 28px; height: 28px; border: 0; border-radius: 50%; background: transparent; color: var(--muted); font-size: 22px; cursor: pointer; }.ai-dialog-close:hover, .ai-dialog-close:focus-visible { background: var(--paper-soft); color: var(--ink); }.ai-material-target { display: grid; gap: 6px; color: var(--muted); font-size: 11px; font-weight: 700; }.ai-material-target select { width: 100%; box-sizing: border-box; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); padding: 9px 10px; background: var(--paper-soft); color: var(--ink); font: inherit; font-size: 12px; }.ai-dialog-error { padding: 9px 10px; border-radius: var(--radius-sm); background: #fff7f4; color: #8e4438; font-size: 11px; }.ai-dialog-loading, .ai-dialog-empty { color: var(--muted); font-size: 11px; }.ai-material-dialog footer { justify-content: flex-end; }
@media (max-width: 1279px) { .ai-center-page { padding-inline: 20px; } }
@media (max-width: 720px) { .ai-workbench-header { align-items: flex-start; flex-direction: column; }.ai-workbench-header__actions { align-items: flex-start; justify-content: flex-start; flex-wrap: wrap; padding-top: 0; }.ai-workbench-context-pill { max-width: 100%; }.ai-workbench-context-note { align-items: stretch; flex-direction: column; }.ai-message.user { width: 86%; }.ai-confirm-backdrop { padding: 14px; } }
</style>
