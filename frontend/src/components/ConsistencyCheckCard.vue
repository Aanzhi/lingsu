<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CircleCheck, MagicStick, Warning } from '@element-plus/icons-vue'
import {
  createAIGeneration, errorMessage, getAIAgents, getAIAvailability, getAIGenerations,
  type AIAgent, type AIGeneration,
} from '../api'
import { aiUnavailableMessage, canGenerateAI, composeAgentPrompt, isAIDemoMode, shouldPollAI } from '../stores/aiModel'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'

const props = defineProps<{ projectId: number }>()
const agents = ref<AIAgent[]>([])
const serviceStatus = ref<string | null>(null)
const focus = ref('')
const loading = ref(false)
const feedback = ref<FeedbackState | null>(null)
const result = ref<AIGeneration | null>(null)
const createdId = ref<number | null>(null)
const parseFailed = ref(false)
let timer: number | undefined

const aiReady = computed(() => canGenerateAI(serviceStatus.value))
const isDemo = computed(() => isAIDemoMode(serviceStatus.value))
interface ConsistencyIssue {
  severity: string
  title: string
  involves: string[]
  detail: string
  suggestion: string
}
interface ConsistencyResult {
  coverageScore: number | null
  missingEvidence: string[]
  conflicts: string[]
  issues: ConsistencyIssue[]
  raw?: string
}
const parsed = computed<ConsistencyResult | null>(() => {
  if (!result.value || result.value.status !== 'completed') return null
  return parseConsistency(result.value.output)
})
const coverageScore = computed(() => parsed.value?.coverageScore ?? null)
const missingEvidence = computed(() => parsed.value?.missingEvidence ?? [])
const conflicts = computed(() => parsed.value?.conflicts ?? [])
const issues = computed<ConsistencyIssue[]>(() => parsed.value?.issues ?? [])
const hasProblems = computed(
  () => issues.value.length > 0 || missingEvidence.value.length > 0 || conflicts.value.length > 0,
)
const isClean = computed(() => !hasProblems.value && !parseFailed.value)
const severityClass = (severity: string) => ({ 高: 'sev-high', 中: 'sev-mid', 低: 'sev-low' }[severity] ?? 'sev-mid')
const scoreClass = computed(() => {
  const s = coverageScore.value
  if (s === null) return ''
  if (s >= 80) return 'score-good'
  if (s >= 50) return 'score-mid'
  return 'score-low'
})

function mapIssue(item: Record<string, unknown>): ConsistencyIssue {
  return {
    severity: String(item.severity ?? ''),
    title: String(item.title ?? ''),
    involves: Array.isArray(item.involves) ? (item.involves as unknown[]).map(String) : [],
    detail: String(item.detail ?? ''),
    suggestion: String(item.suggestion ?? ''),
  }
}

function parseConsistency(text: string): ConsistencyResult {
  parseFailed.value = false
  const empty: ConsistencyResult = { coverageScore: null, missingEvidence: [], conflicts: [], issues: [] }
  try {
    const cleaned = text.replace(/```json|```/gi, '').trim()
    const objMatch = cleaned.match(/\{[\s\S]*\}/)
    const parsedObj = JSON.parse(objMatch ? objMatch[0] : cleaned)
    if (Array.isArray(parsedObj)) {
      // 兼容旧版纯数组输出
      return { coverageScore: null, missingEvidence: [], conflicts: [], issues: parsedObj.map(mapIssue) }
    }
    if (parsedObj && typeof parsedObj === 'object') {
      const cov = parsedObj.coverage_score
      return {
        coverageScore: typeof cov === 'number' ? cov : null,
        missingEvidence: Array.isArray(parsedObj.missing_evidence) ? (parsedObj.missing_evidence as unknown[]).map(String) : [],
        conflicts: Array.isArray(parsedObj.conflicts) ? (parsedObj.conflicts as unknown[]).map(String) : [],
        issues: Array.isArray(parsedObj.issues) ? (parsedObj.issues as unknown[]).map((i) => mapIssue(i as Record<string, unknown>)) : [],
      }
    }
    parseFailed.value = true
    return { ...empty, raw: text }
  } catch {
    parseFailed.value = true
    return { ...empty, raw: text }
  }
}

async function load() {
  try {
    const [agentsRes, availRes] = await Promise.all([getAIAgents(), getAIAvailability().catch(() => null)])
    agents.value = agentsRes.data
    serviceStatus.value = availRes?.data.status ?? 'unavailable'
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '体检功能加载失败，可刷新重试。', '重试')
  }
}

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

async function runCheck() {
  if (!aiReady.value) {
    feedback.value = makeFeedback('info', aiUnavailableMessage(serviceStatus.value), '管理员完成配置前不会发送你的请求。')
    return
  }
  loading.value = true
  feedback.value = null
  result.value = null
  parseFailed.value = false
  try {
    const agent = agents.value.find((a) => a.key === 'cross-consistency') ?? null
    const promptText = agent
      ? composeAgentPrompt(agent, { focus: focus.value })
      : `用户关注点：${focus.value || '整体一致性'}\n请通读该项目全部材料，检查前后矛盾、口径不一致或证据缺失，严格输出 JSON 数组。`
    const created = await createAIGeneration({
      project: props.projectId,
      agent_key: 'cross-consistency',
      purpose: '跨步骤一致性体检',
      prompt: promptText,
      context_scope: { project_basics: true, consistency: true },
    })
    createdId.value = created.data.id
    await poll()
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '体检未启动，可重试。', '重试')
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="consistency-card paper-card">
    <div class="cc-head">
      <span class="botanical-stamp">❧</span>
      <div>
        <p class="eyebrow">灵思 AI · 一致性体检</p>
        <h3>跨步骤一致性体检</h3>
      </div>
    </div>
    <p class="cc-desc">AI 会通读项目各步骤材料，找出前后矛盾、口径不一致或证据缺失。结果仅供参考，采用前请人工核对。</p>
    <FeedbackBanner v-model="feedback" @action="load" />
    <label class="cc-focus">重点关注（可选）<textarea v-model="focus" rows="2" :disabled="loading" placeholder="如：数据是否支撑结论、术语是否前后一致" /></label>
    <button class="primary-button" type="button" :disabled="loading || !aiReady" @click="runCheck">{{ loading ? '体检中…' : aiReady ? '开始体检' : 'AI 未配置' }}</button>

    <div v-if="result" class="cc-result">
      <div v-if="result.status === 'completed'">
        <span v-if="isDemo" class="demo-tag cc-demo">演示模式 · 示例结果</span>
        <div v-if="coverageScore !== null" class="cc-score">
          <div class="score-head"><span>证据覆盖度</span><strong>{{ coverageScore }}<small>/100</small></strong></div>
          <div class="score-bar"><div class="score-fill" :class="scoreClass" :style="{ width: coverageScore + '%' }"></div></div>
        </div>
        <div v-if="isClean" class="cc-clean">
          <el-icon><CircleCheck /></el-icon>
          <div><strong>未发现明显的一致性问题</strong><p>各材料之间暂未检测到前后矛盾或脱节。仍建议通读一遍终稿。</p></div>
        </div>
        <template v-else>
          <ul v-if="issues.length" class="cc-issues">
            <li v-for="(issue, index) in issues" :key="index" :class="severityClass(issue.severity)">
              <div class="issue-head"><span class="sev-badge">{{ issue.severity || '提示' }}</span><strong>{{ issue.title }}</strong></div>
              <p v-if="issue.involves.length" class="issue-involves">涉及：{{ issue.involves.join('、') }}</p>
              <p class="issue-detail">{{ issue.detail }}</p>
              <p v-if="issue.suggestion" class="issue-suggest"><em>建议：{{ issue.suggestion }}</em></p>
            </li>
          </ul>
          <div v-if="missingEvidence.length" class="cc-list cc-missing">
            <p class="list-head"><el-icon><Warning /></el-icon> 建议补充的证据</p>
            <ul><li v-for="(m, i) in missingEvidence" :key="'m' + i">{{ m }}</li></ul>
          </div>
          <div v-if="conflicts.length" class="cc-list cc-conflict">
            <p class="list-head"><el-icon><Warning /></el-icon> 检测到冲突 / 口径不一致</p>
            <ul><li v-for="(c, i) in conflicts" :key="'c' + i">{{ c }}</li></ul>
          </div>
        </template>
        <div v-if="parseFailed" class="cc-parse-failed">
          <el-icon><Warning /></el-icon>
          <div><strong>体检已完成，但返回格式无法自动解析</strong><p>以下是 AI 的原始回复，请人工查看：</p></div>
          <pre>{{ parsed?.raw ?? result.output }}</pre>
        </div>
      </div>
      <div v-else-if="result.status === 'failed'" class="cc-failed">
        <el-icon><Warning /></el-icon>
        <p>{{ result.error_message || '体检失败，请重试。' }}</p>
      </div>
      <div v-else class="cc-pending">
        <p><el-icon class="spin"><MagicStick /></el-icon> AI 正在通读全部材料并比对，请稍候…</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.consistency-card { display: flex; flex-direction: column; gap: 12px; }
.cc-head { display: flex; align-items: center; gap: 12px; }
.botanical-stamp { font-size: 22px; color: var(--moss-dark); }
.cc-head h3 { margin: 0; font-size: 18px; }
.cc-desc { margin: 0; font-size: 13px; color: var(--muted); line-height: 1.6; }
.cc-focus { display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.cc-focus textarea { width: 100%; resize: vertical; padding: 8px; border-radius: 8px; border: 1px solid var(--line); font: inherit; line-height: 1.5; }
.cc-result { border-top: 1px dashed var(--line); padding-top: 12px; }
.cc-score { margin-bottom: 4px; }
.cc-score .score-head { display: flex; justify-content: space-between; align-items: baseline; font-size: 13px; color: var(--muted); }
.cc-score .score-head strong { font-size: 18px; color: var(--ink); }
.cc-score .score-head small { font-size: 12px; color: var(--muted); }
.score-bar { height: 8px; border-radius: 999px; background: var(--line); overflow: hidden; margin-top: 4px; }
.score-fill { height: 100%; border-radius: 999px; background: var(--moss); transition: width .4s ease; }
.score-fill.score-mid { background: #e0a800; }
.score-fill.score-low { background: #c0392b; }
.cc-clean { display: flex; gap: 10px; align-items: flex-start; }
.cc-clean .el-icon { font-size: 22px; color: var(--moss); margin-top: 2px; }
.cc-clean strong { color: var(--moss-dark); }
.cc-clean p { margin: 4px 0 0; font-size: 13px; color: var(--muted); }
.cc-list { border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; background: var(--paper); }
.cc-list .list-head { display: flex; align-items: center; gap: 6px; margin: 0 0 6px; font-size: 13px; color: var(--moss-dark); }
.cc-list .list-head .el-icon { color: #e0a800; }
.cc-list ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.cc-list li { font-size: 12px; color: var(--ink); line-height: 1.5; padding-left: 12px; position: relative; }
.cc-list li::before { content: "•"; position: absolute; left: 0; color: var(--muted); }
.cc-missing .list-head { color: var(--moss-dark); }
.cc-conflict { border-left: 4px solid #c0392b; }
.cc-issues { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.cc-issues li { border: 1px solid var(--line); border-left-width: 4px; border-radius: 8px; padding: 10px 12px; background: var(--paper); }
.cc-issues li.sev-high { border-left-color: #c0392b; }
.cc-issues li.sev-mid { border-left-color: #e0a800; }
.cc-issues li.sev-low { border-left-color: #6b9bd1; }
.issue-head { display: flex; align-items: center; gap: 8px; }
.sev-badge { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: rgba(0,0,0,.05); color: #444; }
.issue-involves { margin: 6px 0 0; font-size: 12px; color: var(--muted); }
.issue-detail { margin: 6px 0 0; font-size: 13px; line-height: 1.6; }
.issue-suggest { margin: 6px 0 0; font-size: 12px; color: var(--moss-dark); }
.cc-parse-failed { display: flex; flex-direction: column; gap: 8px; }
.cc-parse-failed .el-icon { font-size: 20px; color: #e0a800; }
.cc-parse-failed pre { white-space: pre-wrap; background: #f7f7f5; border-radius: 8px; padding: 10px; font-size: 12px; line-height: 1.5; margin: 0; }
.cc-failed { display: flex; gap: 8px; align-items: center; color: #c0392b; }
.cc-pending p { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted); }
.cc-pending .spin { animation: cc-spin 1.2s linear infinite; }
@keyframes cc-spin { to { transform: rotate(360deg); } }
.demo-tag { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px; background: rgba(76,114,69,.12); color: var(--moss-dark); }
.cc-demo { margin-bottom: 8px; }
</style>
