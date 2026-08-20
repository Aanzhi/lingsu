<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { archiveAIConversation, createAIConversation, createAIConversationMessage, errorMessage, getAIAgents, getAIConversationMessages, getAIConversations, getMaterials, getProjects, saveAIGenerationAsMaterial, streamAIConversationMessage, updateAIConversation, type AIAgent, type AIConversation, type AIConversationMessage, type Material, type Project } from '../../api'

const route = useRoute()
const conversations = ref<AIConversation[]>([])
const messages = ref<AIConversationMessage[]>([])
const projects = ref<Project[]>([])
const agents = ref<AIAgent[]>([])
const selectedId = ref<number | null>(null)
const projectFilter = ref<number | null>(Number(route.query.projectId) || null)
const selectedAgent = ref<string | undefined>(typeof route.query.agent === 'string' ? route.query.agent : undefined)
const taskId = ref<number | undefined>(Number(route.query.taskId) || undefined)
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
const paperTypes = [{ value: 'empirical', label: '实证研究' }, { value: 'case', label: '案例研究' }, { value: 'literature-review', label: '文献综述' }, { value: 'theoretical', label: '理论研究' }]

const current = computed(() => conversations.value.find((item) => item.id === selectedId.value) || null)
const currentProject = computed(() => projects.value.find((item) => item.id === current.value?.project) || null)
const visibleConversations = computed(() => conversations.value.filter((item) => showArchived.value || !item.is_archived).filter((item) => projectFilter.value === null || item.project === projectFilter.value))
const currentAgent = computed(() => agents.value.find((item) => item.key === selectedAgent.value) || agents.value.find((item) => item.key === current.value?.current_agent) || null)

async function loadConversations() {
  const response = await getAIConversations({ include_archived: showArchived.value })
  conversations.value = response.data
  const preferred = response.data.find((item) => item.id === selectedId.value) || response.data.find((item) => item.project === projectFilter.value) || response.data[0]
  if (preferred) await selectConversation(preferred)
}
async function selectConversation(item: AIConversation) {
  selectedId.value = item.id
  selectedAgent.value = item.current_agent || selectedAgent.value
  paperType.value = item.paper_type || ''
  agentInputs.value = {}
  messages.value = (await getAIConversationMessages(item.id)).data
  materials.value = item.project ? (await getMaterials(item.project)).data : []
}
async function newConversation() {
  const item = (await createAIConversation({ project: projectFilter.value, current_agent: selectedAgent.value || null })).data
  conversations.value.unshift(item)
  await selectConversation(item)
}
async function archiveCurrent() {
  if (!current.value) return
  await archiveAIConversation(current.value.id)
  await loadConversations()
}
async function sendMessage() {
  const content = draft.value.trim()
  if (!content || !selectedId.value || sending.value || current.value?.is_archived) return
  sending.value = true; error.value = ''; draft.value = ''
  try {
    const response = await createAIConversationMessage(selectedId.value, { content, agent_key: selectedAgent.value, paper_type: paperType.value || undefined, project: current.value?.project, task: taskId.value, input_values: agentInputs.value })
    messages.value.push({ role: 'user', content, status: 'completed', created_at: new Date().toISOString(), id: Date.now() })
    messages.value.push(response.data)
    if (response.data.status === 'queued' && response.data.id) {
      await streamAIConversationMessage(selectedId.value, response.data.id, (event) => {
        const assistant = messages.value.find((item) => item.id === response.data.id)
        if (!assistant) return
        if (event.event === 'message.delta') assistant.content += String(event.data.delta || event.data.text || '')
        if (event.event === 'message.error') { assistant.status = 'failed'; assistant.error_message = String(event.data.error || '生成失败') }
        if (event.event === 'message.done') assistant.status = 'completed'
      })
    }
    await loadConversations()
  } catch (reason) { error.value = errorMessage(reason, '消息发送失败，请重试。'); draft.value = content } finally { sending.value = false }
}
function chooseAgent(agent: AIAgent) { selectedAgent.value = agent.key; agentInputs.value = {}; agentOpen.value = false }
async function changePaperType() { if (current.value) await updateAIConversation(current.value.id, { paper_type: paperType.value || null }) }
async function saveArtifact(message: AIConversationMessage) { const material = materials.value[0]; const logId = Number(message.generation_log); const content = artifactDrafts.value[message.id] || message.artifact_payload?.draft || message.content; if (!material || !logId || !content) return; savingMessage.value = message.id; try { await saveAIGenerationAsMaterial(logId, { material: material.id, content, revision_note: '由全局 AI 对话保存为材料草稿' }) } catch (reason) { error.value = errorMessage(reason, '保存材料草稿失败。') } finally { savingMessage.value = null } }
function onKeydown(event: KeyboardEvent) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage() } }
watch(showArchived, () => { void loadConversations() })
onMounted(async () => { try { const [projectResponse, agentResponse] = await Promise.all([getProjects(), getAIAgents()]); projects.value = projectResponse.data; agents.value = agentResponse.data; await loadConversations(); if (!selectedId.value) await newConversation() } catch (reason) { error.value = errorMessage(reason, 'AI 工作台加载失败。') } finally { loading.value = false } })
</script>

<template>
  <div class="conversation-page">
    <aside class="conversation-sidebar">
      <div class="sidebar-brand"><span>灵思 AI</span><button type="button" @click="newConversation">＋</button></div>
      <button class="new-conversation" type="button" @click="newConversation">＋ 新建对话</button>
      <label class="project-filter"><span>项目</span><select v-model="projectFilter"><option :value="null">全部项目</option><option v-for="project in projects" :key="project.id" :value="project.id">{{ project.title }}</option></select></label>
      <div class="conversation-list"><button v-for="item in visibleConversations" :key="item.id" class="conversation-item" :class="{ active: item.id === selectedId }" type="button" @click="selectConversation(item)"><strong>{{ item.title || '新建科创对话' }}</strong><small>{{ item.project_title || '通用咨询' }}</small></button><p v-if="!visibleConversations.length" class="empty-small">暂无对话</p></div>
      <button class="archive-toggle" type="button" @click="showArchived = !showArchived">{{ showArchived ? '隐藏已归档' : '查看已归档' }}</button>
    </aside>

    <main class="chat-main">
      <header class="chat-header"><div><span class="eyebrow">全局 AI 工作台</span><h1>{{ current?.title || '新建科创对话' }}</h1><small>{{ currentProject?.title || '未绑定项目 · 通用咨询' }}</small></div><div class="chat-actions"><button type="button" @click="agentOpen = !agentOpen">Agent{{ currentAgent ? ` · ${currentAgent.name}` : '' }}⌄</button><button type="button" @click="contextOpen = !contextOpen">上下文{{ contextOpen ? '收起' : '展开' }}</button><button v-if="current && !current.is_archived" type="button" @click="archiveCurrent">归档</button></div></header>
      <div v-if="agentOpen" class="agent-menu"><button v-for="agent in agents" :key="agent.key" type="button" @click="chooseAgent(agent)"><strong>{{ agent.name }}</strong><small>{{ agent.description }}</small></button></div>
      <div v-if="error" class="error-banner">{{ error }}</div>
      <section class="chat-stream" aria-live="polite"><div v-if="loading" class="empty-state">正在加载对话…</div><div v-else-if="!messages.length" class="empty-state"><strong>开始一段科创对话</strong><p>可以直接提问，也可以先选择 Agent。项目材料只会在绑定项目后按契约读取。</p></div><article v-for="message in messages" :key="message.id" class="message" :class="message.role"><div class="message-label">{{ message.role === 'user' ? '你' : '灵思 AI' }}</div><div class="message-body">{{ message.content || (message.status === 'queued' ? '正在准备生成…' : '') }}<div v-if="message.status === 'failed'" class="message-error">{{ message.error_message || '生成失败' }}</div><div v-if="message.artifact_payload?.draft" class="artifact-card"><b>{{ message.artifact_payload.title || '可编辑草稿' }}</b><textarea v-model="artifactDrafts[message.id]" :placeholder="message.artifact_payload.draft" rows="5" /><small>核验项：{{ message.verification_items?.length || 0 }} 项 · {{ message.artifact_payload.next_action || '请核对事实与引用' }}</small><button v-if="materials.length && message.status === 'completed'" type="button" class="save-draft" :disabled="savingMessage === message.id" @click="saveArtifact(message)">{{ savingMessage === message.id ? '保存中…' : `保存到：${materials[0].title}` }}</button></div></div></article></section>
      <footer class="composer"><details v-if="currentAgent?.input_schema?.length" class="input-details"><summary>补充信息（按 Agent 契约填写）</summary><label v-for="field in currentAgent.input_schema" :key="field.key">{{ field.label }}<textarea v-if="field.type === 'textarea'" v-model="agentInputs[field.key]" :placeholder="field.placeholder" rows="2" /><input v-else v-model="agentInputs[field.key]" :placeholder="field.placeholder" /></label></details><div class="composer-meta"><span>{{ currentAgent ? `使用 ${currentAgent.name}` : '自由咨询' }}</span><span>{{ currentProject ? `项目：${currentProject.title}` : '未绑定项目' }}</span></div><textarea v-model="draft" :disabled="sending || current?.is_archived" placeholder="输入问题，或输入 / 选择一个 Agent…" rows="3" @keydown="onKeydown" /><div class="composer-footer"><small>Enter 发送 · Shift+Enter 换行</small><button class="send-button" type="button" :disabled="sending || !draft.trim() || !selectedId" @click="sendMessage">{{ sending ? '生成中…' : '发送' }}</button></div></footer>
    </main>

    <aside v-if="contextOpen" class="context-panel"><div class="context-heading"><b>项目上下文</b><button type="button" @click="contextOpen = false">×</button></div><p class="eyebrow">当前项目</p><h3>{{ currentProject?.title || '未绑定项目' }}</h3><p class="muted">当前对话只能绑定一个项目，切换项目请新建对话。</p><label v-if="currentAgent?.workflow === 'paper'" class="paper-picker"><span class="eyebrow">论文类型</span><select v-model="paperType" @change="changePaperType"><option value="">请选择</option><option v-for="item in paperTypes" :key="item.value" :value="item.value">{{ item.label }}</option></select></label><p class="eyebrow">可读取范围</p><ul><li>项目基本信息</li><li>当前任务与材料</li><li>Agent 契约允许的项目摘要</li></ul><p class="eyebrow">当前 Agent</p><p>{{ currentAgent?.name || '自由咨询' }}</p></aside>
  </div>
</template>

<style scoped>
.conversation-page{display:grid;grid-template-columns:240px minmax(0,1fr) auto;min-height:calc(100vh - 150px);background:var(--paper);border:1px solid var(--line);border-radius:var(--radius-md);overflow:hidden}.conversation-sidebar{background:var(--paper-soft);border-right:1px solid var(--line);padding:16px;display:flex;flex-direction:column;gap:12px}.sidebar-brand{display:flex;justify-content:space-between;align-items:center;font-weight:800;color:var(--moss-dark)}button{font:inherit;cursor:pointer}.sidebar-brand button,.chat-actions button,.archive-toggle{border:0;background:transparent;color:var(--moss-dark);padding:6px;border-radius:8px}.new-conversation,.send-button{border:1px solid var(--moss-dark);background:var(--moss);color:#fff;border-radius:9px;padding:10px}.project-filter{display:grid;gap:5px;font-size:12px;color:var(--muted)}select,textarea{font:inherit;border:1px solid var(--line-dark);border-radius:8px;padding:9px;background:var(--paper);color:var(--ink)}.conversation-list{flex:1;overflow:auto;display:grid;align-content:start;gap:5px}.conversation-item{border:1px solid transparent;background:transparent;text-align:left;padding:11px;border-radius:9px;color:var(--ink)}.conversation-item.active{border-color:var(--line-dark);background:var(--sage-soft)}.conversation-item strong,.conversation-item small{display:block}.conversation-item small{margin-top:4px;color:var(--muted);font-size:11px}.empty-small,.muted{font-size:12px;color:var(--muted)}.chat-main{min-width:0;display:flex;flex-direction:column;position:relative}.chat-header{display:flex;justify-content:space-between;gap:14px;padding:22px 26px;border-bottom:1px solid var(--line)}.chat-header h1{font-family:var(--serif);font-size:24px;margin:4px 0}.chat-header small{color:var(--muted)}.eyebrow{font-size:11px;letter-spacing:.08em;color:var(--moss);text-transform:uppercase}.chat-actions{display:flex;align-items:start;gap:5px}.chat-actions button{border:1px solid var(--line);background:var(--paper);font-size:12px}.agent-menu{position:absolute;right:26px;top:86px;width:280px;z-index:3;background:var(--paper);border:1px solid var(--line-dark);border-radius:10px;box-shadow:0 12px 32px #23331f1c;padding:8px}.agent-menu button{width:100%;text-align:left;border:0;background:transparent;padding:10px;border-radius:7px}.agent-menu button:hover{background:var(--sage-soft)}.agent-menu strong,.agent-menu small{display:block}.agent-menu small{font-size:11px;color:var(--muted);margin-top:4px}.error-banner{margin:12px 24px;padding:10px;border-radius:8px;background:#fff0ed;color:#8e4438;font-size:13px}.chat-stream{flex:1;overflow:auto;padding:26px 8%;display:grid;align-content:start;gap:20px}.empty-state{text-align:center;margin:auto;color:var(--muted)}.empty-state strong{display:block;color:var(--ink);font-family:var(--serif);font-size:22px}.message{max-width:82%;display:flex;gap:10px}.message.user{margin-left:auto;flex-direction:row-reverse}.message-label{font-size:11px;color:var(--muted);padding-top:8px;white-space:nowrap}.message-body{padding:12px 15px;border-radius:12px;background:var(--paper-soft);line-height:1.7;white-space:pre-wrap}.message.user .message-body{background:var(--sage-soft)}.message-error{margin-top:8px;color:#a33}.artifact-card{margin-top:14px;padding:12px;border:1px solid var(--line);border-radius:9px;background:var(--paper)}.artifact-card p{white-space:pre-wrap}.artifact-card small{color:var(--muted)}.composer{margin:0 8%;padding:12px;border:1px solid var(--line-dark);border-radius:12px;background:var(--paper);box-shadow:0 8px 24px #23331f10}.composer-meta,.composer-footer{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:11px;color:var(--muted)}.composer textarea{border:0;padding:10px 0;resize:none;box-shadow:none}.composer textarea:focus{outline:none}.context-panel{width:240px;border-left:1px solid var(--line);padding:20px;background:var(--paper-soft)}.context-heading{display:flex;justify-content:space-between;margin-bottom:22px}.context-heading button{border:0;background:transparent;font-size:20px;color:var(--muted)}.context-panel h3{font-family:var(--serif);font-size:18px}.context-panel li{font-size:12px;line-height:1.9;color:var(--muted)}@media(max-width:900px){.conversation-page{grid-template-columns:190px minmax(0,1fr)}.context-panel{position:fixed;right:0;top:0;bottom:0;z-index:5;box-shadow:-8px 0 24px #23331f18}.chat-stream{padding:20px 5%}.composer{margin:0 5%}}@media(max-width:620px){.conversation-page{display:block;min-height:calc(100vh - 100px)}.conversation-sidebar{border-right:0;border-bottom:1px solid var(--line);max-height:180px}.conversation-list{display:flex;overflow:auto}.conversation-item{min-width:170px}.chat-header{padding:16px;display:block}.chat-actions{margin-top:10px;flex-wrap:wrap}.chat-stream{padding:18px}.message{max-width:95%}.composer{margin:0 12px 12px}}
.input-details{margin-bottom:8px;border-bottom:1px solid var(--line);padding-bottom:8px}.input-details summary{cursor:pointer;font-size:12px;color:var(--moss-dark)}.input-details label,.paper-picker{display:grid;gap:4px;margin-top:8px;font-size:12px;color:var(--muted)}.input-details input,.input-details textarea{width:100%;box-sizing:border-box;border:1px solid var(--line);padding:7px}.paper-picker select{width:100%;margin-top:4px}
</style>
