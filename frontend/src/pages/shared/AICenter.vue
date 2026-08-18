<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { MagicStick } from '@element-plus/icons-vue'
import {
  createAIGeneration, errorMessage, getAIAgents, getAIAvailability, getAIGenerations,
  getMaterials, getProjectTasks, getProjects,
  type AIAgent, type AIGeneration, type ApiTask, type Material, type Project,
} from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import {
  aiHistoryMeta, aiStatusLabel, aiUnavailableMessage, canGenerateAI,
  composeAgentPrompt, isAIDemoMode, normalizeAIAgentSelection,
} from '../../stores/aiModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

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
const preview = computed(() => history.value.find((item) => item.status === 'completed')?.output ?? '')

async function loadAgents() {
  try {
    const res = await getAIAgents()
    agents.value = res.data
    selectedAgent.value = normalizeAIAgentSelection(selectedAgent.value, agents.value)
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
  resetForm()
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

function onStepChange() {
  if (!linkedStep.value) {
    composed.value = selectedAgent.value ? composeAgentPrompt(selectedAgent.value, formValues) : ''
    return
  }
  const step = linkedStep.value
  composed.value = `请结合当前步骤《${step.title}》，给我针对性建议。\n\n${step.description}`
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
    feedback.value = makeFeedback('success', 'AI 草稿任务已创建。', '生成结果会进入历史，采用前请按真实项目核对。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '没有发送成功，可以保留当前内容后重试。', '重试')
  } finally {
    loading.value = false
  }
}

async function copyPreview() {
  try {
    await window.navigator.clipboard.writeText(preview.value)
    feedback.value = makeFeedback('success', 'AI 草稿已复制。', '复制的内容仍需人工核对，不能直接作为原始证据。')
  } catch {
    feedback.value = makeFeedback('error', '浏览器未允许复制。', '请手动选择文本复制。')
  }
}
</script>

<template>
  <div class="page ai-center-page">
    <PageHeader eyebrow="灵思 AI · 真实服务" :title="role === 'teacher' ? '审核与指导思考室' : '你的研究思考室'" description="AI 只生成草稿和建议；不会自动提交、审核或发布，所有调用均记录用途和资料范围。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <div v-if="isDemo" class="demo-banner"><strong>演示模式</strong>：AI 未接入真实模型，将返回示例性建议（不编造数据），仅供演示。配置 OPENAI_API_KEY 后即返回真实结果。</div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="ai-center-grid">
      <aside class="tool-shelf">
        <p class="eyebrow">AI 助手</p>
        <button v-for="agent in agents" :key="agent.id" type="button" :class="{ active: selectedAgent?.id === agent.id }" @click="selectAgent(agent)">
          <el-icon><MagicStick /></el-icon>
          <span>
            <strong>{{ agent.name }}</strong>
            <small v-if="agent.description">{{ agent.description }}</small>
          </span>
        </button>
        <EmptyState v-if="!agents.length" title="暂无可用的 AI 助手" hint="请联系平台管理员配置 AI 模板。" />
      </aside>
      <section class="ai-studio paper-card">
        <div class="paper-heading">
          <span class="botanical-stamp">❧</span>
          <div>
            <p>当前助手</p>
            <h2>{{ selectedAgent?.name ?? '未选择助手' }}</h2>
          </div>
        </div>
        <p v-if="selectedAgent?.description" class="agent-desc">{{ selectedAgent.description }}</p>
        <div v-if="tasks.length" class="step-link">
          <label>关联到当前步骤（可选）</label>
          <el-select v-model="linkedStepId" placeholder="不关联，做通用问答" clearable @change="onStepChange">
            <el-option v-for="t in tasks" :key="t.id" :label="`第 ${t.stage_order} 章 · ${t.title}`" :value="t.id" />
          </el-select>
          <div v-if="linkedContextText" class="step-context">
            <p class="eyebrow">将作为上下文带入 AI</p>
            <pre>{{ linkedContextText }}</pre>
          </div>
          <label class="ref-field">参考更多步骤
            <el-select v-model="relatedTaskIds" multiple collapse-tags placeholder="可多选其它步骤" size="small">
              <el-option v-for="t in tasks" :key="t.id" :label="`第 ${t.stage_order} 章 · ${t.title}`" :value="t.id" />
            </el-select>
          </label>
          <label v-if="materials.length" class="ref-field">参考更多材料
            <el-select v-model="relatedMaterialIds" multiple collapse-tags placeholder="可多选其它材料" size="small">
              <el-option v-for="m in materials" :key="m.id" :label="m.title" :value="m.id" />
            </el-select>
          </label>
        </div>
        <div v-if="selectedAgent && selectedAgent.input_schema.length" class="agent-fields">
          <div v-for="field in selectedAgent.input_schema" :key="field.key" class="agent-field">
            <label :for="field.key">{{ field.label }}<span v-if="field.required" class="req">*</span></label>
            <el-select v-if="field.type === 'select'" v-model="formValues[field.key]" :placeholder="field.placeholder || '请选择'" @change="recompute">
              <el-option v-for="opt in field.options" :key="opt" :label="opt" :value="opt" />
            </el-select>
            <el-input v-else-if="field.type === 'textarea'" v-model="formValues[field.key]" type="textarea" :rows="3" :placeholder="field.placeholder" @input="recompute" />
            <el-input v-else v-model="formValues[field.key]" :placeholder="field.placeholder" @input="recompute" />
          </div>
        </div>
        <label>把以下内容提交给 AI（可继续编辑）<textarea v-model="composed" :disabled="!aiReady" rows="10" :placeholder="selectedAgent ? '上方变量会自动组合成提示词，你可在此修改后再生成' : '描述目标、已知信息和你真正不确定的地方……'" /></label>
        <div class="ai-submit">
          <span>{{ aiReady ? '不会自动提交、审核或发布' : '服务恢复前不会提交你的请求' }}</span>
          <button class="primary-button" :disabled="loading || !aiReady" type="button" @click="generate">{{ loading ? '正在创建任务…' : aiReady ? '生成建议' : 'AI 未配置' }}</button>
        </div>
        <div v-if="!aiReady" class="read-only-banner"><strong>AI 当前不可用。</strong> {{ aiServiceMessage }}</div>
        <p v-else-if="remainingQuota !== null" class="form-hint">本校本月剩余 {{ remainingQuota }} 次 AI 调用配额。</p>
        <div v-if="preview" class="ai-result">
          <span>AI 草稿 · 需人工核对</span>
          <h3>灵思建议</h3>
          <p>{{ preview }}</p>
          <button class="secondary-button" type="button" @click="copyPreview">复制建议</button>
        </div>
      </section>
      <aside class="ai-history">
        <p class="eyebrow">生成历史</p>
        <div v-for="item in history" :key="item.id" class="history-card">
          <strong>{{ item.purpose }}</strong>
          <p>{{ item.status === 'completed' ? item.output : item.status === 'failed' ? item.error_message : aiStatusLabel(item.status) }}</p>
          <small>{{ role === 'teacher' ? aiHistoryMeta({ actorName: item.actor_name, scope: item.context_scope }) : item.model_name }} · {{ item.created_at.slice(0, 16).replace('T', ' ') }}</small>
          <div v-if="item.referenced_sources?.length" class="history-refs">
            <span class="ref-dot">{{ item.referenced_sources.length }} 个来源</span>
            <span v-for="(src, i) in item.referenced_sources.slice(0, 4)" :key="i" class="ref-tag">{{ { task: '步骤', material: '材料', attachment: '文件' }[src.kind] }}：{{ src.title }}</span>
          </div>
        </div>
        <EmptyState v-if="!history.length" title="暂无历史" />
      </aside>
    </div>
  </div>
</template>

<style scoped>
.demo-banner { margin: 0 0 4px; padding: 10px 14px; border: 1px dashed var(--moss); background: rgba(76,114,69,.06); border-radius: 10px; font-size: 13px; color: var(--moss-dark); line-height: 1.6; }
.demo-banner strong { color: var(--moss-dark); }
.ref-field { display: flex; flex-direction: column; gap: 6px; margin-top: 10px; font-size: 12px; color: var(--muted); }
.ref-field :deep(.el-select) { width: 100%; }
.history-refs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.history-refs .ref-dot { font-size: 11px; color: var(--moss-dark); }
.history-refs .ref-tag { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: rgba(76,114,69,.1); color: var(--moss-dark); }
</style>
