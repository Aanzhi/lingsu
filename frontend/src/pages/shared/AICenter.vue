<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  createAIGeneration, errorMessage, getAIAgents, getAIAvailability, getAIGenerations,
  getMaterials, getProjectTasks, getProjects,
  type AIAgent, type AIGeneration, type AISource, type ApiTask, type Material, type Project,
} from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import {
  aiStatusLabel, aiUnavailableMessage, canGenerateAI,
  composeAgentPrompt, isAIDemoMode, normalizeAIAgentSelection,
} from '../../stores/aiModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

// —— 研究旅程阶段：把后端 AgentTemplate.category 映射到学生熟悉的研究旅程 ——
const STAGES = [
  { key: 'kaoti', label: '立项与开题' },
  { key: 'sheji', label: '方案与设计' },
  { key: 'zhizuo', label: '制作与测试' },
  { key: 'chengguo', label: '成果整理' },
  { key: 'dabian', label: '答辩与展示' },
]
const CATEGORY_TO_STAGE: Record<string, string> = {
  '开题': 'kaoti', '实验': 'zhizuo', '写作': 'chengguo', '答辩': 'dabian',
}
function agentStage(a: AIAgent): string {
  return CATEGORY_TO_STAGE[a.category] ?? 'sheji'
}
const activeStage = ref<string>('kaoti')
const groupedAgents = computed(() => STAGES.map((s) => ({
  ...s,
  agents: agents.value.filter((a) => agentStage(a) === s.key),
})))

// —— 快捷指令（mock 交互：本地拼装提示词，不依赖新后端端点）——
const WRITE_QUICK = [
  { key: 'polish', label: '润色', instruction: '请帮我润色下面这段文字，保持原意与事实，输出润色后的文本与改动说明：' },
  { key: 'expand', label: '续写', instruction: '请基于下面这段草稿做适度扩写，补充衔接与论证，不添加未经证实的事实：' },
  { key: 'structure', label: '结构检查', instruction: '请检查下面这段文字的结构与逻辑是否清晰，给出可执行的改写建议：' },
]
function applyQuick(_targetKey: string, instruction: string) {
  const ctx = linkedContextText.value || (selectedAgent.value ? composeAgentPrompt(selectedAgent.value, formValues) : '')
  composed.value = ctx ? `${instruction}\n\n${ctx}` : instruction
}

// —— 后端未配置时的 mock 回退，保证布局与交互可见（字段与真实 AIAgent 对齐）——
const MOCK_AGENTS: AIAgent[] = [
  { id: -1, key: 'thesis-proposal', name: '课题申报助手', description: '完善课题申报书', role: 'student', category: '开题', system_instruction: '', prompt_template: '研究主题：{研究主题}\n已知信息：{已知信息}', input_schema: [{ key: '研究主题', label: '研究主题', type: 'text', required: true }, { key: '已知信息', label: '已知信息', type: 'textarea', required: false }], context_scope_default: { project_basics: true }, is_active: true, school: null, order: 0 },
  { id: -2, key: 'topic-selection-paper', name: '选题助手', description: '评估与细化选题', role: 'student', category: '开题', system_instruction: '', prompt_template: '选题方向：{选题方向}', input_schema: [{ key: '选题方向', label: '选题方向', type: 'text', required: true }], context_scope_default: { project_basics: true }, is_active: true, school: null, order: 1 },
  { id: -3, key: 'literature-review-paper', name: '文献综述助手', description: '起草综述与检索策略', role: 'student', category: '写作', system_instruction: '', prompt_template: '研究主题：{研究主题}', input_schema: [{ key: '研究主题', label: '研究主题', type: 'text', required: true }], context_scope_default: { project_basics: true, approved_materials: true }, is_active: true, school: null, order: 2 },
  { id: -4, key: 'research-design-paper', name: '研究设计助手', description: '评估研究设计', role: 'student', category: '实验', system_instruction: '', prompt_template: '研究问题：{研究问题}', input_schema: [{ key: '研究问题', label: '研究问题', type: 'textarea', required: true }], context_scope_default: { project_basics: true }, is_active: true, school: null, order: 3 },
  { id: -5, key: 'data-analysis-paper', name: '数据分析助手', description: '解读数据趋势', role: 'student', category: '写作', system_instruction: '', prompt_template: '数据描述：{数据描述}', input_schema: [{ key: '数据描述', label: '数据描述', type: 'textarea', required: true }], context_scope_default: { approved_materials: true }, is_active: true, school: null, order: 4 },
  { id: -6, key: 'paper-framework', name: '论文框架助手', description: '搭建报告章节', role: 'student', category: '写作', system_instruction: '', prompt_template: '已有材料：{已有材料}', input_schema: [{ key: '已有材料', label: '已有材料', type: 'textarea', required: false }], context_scope_default: { approved_materials: true }, is_active: true, school: null, order: 5 },
  { id: -7, key: 'paper-polish', name: '论文润色助手', description: '学术规范润色', role: 'student', category: '写作', system_instruction: '', prompt_template: '待润色文本：{待润色文本}', input_schema: [{ key: '待润色文本', label: '待润色文本', type: 'textarea', required: true }], context_scope_default: { approved_materials: true }, is_active: true, school: null, order: 6 },
  { id: -8, key: 'format-proof', name: '结构校对助手', description: '检查结构与逻辑', role: 'student', category: '答辩', system_instruction: '', prompt_template: '待校对文本：{待校对文本}', input_schema: [{ key: '待校对文本', label: '待校对文本', type: 'textarea', required: true }], context_scope_default: { approved_materials: true }, is_active: true, school: null, order: 7 },
]

const route = useRoute()
const composed = ref('')
const selectedAgent = ref<AIAgent | null>(null)
const agents = ref<AIAgent[]>([])
const formValues = reactive<Record<string, string>>({})
const loading = ref(false)
const error = ref('')
const feedback = ref<FeedbackState | null>(null)
const projectId = ref<number | null>(null)
const projects = ref<Project[]>([])
const history = ref<AIGeneration[]>([])
const serviceStatus = ref<string | null>(null)
const remainingQuota = ref<number | null>(null)
// 步骤关联（让 AI 带上“当前在哪一步、写哪份材料”的上下文）
const tasks = ref<ApiTask[]>([])
const materials = ref<Material[]>([])
const relatedTaskIds = ref<number[]>([])
const relatedMaterialIds = ref<number[]>([])
const linkedStepId = ref<number | null>(null)
const linkedMaterialId = computed(() => {
  if (!linkedStepId.value) return null
  const m = materials.value.find((item) => item.task === linkedStepId.value)
  return m?.id ?? null
})
const linkedStep = computed(() => tasks.value.find((t) => t.id === linkedStepId.value) ?? null)
const linkedContextText = computed(() => {
  if (!linkedStep.value) return ''
  const lines = [`当前步骤：${linkedStep.value.stage_name} · ${linkedStep.value.title}`, linkedStep.value.description]
  const m = materials.value.find((item) => item.task === linkedStepId.value)
  if (m?.guidance) lines.push(`这份材料的写作要求：${m.guidance}`)
  return lines.join('\n')
})
const linkedScope = computed<Record<string, boolean | string | number[]>>(() => {
  const base = selectedAgent.value?.context_scope_default ?? { project_basics: true, approved_materials: true }
  if (!linkedStepId.value && !relatedTaskIds.value.length && !relatedMaterialIds.value.length) return base
  return {
    ...base,
    current_task: true,
    current_material_draft: true,
    current_guidance: true,
    ...(relatedTaskIds.value.length ? { related_tasks: relatedTaskIds.value } : {}),
    ...(relatedMaterialIds.value.length ? { selected_materials: relatedMaterialIds.value } : {}),
  }
})
let timer: number | undefined

const role = computed(() => route.path.startsWith('/teacher') ? 'teacher' : 'student')
const aiReady = computed(() => canGenerateAI(serviceStatus.value))
const isDemo = computed(() => isAIDemoMode(serviceStatus.value))
const aiServiceMessage = computed(() => aiUnavailableMessage(serviceStatus.value))

// —— 左栏：项目旅程 tree ——
const collapsedStages = ref<number[]>([])
const treeCollapsed = ref(false)
const treeStages = computed(() => {
  const map = new Map<number, { order: number; name: string; steps: { task: ApiTask; material: Material | null }[] }>()
  for (const t of tasks.value) {
    if (!map.has(t.stage_order)) map.set(t.stage_order, { order: t.stage_order, name: t.stage_name, steps: [] })
    const material = materials.value.find((m) => m.task === t.id) ?? null
    map.get(t.stage_order)!.steps.push({ task: t, material })
  }
  return [...map.values()].sort((a, b) => a.order - b.order)
})
function isStageOpen(order: number) { return !collapsedStages.value.includes(order) }
function toggleStage(order: number) {
  collapsedStages.value = isStageOpen(order)
    ? [...collapsedStages.value, order]
    : collapsedStages.value.filter((o) => o !== order)
}
function isTaskIncluded(taskId: number) { return relatedTaskIds.value.includes(taskId) || linkedStepId.value === taskId }
function toggleTaskContext(taskId: number) {
  const mat = materials.value.find((m) => m.task === taskId)
  if (relatedTaskIds.value.includes(taskId)) {
    relatedTaskIds.value = relatedTaskIds.value.filter((x) => x !== taskId)
    if (mat) relatedMaterialIds.value = relatedMaterialIds.value.filter((x) => x !== mat.id)
  } else {
    relatedTaskIds.value = [...relatedTaskIds.value, taskId]
    if (mat) relatedMaterialIds.value = [...relatedMaterialIds.value, mat.id]
  }
}
function setCurrentStep(task: ApiTask) { linkedStepId.value = linkedStepId.value === task.id ? null : task.id }

// —— 右栏：上下文清单 ——
const contextItems = computed(() => {
  const items: { kind: 'current' | 'step' | 'material'; id: number; label: string }[] = []
  if (linkedStepId.value) {
    const t = tasks.value.find((x) => x.id === linkedStepId.value)
    if (t) items.push({ kind: 'current', id: t.id, label: '当前步骤 · ' + t.title })
  }
  for (const id of relatedTaskIds.value) {
    const t = tasks.value.find((x) => x.id === id)
    if (t) items.push({ kind: 'step', id: t.id, label: '参考步骤 · ' + t.title })
  }
  for (const id of relatedMaterialIds.value) {
    if (id === linkedMaterialId.value) continue
    const m = materials.value.find((x) => x.id === id)
    if (m) items.push({ kind: 'material', id: m.id, label: '材料 · ' + m.title })
  }
  return items
})
function removeContext(item: { kind: 'current' | 'step' | 'material'; id: number }) {
  if (item.kind === 'current') linkedStepId.value = null
  else if (item.kind === 'step') toggleTaskContext(item.id)
  else relatedMaterialIds.value = relatedMaterialIds.value.filter((x) => x !== item.id)
}

// —— 右栏 tab ——
const rightTab = ref<'context' | 'history'>('context')

const showVars = ref(false)

// 从研究旅程页跳转而来（?stage=<阶段order>）时，预选对应阶段 tab
function stageKeyFromQuery(): string | null {
  const raw = route.query.stage
  if (raw == null) return null
  const order = Number(Array.isArray(raw) ? raw[0] : raw)
  if (!Number.isFinite(order) || order < 1) return null
  return STAGES[Math.min(Math.floor(order), STAGES.length) - 1]?.key ?? null
}

async function loadAgents() {
  try {
    const res = await getAIAgents()
    agents.value = res.data.length ? res.data : MOCK_AGENTS
    const fromQuery = stageKeyFromQuery()
    const groups = groupedAgents.value
    const targetStage = fromQuery ?? groups.find((s) => s.agents.length)?.key
    if (targetStage) {
      activeStage.value = targetStage
      selectedAgent.value = groups.find((s) => s.key === targetStage)?.agents[0]
        ?? normalizeAIAgentSelection(selectedAgent.value, agents.value)
    } else {
      selectedAgent.value = normalizeAIAgentSelection(selectedAgent.value, agents.value)
    }
    if (selectedAgent.value) resetForm()
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'AI 模板没有加载完成，可以重试。', '重试')
  }
}

function resetForm() {
  Object.keys(formValues).forEach((k) => delete formValues[k])
  selectedAgent.value?.input_schema.forEach((f) => { formValues[f.key] = '' })
  recompute()
}

function recompute() {
  composed.value = selectedAgent.value ? composeAgentPrompt(selectedAgent.value, formValues) : ''
}

function selectAgent(agent: AIAgent) {
  selectedAgent.value = agent
  activeStage.value = agentStage(agent)
  resetForm()
}

function sourceLabel(src: AISource) {
  const map: Record<AISource['kind'], string> = { task: '步骤', material: '材料', attachment: '文件' }
  return `${map[src.kind]} · ${src.title}`
}

async function loadHistory() {
  history.value = (await getAIGenerations(projectId.value ?? undefined)).data
  window.clearTimeout(timer)
  if (history.value.some((item) => item.status === 'queued' || item.status === 'processing')) {
    timer = window.setTimeout(() => loadHistory().catch(() => undefined), 1500)
  }
}

async function loadSteps() {
  if (!projectId.value) return
  try {
    const [taskRes, matRes] = await Promise.all([getProjectTasks(projectId.value), getMaterials(projectId.value)])
    tasks.value = taskRes.data
    materials.value = matRes.data
  } catch {
    // 步骤关联为可选增强，拉取失败不阻断主流程
  }
}

async function load() {
  try {
    const [projectResponse, availabilityResponse] = await Promise.all([getProjects(), getAIAvailability().catch(() => null)])
    projects.value = projectResponse.data
    projectId.value = projects.value[0]?.id ?? null
    serviceStatus.value = availabilityResponse?.data.status ?? 'unavailable'
    remainingQuota.value = availabilityResponse?.data.remaining_quota ?? null
    await Promise.all([loadAgents(), loadHistory(), loadSteps()])
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'AI 历史没有加载完成，可以重试。', '重试')
  }
}

onMounted(load)

async function generate() {
  error.value = ''
  if (!aiReady.value) {
    feedback.value = makeFeedback('info', aiServiceMessage.value, '管理员完成配置前，系统不会发送你的请求。')
    return
  }
  if (!projectId.value) {
    feedback.value = makeFeedback('error', '请先创建或认领一个项目。', 'AI 需要项目上下文才能工作。')
    return
  }
  if (!composed.value.trim()) {
    feedback.value = makeFeedback('error', '先填写或生成希望 AI 一起思考的内容。', '填写上方变量或直接在文本框描述目标、已知信息与不确定之处后再生成。')
    return
  }
  loading.value = true
  feedback.value = null
  try {
    await createAIGeneration({
      project: projectId.value,
      agent_key: selectedAgent.value?.key,
      purpose: selectedAgent.value?.name,
      prompt: composed.value,
      context_scope: linkedScope.value,
      task: linkedStepId.value ?? undefined,
      material: linkedMaterialId.value ?? undefined,
    })
    await loadHistory()
    feedback.value = makeFeedback('success', 'AI 草稿任务已创建。', '生成结果会进入对话，采用前请按真实项目核对。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '没有发送成功，可以保留当前内容后重试。', '重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page ai-center-page">
    <PageHeader eyebrow="灵思 AI · 真实服务" :title="role === 'teacher' ? '审核与指导工作台' : '你的研究工作台'" description="AI 只生成草稿和建议；不会自动提交、审核或发布，所有调用均记录用途和资料范围。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <div v-if="isDemo" class="demo-banner"><strong>演示模式</strong>：AI 未接入真实模型，将返回示例性建议（不编造数据），仅供演示。配置 OPENAI_API_KEY 后即返回真实结果。</div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>

    <div class="ai-center-grid" :class="{ 'tree-collapsed': treeCollapsed }">
      <!-- 左栏：项目旅程 tree -->
      <aside v-show="!treeCollapsed" class="tree-panel">
        <div class="panel-head">
          <p class="eyebrow">项目旅程</p>
          <button class="icon-btn" type="button" title="收起" @click="treeCollapsed = true">«</button>
        </div>
        <div class="tree-scroll">
          <p v-if="!tasks.length" class="tree-empty">尚未加载项目步骤。</p>
          <div v-for="stage in treeStages" :key="stage.order" class="tree-stage">
            <button class="tree-stage-head" type="button" @click="toggleStage(stage.order)">
              <span class="caret">{{ isStageOpen(stage.order) ? '▾' : '▸' }}</span>
              <span class="tree-stage-name">{{ stage.name }}</span>
              <span class="tree-stage-count">{{ stage.steps.length }}</span>
            </button>
            <div v-show="isStageOpen(stage.order)" class="tree-steps">
              <div v-for="node in stage.steps" :key="node.task.id" class="tree-step" :class="{ current: linkedStepId === node.task.id }">
                <label class="tree-check">
                  <input type="checkbox" :checked="isTaskIncluded(node.task.id)" @change="toggleTaskContext(node.task.id)" />
                </label>
                <button class="tree-step-name" type="button" @click="setCurrentStep(node.task)">
                  {{ node.task.title }}
                  <span v-if="linkedStepId === node.task.id" class="tree-current-tag">当前</span>
                </button>
                <span v-if="node.material" class="tree-mat-dot" title="含关联材料" />
              </div>
            </div>
          </div>
        </div>
      </aside>
      <button v-if="treeCollapsed" class="tree-expand" type="button" @click="treeCollapsed = false">» 项目旅程</button>

      <!-- 中栏：聊天工作台 -->
      <section class="chat-panel">
        <div class="chat-top">
          <div class="stage-tabs">
            <button v-for="s in STAGES" :key="s.key" type="button" class="stage-tab" :class="{ active: activeStage === s.key }" @click="activeStage = s.key">
              {{ s.label }}<span class="stage-tab-count">{{ groupedAgents.find((g) => g.key === s.key)?.agents.length || 0 }}</span>
            </button>
          </div>
          <div class="agent-pills">
            <button v-for="a in groupedAgents.find((g) => g.key === activeStage)?.agents" :key="a.id" type="button" class="agent-pill" :class="{ active: selectedAgent?.id === a.id }" @click="selectAgent(a)">
              {{ a.name }}
            </button>
            <span v-if="!(groupedAgents.find((g) => g.key === activeStage)?.agents.length)" class="agent-pills-empty">该阶段暂无可用 AI 助手</span>
          </div>
        </div>

        <div class="chat-scroll">
          <div v-if="!history.length" class="chat-empty">
            <p class="chat-empty-title">开始与「{{ selectedAgent?.name ?? 'AI 助手' }}」对话</p>
            <p class="chat-empty-hint">{{ selectedAgent?.description || '选择上方阶段的助手，或在下方描述你的目标、已知信息与不确定之处。' }}</p>
          </div>
          <div v-for="item in history" :key="item.id" class="msg-pair">
            <div class="bubble user"><p>{{ item.prompt || item.purpose }}</p></div>
            <div class="bubble ai" :class="item.status">
              <template v-if="item.status === 'completed'">
                <p>{{ item.output }}</p>
                <div v-if="item.referenced_sources?.length" class="src-tags">
                  <span v-for="(src, i) in item.referenced_sources" :key="i" class="src-tag">{{ sourceLabel(src) }}</span>
                </div>
              </template>
              <template v-else-if="item.status === 'failed'">
                <p class="err">{{ item.error_message || '生成失败' }}</p>
              </template>
              <template v-else>
                <p class="pending">{{ aiStatusLabel(item.status) }}…</p>
              </template>
              <small class="msg-meta">{{ item.model_name || item.actor_name }} · {{ item.created_at.slice(0, 16).replace('T', ' ') }}</small>
            </div>
          </div>
        </div>

        <div class="composer">
          <div class="quick-row">
            <span class="quick-label">快捷</span>
            <button v-for="q in WRITE_QUICK" :key="q.label" type="button" class="chip" :disabled="!aiReady" @click="applyQuick(q.key, q.instruction)">{{ q.label }}</button>
          </div>
          <div class="composer-body">
            <button class="vars-toggle" type="button" @click="showVars = !showVars">{{ showVars ? '收起变量' : '填写变量（可选）' }}</button>
            <div v-if="showVars && selectedAgent && selectedAgent.input_schema.length" class="agent-fields">
              <div v-for="field in selectedAgent.input_schema" :key="field.key" class="agent-field">
                <label :for="field.key">{{ field.label }}<span v-if="field.required" class="req">*</span></label>
                <el-select v-if="field.type === 'select'" v-model="formValues[field.key]" :placeholder="field.placeholder || '请选择'" @change="recompute">
                  <el-option v-for="opt in field.options" :key="opt" :label="opt" :value="opt" />
                </el-select>
                <el-input v-else-if="field.type === 'textarea'" v-model="formValues[field.key]" type="textarea" :rows="3" :placeholder="field.placeholder" @input="recompute" />
                <el-input v-else v-model="formValues[field.key]" :placeholder="field.placeholder" @input="recompute" />
              </div>
            </div>
            <label class="composer-label">把以下内容提交给 AI（可继续编辑）
              <textarea v-model="composed" :disabled="!aiReady" rows="5" :placeholder="selectedAgent ? '上方变量会自动组合成提示词，你可在此修改后再生成' : '描述目标、已知信息和你真正不确定的地方……'" />
            </label>
            <div class="ai-submit">
              <span>{{ aiReady ? '不会自动提交、审核或发布' : '服务恢复前不会提交你的请求' }}</span>
              <button class="primary-button" :disabled="loading || !aiReady" type="button" @click="generate">{{ loading ? '正在创建任务…' : aiReady ? '发送' : 'AI 未配置' }}</button>
            </div>
            <p v-if="!aiReady" class="read-only-banner"><strong>AI 当前不可用。</strong> {{ aiServiceMessage }}</p>
            <p v-else-if="remainingQuota !== null" class="form-hint">本校本月剩余 {{ remainingQuota }} 次 AI 调用配额。</p>
          </div>
        </div>
      </section>

      <!-- 右栏：可切 tab -->
      <aside class="context-panel">
        <div class="rt-tabbar">
          <button type="button" :class="{ active: rightTab === 'context' }" @click="rightTab = 'context'">上下文</button>
          <button type="button" :class="{ active: rightTab === 'history' }" @click="rightTab = 'history'">历史</button>
        </div>
        <div class="rt-body">
          <template v-if="rightTab === 'context'">
            <p class="eyebrow">AI 将读取</p>
            <p v-if="!contextItems.length" class="rt-empty">未选择项目步骤或材料。在左侧勾选步骤，或点步骤名设为「当前步骤」。</p>
            <div v-for="item in contextItems" :key="item.kind + item.id" class="ctx-item">
              <span class="ctx-item-label">{{ item.label }}</span>
              <button class="ctx-remove" type="button" @click="removeContext(item)">移除</button>
            </div>
          </template>
          <template v-else>
            <div v-for="item in history" :key="item.id" class="history-card">
              <strong>{{ item.purpose }}</strong>
              <p>{{ item.status === 'completed' ? item.output : item.status === 'failed' ? item.error_message : aiStatusLabel(item.status) }}</p>
              <small>{{ role === 'teacher' ? item.actor_name : item.model_name }} · {{ item.created_at.slice(0, 16).replace('T', ' ') }}</small>
              <div v-if="item.referenced_sources?.length" class="history-refs">
                <span v-for="(src, i) in item.referenced_sources.slice(0, 4)" :key="i" class="ref-tag">{{ sourceLabel(src) }}</span>
              </div>
            </div>
            <EmptyState v-if="!history.length" title="暂无历史" />
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.demo-banner { margin: 0 0 16px; padding: 10px 14px; border: 1px solid var(--sage-line); background: var(--sage-soft); border-radius: var(--radius-md); font-size: 13px; color: var(--moss-dark); line-height: 1.6; }
.demo-banner strong { color: var(--moss-dark); }

.ai-center-grid { display: grid; grid-template-columns: 252px minmax(0,1fr) 308px; gap: 0; border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow); background: var(--paper); height: calc(100vh - 220px); min-height: 560px; overflow: hidden; }
.ai-center-grid.tree-collapsed { grid-template-columns: minmax(0,1fr) 308px; }

.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 16px 10px; }
.icon-btn { border: none; background: transparent; color: var(--muted); cursor: pointer; font-size: 16px; line-height: 1; padding: 2px 6px; border-radius: var(--radius-sm); }
.icon-btn:hover { background: var(--sage-soft); color: var(--moss-dark); }

/* 左栏 tree */
.tree-panel { border-right: 1px solid var(--line); display: flex; flex-direction: column; background: var(--paper-soft); overflow: hidden; }
.tree-scroll { overflow-y: auto; padding: 4px 10px 16px; }
.tree-empty { font-size: 12px; color: var(--muted); padding: 8px; }
.tree-stage { margin-bottom: 4px; }
.tree-stage-head { width: 100%; display: flex; align-items: center; gap: 8px; padding: 9px 10px; background: transparent; border: none; cursor: pointer; text-align: left; color: var(--ink); border-radius: var(--radius-sm); font-size: 13px; }
.tree-stage-head:hover { background: var(--sage-soft); }
.tree-stage-head .caret { font-size: 10px; color: var(--muted); width: 10px; }
.tree-stage-name { font-weight: 600; }
.tree-stage-count { margin-left: auto; font-size: 11px; color: var(--muted); background: var(--sage-soft); border-radius: 999px; padding: 1px 8px; }
.tree-steps { padding: 2px 0 8px 18px; }
.tree-step { display: flex; align-items: center; gap: 8px; padding: 4px 8px; border-radius: var(--radius-sm); }
.tree-step:hover { background: var(--sage-soft); }
.tree-step.current { background: var(--sage-soft); }
.tree-check { display: flex; align-items: center; }
.tree-check input { accent-color: var(--moss); width: 15px; height: 15px; }
.tree-step-name { flex: 1; border: none; background: transparent; text-align: left; cursor: pointer; color: var(--ink); font-size: 12.5px; padding: 2px 0; display: flex; align-items: center; gap: 6px; }
.tree-current-tag { font-size: 10px; color: #fff; background: var(--moss); border-radius: 999px; padding: 1px 7px; }
.tree-mat-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--sage); flex: none; }
.tree-expand { align-self: flex-start; margin: 16px 0 0 16px; border: 1px solid var(--line); background: var(--paper); color: var(--moss-dark); border-radius: var(--radius-sm); padding: 7px 14px; font-size: 12px; cursor: pointer; }
.tree-expand:hover { border-color: var(--moss); }

/* 中栏聊天 */
.chat-panel { display: flex; flex-direction: column; min-width: 0; background: var(--paper); }
.chat-top { padding: 14px 20px 0; border-bottom: 1px solid var(--line); }
.stage-tabs { display: flex; gap: 2px; flex-wrap: wrap; border-bottom: 1px solid var(--line); }
.stage-tab { border: none; background: transparent; padding: 9px 14px; font-size: 13px; cursor: pointer; color: var(--muted); position: relative; font-weight: 600; }
.stage-tab:hover { color: var(--ink); }
.stage-tab.active { color: var(--moss-dark); }
.stage-tab.active::after { content: ''; position: absolute; left: 12px; right: 12px; bottom: -1px; height: 2px; background: var(--moss); border-radius: 2px; }
.stage-tab-count { font-size: 10px; margin-left: 6px; color: var(--muted); background: var(--sage-soft); border-radius: 999px; padding: 0 6px; vertical-align: middle; }
.agent-pills { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 0; }
.agent-pill { border: 1px solid var(--line-dark); background: var(--paper); border-radius: 999px; padding: 5px 14px; font-size: 12.5px; cursor: pointer; color: var(--ink); transition: all .15s ease; }
.agent-pill:hover { border-color: var(--moss); color: var(--moss-dark); }
.agent-pill.active { border-color: var(--moss); background: var(--moss); color: #fff; font-weight: 600; }
.agent-pills-empty { font-size: 12px; color: var(--muted); padding: 8px 2px; }

.chat-scroll { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.chat-empty { margin: auto; text-align: center; color: var(--muted); max-width: 380px; }
.chat-empty-title { font-size: 17px; font-weight: 600; color: var(--ink); margin-bottom: 8px; font-family: var(--serif); }
.chat-empty-hint { font-size: 13px; line-height: 1.7; }
.msg-pair { display: flex; flex-direction: column; gap: 6px; }
.bubble { max-width: 84%; padding: 11px 15px; border-radius: var(--radius-md); font-size: 13.5px; line-height: 1.65; box-shadow: 0 1px 2px rgba(61,68,53,.06); }
.bubble p { white-space: pre-wrap; margin: 0; }
.bubble.user { align-self: flex-end; background: var(--moss); color: #fff; border-bottom-right-radius: 4px; }
.bubble.ai { align-self: flex-start; background: var(--paper); border: 1px solid var(--line); border-bottom-left-radius: 4px; color: var(--ink); }
.bubble.ai.failed { border-color: var(--clay); }
.bubble .pending { color: var(--muted); }
.bubble .err { color: #c0392b; }
.bubble .msg-meta { display: block; margin-top: 7px; font-size: 11px; color: var(--muted); }
.src-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.src-tag { font-size: 11px; padding: 2px 9px; border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); border: 1px solid var(--sage-line); }

/* 中栏底部 composer */
.composer { border-top: 1px solid var(--line); padding: 12px 20px 16px; background: var(--paper-soft); }
.quick-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.quick-label { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.chip { border: 1px solid var(--line-dark); background: var(--paper); color: var(--moss-dark); border-radius: 999px; padding: 4px 13px; font-size: 12px; cursor: pointer; transition: all .15s ease; }
.chip:hover:not(:disabled) { border-color: var(--moss); color: var(--moss); background: var(--sage-soft); }
.chip:disabled { opacity: .5; cursor: not-allowed; }
.vars-toggle { border: none; background: transparent; color: var(--moss-dark); font-size: 12px; cursor: pointer; padding: 2px 0; margin-bottom: 8px; font-weight: 600; }
.vars-toggle:hover { color: var(--moss); }
.agent-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.agent-field { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--muted); }
.agent-field :deep(.el-select), .agent-field :deep(.el-input) { width: 100%; }
.req { color: var(--clay); }
.composer-label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--muted); }
.composer-label textarea { width: 100%; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); padding: 11px 13px; font: inherit; font-size: 13px; resize: vertical; color: var(--ink); background: var(--paper); }
.composer-label textarea:focus { outline: none; border-color: var(--moss); box-shadow: 0 0 0 3px rgba(73,110,69,.12); }
.ai-submit { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 12px; }
.ai-submit > span { font-size: 12px; color: var(--muted); }
.primary-button { background: var(--moss); color: #fff; border: 1px solid var(--moss-dark); border-radius: var(--radius-sm); padding: 9px 24px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all .15s ease; }
.primary-button:hover:not(:disabled) { filter: brightness(.97); transform: translateY(-1px); }
.primary-button:disabled { opacity: .5; cursor: not-allowed; }
.read-only-banner { margin: 10px 0 0; font-size: 12px; color: var(--muted); }
.read-only-banner strong { color: var(--moss-dark); }
.form-hint { margin: 10px 0 0; font-size: 12px; color: var(--muted); }

/* 右栏 tab */
.context-panel { border-left: 1px solid var(--line); display: flex; flex-direction: column; background: var(--paper-soft); overflow: hidden; }
.rt-tabbar { display: flex; border-bottom: 1px solid var(--line); }
.rt-tabbar button { flex: 1; border: none; background: transparent; padding: 13px 0; font-size: 12.5px; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; font-weight: 600; }
.rt-tabbar button.active { color: var(--moss-dark); border-bottom-color: var(--moss); }
.rt-body { overflow-y: auto; padding: 16px; }
.rt-empty { font-size: 12px; color: var(--muted); line-height: 1.7; }
.ctx-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 9px 11px; border: 1px solid var(--line); border-radius: var(--radius-sm); margin-bottom: 8px; background: var(--paper); }
.ctx-item-label { font-size: 12.5px; color: var(--ink); }
.ctx-remove { border: none; background: transparent; color: var(--muted); font-size: 12px; cursor: pointer; }
.ctx-remove:hover { color: var(--clay); }
.history-card { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 11px; margin-bottom: 8px; background: var(--paper); }
.history-card strong { font-size: 12.5px; color: var(--ink); }
.history-card p { font-size: 12px; color: var(--muted); margin: 5px 0; white-space: pre-wrap; }
.history-card small { font-size: 11px; color: var(--muted); }
.history-refs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; }
.ref-tag { font-size: 11px; padding: 2px 9px; border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); border: 1px solid var(--sage-line); }
</style>
