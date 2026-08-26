<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, archiveAIConversation, createAIConversation, createAIConversationMessage, createProjectFromOpening, errorMessage, getAIAgents, getAIConversationMessages, getAIConversations, getMaterials, getProjects, retryAIConversationMessage, saveAIGenerationAsMaterial, streamAIConversationMessage, updateAIConversation, type AIAgent, type AIConversation, type AIConversationMessage, type Material, type Project } from '../../api'
import { auth } from '../../stores/auth'
import { aiWorkspaceMode, buildResearchQuestionPrompt, filterConversations, groupAgentsByCategory, isNearBottom, isTerminalSSEEvent, normalizeResearchQuestionArtifact, optionalAgentInputs, researchProjectDraftFromArtifact, researchResponseNotice, type ResearchQuestionArtifact, type ResearchQuestionInputs } from '../../stores/aiConversationModel'
import { materialSelectionScope, normalizeAIWorkspaceMode, resolveAIContext, visibleAgents, type AIWorkspaceMode } from '../../stores/aiWorkbenchModel'
import { conversationDisplayTitle, groupConversationSummaries } from '../../stores/presentationModel'
import { studentProjectRoute } from '../../stores/pageContracts'
import AIModeTabs from '../../components/ai/AIModeTabs.vue'
import AIContextDrawer from '../../components/ai/AIContextDrawer.vue'
import AIConversationHistory from '../../components/ai/AIConversationHistory.vue'
import AIDraftActions from '../../components/ai/AIDraftActions.vue'
import AIResearchWizard from '../../components/ai/AIResearchWizard.vue'
import AIToolPicker from '../../components/ai/AIToolPicker.vue'
import AIWorkbenchComposer from '../../components/ai/AIWorkbenchComposer.vue'

const route = useRoute()
const router = useRouter()

function queryNumber(value: unknown): number | null {
  const raw = Array.isArray(value) ? value[0] : value
  const parsed = Number(raw)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}
function routeAgent(): string | undefined {
  if (route.query.mode === 'brainstorm' || route.query.mode === 'opening' || route.query.researchQuestion === '1') return 'proposal-topic'
  return typeof route.query.agent === 'string' ? route.query.agent : undefined
}

const conversations = ref<AIConversation[]>([])
const messages = ref<AIConversationMessage[]>([])
const projects = ref<Project[]>([])
const agents = ref<AIAgent[]>([])
const selectedId = ref<number | null>(null)
const projectFilter = ref<number | null>(route.query.mode === 'opening' || route.query.mode === 'brainstorm' ? null : queryNumber(route.query.projectId) ?? auth.user.value?.primaryProject ?? null)
const selectedAgent = ref<string | undefined>(routeAgent())
const taskId = ref<number | undefined>(queryNumber(route.query.taskId) ?? undefined)
const conversationSearch = ref('')
const conversationPreviews = ref<Record<number, string>>({})
const agentSearch = ref('')
const agentCategory = ref('all')
const historyOpen = ref(false)
const draft = ref('')
const loading = ref(true)
const projectsLoading = ref(true)
const agentsLoading = ref(true)
const projectResourceError = ref('')
const agentResourceError = ref('')
const sending = ref(false)
const contextOpen = ref(false)
const agentOpen = ref(false)
const showArchived = ref(false)
const error = ref('')
const paperType = ref('')
const materials = ref<Material[]>([])
const artifactDrafts = ref<Record<number, string>>({})
const savingMessage = ref<number | null>(null)
const targetMaterialId = ref<number | null>(null)
const renaming = ref(false)
const titleDraft = ref('')
const chatStreamRef = ref<HTMLElement | null>(null)
const showJumpLatest = ref(false)
const streamNotice = ref('')
const referencedSources = ref<string[]>([])
const selectedMaterialIds = ref<number[]>([])
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
const currentProject = computed(() => projects.value.find((item) => item.id === (current.value?.project ?? projectFilter.value)) || null)
const currentDisplayTitle = computed(() => current.value ? conversationDisplayTitle(current.value, conversationPreviews.value[current.value.id] || '') : '新建科创对话')
const workbenchMode = computed<AIWorkspaceMode>(() => normalizeAIWorkspaceMode(route.query.mode))
const visibleConversations = computed(() => filterConversations(conversations.value, { project: projectFilter.value, includeArchived: showArchived.value }).filter((item) => {
  const keyword = conversationSearch.value.trim().toLowerCase()
  if (!keyword) return true
  return `${conversationDisplayTitle(item, conversationPreviews.value[item.id] || '')} ${item.project_title || ''}`.toLowerCase().includes(keyword)
}))
const visibleConversationGroups = computed(() => groupConversationSummaries(visibleConversations.value, conversationPreviews.value))
const modeAgents = computed(() => visibleAgents(workbenchMode.value, agents.value))
const currentAgent = computed(() => {
  const selected = modeAgents.value.find((item) => item.key === selectedAgent.value)
  const conversationAgent = modeAgents.value.find((item) => item.key === current.value?.current_agent)
  const guidedOpeningAgent = workbenchMode.value === 'research' && route.query.researchQuestion === '1'
    ? agents.value.find((item) => item.key === selectedAgent.value || item.key === current.value?.current_agent)
    : null
  return selected || conversationAgent || guidedOpeningAgent || modeAgents.value[0] || null
})
const allowedSelections = computed(() => {
  const value = currentAgent.value?.context_scope_default?.allowed_selections
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
})
const canSelectMaterials = computed(() => workbenchMode.value !== 'opening' && allowedSelections.value.includes('selected_materials'))
const hasConversationMessages = computed(() => messages.value.length > 0)
const agentCategories = computed(() => ['all', ...new Set(modeAgents.value.map((agent) => agent.category?.trim()).filter(Boolean) as string[])])
const filteredAgents = computed(() => modeAgents.value.filter((agent) => {
  const keyword = agentSearch.value.trim().toLowerCase()
  const matchesKeyword = !keyword || `${agent.name} ${agent.description} ${agent.category}`.toLowerCase().includes(keyword)
  return matchesKeyword && (agentCategory.value === 'all' || (agent.category || '其他') === agentCategory.value)
}))
const groupedAgents = computed(() => groupAgentsByCategory(filteredAgents.value))
watch(agentCategories, (categories) => {
  if (!categories.includes(agentCategory.value)) agentCategory.value = 'all'
})
const brainstormMode = computed(() => workbenchMode.value === 'opening')
const workspaceMode = computed(() => aiWorkspaceMode({
  brainstorm: brainstormMode.value,
  researchQuestion: route.query.researchQuestion === '1',
  projectId: projectFilter.value,
  conversationProject: current.value?.project ?? null,
  selectedAgent: selectedAgent.value,
}))
const researchMode = computed(() => brainstormMode.value || (workbenchMode.value === 'research' && workspaceMode.value === 'project' && (route.query.researchQuestion === '1' || selectedAgent.value === 'proposal-topic')))
const aiContext = computed(() => resolveAIContext(workbenchMode.value, currentProject.value?.id ?? projectFilter.value))
const workspaceContextLabel = computed(() => brainstormMode.value ? '无项目 · 开题引导' : currentProject.value?.title || (aiContext.value.projectId ? '当前项目 · 正在加载' : '未绑定项目 · 请选择项目'))
const workspaceContextTitle = computed(() => brainstormMode.value ? '开题草稿' : currentProject.value ? '当前项目内容' : '尚未选择项目')
const workspaceContextDetail = computed(() => {
  if (brainstormMode.value) return '开题不读取项目材料'
  if (!currentProject.value) return '选择项目后开始研究'
  const materialLabel = materials.value.length ? `可引用 ${materials.value.length} 份材料` : '暂无可引用材料'
  const selectedLabel = selectedMaterialIds.value.length ? ` · 已选 ${selectedMaterialIds.value.length} 份` : ''
  return `${materialLabel}${selectedLabel} · 仅读取当前项目`
})
const aiPageDescription = computed(() => {
  if (workbenchMode.value === 'opening') return '整理观察、研究问题和开题草稿；确认后再创建项目。'
  if (workbenchMode.value === 'defense') return '围绕已完成成果练习表达，生成可编辑的展示和答辩建议。'
  if (currentProject.value) return '围绕当前项目的任务、材料和进度，直接处理下一步研究工作。'
  return '选择项目后，灵思 AI 才会读取项目范围内的内容。'
})
const aiEmptyDescription = computed(() => {
  if (workbenchMode.value === 'opening') return '写下你的观察或研究想法，先从一个可研究的问题开始。'
  if (workbenchMode.value === 'defense') return '直接说出想准备的展示、摘要或答辩问题，结果会先作为可编辑建议。'
  if (currentProject.value) return '告诉灵思你现在要推进的任务，它会基于当前项目给出可核对的建议。'
  return '选择一个项目后，才能读取项目中的任务和材料。'
})
const resourceErrorMessage = computed(() => [projectResourceError.value, agentResourceError.value].filter(Boolean).join('；'))
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
  selectedMaterialIds.value = []
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
  const modeAgent = modeAgents.value.find((agent) => agent.key === item.current_agent) || modeAgents.value[0]
  selectedAgent.value = modeAgent?.key || item.current_agent || selectedAgent.value
  paperType.value = item.paper_type || ''
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
  const item = (await createAIConversation({ project: workbenchMode.value === 'opening' ? null : projectFilter.value, workspace_mode: workbenchMode.value, current_agent: selectedAgent.value || null })).data
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

function selectWorkbenchMode(mode: AIWorkspaceMode) {
  const projectId = currentProject.value?.id ?? projectFilter.value ?? auth.user.value?.primaryProject ?? projects.value.find((project) => project.status === 'active')?.id ?? null
  const nextAgent = visibleAgents(mode, agents.value)[0]
  selectedAgent.value = nextAgent?.key
  const query: Record<string, string> = { mode }
  if (mode === 'opening') query.agent = 'proposal-topic'
  else {
    if (projectId) query.projectId = String(projectId)
    if (nextAgent) query.agent = nextAgent.key
  }
  void router.push({ path: '/student/ai', query })
}

function openScienceAgentPicker() {
  agentOpen.value = true
  contextOpen.value = false
  historyOpen.value = false
}

function toggleHistory() {
  historyOpen.value = !historyOpen.value
  if (historyOpen.value) {
    contextOpen.value = false
    agentOpen.value = false
  }
}

function toggleContext() {
  if (workbenchMode.value === 'opening') return
  contextOpen.value = !contextOpen.value
  if (contextOpen.value) {
    historyOpen.value = false
    agentOpen.value = false
  }
}

function citeProjectMaterial() {
  if (workbenchMode.value === 'opening') return
  contextOpen.value = true
  streamNotice.value = canSelectMaterials.value ? '选择后会将当前项目材料作为本次生成的可核验来源。' : '当前 Agent 使用默认项目上下文，暂不支持手动选择材料。'
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
    const inputValues = optionalAgentInputs(options.inputValues || {})
    const response = await createAIConversationMessage(conversationId, { content, agent_key: selectedAgent.value, paper_type: paperType.value || undefined, project: current.value?.project, workspace_mode: workbenchMode.value, task: taskId.value, context_scope: materialSelectionScope(workbenchMode.value, selectedMaterialIds.value, allowedSelections.value), ...(inputValues ? { input_values: inputValues } : {}) })
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
  const sourceMessage = [...messages.value].reverse().find((item) => item.role === 'assistant' && item.status === 'completed' && normalizeResearchQuestionArtifact(item.artifact_payload))
  if (!sourceMessage || !selectedId.value) {
    researchSaveError.value = '开题草稿还没有完成，请先生成并核对候选研究问题。'
    return
  }
  creatingProject.value = true
  try {
    const response = await createProjectFromOpening(selectedId.value, {
      confirm: true,
      message_id: sourceMessage.id,
      candidate_index: researchSelectedIndex.value ?? researchArtifact.value?.recommended_index ?? 0,
      ...payload,
    })
    projects.value.unshift(response.data)
    projectCreated.value = true
    await router.push(studentProjectRoute(response.data.id, 'map'))
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
    const response = await retryAIConversationMessage(conversationId, message.id)
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
  agentOpen.value = false
  researchSaveError.value = ''
  if (agent.key === 'proposal-topic') {
    void router.push({ query: { ...route.query, mode: route.query.mode || (currentProject.value ? 'research' : 'opening'), researchQuestion: '1', agent: agent.key } })
    researchStep.value = currentProject.value?.problem?.trim() ? 1 : 1
    prefillResearchFromProject(currentProject.value)
  } else if (route.query.researchQuestion) {
    const query = { ...route.query }; delete query.researchQuestion; query.agent = agent.key
    void router.push({ query })
  }
  if (current.value) void updateAIConversation(current.value.id, { current_agent: agent.key })
}
async function changePaperType() { if (current.value && !sending.value) await updateAIConversation(current.value.id, { paper_type: paperType.value || null }) }
async function saveArtifact(message: AIConversationMessage) { const material = materials.value.find((item) => item.id === targetMaterialId.value); const logId = Number(message.generation_log); const content = artifactDrafts.value[message.id] || message.artifact_payload?.draft || message.content; if (!material) { error.value = '请选择要保存到的目标材料。'; return } if (!logId || !content) { error.value = '这份草稿还没有可保存的内容。'; return } savingMessage.value = message.id; try { await saveAIGenerationAsMaterial(logId, { material: material.id, content, workspace_mode: workbenchMode.value, revision_note: '由全局 AI 对话保存为材料草稿' }); streamNotice.value = `草稿已提交到材料“${material.title}”，请在材料页面继续审核。` } catch (reason) { error.value = errorMessage(reason, '保存材料草稿失败。') } finally { savingMessage.value = null } }
function createProjectFromArtifact(message: AIConversationMessage) { const artifact = normalizeResearchQuestionArtifact(message.artifact_payload); if (!artifact) { error.value = '这份输出还不是结构化开题报告，请先继续对话整理。'; return } researchArtifact.value = artifact; researchSelectedIndex.value = artifact.recommended_index; researchDraft.value = artifact.candidates[artifact.recommended_index]?.question || ''; projectDraft.value = researchProjectDraftFromArtifact(artifact, artifact.recommended_index); researchStep.value = 4; streamNotice.value = '已将开题报告放入确认区，确认后才会创建项目。' }
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
    projectFilter.value = brainstormMode.value ? null : queryNumber(route.query.projectId) ?? auth.user.value?.primaryProject ?? projects.value.find((project) => project.status === 'active')?.id ?? null
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
  if (value === 'brainstorm' || value === 'opening') {
    projectFilter.value = null
    selectedAgent.value = 'proposal-topic'
  }
})
watch(currentProject, (project) => prefillResearchFromProject(project), { immediate: true })

async function loadProjectsResource() {
  projectsLoading.value = true
  projectResourceError.value = ''
  try {
    const response = await getProjects()
    projects.value = response.data
    if (!brainstormMode.value && projectFilter.value === null) {
      projectFilter.value = queryNumber(route.query.projectId)
        ?? auth.user.value?.primaryProject
        ?? projects.value.find((project) => project.status === 'active')?.id
        ?? null
    }
  } catch (reason) {
    projectResourceError.value = errorMessage(reason, '项目上下文加载失败，请重试。')
  } finally {
    projectsLoading.value = false
  }
}

async function loadAgentsResource() {
  agentsLoading.value = true
  agentResourceError.value = ''
  try {
    const response = await getAIAgents()
    agents.value = response.data
    if (!selectedAgent.value && !brainstormMode.value) selectedAgent.value = visibleAgents(workbenchMode.value, response.data)[0]?.key
  } catch (reason) {
    agentResourceError.value = errorMessage(reason, '当前模式的 AI 能力加载失败，请重试。')
  } finally {
    agentsLoading.value = false
  }
}

async function bootstrapWorkbench() {
  loading.value = true
  error.value = ''
  const projectsPromise = loadProjectsResource()
  const agentsPromise = loadAgentsResource()
  try {
    await projectsPromise
    if (brainstormMode.value) {
      projectFilter.value = null
      selectedAgent.value = 'proposal-topic'
      await refreshConversationList()
      if (!selectedId.value) await newConversation()
    } else {
      await loadConversations()
      if (!selectedId.value && projectFilter.value !== null) await newConversation()
    }
    await agentsPromise
  } catch (reason) {
    error.value = errorMessage(reason, '历史会话加载失败，请重试。')
  } finally {
    loading.value = false
    await nextTick()
    scrollToLatest('auto')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
  void bootstrapWorkbench()
})
onBeforeUnmount(() => { window.removeEventListener('keydown', onGlobalKeydown); requestVersion.value += 1; abortActiveStream() })
</script>

<template>
  <div class="page ai-center-page ai-workbench-frame">
    <header class="ai-workbench-header" aria-labelledby="ai-workbench-title">
      <div class="ai-workbench-heading">
        <span class="eyebrow">研究工作台</span>
        <h1 id="ai-workbench-title">灵思 AI</h1>
        <p>{{ aiPageDescription }}</p>
      </div>
      <div class="ai-workbench-header__actions">
        <span class="ai-workbench-context-pill">{{ workspaceContextLabel }}</span>
        <button type="button" :aria-expanded="historyOpen" aria-controls="conversation-history" @click="toggleHistory">历史会话</button>
      </div>
    </header>

    <section class="ai-workbench-mode-region" aria-label="选择灵思 AI 工作模式">
      <div class="ai-workbench-mode-heading">
        <span class="eyebrow">研究方式</span>
        <h2>先选择研究方式</h2>
      </div>
      <AIModeTabs :model-value="workbenchMode" :agents="modeAgents" :selected-agent="selectedAgent" :disabled="sending" @update:model-value="selectWorkbenchMode" @select-agent="chooseAgent" @more-agents="openScienceAgentPicker" />
    </section>

    <section class="ai-workbench-context-strip" aria-label="当前 AI 上下文">
      <div class="ai-workbench-context-strip__main">
        <span class="eyebrow">当前上下文</span>
        <strong>{{ workspaceContextTitle }}</strong>
        <span>{{ workspaceContextDetail }}</span>
      </div>
      <button v-if="workbenchMode !== 'opening'" type="button" class="ai-workbench-context-strip__action" :aria-expanded="contextOpen" aria-controls="ai-context-drawer" @click="toggleContext">{{ contextOpen ? '收起上下文' : '查看上下文' }}</button>
      <span v-else class="ai-workbench-context-strip__readonly">不绑定项目</span>
    </section>

    <section v-if="loading && !modeAgents.length" class="ai-workbench-skeleton" role="status" aria-label="正在准备灵思 AI"><i /><i /><i /></section>

    <Teleport to="body">
      <div v-if="historyOpen || contextOpen" class="ai-workbench-drawer-backdrop" aria-hidden="true" @click="historyOpen = false; contextOpen = false" />
    </Teleport>

    <section class="ai-workbench-conversation" :class="{ 'has-messages': hasConversationMessages }" aria-label="灵思 AI 对话">
      <header v-if="hasConversationMessages" class="ai-session-bar">
        <div class="ai-session-bar__main">
          <span class="eyebrow">当前会话</span>
          <div v-if="renaming" class="rename-row"><input v-model="titleDraft" aria-label="对话标题" @keydown.enter="void saveRename()" /><button type="button" :disabled="sending" @click="void saveRename()">保存</button><button type="button" :disabled="sending" @click="renaming = false">取消</button></div>
          <div v-else class="ai-session-bar__title-row"><h2>{{ currentDisplayTitle }}</h2><button v-if="current && !current.is_archived && !researchMode" class="rename-button" type="button" :disabled="sending" @click="startRename">重命名</button></div>
          <small>{{ workspaceContextLabel }} · {{ currentAgent?.name || '正在准备 Agent' }}</small>
        </div>
        <div class="ai-session-bar__actions">
          <button v-if="current && !current.is_archived && !researchMode" type="button" :disabled="sending" @click="archiveCurrent">归档会话</button>
        </div>
      </header>

      <div v-if="resourceErrorMessage" class="ai-resource-notice" role="status"><span>{{ resourceErrorMessage }}</span><button type="button" :disabled="loading" @click="void bootstrapWorkbench()">重试加载</button></div>
      <div v-if="error" class="error-banner" role="alert"><span>{{ error }}</span><button type="button" :disabled="loading || sending" @click="void bootstrapWorkbench()">重试</button></div>
      <div v-if="streamNotice" class="stream-notice" role="status">{{ streamNotice }}</div>

      <AIResearchWizard v-if="researchMode && researchArtifact && !loading" :workspace-mode="workspaceMode === 'brainstorm' ? 'brainstorm' : 'project'" :workspace-context-label="workspaceContextLabel" :research-step="researchStep" :research-inputs="researchInputs" :research-artifact="researchArtifact" :research-selected-index="researchSelectedIndex" :research-draft="researchDraft" :research-save-confirm="researchSaveConfirm" :research-saved="researchSaved" :research-save-error="researchSaveError" :research-fallback="researchFallback" :project-draft="projectDraft" :current-project="currentProject" :sending="sending" :creating-project="creatingProject" :project-created="projectCreated" @update:research-step="researchStep = $event" @update:research-draft="researchDraft = $event" @update:research-save-confirm="researchSaveConfirm = $event" @update:research-fallback="researchFallback = $event; projectDraft.problem = $event" @advance-from-observation="advanceFromObservation" @generate="void generateResearchCandidates()" @choose-candidate="chooseResearchCandidate" @edit-candidate="editResearchCandidate" @open-draft="openResearchDraft" @request-save="requestResearchSave" @create-project="void createProjectFromResearch()" @save-question="void saveResearchQuestion()" @copy-question="copyResearchQuestion" />

      <section v-if="loading || messages.length" ref="chatStreamRef" class="chat-stream ai-conversation-stream" aria-live="polite" :aria-busy="sending" @scroll="updateScrollAffordance">
        <div v-if="loading" class="ai-stream-loading"><span class="ai-loading-dot" />正在恢复会话…</div>
        <article v-for="message in messages" :key="message.id" class="message" :class="message.role">
          <div class="message-label">{{ message.role === 'user' ? '你' : `灵思 AI · ${currentAgent?.name || '研究伙伴'}` }}</div>
          <div class="message-body">
            {{ message.content || (message.status === 'queued' ? '正在排队…' : message.status === 'streaming' ? '正在生成…' : '') }}
            <div v-if="message.status === 'failed'" class="message-error"><span>{{ message.error_message || '生成失败' }}</span><button type="button" class="retry-button" :disabled="sending" @click="retryMessage(message)">{{ sending ? '重试中…' : '重试' }}</button></div>
            <div v-if="message.artifact_payload?.draft && workbenchMode !== 'opening'" class="artifact-card"><b>{{ message.artifact_payload.title || '可编辑草稿' }}</b><textarea v-model="artifactDrafts[message.id]" :placeholder="message.artifact_payload.draft" rows="5" /><small>核验项：{{ message.verification_items?.length || 0 }} 项 · {{ message.artifact_payload.next_action || '请核对事实与引用' }}</small><label v-if="materials.length" class="target-material"><span>保存到指定材料</span><select v-model="targetMaterialId"><option :value="null">请选择目标材料</option><option v-for="material in materials" :key="material.id" :value="material.id">{{ material.title }}</option></select></label><AIDraftActions :mode="workbenchMode" :status="message.status" :can-save-material="Boolean(materials.length)" :can-create-project="false" :saving="savingMessage === message.id" @save-material="void saveArtifact(message)" @create-project="createProjectFromArtifact(message)" /></div>
          </div>
        </article>
      </section>

      <section v-else class="ai-empty-state" aria-label="开始使用灵思 AI">
        <div class="ai-empty-state__prompt">
          <h2>现在要推进哪一项研究工作？</h2>
          <p>直接输入你的研究目标。{{ aiEmptyDescription }}</p>
        </div>
      </section>

      <button v-if="!researchMode && showJumpLatest" type="button" class="jump-latest" @click="scrollToLatest()">↓ 跳到最新消息</button>
      <div class="ai-workbench-composer-host">
        <AIWorkbenchComposer :draft="draft" :mode="workbenchMode" :agent-name="currentAgent?.name" :project-label="workspaceContextDetail" :disabled="loading || sending || Boolean(current?.is_archived) || !currentAgent || (workbenchMode !== 'opening' && !currentProject)" :can-send="Boolean(draft.trim() && selectedId && currentAgent && (workbenchMode === 'opening' || currentProject))" :selected-material-ids="selectedMaterialIds" :can-cite-materials="canSelectMaterials" :sending="sending" @update:draft="draft = $event" @send="void sendMessage()" @stop="abortActiveStream()" @cite-material="citeProjectMaterial" />
      </div>
    </section>

    <AIConversationHistory v-if="historyOpen" :groups="visibleConversationGroups" :selected-id="selectedId" :sending="sending" :search="conversationSearch" :show-archived="showArchived" @update:search="conversationSearch = $event" @new="void newConversation()" @select="void selectConversation($event)" @toggle-archived="showArchived = !showArchived" @close="historyOpen = false" />
    <AIToolPicker v-if="agentOpen" :categories="agentCategories" :groups="groupedAgents" :search="agentSearch" :category="agentCategory" :sending="sending" @update:search="agentSearch = $event" @update:category="agentCategory = $event" @choose="chooseAgent" @close="agentOpen = false" />
    <AIContextDrawer :open="contextOpen" :mode="workbenchMode" :project="currentProject" :materials="materials" :agent="currentAgent" :paper-type="paperType" :paper-types="paperTypes" :referenced-sources="referencedSources" :selected-material-ids="selectedMaterialIds" :can-select-materials="canSelectMaterials" @close="contextOpen = false" @update:selected-material-ids="selectedMaterialIds = $event" @update-paper-type="paperType = $event; void changePaperType()" />
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
.retry-button {
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
.retry-button:focus-visible {
  border-color: var(--moss);
  background: var(--sage-soft);
}
.retry-button:disabled {
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

/* Project Workbench: the launch state stays light, focused and project-bound. */
.ai-center-page {
  display: flex;
  width: 100%;
  max-width: var(--content-max, 1120px);
  box-sizing: border-box;
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  margin: 0 auto;
  padding: clamp(34px, 7vh, 86px) 0 24px;
}
.ai-workbench-launch {
  display: grid;
  justify-items: center;
  gap: 12px;
  max-width: 680px;
  margin: 0 auto 28px;
  text-align: center;
}
.ai-workbench-launch h1 {
  margin: 0;
  color: var(--ink);
  font: 700 clamp(44px, 5.5vw, 68px)/1.05 var(--sans);
  letter-spacing: -.055em;
}
.ai-workbench-launch > p:last-child { margin: 0; color: var(--muted); font-size: 16px; line-height: 1.7; }
.ai-workbench-launch__history {
  min-height: 32px;
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--paper);
  color: var(--moss-dark);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.ai-workbench-launch__history:hover,
.ai-workbench-launch__history:focus-visible { border-color: var(--moss); background: var(--sage-soft); }
.ai-workbench-skeleton { width: min(100%, 900px); display: grid; gap: 12px; margin: 0 auto 20px; }
.ai-workbench-skeleton i { display: block; height: 12px; border-radius: 999px; background: var(--paper-muted); animation: ai-workbench-pulse 1.2s ease-in-out infinite alternate; }
.ai-workbench-skeleton i:nth-child(1) { width: 42%; }
.ai-workbench-skeleton i:nth-child(2) { width: 68%; animation-delay: .12s; }
.ai-workbench-skeleton i:nth-child(3) { width: 54%; animation-delay: .24s; }
@keyframes ai-workbench-pulse { from { opacity: .45; } to { opacity: 1; } }
.ai-center-page > .ai-mode-tabs { width: min(100%, 980px); margin: 0 auto 22px; border: 0; background: transparent; }
.ai-workbench-page, .ai-simple-layout, .ai-simple-layout.is-research-mode { display: flex; width: 100%; min-width: 0; min-height: 0; flex: 1 1 auto; }
.chat-main.ai-main-panel {
  width: 100%;
  max-width: 1100px;
  flex: 1 1 auto;
  min-height: 0;
  margin: 0 auto;
  overflow: hidden;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.chat-header {
  min-height: 38px;
  padding: 0 0 12px;
  border: 0;
  background: transparent;
}
.chat-header h2 { font-size: 16px; }
.chat-header .eyebrow { display: none; }
.chat-actions { max-width: none; }
.chat-actions button { border-radius: 999px; background: var(--paper); }
.ai-conversation-stream {
  max-height: none;
  min-height: 0;
  padding: 28px 10px 130px;
}
.ai-workbench-page.has-messages .chat-main { min-height: 0; }
.ai-workbench-page.has-messages .chat-header { padding-inline: 10px; border-bottom: 1px solid var(--line); }
.ai-workbench-page:not(.has-messages) .chat-header { display: none; }
.ai-workbench-page:not(.has-messages) .ai-main-panel { display: flex; justify-content: flex-end; }
.ai-workbench-page:not(.has-messages) :deep(.ai-workbench-composer) {
  width: min(100%, 900px);
  margin: 0 auto 8vh;
  border-color: var(--moss-dark);
  border-radius: 14px;
  box-shadow: 0 14px 30px rgba(42, 70, 47, .1);
}
.ai-workbench-page.has-messages :deep(.ai-workbench-composer) {
  position: sticky;
  bottom: 12px;
  width: min(100%, 960px);
  margin: 0 auto 12px;
  box-shadow: 0 12px 28px rgba(42, 70, 47, .12);
}
.message { max-width: min(82%, 820px); }
.message:not(.user) .message-body { padding: 4px 0; background: transparent; }
.message.user .message-body { border: 1px solid var(--sage-line); }
.error-banner, .stream-notice { width: min(100%, 920px); margin-inline: auto; }

/* Action-first workbench: one calm column, with the research action always
   visible before the conversation starts. */
.ai-center-page.ai-workbench-frame {
  display: flex;
  width: 100%;
  max-width: 1120px;
  min-width: 0;
  min-height: calc(100vh - var(--topbar-height));
  box-sizing: border-box;
  flex-direction: column;
  margin: 0 auto;
  padding: 28px 0 24px;
  overflow: visible;
}
.ai-workbench-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  min-width: 0;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--line);
}
.ai-workbench-heading { min-width: 0; }
.ai-workbench-heading h1 {
  margin: 5px 0 6px;
  color: var(--ink);
  font: 700 clamp(32px, 4vw, 46px)/1.05 var(--sans);
  letter-spacing: -.045em;
}
.ai-workbench-heading p {
  max-width: 620px;
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}
.ai-workbench-header__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 8px;
  max-width: 560px;
}
.ai-workbench-header__actions > button,
.ai-session-bar__actions button {
  min-height: 34px;
  padding: 7px 11px;
  border: 1px solid var(--line-dark);
  border-radius: 999px;
  background: var(--paper);
  color: var(--moss-dark);
  font: inherit;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition: border-color var(--transition-fast), background-color var(--transition-fast);
}
.ai-workbench-header__actions > button:hover:not(:disabled),
.ai-workbench-header__actions > button:focus-visible,
.ai-session-bar__actions button:hover:not(:disabled),
.ai-session-bar__actions button:focus-visible {
  border-color: var(--moss);
  background: var(--sage-soft);
}
.ai-workbench-header__actions > button:disabled { cursor: not-allowed; opacity: .45; }
.ai-workbench-context-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  max-width: 290px;
  overflow: hidden;
  padding: 7px 11px;
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  background: var(--sage-soft);
  color: var(--moss-dark);
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-workbench-mode-region {
  display: grid;
  gap: 12px;
  min-width: 0;
  margin-top: 24px;
}
.ai-workbench-mode-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}
.ai-workbench-mode-heading h2 {
  margin: 4px 0 0;
  color: var(--ink);
  font: 700 19px/1.3 var(--sans);
}
.ai-workbench-skeleton {
  display: grid;
  gap: 9px;
  width: min(100%, 960px);
  margin: 14px auto 0;
}
.ai-workbench-skeleton i {
  display: block;
  height: 10px;
  border-radius: 999px;
  background: var(--paper-muted);
  animation: ai-workbench-pulse 1.2s ease-in-out infinite alternate;
}
.ai-workbench-skeleton i:nth-child(1) { width: 38%; }
.ai-workbench-skeleton i:nth-child(2) { width: 70%; animation-delay: .12s; }
.ai-workbench-skeleton i:nth-child(3) { width: 54%; animation-delay: .24s; }
.ai-workbench-drawer-backdrop,
.agent-picker-overlay { position: fixed; inset: 0; }
.ai-workbench-drawer-backdrop { z-index: 89; background: rgba(30, 45, 38, .08); }
.ai-workbench-conversation {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  margin-top: 18px;
}
.ai-session-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  min-width: 0;
  padding: 12px 0 14px;
  border-bottom: 1px solid var(--line);
}
.ai-session-bar__main { min-width: 0; flex: 1 1 auto; }
.ai-session-bar__title-row { display: flex; align-items: center; gap: 9px; min-width: 0; }
.ai-session-bar h2 {
  min-width: 0;
  margin: 4px 0 2px;
  overflow: hidden;
  color: var(--ink);
  font: 700 16px/1.35 var(--sans);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-session-bar small { display: block; overflow-wrap: anywhere; color: var(--muted); font-size: 11px; }
.ai-session-bar__actions { flex: 0 0 auto; }
.rename-button { min-height: 28px; padding: 5px 8px; border: 0; background: transparent; color: var(--moss-dark); font: inherit; font-size: 11px; cursor: pointer; }
.rename-button:hover, .rename-button:focus-visible { text-decoration: underline; }
.rename-row { display: flex; align-items: center; gap: 6px; margin-top: 5px; }
.rename-row input { width: min(340px, 100%); min-height: 32px; padding: 6px 9px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); }
.rename-row button { min-height: 30px; padding: 5px 8px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); color: var(--moss-dark); cursor: pointer; }
.ai-resource-notice,
.ai-center-page .error-banner,
.ai-center-page .stream-notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  box-sizing: border-box;
  margin: 12px 0 0;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.5;
}
.ai-resource-notice { background: var(--amber-soft); color: var(--amber); }
.ai-center-page .error-banner { background: var(--danger-soft); color: var(--danger); }
.ai-center-page .stream-notice { background: var(--sage-soft); color: var(--moss-dark); }
.ai-resource-notice button,
.ai-center-page .error-banner button {
  flex: 0 0 auto;
  min-height: 28px;
  padding: 5px 9px;
  border: 1px solid currentColor;
  border-radius: 999px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}
.ai-resource-notice button:disabled,
.ai-center-page .error-banner button:disabled { cursor: wait; opacity: .5; }
.ai-conversation-stream {
  width: min(100%, 960px);
  max-height: none;
  margin: 0 auto;
  padding: 24px 0 122px;
}
.ai-stream-loading {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
}
.ai-loading-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--sage); animation: ai-workbench-pulse 1s ease-in-out infinite alternate; }
.ai-empty-state {
  display: grid;
  justify-items: center;
  gap: 10px;
  width: min(100%, 680px);
  margin: 20px auto 0;
  text-align: center;
}
.ai-empty-state__agent { color: var(--moss); font-size: 12px; font-weight: 700; }
.ai-empty-state h2 { margin: 0; color: var(--ink); font: 700 clamp(24px, 3vw, 34px)/1.2 var(--sans); letter-spacing: -.025em; }
.ai-empty-state p { max-width: 520px; margin: 0; color: var(--muted); font-size: 13px; line-height: 1.7; }
.ai-workbench-composer-host { width: min(100%, 960px); margin: 16px auto 0; }
.ai-workbench-conversation:not(.has-messages) .ai-workbench-composer-host { margin-top: 16px; }
.ai-workbench-conversation.has-messages .ai-workbench-composer-host { position: sticky; bottom: 12px; z-index: 20; }
.ai-center-page :deep(.ai-workbench-composer) { width: 100%; margin: 0; border-color: var(--line-dark); border-radius: var(--radius-md); box-shadow: 0 12px 30px rgba(42, 70, 47, .09); }
.ai-center-page :deep(.ai-workbench-composer__textarea) { min-height: 82px; }
.ai-center-page :deep(.ai-workbench-composer__footer) { min-height: 34px; }
.jump-latest { align-self: center; margin: 0 0 8px; }
@media (max-width: 900px) {
  .ai-center-page.ai-workbench-frame { padding-inline: 20px; }
  .ai-workbench-header { flex-direction: column; }
  .ai-workbench-header__actions { justify-content: flex-start; }
}
@media (max-width: 620px) {
  .ai-workbench-mode-heading { align-items: flex-start; flex-direction: column; }
  .ai-workbench-context-pill { max-width: 100%; }
  .ai-session-bar { flex-direction: column; }
  .ai-session-bar__actions { align-self: flex-start; }
  .ai-conversation-stream { padding-inline: 0; }
}

/* Compact action-first composition: the input remains in the first viewport,
   while conversation management appears only after a message exists. */
.ai-center-page.ai-workbench-frame {
  min-height: 0;
  padding: 16px 0 18px;
}
.ai-workbench-header {
  align-items: center;
  gap: 18px;
  padding-bottom: 12px;
}
.ai-workbench-heading h1 {
  margin: 3px 0 4px;
  font-size: clamp(28px, 3vw, 34px);
}
.ai-workbench-heading p {
  max-width: 700px;
  font-size: 11px;
  line-height: 1.45;
}
.ai-workbench-header__actions {
  max-width: 430px;
}
.ai-workbench-mode-region {
  gap: 6px;
  margin-top: 12px;
}
.ai-workbench-mode-heading {
  align-items: baseline;
  justify-content: flex-start;
  gap: 10px;
}
.ai-workbench-mode-heading h2 {
  margin: 0;
  font-size: 14px;
}
.ai-workbench-context-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  margin-top: 10px;
  padding: 7px 12px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, .55);
}
.ai-workbench-context-strip__main {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 10px;
  min-width: 0;
}
.ai-workbench-context-strip__main .eyebrow {
  flex: 0 0 auto;
}
.ai-workbench-context-strip__main strong {
  min-width: 0;
  max-width: min(48vw, 480px);
  overflow: hidden;
  color: var(--ink);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-workbench-context-strip__main > span:last-child {
  color: var(--muted);
  font-size: 11px;
}
.ai-workbench-context-strip__action,
.ai-workbench-context-strip__readonly {
  flex: 0 0 auto;
  min-height: 28px;
  padding: 4px 9px;
  border: 1px solid var(--line-dark);
  border-radius: 999px;
  background: var(--paper);
  color: var(--moss-dark);
  font: inherit;
  font-size: 11px;
  font-weight: 650;
}
.ai-workbench-context-strip__action {
  cursor: pointer;
}
.ai-workbench-context-strip__action:hover,
.ai-workbench-context-strip__action:focus-visible {
  border-color: var(--moss);
  background: var(--sage-soft);
}
.ai-workbench-context-strip__readonly {
  color: var(--muted-light);
}
.ai-workbench-skeleton {
  margin-top: 12px;
}
.ai-workbench-conversation {
  flex: 0 1 auto;
  margin-top: 10px;
}
.ai-workbench-conversation.has-messages {
  min-height: min(62vh, 620px);
}
.ai-session-bar {
  padding: 8px 0 10px;
}
.ai-conversation-stream {
  max-height: min(62vh, 620px);
  padding-top: 18px;
}
.ai-empty-state {
  width: min(100%, 720px);
  margin: 10px auto 0;
}
.ai-empty-state__prompt {
  display: grid;
  justify-items: center;
  gap: 8px;
}
.ai-empty-state h2 {
  font-size: clamp(21px, 2.4vw, 28px);
}
.ai-empty-state p {
  max-width: 600px;
  font-size: 12px;
}
.ai-workbench-composer-host {
  margin: 10px auto 0;
}
.ai-workbench-conversation:not(.has-messages) .ai-workbench-composer-host {
  margin-top: 10px;
}
.ai-center-page :deep(.ai-workbench-composer) {
  box-shadow: 0 10px 24px rgba(42, 70, 47, .08);
}
.ai-center-page :deep(.ai-workbench-composer__textarea) {
  height: 72px;
  min-height: 72px;
}
.ai-center-page :deep(.ai-workbench-composer__footer) {
  min-height: 30px;
}
@media (max-width: 900px) {
  .ai-center-page.ai-workbench-frame {
    padding-inline: 20px;
  }
}
@media (max-width: 620px) {
  .ai-workbench-context-strip {
    align-items: flex-start;
    flex-direction: column;
  }
  .ai-workbench-context-strip__main strong {
    max-width: 100%;
  }
  .ai-workbench-context-strip__action,
  .ai-workbench-context-strip__readonly {
    align-self: flex-start;
  }
}
</style>
