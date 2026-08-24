<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { User } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

import { errorMessage, type ProjectTask } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { projectJourneySummary, type ApiTask } from '../../stores/studentApiModel'
import { projectRiskLabel, projectTaskSummary } from '../../stores/teacherProjectModel'
import { projectTypeLabel } from '../../stores/presentationModel'
import { teacherStore } from '../../stores/teacher'

const route = useRoute()
const feedback = ref<FeedbackState | null>(null)
const loading = ref(true)
const projectId = computed(() => Number(route.params.id))
const project = computed(() => teacherStore.state.guided.find((item) => item.id === projectId.value)
  ?? teacherStore.state.archived.find((item) => item.id === projectId.value)
  ?? teacherStore.state.trashed.find((item) => item.id === projectId.value))
const tasks = computed(() => teacherStore.state.detail.projectId === projectId.value ? teacherStore.state.detail.tasks : [])
function compatTaskStatus(task: ProjectTask) {
  if (task.legacy_status === 'locked') return 'locked'
  return task.status === 'in_progress' ? 'available' : task.status
}
const legacyTasks = computed<ApiTask[]>(() => tasks.value.map((task) => ({ ...task, status: compatTaskStatus(task) })))
const materials = computed(() => teacherStore.state.detail.projectId === projectId.value ? teacherStore.state.detail.materials : [])
const summary = computed(() => projectTaskSummary(legacyTasks.value))
const risk = computed(() => projectRiskLabel(legacyTasks.value, materials.value))
const journey = computed(() => projectJourneySummary(legacyTasks.value, materials.value))
const chapters = computed(() => journey.value.chapters)
const currentChapter = computed(() => chapters.value.find((chapter) => chapter.containsCurrent) ?? chapters.value.find((chapter) => chapter.status === 'active') ?? chapters.value[0] ?? null)
const expandedChapter = ref<number | null>(null)

watch(currentChapter, (chapter) => {
  if (expandedChapter.value === null) expandedChapter.value = chapter?.index ?? null
}, { immediate: true })

function chapterStatus(chapter: typeof chapters.value[number]) {
  if (chapter.status === 'done') return 'completed'
  if (chapter.containsCurrent || chapter.status === 'active') return 'current'
  if (currentChapter.value && chapter.index > currentChapter.value.index) return 'locked'
  return 'pending'
}
function toggleChapter(order: number) { expandedChapter.value = expandedChapter.value === order ? null : order }
function materialForStep(stepId: number) { return materials.value.find((item) => item.task === stepId) }
function latestSubmittedRevision(stepId: number) {
  return materialForStep(stepId)?.revisions.at(-1)?.status === 'submitted' ? materialForStep(stepId)?.revisions.at(-1) : null
}
function materialActionLabel(stepId: number) {
  const material = materialForStep(stepId)
  if (latestSubmittedRevision(stepId)) return '开始审核 →'
  if (material?.status === 'approved') return '已通过'
  if (material?.status === 'revision_required') return '等待学生修订'
  return '暂无待审'
}

async function load() {
  loading.value = true
  try {
    await Promise.all([teacherStore.load(), teacherStore.loadArchived(), teacherStore.loadTrashed()])
    await teacherStore.loadProjectDetail(projectId.value)
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '项目详情没有加载完成，可以重试。', '重试')
  } finally {
    loading.value = false
  }
}
onMounted(load)
watch(projectId, load)
</script>

<template>
  <p v-if="loading" class="loading-state" role="status">正在读取指导项目详情…</p>
  <div v-if="project && !loading" class="page teacher-project-detail-page">
    <PageHeader eyebrow="指导项目" :title="project.title" :description="`${project.members[0]?.username || '负责人待定'} · ${projectTypeLabel(project.project_type)} · ${project.members.length} 名成员`">
      <template #actions>
        <RouterLink class="secondary-button" :to="`/teacher/projects/${project.id}/template`">配置材料范本</RouterLink>
      </template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="load" />

    <div class="demo-teacher-detail-layout">
      <div class="demo-teacher-detail-main">
        <section class="paper-card demo-project-summary"><p class="eyebrow">项目摘要</p><h2>{{ project.problem || '未填写研究问题' }}</h2><p class="muted">{{ project.plan || '学生尚未填写初步方案。' }}</p><div class="demo-summary-line"><span>负责人 <strong>{{ project.members[0]?.username || '待定' }}</strong></span><span>成员 <strong>{{ project.members.length }} 人</strong></span><span>完成度 <strong>{{ journey.summary.completed }} / {{ journey.summary.total }} 章</strong></span></div></section>
        <section class="demo-teacher-chapters paper-card"><div class="demo-section-head"><div><h2>研究章节</h2><p>在章节内处理任务与材料，避免重复列表</p></div><StatusTag :status="risk === '当前没有待处理风险' ? 'active' : 'pending_review'" /></div>
          <div class="demo-chapter-list"><article v-for="chapter in chapters" :key="chapter.index" class="demo-chapter-row" :class="{ 'is-open': expandedChapter === chapter.index }"><button type="button" :aria-expanded="expandedChapter === chapter.index" :aria-controls="`teacher-chapter-${chapter.index}`" @click="toggleChapter(chapter.index)"><span class="demo-chapter-index">{{ chapter.index }}</span><strong>{{ chapter.name }}</strong><span>{{ chapter.total }} 项任务 · {{ chapter.done }} 项已通过</span><span>⌄</span></button><div v-if="expandedChapter === chapter.index" :id="`teacher-chapter-${chapter.index}`" class="demo-chapter-body"><div v-for="step in chapter.steps" :key="step.id" class="demo-task-mini"><span>{{ step.title }}</span><StatusTag :status="materialForStep(step.id)?.status || step.taskStatus" /><RouterLink v-if="latestSubmittedRevision(step.id)" class="text-link" :to="`/teacher/reviews/${latestSubmittedRevision(step.id)?.id}`">开始审核 →</RouterLink></div></div></article></div>
          <EmptyState v-if="!chapters.length" title="暂无研究任务" description="项目材料尚未生成，学生提交后会在这里形成指导章节。" compact />
        </section>
      </div>
      <aside class="demo-teacher-detail-aside"><section class="paper-card"><h2>指导动作</h2><div class="demo-action-stack"><RouterLink class="primary-button" to="/teacher/reviews">AI 预审材料</RouterLink><RouterLink class="secondary-button" to="/teacher/reviews">审核待提交材料</RouterLink><RouterLink class="secondary-button" :to="`/teacher/projects/${project.id}/template`">配置材料范本</RouterLink><RouterLink class="secondary-button" to="/teacher/members">查看成员</RouterLink></div></section><section class="paper-card"><h2>指导提醒</h2><div class="callout"><strong>{{ risk }}</strong><span>{{ summary.needsReview ? `当前有 ${summary.needsReview} 项材料需要处理，建议优先查看最早提交的版本。` : '当前没有需要教师立即介入的风险。' }}</span></div></section></aside>
    </div>
  </div>
  <EmptyState v-else-if="!loading" title="找不到指导项目" description="项目可能已经被移除，或不属于当前教师。"><RouterLink class="secondary-button" to="/teacher/projects">返回指导项目</RouterLink></EmptyState>
</template>

<style scoped>
.demo-teacher-detail-layout { display: grid; grid-template-columns: minmax(0, 1fr) 270px; gap: 20px; align-items: start; }
.demo-teacher-detail-main, .demo-teacher-detail-aside { display: grid; gap: 16px; }
.demo-project-summary, .demo-teacher-chapters, .demo-teacher-detail-aside > .paper-card { padding: 26px; }
.demo-project-summary h2 { margin: 6px 0 8px; font-size: 21px; }
.demo-summary-line { display: flex; flex-wrap: wrap; gap: 28px; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--line); color: var(--muted); font-size: 12px; }
.demo-summary-line strong { margin-left: 4px; color: var(--ink); }
.demo-section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
.demo-section-head h2, .demo-teacher-detail-aside h2 { margin: 0 0 4px; font-size: 20px; }
.demo-section-head p { margin: 0; color: var(--muted); font-size: 12px; }
.demo-chapter-list { display: grid; }
.demo-chapter-row { border-top: 1px solid var(--line); }
.demo-chapter-row:first-child { border-top: 0; }
.demo-chapter-row > button { display: grid; width: 100%; grid-template-columns: 30px minmax(0, 1fr) auto 18px; align-items: center; gap: 12px; padding: 13px 0; border: 0; background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
.demo-chapter-row > button > span:nth-child(3) { color: var(--muted); font-size: 11px; }
.demo-chapter-index { display: grid; width: 26px; height: 26px; place-items: center; border-radius: 50%; background: var(--paper-soft); color: var(--muted); font-size: 11px; font-weight: 700; }
.demo-chapter-row.is-open .demo-chapter-index { background: var(--moss); color: white; }
.demo-chapter-body { padding: 0 0 8px 42px; }
.demo-task-mini { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: 12px; min-height: 38px; border-top: 1px dashed var(--line); font-size: 12px; }
.demo-action-stack { display: grid; gap: 9px; margin-top: 16px; }
.demo-action-stack > * { justify-content: center; width: 100%; box-sizing: border-box; }
.demo-teacher-detail-aside .callout { display: grid; gap: 7px; }
.demo-teacher-detail-aside .callout span { color: var(--muted); font-size: 12px; line-height: 1.6; }
.teacher-project-summary__copy { min-width: 0; }
.teacher-project-summary__copy h2 { overflow-wrap: anywhere; }
.teacher-chapters-panel { min-width: 0; }
.teacher-chapters-panel .section-heading p:last-child { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
.teacher-chapters { display: grid; gap: 8px; margin-top: 18px; }
.teacher-chapter { overflow: hidden; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); }
.teacher-chapter.is-current { border-color: var(--sage-line); }
.teacher-chapter.is-locked { background: var(--paper-soft); }
.teacher-chapter__toggle { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto auto 48px; align-items: center; gap: 12px; width: 100%; padding: 13px 14px; border: 0; background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
.teacher-chapter__toggle:hover, .teacher-chapter__toggle:focus-visible { background: var(--paper-soft); }
.teacher-chapter__index { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--moss); color: #fff; font: 700 11px var(--sans); }
.teacher-chapter.is-current .teacher-chapter__index { background: #fff; color: var(--moss-dark); box-shadow: 0 0 0 1px var(--moss); }
.teacher-chapter.is-locked .teacher-chapter__index { background: var(--line-dark); color: var(--muted); }
.teacher-chapter__title { display: grid; gap: 2px; min-width: 0; }
.teacher-chapter__title small { color: var(--moss); font-size: 10px; font-weight: 700; }
.teacher-chapter__title strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 700 14px/1.35 var(--sans); }
.teacher-chapter__summary { color: var(--muted); font-size: 11px; white-space: nowrap; }
.teacher-chapter__chevron { color: var(--moss-dark); font-size: 11px; font-weight: 700; text-align: right; }
.teacher-chapter__body { border-top: 1px solid var(--line); }
.teacher-chapter__columns, .teacher-task-row { display: grid; grid-template-columns: minmax(0, 1.7fr) 86px 70px 86px; gap: 12px; align-items: center; }
.teacher-chapter__columns { padding: 9px 14px; background: var(--paper-soft); color: var(--muted); font-size: 10px; font-weight: 700; }
.teacher-task-row { min-width: 0; padding: 12px 14px; border-bottom: 1px dashed var(--line); font-size: 11px; }
.teacher-task-row:last-child { border-bottom: 0; }
.teacher-task-row__main { display: grid; gap: 3px; min-width: 0; }
.teacher-task-row__main strong { overflow-wrap: anywhere; font-size: 12px; }
.teacher-task-row__main small { overflow: hidden; color: var(--muted); text-overflow: ellipsis; white-space: nowrap; }
.teacher-task-row__version { color: var(--muted); white-space: nowrap; }
.teacher-task-row > a { white-space: nowrap; }
@media (max-width: 900px) {
  .teacher-chapter__toggle { grid-template-columns: 32px minmax(0, 1fr) auto 42px; gap: 9px; }
  .teacher-chapter__summary { grid-column: 2; justify-self: start; }
  .teacher-chapter__toggle > .status-tag { grid-column: 3; grid-row: 1 / span 2; }
  .teacher-chapter__chevron { grid-column: 4; grid-row: 1 / span 2; }
  .teacher-chapter__columns { display: none; }
  .teacher-task-row { grid-template-columns: minmax(0, 1fr) auto; gap: 8px 12px; }
  .teacher-task-row__main { grid-column: 1 / -1; }
  .teacher-task-row > .status-tag { justify-self: start; }
  .teacher-task-row__version { justify-self: end; }
  .teacher-task-row > a, .teacher-task-row > .archive-read-only { justify-self: end; }
}
@media (max-width: 430px) {
  .teacher-task-row__main small { white-space: normal; }
}
</style>
