<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createAIConversation, createAIConversationMessage, createProjectFromOpening, errorMessage, getAIAgents, getAIConversationMessages, getAIConversations, getMaterials, getProjects, retryAIConversationMessage, saveAIGenerationAsMaterial, streamAIConversationMessage, type AIAgent, type AIConversation, type AIConversationMessage, type Material, type Project } from '../../api'
import { auth } from '../../stores/auth'
import { groupAgentsByCategory, isNearBottom, isTerminalSSEEvent, normalizeResearchQuestionArtifact, researchProjectDraftFromArtifact } from '../../stores/aiConversationModel'
import { normalizeAIWorkspaceMode, resolveStudentAgent, visibleAgents, workspaceModeDescription, type AIWorkspaceMode } from '../../stores/aiWorkbenchModel'
import { PAPER_TYPES, type PaperType } from '../../stores/aiModel'
import { studentProjectRoute } from '../../stores/pageContracts'
import { filterConversationSummaries, groupConversationSummaries, hasConversationMessages } from '../../stores/presentationModel'
import AIConversationHistory from '../../components/ai/AIConversationHistory.vue'
import AIModeTabs from '../../components/ai/AIModeTabs.vue'
import AIResultCard from '../../components/ai/AIResultCard.vue'
import AIToolPicker from '../../components/ai/AIToolPicker.vue'
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

function routeConversationId() {
  return queryNumber(route.query.conversationId)
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
const historyConversations = ref<AIConversation[]>([])
const messages = ref<AIConversationMessage[]>([])
const projects = ref<Project[]>([])
const agents = ref<AIAgent[]>([])
const selectedId = ref<number | null>(null)
const skillPickerOpen = ref(false)
const skillSearch = ref('')
const skillCategory = ref('all')
const historyOpen = ref(false)
const historySearch = ref('')
const showArchivedConversations = ref(false)
const historyModeFilter = ref<AIWorkspaceMode>(routeModeValue())
const projectFilter = ref<number | null>(routeModeValue() === 'opening' ? null : queryNumber(route.query.projectId) ?? auth.user.value?.primaryProject ?? null)
const selectedSkillKey = ref<string | undefined>(routeAgentValue())
const paperType = ref<PaperType | ''>('')
const taskId = ref<number | undefined>(queryNumber(route.query.taskId) ?? undefined)
const draft = ref('')
const draftsByConversation = ref<Record<string, string>>({})
const draftContextMode = ref<AIWorkspaceMode>(routeModeValue())
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
const currentAgent = computed(() => resolveStudentAgent(workbenchMode.value, agents.value, selectedSkillKey.value, current.value?.current_agent))
const activeSkill = computed(() => {
  const key = selectedSkillKey.value || current.value?.current_agent
  return key ? modeAgents.value.find((agent) => agent.key === key) || null : null
})
const skillCategories = computed(() => ['all', ...new Set(modeAgents.value.map((agent) => agent.category?.trim()).filter(Boolean) as string[])])
const skillGroups = computed(() => {
  const keyword = skillSearch.value.trim().toLowerCase()
  const filtered = modeAgents.value.filter((agent) => {
    const matchesSearch = !keyword || `${agent.name} ${agent.description} ${agent.key}`.toLowerCase().includes(keyword)
    const matchesCategory = skillCategory.value === 'all' || (agent.category || '其他') === skillCategory.value
    return matchesSearch && matchesCategory
  })
  return groupAgentsByCategory(filtered)
})
const projectRequired = computed(() => workbenchMode.value !== 'opening')
const isConversationStarted = computed(() => messages.value.some((message) => Boolean(message.content?.trim()) || message.status === 'queued' || message.status === 'streaming'))
const isNewConversation = computed(() => !isConversationStarted.value)
const workbenchDescription = computed(() => workspaceModeDescription(workbenchMode.value))
const resourceErrorMessage = computed(() => [projectResourceError.value, agentResourceError.value].filter(Boolean).join('；'))
const historyGroups = computed(() => {
  const modeScoped = historyConversations.value.filter((item) => item.workspace_mode === historyModeFilter.value)
  return groupConversationSummaries(filterConversationSummaries(modeScoped, historySearch.value, showArchivedConversations.value))
})
const workspaceContextLabel = computed(() => {
  if (workbenchMode.value === 'opening') return '开题 · 不绑定项目'
  const modeLabel = workbenchMode.value === 'defense' ? '成果表达' : '研究'
  return currentProject.value ? `当前项目 · ${currentProject.value.title}` : `${modeLabel} · 尚未选择项目`
})
const modeLabel = computed(() => workbenchMode.value === 'opening' ? '开题' : workbenchMode.value === 'defense' ? '成果表达' : '研究')
const newConversationTitle = computed(() => workbenchMode.value === 'opening' ? '从一个问题开始' : workbenchMode.value === 'defense' ? '把成果说清楚' : '推进下一步研究')
const newConversationHint = computed(() => workbenchMode.value === 'opening'
  ? '写下你的观察、问题或研究想法，灵思会直接回应并帮你整理成下一步。'
  : workbenchMode.value === 'defense'
    ? '写下要展示的成果或担心的答辩问题，灵思会帮你整理表达。'
    : '写下你要继续完成的研究任务，灵思会结合当前项目给出建议。')
const emptyWorkflow = computed(() => {
  if (workbenchMode.value === 'opening') {
    return [
      { label: '01', title: '描述一个观察', description: '现象、困惑或想验证的事情' },
      { label: '02', title: '形成研究问题', description: '拆出对象、变量和证据计划' },
      { label: '03', title: '确认开题草稿', description: '修改后再保存为项目' },
    ]
  }
  if (workbenchMode.value === 'defense') {
    return [
      { label: '01', title: '说出要表达的成果', description: '项目亮点、过程或答辩担心的地方' },
      { label: '02', title: '整理表达重点', description: '形成摘要、展示结构和回应思路' },
      { label: '03', title: '确认展示内容', description: '按需修改后用于汇报或答辩' },
    ]
  }
  return [
    { label: '01', title: '说出当前任务', description: '实验、数据、材料或卡住的位置' },
    { label: '02', title: '得到下一步方案', description: '明确动作、证据和需要核验的风险' },
    { label: '03', title: '留存研究记录', description: '确认后再保存到项目材料' },
  ]
})
const composerDisabled = computed(() => loading.value || conversationLoading.value || sending.value || Boolean(current.value?.is_archived) || (projectRequired.value && !currentProject.value))
const composerCanSend = computed(() => Boolean(draft.value.trim() && !composerDisabled.value))
const pendingMaterialMessage = computed(() => messages.value.find((message) => message.id === pendingMaterialMessageId.value) || null)

function draftKey(id: number | null, mode = draftContextMode.value) {
  return id === null ? `new:${mode}` : `conversation:${id}`
}

function stashDraft(id = selectedId.value, mode = draftContextMode.value) {
  const key = draftKey(id, mode)
  if (draft.value) draftsByConversation.value[key] = draft.value
  else delete draftsByConversation.value[key]
}

function restoreDraft(id: number | null, mode = draftContextMode.value) {
  draft.value = draftsByConversation.value[draftKey(id, mode)] || ''
}

function normalizePaperType(value: unknown): PaperType | '' {
  return PAPER_TYPES.some((item) => item.key === value) ? value as PaperType : ''
}

function paperTypeForRequest(): PaperType | undefined {
  if (paperType.value) return paperType.value
  // Paper templates still have a backend paper_type contract. Keep that
  // compatibility internal so the simplified student chat never asks users
  // to fill in a technical field before they can send a message.
  return workbenchMode.value === 'opening' || currentAgent.value?.key.startsWith('paper-') ? PAPER_TYPES[0].key : undefined
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
  stashDraft(selectedId.value, draftContextMode.value)
  abortActiveStream()
  requestVersion.value += 1
  selectionVersion.value += 1
  selectedId.value = null
  skillPickerOpen.value = false
  skillSearch.value = ''
  skillCategory.value = 'all'
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
  historyOpen.value = false
  draftContextMode.value = workbenchMode.value
  restoreDraft(null, draftContextMode.value)
}

function replaceMessage(next: AIConversationMessage) {
  const index = messages.value.findIndex((item) => item.id === next.id)
  if (index >= 0) messages.value[index] = next
}

function scopedConversation(item: AIConversation) {
  if ((!showArchivedConversations.value && item.is_archived) || item.workspace_mode !== workbenchMode.value) return false
  return workbenchMode.value === 'opening' ? item.project === null : item.project === projectFilter.value
}

function currentContextConversations(items: AIConversation[]) {
  const scoped = items.filter(scopedConversation)
  const requestedId = routeConversationId()
  const requested = requestedId ? items.find((item) => item.id === requestedId) : undefined
  if (requested && !scoped.some((item) => item.id === requested.id)) return [requested, ...scoped]
  return scoped
}

async function loadConversations(restoreConversation = true) {
  const response = await getAIConversations({ include_archived: true })
  historyConversations.value = response.data.filter(hasConversationMessages)
  const scoped = currentContextConversations(response.data)
  conversations.value = scoped
  if (!restoreConversation) return
  const requestedId = routeConversationId()
  const preferred = requestedId
    ? response.data.find((item) => item.id === requestedId)
    : undefined
  if (preferred) await selectConversation(preferred)
}

async function refreshConversationList() {
  const response = await getAIConversations({ include_archived: true })
  historyConversations.value = response.data.filter(hasConversationMessages)
  conversations.value = currentContextConversations(response.data)
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
  stashDraft()
  const version = ++selectionVersion.value
  selectedId.value = item.id
  draftContextMode.value = workbenchMode.value
  restoreDraft(item.id, draftContextMode.value)
  const modeAgent = modeAgents.value.find((agent) => agent.key === item.current_agent)
  selectedSkillKey.value = modeAgent?.key
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
  stashDraft(null, draftContextMode.value)
  conversations.value = [item, ...conversations.value]
  selectedId.value = item.id
  messages.value = []
  void router.replace({ path: '/student/ai', query: { ...route.query, conversationId: String(item.id) } })
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
  if (shouldClearDraft) {
    draft.value = ''
    stashDraft()
  }
  let assistantId: number | undefined
  try {
    const response = await createAIConversationMessage(conversationId, {
      content,
      agent_key: currentAgent.value?.key,
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
    if (shouldClearDraft) {
      draft.value = previousDraft
      stashDraft()
    }
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
  skillPickerOpen.value = false
  historyModeFilter.value = mode
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
  selectedSkillKey.value = routeAgentValue()
  normalizeSelectedAgent()
  if (routeConversationId() !== null) {
    const query = { ...route.query }
    delete query.conversationId
    void router.replace({ path: '/student/ai', query })
  }
}

function openSkillPicker() {
  if (sending.value) return
  skillPickerOpen.value = true
}

function closeSkillPicker() {
  skillPickerOpen.value = false
}

function chooseSkill(agent: AIAgent) {
  selectedSkillKey.value = agent.key
  closeSkillPicker()
  skillSearch.value = ''
  skillCategory.value = 'all'
}

function openHistory() {
  if (sending.value) return
  historyOpen.value = true
}

function openConversationFromHistory(item: AIConversation) {
  if (sending.value) return
  historyOpen.value = false
  const mode = normalizeAIWorkspaceMode(item.workspace_mode)
  const query: Record<string, string> = { mode, conversationId: String(item.id) }
  if (mode !== 'opening' && item.project) query.projectId = String(item.project)
  if (item.current_agent) query.agent = item.current_agent
  skipConversationRestore.value = false
  void router.push({ path: '/student/ai', query })
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
  if (event.key === 'Escape' && skillPickerOpen.value) {
    closeSkillPicker()
    return
  }
  if (event.key === 'Escape' && historyOpen.value) {
    closeHistory()
    return
  }
  if (event.key === 'Escape' && materialDialogOpen.value) closeMaterialDialog()
}

function normalizeSelectedAgent() {
  if (agentsLoading.value) return
  if (selectedSkillKey.value && !modeAgents.value.some((agent) => agent.key === selectedSkillKey.value)) selectedSkillKey.value = undefined
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
    await loadConversations(routeConversationId() !== null)
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
    const restoreConversation = routeConversationId() !== null && !skipConversationRestore.value
    skipConversationRestore.value = false
    historyModeFilter.value = workbenchMode.value
    projectFilter.value = workbenchMode.value === 'opening' ? null : queryNumber(route.query.projectId) ?? defaultProjectId(workbenchMode.value, projects.value)
    taskId.value = queryNumber(route.query.taskId) ?? undefined
    selectedSkillKey.value = routeAgentValue()
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
watch(() => [route.query.mode, route.query.projectId, route.query.taskId, route.query.researchQuestion, route.query.agent, route.query.conversationId] as const, (next, previous) => {
  if (!previous || next.every((value, index) => value === previous[index])) return
  const contextChanged = next.slice(0, 5).some((value, index) => value !== previous[index])
  if (!contextChanged && routeConversationId() === selectedId.value) {
    historyOpen.value = false
    return
  }
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
  <div class="page ai-center-page ai-workbench-frame ai-workbench-main" :class="{ 'ai-workbench-page--new': isNewConversation, 'ai-workbench-page--active': isConversationStarted }">
    <div class="ai-workbench-canvas">
      <template v-if="isNewConversation">
        <header class="ai-workbench-header" aria-labelledby="ai-workbench-title">
          <div class="ai-workbench-heading">
            <span class="eyebrow">研究工作台</span>
            <h1 id="ai-workbench-title">灵思 AI</h1>
            <p>{{ workbenchDescription }}</p>
          </div>
          <div class="ai-workbench-header__actions">
            <span class="ai-workbench-context-pill">{{ workspaceContextLabel }}</span>
            <button v-if="historyConversations.length" class="text-button ai-workbench-history-button" type="button" :disabled="sending || loading" aria-controls="conversation-history" :aria-expanded="historyOpen" @click="openHistory">历史会话</button>
          </div>
        </header>

        <section class="ai-workbench-content" :class="{ 'ai-workbench-content--opening': workbenchMode === 'opening' }" aria-label="新建灵思 AI 对话">
          <section class="ai-workbench-mode-region" aria-label="灵思 AI 主 Agent">
            <AIModeTabs :model-value="workbenchMode" :disabled="sending" :show-agent-rail="false" :show-mode-descriptions="true" @update:model-value="selectWorkbenchMode" />
          </section>

          <section v-if="loading || projectsLoading || conversationLoading" class="ai-workbench-skeleton" role="status" aria-label="正在准备灵思 AI"><i /><i /><i /></section>
          <section v-else-if="projectRequired && !currentProject" class="ai-workbench-context-note" role="status">
            <span v-if="projectRequired && !currentProject">研究和成果表达默认绑定你的主项目，请先在“我的项目”创建或设置主项目。</span>
            <button v-if="projectRequired && !currentProject" class="secondary-button" type="button" @click="chooseProject">去我的项目</button>
          </section>
          <section v-else class="ai-workbench-empty" aria-label="开始对话">
            <div class="ai-workbench-empty__intro">
              <span class="eyebrow">{{ modeLabel }} · 直接输入</span>
              <h2>{{ newConversationTitle }}</h2>
              <p>{{ newConversationHint }}</p>
            </div>
            <div class="ai-workbench-empty__guide" aria-label="工作方式">
              <div class="ai-workbench-empty__guide-heading">
                <span class="eyebrow">灵思会这样推进</span>
                <span>一段输入，三步得到可继续修改的结果</span>
              </div>
              <ol class="ai-workbench-empty__steps">
                <li v-for="step in emptyWorkflow" :key="step.label">
                  <span class="ai-workbench-empty__step-index">{{ step.label }}</span>
                  <span class="ai-workbench-empty__step-copy">
                    <strong>{{ step.title }}</strong>
                    <small>{{ step.description }}</small>
                  </span>
                </li>
              </ol>
            </div>
          </section>
        </section>
      </template>

      <section v-else class="ai-active-chat" aria-label="灵思 AI 对话工作区">
        <div class="ai-workbench-active-toolbar" aria-label="当前对话工具栏">
          <div class="ai-active-toolbar__identity">
            <strong>灵思 AI</strong>
            <span class="ai-active-toolbar__context">{{ workspaceContextLabel }}</span>
            <span class="ai-active-toolbar__mode">{{ modeLabel }}</span>
          </div>
          <div class="ai-active-toolbar__actions">
            <button v-if="historyConversations.length" class="text-button" type="button" :disabled="sending || loading" aria-controls="conversation-history" :aria-expanded="historyOpen" @click="openHistory">历史会话</button>
            <button class="text-button" type="button" :disabled="sending" @click="startNewConversation">新建对话</button>
          </div>
        </div>

        <div class="ai-active-chat__stream">
          <section ref="chatStreamRef" class="ai-conversation-stream" aria-live="polite" :aria-busy="sending" @scroll="updateScrollAffordance">
            <div v-if="conversationLoading" class="ai-stream-loading"><span class="ai-loading-dot" />正在恢复对话…</div>
            <template v-else>
              <article v-for="message in messages" :key="message.id" class="ai-message" :class="message.role">
                <div class="ai-message__label">{{ message.role === 'user' ? '你' : '灵思 AI' }}</div>
                <div class="ai-message__body">
                  <template v-if="!hasResult(message)">
                    <p v-for="(block, blockIndex) in messageBlocks(message.content)" :key="`${message.id}-${blockIndex}`">{{ block }}</p>
                  </template>
                  <p v-if="!message.content && (message.status === 'queued' || message.status === 'streaming')" class="ai-message__pending">{{ message.status === 'queued' ? '正在排队…' : '正在生成…' }}</p>
                  <div v-if="message.status === 'failed'" class="ai-message__error"><span>{{ message.error_message || '生成失败' }}</span><button type="button" :disabled="sending" @click="retryMessage(message)">{{ sending ? '重试中…' : '重试' }}</button></div>
                  <AIResultCard
                    v-if="hasResult(message)"
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
            </template>
          </section>
        </div>
        <button v-if="showJumpLatest" type="button" class="jump-latest" @click="scrollToLatest()">↓ 跳到最新消息</button>
      </section>

      <div v-if="resourceErrorMessage || error || streamNotice || copyNotice" class="ai-active-chat__notices">
        <div class="ai-workbench-notices">
          <div v-if="resourceErrorMessage" class="ai-resource-notice" role="status"><span>{{ resourceErrorMessage }}</span><button type="button" :disabled="loading" @click="void bootstrapWorkbench()">重试加载</button></div>
          <div v-if="error" class="error-banner" role="alert"><span>{{ error }}</span><button type="button" :disabled="loading || sending" @click="void bootstrapWorkbench()">重试</button></div>
          <div v-if="streamNotice || copyNotice" class="stream-notice" role="status">{{ streamNotice || copyNotice }}</div>
        </div>
      </div>

      <div v-if="!isNewConversation || !projectRequired || currentProject" class="ai-active-chat__composer">
        <div class="ai-workbench-composer-dock" :class="{ 'ai-workbench-composer-dock--new': isNewConversation }">
          <AIWorkbenchComposer
            :draft="draft"
            :mode="workbenchMode"
            :disabled="composerDisabled"
            :can-send="composerCanSend"
            :sending="sending"
            :show-meta="false"
            :show-material-citation="false"
            :show-skill-picker="true"
            :skill-name="activeSkill?.name"
            :show-send-icon="true"
            @update:draft="draft = $event"
            @send="void sendMessage()"
            @stop="abortActiveStream()"
            @add-skill="openSkillPicker"
          />
        </div>
      </div>
    </div>

    <AIConversationHistory
      v-if="historyOpen"
      :groups="historyGroups"
      :selected-id="selectedId"
      :sending="sending"
      :search="historySearch"
      :show-archived="showArchivedConversations"
      :mode-filter="historyModeFilter"
      @update:search="historySearch = $event"
      @update:mode-filter="historyModeFilter = $event"
      @new="startNewConversation"
      @select="openConversationFromHistory"
      @toggle-archived="void toggleHistoryArchived()"
      @close="closeHistory"
    />

    <AIToolPicker
      v-if="skillPickerOpen"
      :categories="skillCategories"
      :groups="skillGroups"
      :search="skillSearch"
      :category="skillCategory"
      :sending="sending"
      @update:search="skillSearch = $event"
      @update:category="skillCategory = $event"
      @choose="chooseSkill"
      @close="closeSkillPicker"
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
 .ai-workbench-main { background: var(--color-bg-canvas); color: var(--color-text-primary); }
 :global(.workspace-main:has(.ai-workbench-main)) { background: var(--color-bg-canvas); }
 .ai-center-page { display: flex; width: 100%; max-width: none; min-width: 0; min-height: calc(100vh - var(--topbar-height) - 104px); flex-direction: column; box-sizing: border-box; margin: 0 auto; padding: 28px 0 24px; overflow: hidden; }
 .ai-workbench-page--new { min-height: calc(100vh - var(--topbar-height) - 104px); padding-bottom: 24px; }
  .ai-workbench-page--active { height: calc(100vh - var(--topbar-height) - 104px); min-height: 0; overflow: hidden; background: var(--color-bg-canvas); }
 .ai-workbench-canvas { display: flex; width: min(100%, 1080px); min-width: 0; min-height: 0; flex: 1 1 auto; flex-direction: column; box-sizing: border-box; margin: 0 auto; padding: clamp(20px, 2.5vw, 32px) clamp(20px, 3vw, 44px) clamp(20px, 2.5vw, 28px); border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-soft); }
 .ai-workbench-page--active .ai-workbench-canvas { overflow: hidden; }
 .ai-workbench-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 28px; padding-bottom: 0; border-bottom: 0; }
 .ai-workbench-heading { min-width: 0; }
  .ai-workbench-heading .eyebrow { margin-bottom: 7px; color: var(--moss); font-size: 11px; letter-spacing: .1em; }
  .ai-workbench-heading h1 { margin: 2px 0 7px; color: var(--ink); font-family: var(--sans); font-size: clamp(24px, 2.4vw, 30px); font-weight: 700; line-height: 1.25; letter-spacing: -.025em; }
  .ai-workbench-heading p { max-width: 720px; margin: 0; color: var(--muted); font-size: 12px; line-height: 1.65; }
 .ai-workbench-header__actions { display: flex; align-items: center; justify-content: flex-end; gap: 14px; min-width: 0; max-width: 100%; padding-top: 2px; }
.ai-workbench-active-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-width: 0; padding: 0 0 12px; border-bottom: 1px solid var(--line); }
.ai-active-toolbar__actions { display: flex; align-items: center; justify-content: flex-end; gap: 8px; flex: 0 0 auto; }
.ai-active-toolbar__identity { display: flex; align-items: baseline; gap: 12px; min-width: 0; }
.ai-active-toolbar__identity strong { color: var(--ink); font: 700 16px/1.2 var(--sans); letter-spacing: -.02em; }
.ai-active-toolbar__identity span { overflow: hidden; color: var(--muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.ai-active-toolbar__mode { flex: 0 0 auto; padding-left: 12px; border-left: 1px solid var(--line); color: var(--moss-dark) !important; font-weight: 700; }
  .ai-workbench-context-pill { display: inline-flex; align-items: center; flex: 0 1 360px; min-width: 0; max-width: 360px; min-height: 32px; overflow: hidden; padding: 8px 11px; border: 1px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--paper); color: var(--moss-dark); font-size: 12px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
 .ai-workbench-history-button { flex: 0 0 auto; }
.text-button { min-height: 32px; padding: 6px 10px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); background: var(--paper); color: var(--moss-dark); font: inherit; font-size: 11px; font-weight: 700; cursor: pointer; }
.text-button:hover:not(:disabled), .text-button:focus-visible { border-color: var(--moss); background: var(--sage-soft); }
.text-button:disabled { cursor: not-allowed; opacity: .48; }
  .ai-workbench-content { display: grid; flex: 1 1 auto; grid-template-rows: auto minmax(260px, 1fr); gap: 0; width: 100%; min-width: 0; min-height: 0; margin: 32px auto 0; }
  .ai-workbench-mode-region { width: 100%; margin: 0; }
  .ai-workbench-page--new :deep(.ai-mode-tabs__row) { border-color: var(--line); border-radius: var(--radius-md); }
   .ai-workbench-page--new :deep(.ai-mode-tab) { min-height: 68px; gap: 4px; padding: 12px 16px; }
   .ai-workbench-page--new :deep(.ai-mode-tab strong) { font-size: 15px; line-height: 1.25; }
   .ai-workbench-page--new :deep(.ai-mode-tab small) { font-size: 11px; line-height: 1.4; }
  .ai-workbench-empty { display: flex; min-width: 0; flex-direction: column; align-items: stretch; justify-content: center; gap: 12px; padding: 26px 0 28px; }
  .ai-workbench-empty__intro { display: grid; justify-items: center; gap: 7px; text-align: center; }
  .ai-workbench-empty__intro .eyebrow { color: var(--moss); font-size: 10px; letter-spacing: .1em; }
  .ai-workbench-empty h2 { margin: 0; color: var(--ink); font-family: var(--sans); font-size: clamp(22px, 2.2vw, 28px); font-weight: 700; line-height: 1.3; letter-spacing: -.025em; }
  .ai-workbench-empty__intro p { max-width: 720px; margin: 0; color: var(--muted); font-size: 12px; line-height: 1.65; }
  .ai-workbench-empty__guide { width: min(100%, 780px); margin: 12px auto 0; padding-top: 16px; border-top: 1px solid var(--line); }
  .ai-workbench-empty__guide-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 10px; color: var(--muted); font-size: 11px; }
  .ai-workbench-empty__guide-heading .eyebrow { color: var(--moss); font-size: 10px; letter-spacing: .1em; }
  .ai-workbench-empty__steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0; padding: 0; list-style: none; }
  .ai-workbench-empty__steps li { display: grid; gap: 7px; min-width: 0; padding: 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); }
  .ai-workbench-empty__step-index { color: var(--moss); font: 700 10px/1 var(--sans); letter-spacing: .08em; }
  .ai-workbench-empty__step-copy { display: grid; gap: 4px; }
  .ai-workbench-empty__step-copy strong { color: var(--ink); font-size: 11px; }
  .ai-workbench-empty__step-copy small { color: var(--muted); font-size: 10px; line-height: 1.5; }
.ai-workbench-skeleton { display: grid; gap: 10px; width: 100%; margin: 8px auto 0; }
.ai-workbench-skeleton i { display: block; height: 10px; border-radius: 999px; background: var(--paper-muted); animation: ai-workbench-pulse 1.2s ease-in-out infinite alternate; }
.ai-workbench-skeleton i:nth-child(1) { width: 42%; }.ai-workbench-skeleton i:nth-child(2) { width: 68%; animation-delay: .12s; }.ai-workbench-skeleton i:nth-child(3) { width: 54%; animation-delay: .24s; }
@keyframes ai-workbench-pulse { from { opacity: .45; } to { opacity: 1; } }
.ai-workbench-context-note { display: flex; align-items: center; justify-content: space-between; gap: 14px; width: 100%; box-sizing: border-box; margin: 0; padding: 12px 14px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--muted); font-size: 11px; line-height: 1.55; }
.ai-workbench-context-note .secondary-button { flex: 0 0 auto; }
.ai-active-chat { display: grid; grid-template-rows: auto minmax(0, 1fr); min-width: 0; min-height: 0; flex: 1 1 auto; overflow: hidden; }
.ai-active-chat__stream { display: flex; min-width: 0; min-height: 0; overflow: hidden; }
.ai-conversation-stream { display: grid; align-content: start; gap: 28px; width: 100%; min-width: 0; min-height: 0; flex: 1 1 auto; overflow-y: auto; overflow-x: hidden; box-sizing: border-box; margin: 0; padding: 28px clamp(12px, 7vw, 72px) 36px; scrollbar-width: thin; }
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
.jump-latest { align-self: center; border: 1px solid var(--line-dark); border-radius: 999px; padding: 6px 11px; background: var(--paper); color: var(--moss-dark); font: inherit; font-size: 10px; cursor: pointer; }
 .ai-workbench-composer-dock { width: 100%; min-width: 0; margin: 24px auto 0; }
.ai-workbench-composer-dock--new { margin-top: 20px; }
 .ai-workbench-page--active .ai-workbench-composer-dock { width: 100%; margin-top: 8px; position: sticky; bottom: 0; z-index: 2; padding-top: 8px; background: linear-gradient(to bottom, rgba(255, 255, 255, 0), var(--paper) 26%); }
.ai-active-chat__composer { flex: 0 0 auto; min-width: 0; }
   .ai-center-page :deep(.ai-workbench-composer) { width: 100%; box-sizing: border-box; border-color: var(--line-dark); box-shadow: var(--shadow-soft); }
  .ai-center-page :deep(.ai-workbench-composer__textarea) { min-height: 78px; }
  .ai-workbench-page--new :deep(.ai-workbench-composer) { min-height: 148px; padding: 16px 18px 12px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); box-shadow: var(--shadow-soft); }
   .ai-workbench-page--new :deep(.ai-workbench-composer__textarea) { height: 68px; min-height: 68px; padding: 5px 0 8px; font-size: 13px; line-height: 1.55; resize: none; }
  .ai-workbench-page--new :deep(.ai-workbench-composer__footer) { gap: 8px; font-size: 11px; }
 .ai-workbench-page--new :deep(.composer-hint) { margin-left: 0; margin-right: auto; color: var(--muted-light); }
   .ai-workbench-page--new :deep(.send-button) { min-width: 80px; min-height: 36px; padding: 7px 12px; border-radius: var(--radius-sm); font-size: 12px; }
   .ai-workbench-page--new :deep(.send-button__icon) { width: 14px; height: 14px; margin-left: 3px; }
 .ai-workbench-page--new .ai-workbench-header__actions { flex-wrap: wrap; }
 .ai-workbench-page--new .text-button { min-height: 32px; padding: 7px 0; border-color: transparent; background: transparent; color: var(--muted); white-space: nowrap; }
 .ai-workbench-page--new .text-button:hover:not(:disabled), .ai-workbench-page--new .text-button:focus-visible { border-color: transparent; background: transparent; color: var(--moss-dark); text-decoration: underline; text-underline-offset: 4px; }
.ai-active-chat__notices { flex: 0 0 auto; min-width: 0; }
.ai-workbench-notices { display: grid; gap: 8px; min-width: 0; margin-top: 9px; }
.ai-resource-notice, .error-banner, .stream-notice { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 11px; border: 1px solid var(--line); border-radius: var(--radius-sm); font-size: 11px; line-height: 1.5; }
.ai-resource-notice { background: var(--paper-soft); color: var(--muted); }.error-banner { border-color: #e5c8c0; background: #fff7f4; color: #8e4438; }.stream-notice { background: var(--sage-soft); color: var(--moss-dark); }
.ai-resource-notice button, .error-banner button { flex: 0 0 auto; border: 0; background: transparent; color: var(--moss-dark); font: inherit; font-weight: 700; cursor: pointer; }
.primary-button, .secondary-button { min-height: 34px; padding: 7px 13px; border-radius: var(--radius-sm); font: inherit; font-size: 11px; cursor: pointer; }.primary-button { border: 1px solid var(--moss-dark); background: var(--moss); color: #fff; font-weight: 700; }.primary-button:hover:not(:disabled), .primary-button:focus-visible { background: var(--moss-dark); }.secondary-button { border: 1px solid var(--line-dark); background: var(--paper); color: var(--moss-dark); }.secondary-button:hover:not(:disabled), .secondary-button:focus-visible { border-color: var(--moss); background: var(--paper-soft); }.primary-button:disabled, .secondary-button:disabled { cursor: wait; opacity: .55; }
.ai-confirm-backdrop { position: fixed; inset: 0; z-index: 100; display: grid; place-items: center; padding: 24px; background: rgba(32, 47, 38, .22); }.ai-material-dialog { display: grid; gap: 14px; width: min(100%, 480px); box-sizing: border-box; padding: 22px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-hover); }.ai-material-dialog header, .ai-material-dialog footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.ai-material-dialog h2 { margin: 4px 0 0; color: var(--ink); font: 700 22px/1.2 var(--sans); }.ai-material-dialog > p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.65; }.ai-dialog-close { width: 28px; height: 28px; border: 0; border-radius: 50%; background: transparent; color: var(--muted); font-size: 22px; cursor: pointer; }.ai-dialog-close:hover, .ai-dialog-close:focus-visible { background: var(--paper-soft); color: var(--ink); }.ai-material-target { display: grid; gap: 6px; color: var(--muted); font-size: 11px; font-weight: 700; }.ai-material-target select { width: 100%; box-sizing: border-box; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); padding: 9px 10px; background: var(--paper-soft); color: var(--ink); font: inherit; font-size: 12px; }.ai-dialog-error { padding: 9px 10px; border-radius: var(--radius-sm); background: #fff7f4; color: #8e4438; font-size: 11px; }.ai-dialog-loading, .ai-dialog-empty { color: var(--muted); font-size: 11px; }.ai-material-dialog footer { justify-content: flex-end; }
 @media (max-width: 1024px) {
   .ai-workbench-canvas { padding: 20px 24px 18px; }
   .ai-workbench-heading h1 { font-size: 28px; }
   .ai-workbench-heading p { font-size: 12px; }
   .ai-workbench-content { margin-top: 24px; }
   .ai-workbench-page--new :deep(.ai-mode-tab) { min-height: 64px; padding: 12px 15px; }
   .ai-workbench-page--new :deep(.ai-mode-tab small) { white-space: normal; overflow: visible; text-overflow: clip; }
   .ai-workbench-empty { gap: 10px; padding: 22px 8px 26px; }
   .ai-workbench-empty h2 { font-size: 25px; }
   .ai-workbench-empty__intro p { font-size: 12px; }
   .ai-workbench-page--new :deep(.ai-workbench-composer) { min-height: 140px; padding: 15px 17px 11px; }
   .ai-workbench-page--new :deep(.ai-workbench-composer__textarea) { height: 64px; min-height: 64px; }
   .ai-workbench-page--new :deep(.send-button) { min-width: 78px; min-height: 34px; }
 }
  @media (max-width: 1279px) { .ai-center-page { padding-inline: 20px; } }
  @media (max-width: 720px) { .ai-workbench-header { align-items: flex-start; flex-direction: column; }.ai-workbench-heading .eyebrow { margin-bottom: 10px; }.ai-workbench-heading h1 { margin-bottom: 12px; }.ai-workbench-heading p { font-size: 13px; }.ai-workbench-header__actions { align-items: flex-start; justify-content: flex-start; flex-wrap: wrap; padding-top: 0; }.ai-workbench-active-toolbar { align-items: flex-start; flex-direction: column; }.ai-workbench-context-pill { max-width: 100%; padding: 8px 11px; }.ai-workbench-canvas { padding: 22px 18px; border-radius: var(--radius-md); }.ai-workbench-content { margin-top: 28px; }.ai-workbench-page--new :deep(.ai-mode-tabs__row) { border-radius: var(--radius-md); }.ai-workbench-page--new :deep(.ai-mode-tab) { min-height: 64px; gap: 4px; padding: 12px 10px; }.ai-workbench-page--new :deep(.ai-mode-tab strong) { font-size: 15px; }.ai-workbench-page--new :deep(.ai-mode-tab small) { font-size: 10px; white-space: normal; }.ai-workbench-empty { padding: 28px 10px 34px; }.ai-workbench-empty h2 { font-size: 26px; }.ai-workbench-empty__intro p { font-size: 13px; }.ai-workbench-page--new :deep(.ai-workbench-composer) { min-height: 176px; padding: 18px 16px 14px; border-radius: var(--radius-md); }.ai-workbench-page--new :deep(.ai-workbench-composer__textarea) { height: 88px; min-height: 88px; font-size: 14px; }.ai-workbench-page--new :deep(.send-button) { min-width: 88px; min-height: 40px; border-radius: var(--radius-sm); font-size: 13px; }.ai-workbench-page--new :deep(.send-button__icon) { width: 16px; height: 16px; }.ai-workbench-active-toolbar { align-items: flex-start; flex-direction: column; }.ai-workbench-context-note { align-items: stretch; flex-direction: column; }.ai-message.user { width: 86%; }.ai-confirm-backdrop { padding: 14px; } }
</style>
