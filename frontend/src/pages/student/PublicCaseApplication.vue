<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { errorMessage, getMaterials, getProjects, getPublicCases, type Material, type Project, type PublicCase } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import PublicCaseDialog from '../../components/PublicCaseDialog.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { publicCaseAction } from '../../stores/publicCaseModel'

const projects = ref<Project[]>([])
const materials = ref<Material[]>([])
const applications = ref<PublicCase[]>([])
const error = ref('')
const feedback = ref<FeedbackState | null>(null)
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
  try {
    const [projectResponse, materialResponse, caseResponse] = await Promise.all([getProjects(), getMaterials(), getPublicCases()])
    projects.value = projectResponse.data
    materials.value = materialResponse.data
    applications.value = caseResponse.data.filter((item) => projectResponse.data.some((project) => project.id === item.project))
    selectedProject.value = selectedProject.value && projectResponse.data.some((item) => item.id === selectedProject.value) ? selectedProject.value : projectResponse.data[0]?.id ?? null
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '公开申请列表没有加载完成，可以重试。', '重试')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="案例公开" title="申请展示项目成果" description="仅选择已通过且适合对外展示的材料；未选择的附件、源代码和过程数据不会公开。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="error" class="form-error">{{ error }}</p>
    <section v-if="projects.length" class="paper-card overview-paper">
      <label>选择项目<select v-model="selectedProject"><option v-for="project in projects" :key="project.id" :value="project.id">{{ project.title }}</option></select></label>
      <div class="section-heading"><div><p class="eyebrow">公开准备度</p><h2>{{ action.label }}</h2><p>{{ action.reason || `当前有 ${approvedMaterials.length} 项已通过材料可选择。` }}</p></div><StatusTag v-if="selectedApplication" :status="selectedApplication.status === 'pending_teacher' ? 'pending_review' : selectedApplication.status === 'offline' ? 'disabled' : selectedApplication.status" /></div>
      <p v-if="selectedApplication?.status === 'rejected'" class="form-error">教师意见：{{ selectedApplication.review_comment }}</p>
      <PublicCaseDialog v-if="selectedProject" :project-id="selectedProject" :materials="approvedMaterials" :application="selectedApplication" :enabled="action.enabled" :label="action.label" @submitted="load" />
    </section>
    <EmptyState v-else title="暂无可申请项目" description="先创建项目并完成材料审核。" />
    <section class="materials-table paper-card"><div class="section-heading"><div><p class="eyebrow">申请历史</p><h2>公开状态</h2></div></div><div v-for="item in applications" :key="item.id" class="material-row"><span class="file-glyph">{{ item.project_title.slice(0, 1) }}</span><div><strong>{{ item.project_title }}</strong><small>{{ item.selected_materials.length }} 项公开材料</small><small v-if="item.status === 'rejected' && item.review_comment" class="form-error">教师意见：{{ item.review_comment }}</small></div><StatusTag :status="item.status === 'pending_teacher' ? 'pending_review' : item.status === 'offline' ? 'disabled' : item.status" /></div><EmptyState v-if="!applications.length" title="还没有公开申请" /></section>
  </div>
</template>
