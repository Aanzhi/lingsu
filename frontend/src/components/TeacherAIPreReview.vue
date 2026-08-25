<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { MagicStick, Warning } from '@element-plus/icons-vue'
import {
  createAIGeneration,
  errorMessage,
  getAIAvailability,
  getMaterial,
  getAIGenerations,
  type AIGeneration,
  type Material,
} from '../api'
import { aiUnavailableMessage, canGenerateAI, isAIDemoMode, shouldPollAI } from '../stores/aiModel'
import FeedbackBanner from './FeedbackBanner.vue'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'

const props = withDefaults(defineProps<{
  materialId: number
  materialTitle?: string
  materialContent?: string
  taskTitle?: string
  projectId?: number
}>(), {})
const emit = defineEmits<{ (event: 'use-draft', value: string): void }>()

const material = ref<Material | null>(null)
const serviceStatus = ref<string | null>(null)
const focus = ref('')
const loading = ref(false)
const loadingContext = ref(true)
const feedback = ref<FeedbackState | null>(null)
const result = ref<AIGeneration | null>(null)
const createdId = ref<number | null>(null)
let timer: number | undefined

const projectId = computed(() => props.projectId ?? material.value?.project ?? null)
const materialText = computed(() => props.materialContent?.trim() || material.value?.revisions?.[0]?.content?.trim() || '')
const materialLabel = computed(() => props.materialTitle || material.value?.title || '当前提交材料')
const aiReady = computed(() => canGenerateAI(serviceStatus.value))
const isDemo = computed(() => isAIDemoMode(serviceStatus.value))
const verificationItems = computed(() => result.value?.verification_items ?? [])
const reviewDraft = computed(() => result.value?.status === 'completed' ? result.value.output?.trim() || '' : '')

function useDraft() {
  if (reviewDraft.value) emit('use-draft', reviewDraft.value)
}

async function load() {
  loadingContext.value = true
  try {
    const [availability, materialResponse] = await Promise.all([
      getAIAvailability().catch(() => null),
      getMaterial(props.materialId),
    ])
    serviceStatus.value = availability?.data.status ?? 'unavailable'
    material.value = materialResponse.data
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '材料上下文没有加载成功，可刷新重试。', '重试')
  } finally {
    loadingContext.value = false
  }
}

async function poll() {
  if (!projectId.value || !createdId.value) return
  try {
    const logs = (await getAIGenerations(projectId.value)).data
    const entry = logs.find((item) => item.id === createdId.value) ?? null
    result.value = entry
    if (entry && shouldPollAI(entry.status)) {
      timer = window.setTimeout(() => void poll(), 1500)
    } else {
      loading.value = false
    }
  } catch (reason) {
    loading.value = false
    feedback.value = makeFeedback('error', errorMessage(reason), '可以稍后刷新查看预审结果。', '重试')
  }
}

async function runReview() {
  if (!aiReady.value) {
    feedback.value = makeFeedback('info', aiUnavailableMessage(serviceStatus.value), 'AI 只会在服务可用时发送，不影响你继续人工审核。')
    return
  }
  if (!projectId.value) {
    feedback.value = makeFeedback('error', '当前材料没有关联项目。', '请返回审核队列刷新这份提交。')
    return
  }
  if (!materialText.value) {
    feedback.value = makeFeedback('error', '这份提交没有可供预审的正文。', '请以附件和真实性确认作为人工审核依据。')
    return
  }
  loading.value = true
  result.value = null
  feedback.value = null
  try {
    const created = await createAIGeneration({
      project: projectId.value,
      material: props.materialId,
      task: material.value?.task ?? undefined,
      agent_key: 'material-feedback',
      purpose: '材料 AI 预审',
      prompt: `请预审《${materialLabel.value}》这次提交，先指出需要教师核验的事实、证据、结构和可行性问题，再给出可执行的修改建议。${focus.value ? `\n教师特别关注：${focus.value}` : ''}`,
      input_values: {
        material_text: materialText.value.slice(0, 10000),
        focus: focus.value.trim() || '事实、证据、结构、可行性和安全边界',
      },
      context_scope: {},
    })
    createdId.value = created.data.id
    await poll()
  } catch (reason) {
    loading.value = false
    feedback.value = makeFeedback('error', errorMessage(reason), '预审没有发送成功，人工审核内容不会丢失。', '重试')
  }
}

onMounted(() => void load())
onBeforeUnmount(() => {
  if (timer) window.clearTimeout(timer)
})
</script>

<template>
  <section class="teacher-ai-pre-review paper-card">
    <div class="teacher-ai-pre-review__head">
      <div>
        <p class="eyebrow">灵思 AI · 审核辅助</p>
        <h3>AI 预审材料</h3>
        <p class="teacher-ai-pre-review__desc">AI 只提供核验清单和修改建议，不替教师通过、打回或解锁任务。</p>
      </div>
      <span class="teacher-ai-pre-review__badge">仍由教师决定</span>
    </div>

    <div class="teacher-ai-pre-review__scope">
      <span>当前提交材料</span>
      <strong>{{ materialLabel }}</strong>
      <small v-if="taskTitle">{{ taskTitle }}</small>
    </div>

    <FeedbackBanner v-model="feedback" @action="load" />

    <div v-if="loadingContext" class="teacher-ai-pre-review__loading">正在读取材料上下文…</div>
    <template v-else>
      <label class="teacher-ai-pre-review__focus">教师关注点（可选）
        <input v-model="focus" :disabled="loading" placeholder="如：数据是否支撑结论、实验是否安全" />
      </label>
      <div class="teacher-ai-pre-review__actions">
        <button class="secondary-button" type="button" :disabled="loading || !aiReady" @click="runReview">
          <el-icon><MagicStick /></el-icon>
          {{ loading ? 'AI 正在预审…' : aiReady ? '开始 AI 预审' : 'AI 暂不可用' }}
        </button>
        <span class="teacher-ai-pre-review__hint">预审结果只作为旁证，决定前仍请查看正文、附件和真实性确认。</span>
      </div>
    </template>

    <div v-if="result" class="teacher-ai-pre-review__result">
      <div class="teacher-ai-pre-review__result-head">
        <strong>{{ result.status === 'completed' ? '预审建议 · 请人工核验' : result.status === 'failed' ? '预审失败' : '预审进行中…' }}</strong>
        <span v-if="isDemo" class="demo-tag">演示模式</span>
      </div>
      <div v-if="result.status === 'completed'" class="teacher-ai-pre-review__output-wrap">
        <p class="teacher-ai-pre-review__output">{{ result.output }}</p>
        <button v-if="reviewDraft" class="secondary-button teacher-ai-pre-review__draft-button" type="button" @click="useDraft">写入评语草稿</button>
      </div>
      <p v-else-if="result.status === 'failed'" class="teacher-ai-pre-review__error"><el-icon><Warning /></el-icon>{{ result.error_message || 'AI 没有返回结果。' }}</p>
      <p v-else class="teacher-ai-pre-review__pending"><el-icon class="spin"><MagicStick /></el-icon> AI 正在通读当前提交，请稍候…</p>
      <ul v-if="result.status === 'completed' && verificationItems.length" class="teacher-ai-pre-review__checks">
        <li v-for="item in verificationItems" :key="item.item"><strong>{{ item.item }}</strong><small v-if="item.guidance">{{ item.guidance }}</small></li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.teacher-ai-pre-review { display: grid; gap: 14px; background: var(--sage-soft); }
.teacher-ai-pre-review__head, .teacher-ai-pre-review__result-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.teacher-ai-pre-review h3 { margin: 0; font: 700 19px var(--sans); color: var(--ink); }
.teacher-ai-pre-review__desc, .teacher-ai-pre-review__hint { margin: 5px 0 0; color: var(--muted); font-size: 12px; line-height: 1.6; }
.teacher-ai-pre-review__badge { flex: 0 0 auto; padding: 5px 9px; border: 1px solid rgba(76, 114, 69, .22); border-radius: 999px; color: var(--moss-dark); background: rgba(255, 255, 255, .7); font-size: 11px; white-space: nowrap; }
.teacher-ai-pre-review__scope { display: grid; gap: 3px; padding: 11px 13px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); }
.teacher-ai-pre-review__scope span, .teacher-ai-pre-review__scope small { color: var(--muted); font-size: 11px; }
.teacher-ai-pre-review__scope strong { color: var(--ink); font-size: 13px; }
.teacher-ai-pre-review__focus { display: grid; gap: 6px; color: var(--ink); font-size: 12px; font-weight: 700; }
.teacher-ai-pre-review__focus input { min-height: 38px; padding: 9px 11px; border: 1px solid var(--line-dark); border-radius: 8px; color: var(--ink); background: rgba(255, 255, 255, .78); font: inherit; font-weight: 400; }
.teacher-ai-pre-review__focus input:focus { outline: 3px solid rgba(76, 114, 69, .14); border-color: var(--moss); }
.teacher-ai-pre-review__actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.teacher-ai-pre-review__actions button { display: inline-flex; align-items: center; gap: 6px; }
.teacher-ai-pre-review__loading, .teacher-ai-pre-review__pending { color: var(--muted); font-size: 12px; }
.teacher-ai-pre-review__result { display: grid; gap: 10px; padding-top: 13px; border-top: 1px dashed var(--line-dark); }
.teacher-ai-pre-review__result-head strong { font-size: 13px; color: var(--moss-dark); }
.teacher-ai-pre-review__output-wrap { display: grid; gap: 8px; }
.teacher-ai-pre-review__output { margin: 0; padding: 12px; border-radius: 8px; color: var(--ink); background: rgba(255, 255, 255, .72); font-size: 12px; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.teacher-ai-pre-review__draft-button { justify-self: start; }
.teacher-ai-pre-review__error { display: flex; align-items: flex-start; gap: 6px; margin: 0; color: var(--danger); font-size: 12px; }
.teacher-ai-pre-review__checks { display: grid; gap: 7px; margin: 0; padding: 0; list-style: none; }
.teacher-ai-pre-review__checks li { display: grid; gap: 3px; padding-left: 12px; border-left: 3px solid var(--moss); color: var(--ink); font-size: 12px; }
.teacher-ai-pre-review__checks small { color: var(--muted); line-height: 1.5; }
.teacher-ai-pre-review .spin { animation: teacher-ai-spin 1.2s linear infinite; }
@keyframes teacher-ai-spin { to { transform: rotate(360deg); } }
@media (max-width: 640px) {
  .teacher-ai-pre-review__head { display: grid; }
  .teacher-ai-pre-review__badge { justify-self: start; }
  .teacher-ai-pre-review__actions { align-items: stretch; flex-direction: column; }
  .teacher-ai-pre-review__actions button { justify-content: center; width: 100%; }
}
@media (prefers-reduced-motion: reduce) { .teacher-ai-pre-review .spin { animation: none; } }
</style>
