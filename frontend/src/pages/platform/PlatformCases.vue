<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage, getPublicCases, setCaseVisibility, type PublicCase } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const cases = ref<PublicCase[]>([])
const error = ref('')
const busy = ref(false)
const feedback = ref<FeedbackState | null>(null)
const confirmCase = ref<PublicCase | null>(null)

async function load() { cases.value = (await getPublicCases()).data }
onMounted(() => load().catch((reason) => { feedback.value = makeFeedback('error', errorMessage(reason), '案例治理列表没有加载完成，可以重试。', '重试') }))
function ask(item: PublicCase) { confirmCase.value = item }
async function toggle() {
  if (!confirmCase.value) return
  const item = confirmCase.value; confirmCase.value = null; busy.value = true; feedback.value = null
  try { await setCaseVisibility(item.id, item.status !== 'published'); await load(); feedback.value = makeFeedback('success', item.status === 'published' ? '案例已下架。' : '案例已恢复公开。', '公开状态已同步到案例库。') }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '案例状态没有改变，可以重试。', '重试') }
  finally { busy.value = false }
}
</script>

<template><div class="page platform-page"><PageHeader eyebrow="内容治理" title="公开案例治理" description="平台只执行全局下架与恢复，不进入学校项目材料编辑和教师常规审核。" /><FeedbackBanner v-model="feedback" @action="load" /><p v-if="error" class="form-error">{{ error }}</p><section class="management-list case-governance"><article v-for="item in cases" :key="item.id"><span class="management-icon">{{ item.project_title.slice(0, 1) }}</span><div><small>{{ item.school_name }} · {{ item.discipline }}</small><h2>{{ item.project_title }}</h2><p>{{ item.public_summary }}</p></div><StatusTag :status="item.status === 'published' ? 'published' : 'offline'" /><button :class="item.status === 'published' ? 'return-button' : 'approve-button'" :disabled="busy" type="button" @click="ask(item)">{{ item.status === 'published' ? '下架' : '恢复' }}</button></article><EmptyState v-if="!cases.length" title="暂无公开案例" description="教师审核通过的公开案例会出现在这里。" /></section><ConfirmDialog v-if="confirmCase" :model-value="true" :title="confirmCase.status === 'published' ? '下架这个公开案例？' : '恢复这个公开案例？'" :description="confirmCase.status === 'published' ? '下架后师生将暂时无法检索该案例，平台仍保留治理记录。' : '恢复后案例会重新出现在全平台案例库。'" :confirm-text="confirmCase.status === 'published' ? '确认下架' : '确认恢复'" :danger="confirmCase.status === 'published'" @update:model-value="confirmCase = null" @confirm="toggle" /></div></template>
