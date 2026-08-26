<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createAIConversation, createAIConversationMessage, errorMessage, getAIAgents, getAIConversationMessages, getAIConversations, getProjects, streamAIConversationMessage, type AIAgent, type AIConversation, type AIConversationMessage, type Project } from '../../api'
import AIConversationHistory from '../../components/ai/AIConversationHistory.vue'
import AIModeTabs from '../../components/ai/AIModeTabs.vue'
import AIWorkspaceShell from '../../components/ai/AIWorkspaceShell.vue'
import AIWorkbenchComposer from '../../components/ai/AIWorkbenchComposer.vue'
import { filterConversations } from '../../stores/aiConversationModel'
import { normalizeAIWorkspaceMode, visibleAgents, type AIWorkspaceMode } from '../../stores/aiWorkbenchModel'
import { groupConversationSummaries } from '../../stores/presentationModel'
import { auth } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const projects = ref<Project[]>([])
const agents = ref<AIAgent[]>([])
const conversations = ref<AIConversation[]>([])
const messages = ref<AIConversationMessage[]>([])
const projectId = ref<number | null>(Number(route.query.projectId) || null)
const selectedId = ref<number | null>(null)
const selectedAgent = ref<string | undefined>(typeof route.query.agent === 'string' ? route.query.agent : undefined)
const draft = ref('')
const loading = ref(true)
const sending = ref(false)
const historyOpen = ref(false)
const contextOpen = ref(false)
const error = ref('')
const search = ref('')

const mode = computed<AIWorkspaceMode>(() => normalizeAIWorkspaceMode(route.query.mode))
const project = computed(() => projects.value.find((item) => item.id === projectId.value) || null)
const current = computed(() => conversations.value.find((item) => item.id === selectedId.value) || null)
const currentAgent = computed(() => agents.value.find((item) => item.key === selectedAgent.value) || null)
const modeAgents = computed(() => visibleAgents(mode.value, agents.value, 'teacher'))
const visibleGroups = computed(() => groupConversationSummaries(filterConversations(conversations.value, { project: projectId.value, includeArchived: false }), {}))
const hasMessages = computed(() => messages.value.length > 0)

function setMode(value: AIWorkspaceMode) {
  const query: Record<string, string> = { mode: value === 'opening' ? 'research' : value }
  if (projectId.value) query.projectId = String(projectId.value)
  void router.push({ path: '/teacher/ai', query })
}
function chooseAgent(agent: AIAgent) { selectedAgent.value = agent.key }
async function selectConversation(item: AIConversation) {
  selectedId.value = item.id
  selectedAgent.value = item.current_agent || selectedAgent.value
  messages.value = (await getAIConversationMessages(item.id)).data
}
async function createConversation() {
  if (!projectId.value) return
  const response = await createAIConversation({ project: projectId.value, workspace_mode: mode.value === 'opening' ? 'research' : mode.value, current_agent: selectedAgent.value || null })
  conversations.value.unshift(response.data)
  await selectConversation(response.data)
}
async function load() {
  loading.value = true; error.value = ''
  try {
    const [projectResponse, agentResponse, conversationResponse] = await Promise.all([getProjects(), getAIAgents(), getAIConversations()])
    projects.value = projectResponse.data.filter((item) => item.primary_teacher === auth.user.value?.id)
    agents.value = agentResponse.data
    if (!projectId.value) projectId.value = projects.value.find((item) => item.status === 'active')?.id || projects.value[0]?.id || null
    conversations.value = conversationResponse.data.filter((item) => item.project === projectId.value)
    if (conversations.value[0]) await selectConversation(conversations.value[0])
    else if (projectId.value) await createConversation()
  } catch (reason) { error.value = errorMessage(reason, '指导室加载失败，请稍后重试。') }
  finally { loading.value = false }
}
async function send() {
  if (!draft.value.trim() || !selectedId.value || sending.value || current.value?.is_archived) return
  const content = draft.value.trim(); draft.value = ''; sending.value = true; error.value = ''
  try {
    const response = await createAIConversationMessage(selectedId.value, { content, project: projectId.value, workspace_mode: mode.value === 'opening' ? 'research' : mode.value, agent_key: selectedAgent.value })
    messages.value.push({ id: -Date.now(), role: 'user', content, status: 'completed', created_at: new Date().toISOString() }, response.data)
    if (response.data.status === 'queued') await streamAIConversationMessage(selectedId.value, response.data.id, (event) => {
      const message = messages.value.find((item) => item.id === response.data.id)
      if (!message) return
      if (event.event === 'message.delta') { message.status = 'streaming'; message.content += String(event.data.delta || event.data.text || '') }
      if (event.event === 'message.done') message.status = 'completed'
      if (event.event === 'message.error') { message.status = 'failed'; message.error_message = String(event.data.error || '生成失败') }
    })
  } catch (reason) { draft.value = content; error.value = errorMessage(reason, '指导建议生成失败，请稍后重试。') }
  finally { sending.value = false }
}

watch(() => route.query.projectId, (value) => { const next = Number(value); if (Number.isFinite(next) && next > 0 && next !== projectId.value) { projectId.value = next; void load() } })
onMounted(load)
</script>

<template>
  <AIWorkspaceShell :mode="mode" role-tone="teacher" :project-label="project ? `指导项目 · ${project.title}` : '选择一个指导项目'" :history-open="historyOpen" :context-open="contextOpen" @toggle-history="historyOpen = !historyOpen" @toggle-context="contextOpen = !contextOpen" @close-drawers="historyOpen = false; contextOpen = false">
    <section class="teacher-ai-studio page" :class="{ 'has-messages': hasMessages }">
      <header v-if="!hasMessages" class="teacher-ai-studio__intro"><p class="eyebrow">项目指导室</p><h1>灵思 AI</h1><p>围绕你负责的项目诊断风险、准备指导问题，并形成需要你确认的建议。</p></header>
      <AIModeTabs :model-value="mode" :modes="['research', 'defense']" :agents="modeAgents" :selected-agent="selectedAgent" :disabled="sending" @update:model-value="setMode" @select-agent="chooseAgent" @more-agents="contextOpen = true" />
      <p v-if="error" class="teacher-ai-studio__error">{{ error }}</p>
      <div v-if="loading" class="teacher-ai-studio__empty">正在加载指导会话…</div>
      <div v-else-if="!project" class="teacher-ai-studio__empty"><strong>还没有可指导的项目</strong><span>先从项目池认领项目，再进入指导室。</span></div>
      <section v-else class="teacher-ai-studio__conversation" aria-live="polite"><article v-for="message in messages" :key="message.id" class="teacher-ai-message" :class="message.role"><span>{{ message.role === 'user' ? '教师' : '灵思 AI' }}</span><div>{{ message.content || (message.status === 'streaming' ? '正在生成…' : '正在准备建议…') }}</div></article></section>
      <AIWorkbenchComposer v-if="project && !loading" :draft="draft" :mode="mode" :agent-name="currentAgent?.name" :project-label="project.title" :disabled="Boolean(current?.is_archived)" :can-send="Boolean(draft.trim() && selectedId)" :sending="sending" @update:draft="draft = $event" @send="void send()" @stop="sending = false" @cite-material="contextOpen = true" />
      <AIConversationHistory v-if="historyOpen" :groups="visibleGroups" :selected-id="selectedId" :sending="sending" :search="search" :show-archived="false" @update:search="search = $event" @new="void createConversation()" @select="void selectConversation($event)" @toggle-archived="undefined" @close="historyOpen = false" />
      <aside v-if="contextOpen" class="teacher-ai-studio__context"><strong>{{ project?.title || '未选择项目' }}</strong><p>仅读取你负责项目的已提交材料、审核变化和任务状态。学生未保存的私密对话不会出现在这里。</p><button type="button" @click="contextOpen = false">关闭</button></aside>
    </section>
  </AIWorkspaceShell>
</template>

<style scoped>
.teacher-ai-studio { display: flex; width: min(1120px, calc(100vw - 48px)); min-width: 0; min-height: 0; flex: 1; flex-direction: column; margin: 0 auto; padding: clamp(36px, 7vh, 84px) 0 24px; }
.teacher-ai-studio__intro { display: grid; justify-items: center; gap: 12px; max-width: 720px; margin: 0 auto 28px; text-align: center; }.teacher-ai-studio__intro h1 { margin: 0; font: 700 clamp(44px, 5.5vw, 68px)/1 var(--sans); letter-spacing: -.05em; }.teacher-ai-studio__intro > p:last-child { margin: 0; color: var(--muted); line-height: 1.7; }.teacher-ai-studio :deep(.ai-mode-tabs) { width: min(100%, 980px); margin-inline: auto; border: 0; background: transparent; }.teacher-ai-studio__conversation { display: grid; align-content: start; gap: 22px; min-height: 0; flex: 1; overflow-y: auto; padding: 28px 92px 126px; }.teacher-ai-message { display: grid; gap: 8px; max-width: 820px; color: var(--ink); line-height: 1.75; }.teacher-ai-message > span { color: var(--muted); font-size: 11px; }.teacher-ai-message.user { margin-left: auto; }.teacher-ai-message.user > div { padding: 12px 15px; border: 1px solid var(--sage-line); border-radius: 12px; background: var(--sage-soft); }.teacher-ai-studio :deep(.ai-workbench-composer) { position: sticky; bottom: 12px; width: min(100%, 960px); margin: 0 auto 12px; box-shadow: 0 12px 28px rgba(42, 70, 47, .12); }.teacher-ai-studio:not(.has-messages) :deep(.ai-workbench-composer) { margin-bottom: 8vh; border-color: var(--moss-dark); }.teacher-ai-studio__empty, .teacher-ai-studio__error { margin: auto; color: var(--muted); text-align: center; }.teacher-ai-studio__empty { display: grid; gap: 8px; }.teacher-ai-studio__empty strong { color: var(--ink); font-size: 20px; }.teacher-ai-studio__error { padding: 10px; color: #8e4438; }.teacher-ai-studio__context { position: fixed; top: 112px; right: 24px; z-index: 80; width: 300px; padding: 20px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-hover); }.teacher-ai-studio__context p { color: var(--muted); font-size: 12px; line-height: 1.65; }.teacher-ai-studio__context button { border: 0; background: transparent; color: var(--moss-dark); cursor: pointer; }
</style>
