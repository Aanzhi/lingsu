<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, archiveAIConversation, createAIConversation, createAIConversationMessage, createProject, errorMessage, getAIAgents, getAIConversationMessages, getAIConversations, getMaterials, getProjects, saveAIGenerationAsMaterial, streamAIConversationMessage, updateAIConversation, type AIAgent, type AIConversation, type AIConversationMessage, type Material, type Project } from '../../api'
import { auth } from '../../stores/auth'
import { aiWorkspaceMode, buildResearchQuestionPrompt, filterConversations, groupAgentsByCategory, isNearBottom, isTerminalSSEEvent, normalizeResearchQuestionArtifact, optionalAgentInputs, researchProjectDraftFromArtifact, researchResponseNotice, type ResearchQuestionArtifact, type ResearchQuestionInputs } from '../../stores/aiConversationModel'
import { conversationDisplayTitle, groupConversationSummaries } from '../../stores/presentationModel'
import AIContextChooser from '../../components/ai/AIContextChooser.vue'
import AIConversationHistory from '../../components/ai/AIConversationHistory.vue'
import AIProjectAssistant from '../../components/ai/AIProjectAssistant.vue'
import AIResearchWizard from '../../components/ai/AIResearchWizard.vue'
import AIToolPicker from '../../components/ai/AIToolPicker.vue'
import PageHeader from '../../components/PageHeader.vue'

const route = useRoute()
const router = useRouter()

function queryNumber(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}
function routeAgent(): string | undefined {
  if (route.query.mode === 'brainstorm' || route.query.researchQuestion === '1') return 'proposal-topic'
  return typeof route.query.agent === 'string' ? route.query.agent : undefined
}

const conversations = ref<AIConversation[]>([])
const messages = ref<AIConversationMessage[]>([])
const projects = ref<Project[]>([])
const agents = ref<AIAgent[]>([])
const selectedId = ref<number | null>(null)
const projectFilter = ref<number | null>(queryNumber(route.query.projectId))
const selectedAgent = ref<string | undefined>(routeAgent())
const taskId = ref<number | undefined>(queryNumber(route.query.taskId) ?? undefined)
const conversationSearch = ref('')
const conversationPreviews = ref<Record<number, string>>({})
const agentSearch = ref('')
const agentCategory = ref('all')
const historyOpen = ref(false)
const draft = ref('')
const loading = ref(true)
const sending = ref(false)
const contextOpen = ref(false)
const agentOpen = ref(false)
const showArchived = ref(false)
const error = ref('')
const paperType = ref('')
const agentInputs = ref<Record<string, string>>({})
const materials = ref<Material[]>([])
const artifactDrafts = ref<Record<number, string>>({})
const savingMessage = ref<number | null>(null)
const targetMaterialId = ref<number | null>(null)
const renaming = ref(false)
const titleDraft = ref('')
const chatStreamRef = ref<HTMLElement | null>(null)
const showJumpLatest = ref(false)
const streamNotice = ref('')
const streamController = ref<AbortController | null>(null)
const requestVersion = ref(0)
const selectionVersion = ref(0)
const researchStep = ref<1 | 2 | 3 | 4>(1)
const researchInputs = ref<ResearchQuestionInputs>({ phenomenon: '', object_context: '', goal: '', constraints: '' })
const researchArtifact = ref<ResearchQuestionArtifact | null>(null)
const researchSelectedIndex = ref<number | null>(null)
const researchDraft = ref('')
const researchSaveConfirm = ref(false)
const researchSaved = ref(false)
const researchSaveError = ref('')
const researchFallback = ref('')
const projectDraft = ref<{ title: string; problem: string; plan: string; project_type: Project['project_type'] }>({ title: '', problem: '', plan: '', project_type: 'research' })
const creatingProject = ref(false)
const projectCreated = ref(false)
const paperTypes = [{ value: 'empirical', label: '实证研究' }, { value: 'case', label: '案例研究' }, { value: 'literature-review', label: '文献综述' }, { value: 'theoretical', label: '理论研究' }]

const current = computed(() => conversations.value.find((item) => item.id === selectedId.value) || null)
const currentProject = computed(() => projects.value.find((item) => item.id === current.value?.project) || null)
const currentDisplayTitle = computed(() => current.value ? conversationDisplayTitle(current.value, conversationPreviews.value[current.value.id] || '') : '新建科创对话')
const visibleConversations = computed(() => filterConversations(conversations.value, { project: projectFilter.value, includeArchived: showArchived.value }).filter((item) => {
  const keyword = conversationSearch.value.trim().toLowerCase()
  if (!keyword) return true
  return `${conversationDisplayTitle(item, conversationPreviews.value[item.id] || '')} ${item.project_title || ''}`.toLowerCase().includes(keyword)
}))
const visibleConversationGroups = computed(() => groupConversationSummaries(visibleConversations.value, conversationPreviews.value))
const currentAgent = computed(() => agents.value.find((item) => item.key === selectedAgent.value) || agents.value.find((item) => item.key === current.value?.current_agent) || null)
const agentCategories = computed(() => ['all', ...new Set(agents.value.map((agent) => agent.category?.trim()).filter(Boolean) as string[])])
const filteredAgents = computed(() => agents.value.filter((agent) => {
  const keyword = agentSearch.value.trim().toLowerCase()
  const matchesKeyword = !keyword || `${agent.name} ${agent.description} ${agent.category}`.toLowerCase().includes(keyword)
  return matchesKeyword && (agentCategory.value === 'all' || (agent.category || '其他') === agentCategory.value)
}))
const groupedAgents = computed(() => groupAgentsByCategory(filteredAgents.value))
const brainstormMode = computed(() => route.query.mode === 'brainstorm')
const workspaceMode = computed(() => aiWorkspaceMode({
  brainstorm: brainstormMode.value,
  researchQuestion: route.query.researchQuestion === '1',
  projectId: projectFilter.value,
  conversationProject: current.value?.project ?? null,
  selectedAgent: selectedAgent.value,
}))
const researchMode = computed(() => workspaceMode.value === 'brainstorm' || (workspaceMode.value === 'project' && (route.query.researchQuestion === '1' || selectedAgent.value === 'proposal-topic')))
const workspaceContextLabel = computed(() => workspaceMode.value === 'brainstorm' ? '无项目 · 选题引导' : currentProject.value?.title || (workspaceMode.value === 'project' ? '当前项目 · 正在加载' : '未绑定项目 · 通用咨询'))
const aiPageDescription = computed(() => {
  if (researchMode.value) return '从真实观察开始，AI 会逐步追问、比较和整理；确认前不会创建项目。'
  if (currentProject.value) return '围绕当前项目和当前任务提供帮助，生成内容先由你检查，再决定保存位置。'
  return '可以开题选题，也可以围绕项目持续对话、完善材料，或调用专门的科创 Agent。'
})
const aiContextTitle = computed(() => {
  if (researchMode.value || brainstormMode.value) return '从一个真实观察开始'
  if (currentProject.value) return '围绕当前项目继续研究'
  return '先选择一个研究场景'
})
const aiContextDescription = computed(() => {
  if (researchMode.value || brainstormMode.value) return 'AI 不会直接替你命题，会先追问、比较和整理，最后由你确认项目草稿。'
  if (currentProject.value) return 'AI 只读取当前项目和当前任务，不会替你创建新项目或直接提交材料。'
  return '先选择已有项目，或进入“无课题”引导；未绑定项目时不会读取任何项目材料。'
})
const aiStepperLabels = computed(() => currentProject.value ? ['选择目标', '补充背景', '得到建议', '确认保存'] : ['发现现象', '打开问题', '头脑风暴', '共同成题'])
const isResearchLeader = computed(() => Boolean(currentProject.value && auth.user.value?.authorized && currentProject.value.leader === auth.user.value.id))

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
  streamController.value?.abort()
  streamController.value = null
}
function resetConversationSelection() {
  abortActiveStream()
  requestVersion.value += 1
  selectionVersion.value += 1
  selectedId.value = null
  messages.value = []
  materials.value = []
  targetMaterialId.value = null
  streamNotice.value = ''
  error.value = ''
  renaming.value = false
  resetResearchState()
}
function replaceMessage(next: AIConversationMessage) {
  const index = messages.value.findIndex((item) => item.id === next.id)
  if (index >= 0) messages.value[index] = next
}
async function refreshConversationList() {
  const response = await getAIConversations({ include_archived: showArchived.value })
  conversations.value = response.data
  void loadConversationPreviews(response.data)
}
async function loadConversations() {
  const response = await getAIConversations({ include_archived: showArchived.value })
  conversations.value = response.data
  void loadConversationPreviews(response.data)
  const matchesContext = (item: AIConversation) => projectFilter.value === null ? item.project === null : item.project === projectFilter.value
  const preferred = response.data.find((item) => matchesContext(item) && item.id === selectedId.value)
    || (brainstormMode.value ? response.data.find((item) => item.project === null && item.current_agent === 'proposal-topic') : null)
    || response.data.find(matchesContext)
  if (preferred) await selectConversation(preferred)
}

async function loadConversationPreviews(items: AIConversation[]) {
  const candidates = items.filter((item) => !item.title?.trim() || ['新对话', '新建科创对话', '通用咨询'].includes(item.title.trim())).slice(0, 12)
  if (!candidates.length) return
  const entries = await Promise.all(candidates.map(async (item) => {
    try {
      const response = await getAIConversationMessages(item.id)
      const firstPrompt = response.data.find((message) => message.role === 'user' && message.content?.trim())
      return firstPrompt ? [item.id, firstPrompt.content] as const : null
    } catch {
      return null
    }
  }))
  conversationPreviews.value = { ...conversationPreviews.value, ...Object.fromEntries(entries.filter((entry): entry is readonly [number, string] => Boolean(entry))) }
}

function resetResearchState() {
  researchStep.value = 1
  researchArtifact.value = null
  researchSelectedIndex.value = null
  researchDraft.value = ''
  researchSaveConfirm.value = false
  researchSaved.value = false
  researchSaveError.value = ''
  researchFallback.value = ''
  projectCreated.value = false
  projectDraft.value = { title: '', problem: '', plan: '', project_type: 'research' }
}

async function selectConversation(item: AIConversation) {
  if (sending.value) return
  const version = ++selectionVersion.value
  selectedId.value = item.id
  selectedAgent.value = item.current_agent || selectedAgent.value
  paperType.value = item.paper_type || ''
  agentInputs.value = {}
  const [messageResponse, materialResponse] = await Promise.all([
    getAIConversationMessages(item.id),
    item.project ? getMaterials(item.project) : Promise.resolve({ data: [] as Material[] }),
  ])
  if (version !== selectionVersion.value || selectedId.value !== item.id) return
  messages.value = messageResponse.data
  const firstPrompt = messages.value.find((message) => message.role === 'user' && message.content?.trim())
  if (firstPrompt) conversationPreviews.value[item.id] = firstPrompt.content
  materials.value = materialResponse.data
  targetMaterialId.value = null
  titleDraft.value = item.title || ''
  streamNotice.value = ''
  if (researchMode.value) {
    resetResearchState()
    const latestAssistant = [...messages.value].reverse().find((message) => message.role === 'assistant' && (message.artifact_payload || message.content?.trim()))
    if (latestAssistant) syncResearchArtifact(latestAssistant)
  }
  await nextTick()
  scrollToLatest('auto')
}
async function newConversation() {
  if (sending.value) return
  const item = (await createAIConversation({ project: projectFilter.value, current_agent: selectedAgent.value || null })).data
  conversations.value.unshift(item)
  await selectConversation(item)
}
async function archiveCurrent() {
  if (!current.value || sending.value) return
  try {
    await archiveAIConversation(current.value.id)
    await loadConversations()
  } catch (reason) {
    error.value = errorMessage(reason, '归档对话失败，请重试。')
  }
}
function startRename() {
  if (!current.value || current.value.is_archived) return
  titleDraft.value = current.value.title || ''
  renaming.value = true
}
async function saveRename() {
  if (!current.value || !titleDraft.value.trim() || sending.value) return
  try {
    const response = await updateAIConversation(current.value.id, { title: titleDraft.value.trim() })
    const index = conversations.value.findIndex((item) => item.id === current.value?.id)
    if (index >= 0) conversations.value[index] = response.data
    renaming.value = false
  } catch (reason) {
    error.value = errorMessage(reason, '对话重命名失败，请重试。')
  }
}

function syncResearchArtifact(message?: AIConversationMessage) {
  if (!message) return
  const responseNotice = researchResponseNotice(message)
  if (responseNotice) researchSaveError.value = responseNotice
  let parsed = normalizeResearchQuestionArtifact(message.artifact_payload)
  if (!parsed && message.content?.trim()) {
    try { parsed = normalizeResearchQuestionArtifact(JSON.parse(message.content)) } catch { /* keep editable text fallback */ }
  }
  if (parsed) {
    researchArtifact.value = parsed
    researchFallback.value = ''
    researchSelectedIndex.value = parsed.recommended_index
    researchDraft.value = parsed.candidates[parsed.recommended_index]?.question || ''
    projectDraft.value = researchProjectDraftFromArtifact(parsed, parsed.recommended_index, researchFallback.value)
  } else if (message.content?.trim()) {
    researchArtifact.value = null
    researchFallback.value = message.content.trim()
    researchDraft.value = message.content.trim()
    projectDraft.value = { ...researchProjectDraftFromArtifact(null, null, message.content), plan: '', project_type: 'research' }
  }
  if (researchMode.value) researchStep.value = 3
}

function goToBrainstorm() {
  void router.push({ path: '/student/ai', query: { mode: 'brainstorm', agent: 'proposal-topic' } })
}

function goToExistingProject() {
  const projectId = currentProject.value?.id ?? projectFilter.value
  if (!projectId) {
    void router.push('/student/projects')
    return
  }
  void router.push({ path: '/student/ai', query: { projectId: String(projectId) } })
}

function openScienceAgentPicker() {
  agentOpen.value = true
  contextOpen.value = false
}

function fillQuickPrompt(prompt: string) {
  draft.value = prompt
  void nextTick(() => document.querySelector<HTMLTextAreaElement>('.composer textarea')?.focus())
}

function advanceFromObservation() {
  if (researchInputs.value.phenomenon.trim()) {
    researchSaveError.value = ''
    researchStep.value = 2
    return
  }
  researchSaveError.value = '先写下你观察到的现象或痛点。'
}

function openResearchDraft() {
  if (researchArtifact.value && researchSelectedIndex.value === null) {
    researchSaveError.value = '先选择一个你愿意继续核验的方向。'
    return
  }
  if (!researchDraft.value.trim() && !researchFallback.value.trim()) {
    researchSaveError.value = '还没有可以继续整理的研究问题，请先重新生成。'
    return
  }
  researchSaveError.value = ''
  researchStep.value = 4
}

function prefillResearchFromProject(project: Project | null) {
  if (!project || !researchMode.value) return
  if (!researchInputs.value.phenomenon.trim() && project.problem?.trim()) researchInputs.value.phenomenon = project.problem.trim()
}

function chooseResearchCandidate(index: number) {
  researchSelectedIndex.value = index
  const candidate = researchArtifact.value?.candidates[index]
  researchDraft.value = candidate?.question || researchFallback.value
  projectDraft.value.problem = researchDraft.value
  if (!projectDraft.value.plan.trim() && candidate?.evidence_plan?.trim()) projectDraft.value.plan = candidate.evidence_plan.trim()
}

function editResearchCandidate(index: number, value: string) {
  const candidate = researchArtifact.value?.candidates[index]
  if (!candidate) return
  candidate.question = value
  if (researchSelectedIndex.value === index) {
    researchDraft.value = value
    projectDraft.value.problem = value
  }
}

async function sendMessage(options: { content?: string; inputValues?: Record<string, string> } = {}) {
  const content = (options.content ?? draft.value).trim()
  if (!content || !selectedId.value || sending.value || current.value?.is_archived) return
  const conversationId = selectedId.value
  const version = ++requestVersion.value
  const controller = new AbortController()
  streamController.value = controller
  sending.value = true; error.value = ''; streamNotice.value = ''
  if (!options.content) draft.value = ''
  let assistantId: number | undefined
  try {
    const inputValues = optionalAgentInputs(options.inputValues || agentInputs.value)
    const response = await createAIConversationMessage(conversationId, { content, agent_key: selectedAgent.value, paper_type: paperType.value || undefined, project: current.value?.project, task: taskId.value, ...(inputValues ? { input_values: inputValues } : {}) })
    if (version !== requestVersion.value || controller.signal.aborted) return
    messages.value.push({ role: 'user', content, status: 'completed', created_at: new Date().toISOString(), id: -Date.now() })
    messages.value.push(response.data)
    assistantId = response.data.id
    maybeScrollLatest(true)
    if (response.data.status === 'queued' && response.data.id) await streamAssistant(conversationId, response.data.id, version, controller)
    if (researchMode.value && assistantId) syncResearchArtifact(messages.value.find((item) => item.id === assistantId))
    await refreshConversationList()
  } catch (reason) {
    if (controller.signal.aborted) return
    const assistant = assistantId ? messages.value.find((item) => item.id === assistantId) : undefined
    if (assistant) { assistant.status = 'failed'; assistant.error_message = errorMessage(reason, '生成失败，请点击重试。') }
    error.value = errorMessage(reason, '消息发送失败，请重试。')
    if (researchMode.value) researchSaveError.value = errorMessage(reason, '研究问题助手暂时无法生成候选，请稍后重试。')
    if (!options.content) draft.value = content
  } finally {
    if (version === requestVersion.value) { sending.value = false; streamController.value = null }
  }
}

async function generateResearchCandidates() {
  if (!selectedId.value) {
    researchSaveError.value = '研究问题助手还没有准备好，请新建一段对话后重试。'
    return
  }
  if (!researchInputs.value.phenomenon.trim()) { researchSaveError.value = '先写下你观察到的现象或痛点。'; researchStep.value = 1; return }
  if (!researchInputs.value.object_context.trim() || !researchInputs.value.goal.trim()) { researchSaveError.value = '请补充研究对象和想弄清楚的方向。'; researchStep.value = 2; return }
  researchSaveError.value = ''
  selectedAgent.value = 'proposal-topic'
  await sendMessage({
    content: buildResearchQuestionPrompt(researchInputs.value),
    inputValues: {
      topic: researchInputs.value.phenomenon,
      observations: [researchInputs.value.object_context, researchInputs.value.goal, researchInputs.value.constraints].filter(Boolean).join('；'),
    },
  })
}

function requestResearchSave() {
  researchSaveError.value = ''
  if (!researchDraft.value.trim()) { researchSaveError.value = '请先选择或编辑一个研究问题。'; return }
  if (!isResearchLeader.value) { researchSaveError.value = '只有项目负责人且学校账号已授权时才能保存项目问题。'; return }
  researchSaveConfirm.value = true
}

async function createProjectFromResearch() {
  researchSaveError.value = ''
  if (workspaceMode.value !== 'brainstorm') {
    researchSaveError.value = '当前对话绑定了已有项目，不能在这里新建项目。请从项目内继续完善研究问题。'
    return
  }
  const payload = {
    title: projectDraft.value.title.trim(),
    problem: projectDraft.value.problem.trim() || researchDraft.value.trim(),
    plan: projectDraft.value.plan.trim(),
    project_type: projectDraft.value.project_type,
  }
  if (!payload.title) { researchSaveError.value = '请补充项目标题后再生成项目。'; return }
  if (!payload.problem) { researchSaveError.value = '请补充研究问题后再生成项目。'; return }
  creatingProject.value = true
  try {
    const response = await createProject(payload)
    projects.value.unshift(response.data)
    projectCreated.value = true
    await router.push({ path: `/student/projects/${response.data.id}/map` })
  } catch (reason) {
    researchSaveError.value = errorMessage(reason, '项目生成失败，当前草稿已保留，请重试。')
  } finally {
    creatingProject.value = false
  }
}

async function saveResearchQuestion() {
  if (workspaceMode.value !== 'project' || !currentProject.value || !researchDraft.value.trim() || !isResearchLeader.value) return
  try {
    const response = await api.post<Project>(`projects/${currentProject.value.id}/update_basics/`, { problem: researchDraft.value.trim() })
    const index = projects.value.findIndex((item) => item.id === response.data.id)
    if (index >= 0) projects.value[index] = response.data
    researchSaveConfirm.value = false
    researchSaved.value = true
    researchSaveError.value = ''
  } catch (reason) {
    researchSaveError.value = errorMessage(reason, '研究问题保存失败，候选和编辑内容已保留，请重试。')
    researchSaveConfirm.value = false
  }
}

function copyResearchQuestion() {
  const value = researchDraft.value.trim()
  if (!value) return
  void navigator.clipboard?.writeText(value)
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
    if (isTerminalSSEEvent(event.event)) terminal = true
    if (event.event === 'message.done') assistant.status = 'completed'
    maybeScrollLatest()
  }, controller.signal)
  if (researchMode.value) syncResearchArtifact(messages.value.find((item) => item.id === assistantId))
  if (version !== requestVersion.value || selectedId.value !== conversationId || controller.signal.aborted || terminal) return
  const latest = (await getAIConversationMessages(conversationId)).data.find((item) => item.id === assistantId)
  if (!latest || version !== requestVersion.value || selectedId.value !== conversationId) return
  replaceMessage(latest)
  if (researchMode.value) syncResearchArtifact(latest)
  if (latest.status === 'queued' || latest.status === 'streaming') streamNotice.value = '生成仍在后台，刷新对话查看结果。'
  maybeScrollLatest()
}
async function retryMessage(message: AIConversationMessage) {
  if (!selectedId.value || sending.value || message.status !== 'failed' || current.value?.is_archived) return
  const conversationId = selectedId.value
  const version = ++requestVersion.value
  const controller = new AbortController()
  streamController.value = controller
  sending.value = true; error.value = ''; streamNotice.value = ''
  message.content = ''; message.error_message = undefined; message.status = 'queued'; message.artifact_payload = null
  try {
    const response = await api.post<AIConversationMessage>(`ai-conversations/${conversationId}/messages/${message.id}/retry/`)
    if (version !== requestVersion.value || controller.signal.aborted) return
    replaceMessage(response.data)
    maybeScrollLatest(true)
    if (response.data.status === 'queued') await streamAssistant(conversationId, response.data.id, version, controller)
    await refreshConversationList()
  } catch (reason) {
    if (controller.signal.aborted) return
    const failedMessage = messages.value.find((item) => item.id === message.id) || message
    failedMessage.status = 'failed'
    failedMessage.error_message = errorMessage(reason, '重试失败，请稍后再试。')
  } finally {
    if (version === requestVersion.value) { sending.value = false; streamController.value = null }
  }
}
function chooseAgent(agent: AIAgent) {
  if (sending.value) return
  selectedAgent.value = agent.key
  agentInputs.value = {}
  agentOpen.value = false
  researchSaveError.value = ''
  if (agent.key === 'proposal-topic') {
    void router.push({ query: { ...route.query, researchQuestion: '1', agent: agent.key } })
    researchStep.value = currentProject.value?.problem?.trim() ? 1 : 1
    prefillResearchFromProject(currentProject.value)
  } else if (route.query.researchQuestion || route.query.mode) {
    const query = { ...route.query }; delete query.researchQuestion; delete query.mode; query.agent = agent.key
    void router.push({ query })
  }
  if (current.value) void updateAIConversation(current.value.id, { current_agent: agent.key })
}
async function changePaperType() { if (current.value && !sending.value) await updateAIConversation(current.value.id, { paper_type: paperType.value || null }) }
async function saveArtifact(message: AIConversationMessage) { const material = materials.value.find((item) => item.id === targetMaterialId.value); const logId = Number(message.generation_log); const content = artifactDrafts.value[message.id] || message.artifact_payload?.draft || message.content; if (!material || !logId || !content) return; savingMessage.value = message.id; try { await saveAIGenerationAsMaterial(logId, { material: material.id, content, revision_note: '由全局 AI 对话保存为材料草稿' }) } catch (reason) { error.value = errorMessage(reason, '保存材料草稿失败。') } finally { savingMessage.value = null } }
function onKeydown(event: KeyboardEvent) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage() } }
function onGlobalKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  agentOpen.value = false
  contextOpen.value = false
  historyOpen.value = false
}
watch(showArchived, () => { void loadConversations() })
let applyingRouteContext = false
watch(projectFilter, (value, previous) => {
  if (value === previous || applyingRouteContext || brainstormMode.value) return
  void reloadForProjectFilter()
})
async function reloadForProjectFilter() {
  if (applyingRouteContext) return
  applyingRouteContext = true
  try {
    resetConversationSelection()
    await loadConversations()
    if (!selectedId.value) await newConversation()
  } catch (reason) {
    error.value = errorMessage(reason, '项目筛选切换失败，请重试。')
  } finally {
    applyingRouteContext = false
  }
}
async function reloadForRouteContext() {
  if (applyingRouteContext) return
  applyingRouteContext = true
  try {
    projectFilter.value = brainstormMode.value ? null : queryNumber(route.query.projectId)
    taskId.value = queryNumber(route.query.taskId) ?? undefined
    selectedAgent.value = routeAgent()
    resetConversationSelection()
    if (brainstormMode.value) {
      await refreshConversationList()
      await newConversation()
    } else {
      await loadConversations()
      if (!selectedId.value) await newConversation()
    }
  } catch (reason) {
    error.value = errorMessage(reason, 'AI 工作台上下文切换失败，请重试。')
  } finally {
    applyingRouteContext = false
  }
}
watch(() => [route.query.projectId, route.query.taskId, route.query.mode] as const, (next, previous) => {
  if (!previous || next.every((value, index) => value === previous[index])) return
  void reloadForRouteContext()
})
watch(() => route.query.researchQuestion, (value) => {
  if (value === '1') {
    selectedAgent.value = 'proposal-topic'
    prefillResearchFromProject(currentProject.value)
  }
})
watch(() => route.query.mode, (value) => {
  if (value === 'brainstorm') {
    projectFilter.value = null
    selectedAgent.value = 'proposal-topic'
  }
})
watch(currentProject, (project) => prefillResearchFromProject(project), { immediate: true })
onMounted(async () => { window.addEventListener('keydown', onGlobalKeydown); try { if (brainstormMode.value) { projectFilter.value = null; selectedAgent.value = 'proposal-topic' } const [projectResponse, agentResponse] = await Promise.all([getProjects(), getAIAgents()]); projects.value = projectResponse.data; agents.value = agentResponse.data; if (brainstormMode.value) { await refreshConversationList(); await newConversation() } else { await loadConversations(); if (!selectedId.value) await newConversation() } } catch (reason) { error.value = errorMessage(reason, 'AI 工作台加载失败。') } finally { loading.value = false; await nextTick(); scrollToLatest('auto') } })
onBeforeUnmount(() => { window.removeEventListener('keydown', onGlobalKeydown); requestVersion.value += 1; abortActiveStream() })
</script>

<template>
  <div class="page ai-center-page">
    <PageHeader eyebrow="AI 助手" :title="researchMode ? '一步一步把问题想清楚' : '灵思 AI'" :description="aiPageDescription" />
    <div class="conversation-page">
    <AIConversationHistory v-if="historyOpen" :groups="visibleConversationGroups" :selected-id="selectedId" :sending="sending" :search="conversationSearch" :show-archived="showArchived" @update:search="conversationSearch = $event" @new="void newConversation()" @select="void selectConversation($event)" @toggle-archived="showArchived = !showArchived" @close="historyOpen = false" />

    <div class="ai-simple-layout" :class="{ 'is-research-mode': researchMode }">
      <section class="chat-main ai-main-panel">
        <header class="chat-header"><div><span class="eyebrow">灵思 AI · 研究伙伴</span><div v-if="renaming" class="rename-row"><input v-model="titleDraft" aria-label="对话标题" @keydown.enter="void saveRename()" /><button type="button" :disabled="sending" @click="void saveRename()">保存</button><button type="button" :disabled="sending" @click="renaming = false">取消</button></div><div v-else class="title-row"><h2>{{ researchMode ? '研究问题引导' : currentDisplayTitle }}</h2><button v-if="current && !current.is_archived && !researchMode" class="rename-button" type="button" :disabled="sending" @click="startRename">重命名对话</button></div><small>{{ researchMode ? 'AI 会追问、比较和整理；最终决定权在你。' : workspaceContextLabel }}</small></div><div class="chat-actions"><button v-if="!researchMode" type="button" :aria-expanded="historyOpen" aria-controls="conversation-history" @click="historyOpen = !historyOpen">历史对话</button><button v-if="!researchMode" type="button" :disabled="sending" :aria-label="`选择 AI 工具（${agents.length} 个）${currentAgent ? ` · ${currentAgent.name}` : ''}`" aria-controls="agent-menu" :aria-expanded="agentOpen" @click="agentOpen = !agentOpen">科创 Agent{{ currentAgent ? ` · ${currentAgent.name}` : '' }}⌄</button><button v-if="current && !current.is_archived && !researchMode" type="button" :disabled="sending" @click="archiveCurrent">归档</button></div></header>
        <AIContextChooser :brainstorm="brainstormMode" :agent-active="agentOpen" :disabled="sending" @existing="goToExistingProject" @brainstorm="goToBrainstorm" @agent="openScienceAgentPicker" />
        <div v-if="!researchMode" class="ai-context-summary"><div><p class="eyebrow">当前使用场景</p><h2>{{ aiContextTitle }}</h2><p>{{ aiContextDescription }}</p></div><span class="ai-context-status">{{ currentProject ? '已有项目 · 当前任务' : brainstormMode ? '无项目 · 选题引导' : '等待选择场景' }}</span></div>
        <div v-if="!researchMode && !loading && !messages.length" class="ai-stepper-simple" aria-label="AI 工作方式"><div v-for="(label, index) in aiStepperLabels" :key="label" class="ai-step-simple" :class="{ active: index === 0 }"><span>{{ index + 1 }}</span><small>{{ label }}</small></div></div>
        <div v-if="!researchMode && !loading && !messages.length" class="ai-guide-card"><AIProjectAssistant :project="currentProject" @prompt="fillQuickPrompt" @choose-project="router.push('/student/projects')" /></div>
      <AIToolPicker v-if="agentOpen" :categories="agentCategories" :groups="groupedAgents" :search="agentSearch" :category="agentCategory" :sending="sending" @update:search="agentSearch = $event" @update:category="agentCategory = $event" @choose="chooseAgent" />
      <AIResearchWizard v-if="researchMode && !loading" :workspace-mode="workspaceMode === 'brainstorm' ? 'brainstorm' : 'project'" :workspace-context-label="workspaceContextLabel" :research-step="researchStep" :research-inputs="researchInputs" :research-artifact="researchArtifact" :research-selected-index="researchSelectedIndex" :research-draft="researchDraft" :research-save-confirm="researchSaveConfirm" :research-saved="researchSaved" :research-save-error="researchSaveError" :research-fallback="researchFallback" :project-draft="projectDraft" :current-project="currentProject" :sending="sending" :creating-project="creatingProject" :project-created="projectCreated" @update:research-step="researchStep = $event" @update:research-draft="researchDraft = $event" @update:research-save-confirm="researchSaveConfirm = $event" @update:research-fallback="researchFallback = $event; projectDraft.problem = $event" @advance-from-observation="advanceFromObservation" @generate="void generateResearchCandidates()" @choose-candidate="chooseResearchCandidate" @edit-candidate="editResearchCandidate" @open-draft="openResearchDraft" @request-save="requestResearchSave" @create-project="void createProjectFromResearch()" @save-question="void saveResearchQuestion()" @copy-question="copyResearchQuestion" />
      <div v-if="error" class="error-banner">{{ error }}</div><div v-if="streamNotice" class="stream-notice">{{ streamNotice }}</div>
      <section v-if="!researchMode && (loading || messages.length)" ref="chatStreamRef" class="chat-stream" aria-live="polite" :aria-busy="sending" @scroll="updateScrollAffordance"><div v-if="loading" class="empty-state">正在加载对话…</div><article v-for="message in messages" :key="message.id" class="message" :class="message.role"><div class="message-label">{{ message.role === 'user' ? '你' : '灵思 AI' }}</div><div class="message-body">{{ message.content || (message.status === 'queued' ? '正在排队…' : message.status === 'streaming' ? '正在生成…' : '') }}<div v-if="message.status === 'failed'" class="message-error"><span>{{ message.error_message || '生成失败' }}</span><button type="button" class="retry-button" :disabled="sending" @click="retryMessage(message)">{{ sending ? '重试中…' : '重试' }}</button></div><div v-if="message.artifact_payload?.draft" class="artifact-card"><b>{{ message.artifact_payload.title || '可编辑草稿' }}</b><textarea v-model="artifactDrafts[message.id]" :placeholder="message.artifact_payload.draft" rows="5" /><small>核验项：{{ message.verification_items?.length || 0 }} 项 · {{ message.artifact_payload.next_action || '请核对事实与引用' }}</small><label v-if="materials.length" class="target-material"><span>保存到指定材料</span><select v-model="targetMaterialId"><option :value="null">请选择目标材料</option><option v-for="material in materials" :key="material.id" :value="material.id">{{ material.title }}</option></select></label><button v-if="materials.length && message.status === 'completed'" type="button" class="save-draft" :disabled="savingMessage === message.id || !targetMaterialId" @click="saveArtifact(message)">{{ savingMessage === message.id ? '保存中…' : '保存到指定材料' }}</button></div></div></article></section>
      <button v-if="!researchMode && showJumpLatest" type="button" class="jump-latest" @click="scrollToLatest()">↓ 跳到最新消息</button>
      <footer v-if="(!researchMode && currentProject) || researchSaved" class="composer"><details v-if="!researchMode && currentAgent?.input_schema?.length" class="input-details"><summary>补充信息（可选）</summary><p class="input-help">填写后可让 AI 工具更准确；不填写也可以直接提问。</p><label v-for="field in currentAgent.input_schema" :key="field.key">{{ field.label }}<textarea v-if="field.type === 'textarea'" v-model="agentInputs[field.key]" :placeholder="field.placeholder" rows="2" /><input v-else v-model="agentInputs[field.key]" :placeholder="field.placeholder" /></label></details><div class="composer-meta"><span>{{ currentAgent ? `使用 ${currentAgent.name}` : '自由咨询' }}</span><span>{{ currentProject ? `项目：${currentProject.title}` : '未绑定项目' }}</span></div><textarea v-model="draft" :disabled="sending || current?.is_archived" placeholder="输入问题，或输入 / 选择一个 AI 工具…" rows="3" @keydown="onKeydown" /><div class="composer-footer"><small>Enter 发送 · Shift+Enter 换行</small><button class="send-button" type="button" :disabled="sending || !draft.trim() || !selectedId" @click="void sendMessage()">{{ sending ? '生成中…' : '发送' }}</button></div></footer>
      </section>

      <aside v-if="!researchMode" class="ai-scope-card"><p class="eyebrow">AI 的边界</p><h2>{{ currentProject ? '只帮助当前项目' : '你决定，AI 陪你想' }}</h2><ul><li>AI 会追问和整理，不直接替你下结论</li><li>{{ currentProject ? '不会切换到其他项目' : '确认草稿前不会创建空项目' }}</li><li>每次生成后都由你检查和确认</li></ul><div class="ai-scope-divider" /><p class="eyebrow">下一步</p><strong>{{ currentProject ? '确认建议是否可用' : '先选择已有项目或进入选题引导' }}</strong><p class="ai-note">{{ currentProject ? '建议只作为研究过程中的辅助，保存前请核对事实和引用。' : '无课题时，AI 会从现象、问题和头脑风暴开始，不会直接替你命题。' }}</p><button class="scope-context-button" type="button" @click="contextOpen = !contextOpen">{{ contextOpen ? '收起上下文设置' : '查看上下文设置' }}</button></aside>
    </div>
    <aside v-if="contextOpen" id="conversation-context" class="context-panel"><div class="context-heading"><b>项目上下文</b><button type="button" aria-label="关闭上下文设置" @click="contextOpen = false">×</button></div><p class="eyebrow">当前项目</p><h3>{{ currentProject?.title || '未绑定项目' }}</h3><p class="muted">当前对话只能绑定一个项目，切换项目请新建对话。</p><label v-if="currentAgent?.workflow === 'paper'" class="paper-picker"><span class="eyebrow">论文类型</span><select v-model="paperType" @change="changePaperType"><option value="">请选择</option><option v-for="item in paperTypes" :key="item.value" :value="item.value">{{ item.label }}</option></select></label><p class="eyebrow">可读取范围</p><ul><li>项目基本信息</li><li>当前任务与材料</li><li>AI 工具允许读取的项目摘要</li></ul><p class="eyebrow">当前 AI 工具</p><p>{{ currentAgent?.name || '自由咨询' }}</p></aside>
    </div>
  </div>
</template>

<style scoped>
.conversation-page {
  min-width: 0;
  max-width: 1120px;
  margin: 0 auto;
  overflow: visible;
}
.ai-simple-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(260px, .6fr);
  gap: 20px;
  align-items: start;
  min-width: 0;
}
.ai-simple-layout.is-research-mode {
  grid-template-columns: minmax(0, 1fr);
}
.chat-main {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  position: relative;
  overflow: visible;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: var(--shadow-soft);
}
.chat-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  min-width: 0;
  padding: 18px 26px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--paper);
}
.chat-header > div:first-child {
  min-width: 0;
  flex: 1 1 auto;
}
.chat-header h2 {
  margin: 4px 0 6px;
  color: var(--ink);
  font: 700 19px/1.3 var(--sans);
}
.chat-header small {
  display: block;
  color: var(--muted);
  line-height: 1.55;
}
.ai-context-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin: 0 26px;
  padding: 18px 0;
  border-bottom: 1px solid var(--line);
}
.ai-context-summary h2 {
  margin: 3px 0 5px;
  color: var(--ink);
  font: 700 22px/1.35 var(--sans);
}
.ai-context-summary p:last-child {
  max-width: 620px;
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.65;
}
.ai-context-status {
  flex: 0 0 auto;
  padding: 5px 9px;
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  background: var(--sage-soft);
  color: var(--moss-dark);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}
.ai-stepper-simple {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 18px 26px 10px;
}
.ai-step-simple {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  color: var(--muted-light);
  font-size: 11px;
}
.ai-step-simple span {
  display: grid;
  width: 24px;
  height: 24px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: var(--paper-muted);
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
}
.ai-step-simple.active {
  color: var(--moss-dark);
  font-weight: 700;
}
.ai-step-simple.active span {
  background: var(--moss);
  color: #fff;
}
.ai-guide-card {
  margin: 0 26px 18px;
  padding-top: 16px;
}
.eyebrow {
  color: var(--moss);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .08em;
  line-height: 1.4;
  text-transform: uppercase;
}
.title-row,
.rename-row {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 8px;
}
.title-row { display: block; }
.title-row h1 {
  min-width: 0;
  overflow-wrap: anywhere;
}
.title-row .rename-button { margin-top: 6px; }
.rename-row input {
  min-width: 0;
  width: min(320px, 100%);
  padding: 8px 10px;
}
.rename-button,
.rename-row button,
.chat-actions button {
  min-height: 32px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--ink);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.rename-button:hover,
.rename-button:focus-visible,
.rename-row button:hover,
.rename-row button:focus-visible,
.chat-actions button:hover,
.chat-actions button:focus-visible {
  border-color: var(--moss);
  background: var(--sage-soft);
}
.rename-row button:disabled,
.chat-actions button:disabled {
  cursor: wait;
  opacity: .65;
}
.chat-actions {
  flex: 0 0 auto;
  max-width: 260px;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
}
.chat-actions button {
  background: var(--paper-soft);
  white-space: nowrap;
}
.error-banner,
.stream-notice {
  margin: 12px 26px 0;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.5;
}
.error-banner {
  background: #fff0ed;
  color: #8e4438;
}
.stream-notice {
  background: var(--sage-soft);
  color: var(--moss-dark);
}
.chat-stream {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  max-height: min(58vh, 680px);
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  padding: 26px;
  display: grid;
  align-content: start;
  gap: 20px;
}
.empty-state {
  display: grid;
  place-items: center;
  min-height: 220px;
  margin: auto;
  color: var(--muted);
  text-align: center;
}
.empty-state strong {
  display: block;
  color: var(--ink);
  font: 700 22px/1.35 var(--sans);
}
.empty-state p {
  max-width: 420px;
  margin: 8px 0 0;
  line-height: 1.6;
}
.message {
  display: flex;
  max-width: 82%;
  min-width: 0;
  gap: 10px;
}
.message.user {
  flex-direction: row-reverse;
  margin-left: auto;
}
.message-label {
  flex: 0 0 auto;
  padding-top: 8px;
  color: var(--muted);
  font-size: 11px;
  white-space: nowrap;
}
.message-body {
  min-width: 0;
  padding: 12px 15px;
  border-radius: 12px;
  background: var(--paper-soft);
  color: var(--ink);
  line-height: 1.7;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.message.user .message-body {
  background: var(--sage-soft);
}
.message-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
  color: #9b4d3e;
}
.retry-button,
.save-draft {
  border: 1px solid var(--line-dark);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--moss-dark);
  padding: 6px 9px;
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}
.retry-button:hover,
.retry-button:focus-visible,
.save-draft:hover,
.save-draft:focus-visible {
  border-color: var(--moss);
  background: var(--sage-soft);
}
.retry-button:disabled,
.save-draft:disabled {
  cursor: wait;
  opacity: .65;
}
.artifact-card {
  display: grid;
  gap: 8px;
  margin-top: 14px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--paper);
}
.artifact-card textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
}
.artifact-card small {
  color: var(--muted);
  line-height: 1.5;
}
.target-material {
  display: grid;
  gap: 4px;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}
.target-material select {
  width: 100%;
  box-sizing: border-box;
  padding: 7px;
}
.jump-latest {
  align-self: flex-end;
  margin: 0 26px 10px;
  padding: 7px 10px;
  border: 1px solid var(--line-dark);
  border-radius: 999px;
  background: var(--paper);
  color: var(--moss-dark);
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}
.jump-latest:hover,
.jump-latest:focus-visible {
  border-color: var(--moss);
  background: var(--sage-soft);
}
.composer {
  display: grid;
  gap: 8px;
  margin: 0 26px 24px;
  padding: 12px;
  border: 1px solid var(--line-dark);
  border-radius: var(--radius-md);
  background: var(--paper);
}
.composer textarea {
  width: 100%;
  box-sizing: border-box;
  min-height: 72px;
  border: 0;
  padding: 10px 0;
  resize: vertical;
  box-shadow: none;
}
.composer textarea:focus {
  outline: none;
}
.composer-meta,
.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
  color: var(--muted);
  font-size: 11px;
}
.composer-meta span {
  min-width: 0;
  overflow-wrap: anywhere;
}
.composer-footer {
  align-items: flex-end;
}
.input-details {
  display: grid;
  gap: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.input-details summary {
  color: var(--moss-dark);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}
.input-details label {
  display: grid;
  gap: 4px;
  color: var(--muted);
  font-size: 12px;
}
.input-details input,
.input-details textarea {
  min-height: 36px;
  border: 1px solid var(--line);
  padding: 8px;
}
.input-help {
  margin: 0;
  color: var(--muted);
  font-size: 11px;
}
.send-button {
  min-width: 72px;
  min-height: 36px;
  padding: 8px 13px;
  border: 1px solid var(--moss-dark);
  border-radius: var(--radius-sm);
  background: var(--moss);
  color: #fff;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.send-button:hover,
.send-button:focus-visible {
  background: var(--moss-dark);
}
.send-button:disabled {
  cursor: wait;
  opacity: .62;
}
.ai-scope-card {
  align-self: start;
  position: sticky;
  top: 146px;
  min-width: 0;
  padding: 22px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: var(--shadow-soft);
}
.ai-scope-card h2 {
  margin: 6px 0 14px;
  color: var(--ink);
  font: 700 20px/1.35 var(--sans);
}
.ai-scope-card ul {
  display: grid;
  gap: 10px;
  margin: 0 0 20px;
  padding-left: 17px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
}
.ai-scope-divider {
  height: 1px;
  margin: 0 0 18px;
  background: var(--line);
}
.ai-scope-card > strong {
  display: block;
  margin: 4px 0 8px;
  color: var(--moss-dark);
  font-size: 13px;
}
.ai-note {
  margin: 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.6;
}
.scope-context-button {
  margin-top: 16px;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--moss-dark);
  font: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}
.context-panel {
  position: fixed;
  top: 112px;
  right: 24px;
  z-index: 90;
  width: min(300px, calc(100vw - 48px));
  max-height: calc(100vh - 136px);
  overflow-y: auto;
  padding: 20px;
  border: 1px solid var(--line-dark);
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: var(--shadow-hover);
}
.context-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 22px;
}
.context-heading button {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 20px;
  cursor: pointer;
}
.context-panel h3 {
  margin: 6px 0 16px;
  color: var(--ink);
  font: 700 18px/1.35 var(--sans);
  overflow-wrap: anywhere;
}
.context-panel ul {
  margin: 6px 0 18px;
  padding-left: 17px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.9;
}
.paper-picker {
  display: grid;
  gap: 6px;
  margin: 16px 0;
}
.paper-picker select {
  width: 100%;
  box-sizing: border-box;
}
.muted {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}
@media (max-width: 900px) {
  .ai-simple-layout,
  .ai-simple-layout.is-research-mode {
    grid-template-columns: minmax(0, 1fr);
  }
  .ai-scope-card {
    position: static;
  }
  .chat-stream {
    max-height: none;
  }
  .context-panel {
    top: 94px;
    right: 16px;
    max-height: calc(100vh - 110px);
  }
}
@media (max-width: 620px) {
  .ai-context-summary {
    flex-direction: column;
    gap: 10px;
    margin-inline: 16px;
  }
  .ai-context-summary h2 {
    font-size: 20px;
  }
  .ai-stepper-simple {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-inline: 16px;
  }
  .ai-guide-card {
    margin-inline: 16px;
  }
  .chat-header {
    display: block;
    padding: 18px 16px;
  }
  .chat-actions {
    justify-content: flex-start;
    margin-top: 10px;
  }
  .title-row,
  .rename-row {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .chat-stream {
    padding: 18px;
  }
  .message {
    max-width: 100%;
  }
  .message.user {
    margin-left: 0;
  }
  .composer {
    margin: 0 12px 12px;
  }
  .ai-scope-card {
    padding: 18px;
  }
  .context-panel {
    left: 12px;
    right: 12px;
    width: auto;
  }
  .composer-meta,
  .composer-footer {
    align-items: flex-start;
    flex-direction: column;
  }
  .composer-footer {
    align-items: stretch;
  }
  .send-button {
    width: 100%;
  }
}
</style>
