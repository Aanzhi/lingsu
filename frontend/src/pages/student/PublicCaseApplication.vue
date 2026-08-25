<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { errorMessage, getMaterials, getProjects, getPublicCases, studentConsentPublicCase, type Material, type Project, type PublicCase } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import PublicCaseDialog from '../../components/PublicCaseDialog.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { publicCaseAction } from '../../stores/publicCaseModel'

const projects = ref<Project[]>([])
const route = useRoute()
const materials = ref<Material[]>([])
const applications = ref<PublicCase[]>([])
const error = ref('')
const loading = ref(false)
const feedback = ref<FeedbackState | null>(null)
const consentCase = ref<PublicCase | null>(null)
const selectedProject = ref<number | null>(null)
const selected = computed(() => projects.value.find((project) => project.id === selectedProject.value) ?? null)
const selectedApplication = computed(() => applications.value.find((item) => item.project === selectedProject.value) ?? null)
const approvedMaterials = computed(() => materials.value
  .filter((item) => item.project === selectedProject.value && item.status === 'approved')
  .map((item) => ({ id: item.id, title: item.title, reportSection: item.report_section })))
const action = computed(() => selected.value
  ? publicCaseAction({ projectStatus: selected.value.status, approvedMaterialCount: approvedMaterials.value.length, applicationStatus: selectedApplication.value?.status ?? null })
  : { enabled: false, label: '选择项目', reason: '请先选择一个项目。' })

async function load() {
  loading.value = true
  try {
    const [projectResponse, materialResponse, caseResponse] = await Promise.all([getProjects(), getMaterials(), getPublicCases()])
    projects.value = projectResponse.data
    materials.value = materialResponse.data
    applications.value = caseResponse.data.filter((item) => projectResponse.data.some((project) => project.id === item.project))
    const requestedProjectId = Number(route.query.projectId)
    selectedProject.value = projectResponse.data.some((item) => item.id === requestedProjectId)
      ? requestedProjectId
      : selectedProject.value && projectResponse.data.some((item) => item.id === selectedProject.value)
        ? selectedProject.value
        : projectResponse.data[0]?.id ?? null
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '公开申请列表没有加载完成，可以重试。', '重试')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => route.query.projectId, () => {
  feedback.value = null
  void load()
})

async function giveConsent() {
  if (!consentCase.value) return
  const target = consentCase.value
  consentCase.value = null
  try {
    await studentConsentPublicCase(target.id)
    feedback.value = makeFeedback('success', '已同意全平台展示。', '申请已进入平台审核，平台通过后才会公开。')
    await load()
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '同意状态没有改变，可以重试。', '重试') }
}

async function handleSubmitted() {
  await load()
  feedback.value = makeFeedback(
    'success',
    '公开申请已提交。',
    '主指导教师审核通过前，任何材料都不会对外展示。',
  )
}
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="成果" title="公开成果申请" description="查看校内展示申请和教师发起的全平台展示邀请，确认公开材料范围后再提交。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-if="loading" class="loading-state" role="status">正在读取公开申请…</p>
    <section v-if="!loading" class="demo-application-list paper-card">
      <article v-for="item in applications" :key="item.id" class="list-row"><div class="row-main"><div class="row-title">{{ item.project_title }}</div><div class="row-meta">{{ item.selected_materials.length }} 项公开材料<span v-if="item.status === 'rejected' && item.review_comment"> · 教师意见：{{ item.review_comment }}</span></div></div><div class="row-actions"><StatusTag :status="item.status === 'pending_teacher' ? 'pending_review' : item.status === 'offline' ? 'disabled' : item.status" /><button v-if="item.status === 'waiting_student'" class="primary-button" type="button" @click="consentCase = item">同意全平台展示</button></div></article>
      <EmptyState v-if="!applications.length" title="还没有公开申请" />
    </section>
    <section v-if="!loading && projects.length" class="paper-card demo-application-panel"><div><p class="eyebrow">从项目申请</p><h2>{{ action.label }}</h2><p class="muted">{{ action.reason || `当前有 ${approvedMaterials.length} 项已通过材料可选择。` }}</p></div><label>选择项目<select v-model="selectedProject"><option v-for="project in projects" :key="project.id" :value="project.id">{{ project.title }}</option></select></label><p v-if="selectedApplication?.status === 'rejected'" class="form-error">教师意见：{{ selectedApplication.review_comment }}</p><PublicCaseDialog v-if="selectedProject" :project-id="selectedProject" :materials="approvedMaterials" :application="selectedApplication" :enabled="action.enabled" :label="action.label" @submitted="handleSubmitted" /></section>
    <EmptyState v-else-if="!loading" title="暂无可申请项目" description="先创建项目并完成材料审核。" />
    <ConfirmDialog v-if="consentCase" :model-value="true" title="同意教师发起的全平台展示？" description="同意后，项目摘要和你选择的材料会提交给平台审核；平台通过前不会公开。" confirm-text="确认同意" @update:model-value="consentCase = null" @confirm="giveConsent" />
  </div>
</template>

<style scoped>
.demo-application-list { padding: 26px; }
.demo-application-list .list-row:first-child { border-top: 0; }
.demo-application-panel { display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, .55fr); gap: 20px; align-items: end; margin-top: 16px; padding: 26px; }
.demo-application-panel h2 { margin: 5px 0 7px; font-size: 20px; }
.demo-application-panel label { display: grid; gap: 7px; color: var(--muted); font-size: 12px; }
.demo-application-panel select { min-height: 38px; padding: 0 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); }
</style>
