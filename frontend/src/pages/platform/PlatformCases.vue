<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Collection } from '@element-plus/icons-vue'
import { errorMessage, getPublicCases, platformReviewPublicCase, setCaseVisibility, type PublicCase } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const cases = ref<PublicCase[]>([])
const error = ref('')
const busy = ref(false)
const loading = ref(false)
const feedback = ref<FeedbackState | null>(null)
const confirmCase = ref<PublicCase | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  cases.value = []
  try { cases.value = (await getPublicCases()).data }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '案例治理列表没有加载完成，可以重试。', '重试'); throw reason }
  finally { loading.value = false }
}
onMounted(() => { void load().catch(() => undefined) })
function ask(item: PublicCase) { confirmCase.value = item }
async function toggle() {
  if (!confirmCase.value) return
  const item = confirmCase.value; confirmCase.value = null; busy.value = true; feedback.value = null
  try {
    if (item.status === 'pending_platform') {
      await platformReviewPublicCase(item.id, true)
      await load()
      feedback.value = makeFeedback('success', '案例已通过平台审核并发布。', '案例现在会出现在全平台案例库。')
    } else {
      await setCaseVisibility(item.id, item.status !== 'published')
      await load()
      feedback.value = makeFeedback('success', item.status === 'published' ? '案例已下架。' : '案例已恢复公开。', '公开状态已同步到案例库。')
    }
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '案例状态没有改变，可以重试。', '重试') }
  finally { busy.value = false }
}
</script>

<template><div class="page platform-page"><PageHeader eyebrow="内容治理" title="公开案例治理" description="审核学生公开成果申请，决定发布、下架或恢复。" /><FeedbackBanner v-model="feedback" @action="() => void load().catch(() => undefined)" /><p v-if="error" class="form-error" role="alert">{{ error }}</p><p v-if="loading" class="loading-state" role="status">正在读取公开案例…</p><section v-else class="demo-governance-grid"><article v-for="item in cases" :key="item.id" class="paper-card"><p class="eyebrow">案例 · {{ item.school_name }}</p><h3>{{ item.project_title }}</h3><p class="muted">{{ item.public_summary }}</p><div class="case-governance-steps" aria-label="成果公开审核链"><span :class="{ 'is-done': item.request_type === 'student_school' || Boolean(item.student_consent_at) }">学生同意</span><span :class="{ 'is-done': item.request_type === 'student_school' ? item.status !== 'pending_teacher' : Boolean(item.teacher_reviewer) }">指导教师审核</span><span :class="{ 'is-done': item.status === 'published' || item.status === 'offline' }">平台审核</span></div><div class="governance-card__footer"><StatusTag :status="item.status" /><button v-if="item.status === 'pending_platform'" class="approve-button" :disabled="busy" type="button" @click="ask(item)">通过并发布</button><button v-else-if="item.status === 'published'" class="return-button" :disabled="busy" type="button" @click="ask(item)">下架</button><button v-else-if="item.status === 'offline' && item.student_consent_at" class="approve-button" :disabled="busy" type="button" @click="ask(item)">恢复公开</button></div></article><EmptyState v-if="!cases.length" title="暂无公开案例" description="教师审核通过的公开案例会出现在这里。" /></section><ConfirmDialog v-if="confirmCase" :model-value="true" :title="confirmCase.status === 'pending_platform' ? '通过这个平台案例申请？' : confirmCase.status === 'published' ? '下架这个公开案例？' : '恢复这个公开案例？'" :description="confirmCase.status === 'pending_platform' ? '通过后案例会进入全平台公域，学生和教师都能检索。' : confirmCase.status === 'published' ? '下架后师生将暂时无法检索该案例，平台仍保留治理记录。' : '恢复后案例会重新出现在全平台案例库。'" :confirm-text="confirmCase.status === 'pending_platform' ? '确认发布' : confirmCase.status === 'published' ? '确认下架' : '确认恢复'" :danger="confirmCase.status === 'published'" @update:model-value="confirmCase = null" @confirm="toggle" /></div></template>

<style scoped>
.demo-governance-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.demo-governance-grid > article { display: flex; min-height: 210px; flex-direction: column; padding: 26px; }
.demo-governance-grid h3 { margin: 7px 0 10px; font-size: 18px; }
.demo-governance-grid .muted { flex: 1; margin: 0 0 18px; line-height: 1.65; }
.case-governance-steps { display: flex; gap: 5px; margin-bottom: 17px; }
.case-governance-steps span { flex: 1; padding: 6px 5px; border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--muted-light); font-size: 10px; text-align: center; }
.case-governance-steps span.is-done { background: var(--sage-soft); color: var(--moss-dark); font-weight: 700; }
.governance-card__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
</style>
