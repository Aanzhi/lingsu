<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import {
  createAIGeneration, errorMessage, getAIAgents, getAIAvailability, getAIGenerations,
  type AIAgent, type AIGeneration, type Material, type ProjectTaskBrief,
} from '../api'
import {
  aiUnavailableMessage, canGenerateAI, composeAgentPrompt, isAIDemoMode, normalizeAIAgentSelection, shouldPollAI,
} from '../stores/aiModel'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'

const props = withDefaults(defineProps<{
  projectId: number
  taskId?: number
  materialId?: number
  materialTitle?: string
  taskTitle?: string
  taskDescription?: string
  materialContent?: string
  availableTasks?: ProjectTaskBrief[]
  availableMaterials?: Material[]
}>(), {})

const agents = ref<AIAgent[]>([])
const selectedAgent = ref<AIAgent | null>(null)
const serviceStatus = ref<string | null>(null)
const prompt = ref('')
const loading = ref(false)
const feedback = ref<FeedbackState | null>(null)
const result = ref<AIGeneration | null>(null)
const createdId = ref<number | null>(null)
// 学生可勾选“参考其它步骤/材料”，让 AI 带上额外上下文
const relatedTaskIds = ref<number[]>([])
const relatedMaterialIds = ref<number[]>([])
let timer: number | undefined

const aiReady = computed(() => canGenerateAI(serviceStatus.value))
const isDemo = computed(() => isAIDemoMode(serviceStatus.value))
const studentAgents = computed(() => agents.value.filter((a) => a.role !== 'teacher'))

// 按研究旅程阶段把助手分组，避免窄栏里一堆 pill 无序换行
const STAGES_MA = [
  { key: 'kaoti', label: '开题' },
  { key: 'sheji', label: '设计' },
  { key: 'zhizuo', label: '实验' },
  { key: 'chengguo', label: '写作' },
  { key: 'dabian', label: '答辩' },
]
const CATEGORY_TO_STAGE_MA: Record<string, string> = {
  '开题': 'kaoti', '实验': 'zhizuo', '写作': 'chengguo', '答辩': 'dabian',
}
function agentStageMA(a: AIAgent): string {
  return CATEGORY_TO_STAGE_MA[a.category] ?? 'sheji'
}
const groupedStudentAgents = computed(() =>
  STAGES_MA
    .map((s) => ({ ...s, agents: studentAgents.value.filter((a) => agentStageMA(a) === s.key) }))
    .filter((g) => g.agents.length),
)
const paperActionKeys = computed(() => Object.keys(PAPER_ACTIONS))

function prefill() {
  const parts: string[] = []
  if (props.taskTitle) parts.push(`当前步骤：${props.taskTitle}`)
  if (props.taskDescription) parts.push(props.taskDescription)
  const draft = props.materialContent ?? ''
  if (draft.trim()) parts.push(`我目前的草稿（节选）：\n${draft.slice(0, 1500)}`)
  prompt.value = parts.join('\n\n')
}

async function load() {
  try {
    const [agentsRes, availRes] = await Promise.all([getAIAgents(), getAIAvailability().catch(() => null)])
    agents.value = agentsRes.data
    selectedAgent.value = normalizeAIAgentSelection(selectedAgent.value, studentAgents.value)
    serviceStatus.value = availRes?.data.status ?? 'unavailable'
    if (!prompt.value) prefill()
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'AI 助手加载失败，可刷新重试。', '重试')
  }
}

function onAgentChange() {
  if (!prompt.value.trim()) prefill()
}

function pickAgent(a: AIAgent) { selectedAgent.value = a; onAgentChange() }

// 写作辅助：一键把当前草稿交给对应助手做润色/续写/结构检查（C3 实时写作助手）
function quickAction(kind: 'polish' | 'expand' | 'structure') {
  const draft = (props.materialContent ?? '').trim().slice(0, 2500)
  const instruction = {
    polish: '请帮我润色下面这段文字，保持原意与事实，输出润色后的文本与改动说明：',
    expand: '请基于下面这段草稿做适度扩写，补充衔接与论证，不添加未经证实的事实：',
    structure: '请检查下面这段文字的结构与逻辑是否清晰，给出可执行的改写建议：',
  }[kind]
  const key = kind === 'structure' ? 'format-proof' : 'polish-expand'
  const agent = agents.value.find((a) => a.key === key) ?? null
  if (agent) selectedAgent.value = agent
  prompt.value = draft
    ? `${instruction}\n\n${draft}`
    : `${instruction}\n\n（当前材料暂无正文，可先粘贴你想处理的文字到这里。）`
}

// 论文快捷：一键把当前草稿交给对应论文 agent（复用现有 agent 机制）
const PAPER_ACTIONS: Record<string, { label: string; key: string; instruction: string }> = {
  'thesis-proposal': { label: '课题申报', key: 'thesis-proposal', instruction: '请帮我完善课题申报书，明确研究问题、背景与研究价值：' },
  'topic-selection-paper': { label: '选题', key: 'topic-selection-paper', instruction: '请评估并细化我的研究选题，判断其是否真实、可行、有价值：' },
  'literature-review-paper': { label: '文献综述', key: 'literature-review-paper', instruction: '请基于我的研究主题起草文献综述提纲与检索策略，标注需自行核实的文献：' },
  'research-design-paper': { label: '研究设计', key: 'research-design-paper', instruction: '请评估并完善我的研究设计，判断其是否足以支撑结论（变量、样本、混淆因素）：' },
  'data-analysis-paper': { label: '数据分析', key: 'data-analysis-paper', instruction: '请解读下列数据趋势，并标注哪些结论需要真实统计验证：' },
  'paper-framework': { label: '论文框架', key: 'paper-framework', instruction: '请为我的研究报告搭建章节框架，并标注每部分应写什么：' },
  'paper-polish': { label: '论文润色', key: 'paper-polish', instruction: '请按学术规范润色定稿下列文本，逐句对比并说明修改原因：' },
}
function paperAction(kind: string) {
  const cfg = PAPER_ACTIONS[kind]
  if (!cfg) return
  const draft = (props.materialContent ?? '').trim().slice(0, 2500)
  const agent = agents.value.find((a) => a.key === cfg.key) ?? null
  if (agent) selectedAgent.value = agent
  prompt.value = draft
    ? `${cfg.instruction}\n\n${draft}`
    : `${cfg.instruction}\n\n（当前材料暂无正文，可先粘贴你想处理的文字到这里。）`
}

const referencedSources = computed(() => result.value?.referenced_sources ?? [])

async function poll() {
  const logs = (await getAIGenerations(props.projectId)).data
  const entry = logs.find((item) => item.id === createdId.value) ?? null
  result.value = entry
  if (entry && shouldPollAI(entry.status)) {
    timer = window.setTimeout(poll, 1500)
  } else {
    loading.value = false
  }
}

async function generate() {
  if (!aiReady.value) {
    feedback.value = makeFeedback('info', aiUnavailableMessage(serviceStatus.value), '管理员完成配置前不会发送你的请求。')
    return
  }
  if (!prompt.value.trim()) {
    feedback.value = makeFeedback('error', '先描述你希望 AI 一起思考的内容。', '可基于上方预填的当前步骤与草稿补充后再生成。')
    return
  }
  loading.value = true
  feedback.value = null
  result.value = null
  try {
    const created = await createAIGeneration({
      project: props.projectId,
      agent_key: selectedAgent.value?.key,
      purpose: selectedAgent.value?.name ?? '材料助手',
      prompt: prompt.value,
      context_scope: {
        ...(selectedAgent.value?.context_scope_default ?? { project_basics: true }),
        current_task: true,
        current_material_draft: true,
        current_guidance: true,
        ...(relatedTaskIds.value.length ? { related_tasks: relatedTaskIds.value } : {}),
        ...(relatedMaterialIds.value.length ? { selected_materials: relatedMaterialIds.value } : {}),
      },
      task: props.taskId,
      material: props.materialId,
    })
    createdId.value = created.data.id
    await poll()
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '没有发送成功，可保留内容后重试。', '重试')
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="material-ai">
    <p class="eyebrow">灵思 AI · 材料助手</p>
    <h3>就这份材料聊一聊</h3>
    <p class="hint">AI 只给草稿建议，不替代你的真实观察；生成内容采用前会保留使用记录。</p>
    <div class="ctx-strip">
      <span class="eyebrow">本次将读取</span>
      <span v-if="props.taskTitle" class="ctx-chip">步骤 · {{ props.taskTitle }}</span>
      <span class="ctx-chip">材料草稿 · {{ props.materialTitle || '当前材料' }}</span>
    </div>
    <FeedbackBanner v-model="feedback" @action="load" />
    <div v-if="studentAgents.length" class="agent-pick">
      <span class="eyebrow">选择助手</span>
      <div class="agent-groups">
        <div v-for="g in groupedStudentAgents" :key="g.key" class="agent-group">
          <p class="agent-group-label">{{ g.label }}</p>
          <div class="agent-pills">
            <button v-for="a in g.agents" :key="a.id" type="button" class="agent-pill" :class="{ active: selectedAgent?.id === a.id }" @click="pickAgent(a)">{{ a.name }}</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="availableTasks?.length || availableMaterials?.length" class="ref-extra">
      <details>
        <summary>参考更多步骤与材料（可选）</summary>
        <label class="ref-field">关联其它步骤
          <el-select v-model="relatedTaskIds" multiple collapse-tags placeholder="可多选" size="small">
            <el-option v-for="t in (availableTasks ?? [])" :key="t.id" :label="`${t.stage_name} · ${t.title}`" :value="t.id" />
          </el-select>
        </label>
        <label class="ref-field">关联其它材料
          <el-select v-model="relatedMaterialIds" multiple collapse-tags placeholder="可多选" size="small">
            <el-option v-for="m in (availableMaterials ?? [])" :key="m.id" :label="m.title" :value="m.id" />
          </el-select>
        </label>
      </details>
    </div>
    <label class="prompt-label">提交给 AI 的内容（可继续编辑）<textarea v-model="prompt" :disabled="!aiReady" rows="6" placeholder="上方会预填当前步骤与草稿，你可补充目标、已知信息和不确定之处……" /></label>
    <div class="quick-block">
      <span class="eyebrow">快捷指令</span>
      <div class="quick-row">
        <button type="button" class="chip" :disabled="!aiReady" @click="quickAction('polish')">润色这段</button>
        <button type="button" class="chip" :disabled="!aiReady" @click="quickAction('expand')">续写建议</button>
        <button type="button" class="chip" :disabled="!aiReady" @click="quickAction('structure')">结构检查</button>
      </div>
      <details class="more-actions">
        <summary>论文助手（{{ paperActionKeys.length }}）</summary>
        <div class="quick-row">
          <button v-for="key in paperActionKeys" :key="key" type="button" class="chip" :disabled="!aiReady" @click="paperAction(key)">{{ PAPER_ACTIONS[key].label }}</button>
        </div>
      </details>
    </div>
    <div class="ai-submit">
      <button class="primary-button" :disabled="loading || !aiReady" type="button" @click="generate">{{ loading ? '正在生成…' : aiReady ? '生成建议' : 'AI 未配置' }}</button>
      <RouterLink class="ghost-link" to="/student/ai">打开完整思考室 →</RouterLink>
    </div>
    <div v-if="result" class="ai-result">
      <span class="result-status">{{ result.status === 'completed' ? '灵思建议 · 需人工核对' : result.status === 'failed' ? '生成失败' : '生成中…' }}<em v-if="isDemo && result.status === 'completed'" class="demo-tag">演示模式</em></span>
      <p v-if="result.status === 'completed'">{{ result.output }}</p>
      <p v-else-if="result.status === 'failed'" class="error-text">{{ result.error_message }}</p>
      <p v-else class="pending-text">AI 正在通读项目上下文，请稍候…</p>
      <div v-if="result.status === 'completed' && referencedSources.length" class="ref-trace">
        <p class="eyebrow">本次已读取的项目来源</p>
        <ul>
          <li v-for="(src, i) in referencedSources" :key="i">
            <span :class="['src-kind', src.kind]">{{ { task: '步骤', material: '材料', attachment: '文件' }[src.kind] }}</span>
            {{ src.title }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.material-ai { display: flex; flex-direction: column; gap: 14px; }
.material-ai h3 { margin: 0; font-size: 16px; font-family: var(--serif); letter-spacing: .01em; }
.hint { margin: 0; font-size: 12px; color: var(--muted); line-height: 1.55; }

.ctx-strip { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ctx-strip .eyebrow { font-size: 11px; margin: 0; }
.ctx-chip { font-size: 11px; padding: 2px 10px; border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); border: 1px solid var(--sage-line); }

.agent-pick { display: flex; flex-direction: column; gap: 8px; }
.agent-groups { display: flex; flex-direction: column; gap: 12px; }
.agent-group-label { margin: 0 0 7px; font-size: 11px; font-weight: 700; letter-spacing: .06em; color: var(--muted); }
.agent-pills { display: flex; gap: 7px; flex-wrap: wrap; }
.agent-pill { border: 1px solid var(--line-dark); background: var(--paper); border-radius: 999px; padding: 4px 13px; font-size: 12px; cursor: pointer; color: var(--ink); transition: all .15s ease; }
.agent-pill:hover { border-color: var(--moss); color: var(--moss-dark); }
.agent-pill.active { border-color: var(--moss); background: var(--moss); color: #fff; font-weight: 600; }

.quick-block { display: flex; flex-direction: column; gap: 9px; }
.quick-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.chip { border: 1px solid var(--line-dark); background: var(--paper); color: var(--moss-dark); border-radius: 999px; padding: 4px 13px; font-size: 12px; cursor: pointer; transition: all .15s ease; }
.chip:hover:not(:disabled) { border-color: var(--moss); color: var(--moss); background: var(--sage-soft); }
.chip:disabled { opacity: .5; cursor: not-allowed; }
.more-actions { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 9px 11px; background: var(--paper-soft); }
.more-actions summary { cursor: pointer; color: var(--moss-dark); font-size: 12px; font-weight: 600; list-style: none; }
.more-actions summary::-webkit-details-marker { display: none; }
.more-actions summary::before { content: '▸ '; color: var(--muted); }
.more-actions[open] summary::before { content: '▾ '; }
.more-actions .quick-row { margin-top: 9px; }

.prompt-label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.prompt-label textarea { width: 100%; resize: vertical; padding: 10px 12px; border-radius: var(--radius-sm); border: 1px solid var(--line-dark); background: var(--paper); font: inherit; line-height: 1.55; }
.prompt-label textarea:focus { outline: none; border-color: var(--moss); box-shadow: 0 0 0 3px rgba(73,110,69,.12); }

.ai-submit { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.ghost-link { font-size: 12px; color: var(--moss-dark); text-decoration: none; font-weight: 600; }
.ghost-link:hover { color: var(--moss); text-decoration: underline; text-underline-offset: 3px; }

.ref-extra { font-size: 13px; }
.ref-extra details { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 9px 11px; background: var(--paper-soft); }
.ref-extra summary { cursor: pointer; color: var(--moss-dark); font-size: 13px; font-weight: 600; }
.ref-field { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; font-size: 12px; color: var(--muted); }
.ref-field :deep(.el-select) { width: 100%; }

.ref-trace { margin-top: 10px; border-top: 1px dashed var(--line-dark); padding-top: 10px; }
.ref-trace ul { list-style: none; margin: 6px 0 0; padding: 0; display: flex; flex-direction: column; gap: 5px; }
.ref-trace li { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; }
.src-kind { font-size: 10px; padding: 1px 7px; border-radius: 999px; color: #fff; background: var(--moss); }
.src-kind.attachment { background: #6b9bd1; }
.src-kind.material { background: var(--moss-dark); }

.ai-result { border-top: 1px dashed var(--line-dark); padding-top: 12px; }
.result-status { font-size: 12px; color: var(--moss); font-weight: 600; }
.ai-result p { white-space: pre-wrap; font-size: 13px; line-height: 1.6; margin: 7px 0 0; color: var(--ink); }
.error-text { color: #c0392b; }
.pending-text { color: var(--muted); }
.demo-tag { display: inline-block; margin-left: 8px; padding: 1px 8px; border-radius: 999px; font-style: normal; font-size: 11px; background: var(--sage-soft); color: var(--moss-dark); border: 1px solid var(--sage-line); vertical-align: middle; }
</style>
