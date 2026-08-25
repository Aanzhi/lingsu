<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download, MagicStick, User } from '@element-plus/icons-vue'
import { createReportExport, errorMessage, getReportExports, type ReportExport } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import JourneyDeliveryBoard, { type DeliveryItem } from '../../components/JourneyDeliveryBoard.vue'
import JourneyHero, { type JourneyKpi } from '../../components/JourneyHero.vue'
import JourneyTimeline, { type JourneyNode } from '../../components/JourneyTimeline.vue'
import PageHeader from '../../components/PageHeader.vue'
import ProjectLifecycleMenu from '../../components/ProjectLifecycleMenu.vue'
import StatusTag from '../../components/StatusTag.vue'
import MemberInvitationDialog from '../../components/MemberInvitationDialog.vue'
import { student } from '../../stores/student'
import { projectJourneySummary } from '../../stores/studentApiModel'
import { exportStatusLabel, shouldPollExport } from '../../stores/reportModel'
import { auth } from '../../stores/auth'
import { canInviteMember } from '../../stores/memberModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { studentProjectRoute, studentTaskRoute } from '../../stores/pageContracts'
import { projectTypeLabel } from '../../stores/presentationModel'

const route = useRoute(); const router = useRouter(); const error = ref(''); const feedback = ref<FeedbackState | null>(null); const exports = ref<ReportExport[]>([]); const exportBusy = ref(false); let pollTimer: number | undefined
const loading = ref(true)
const surface = computed(() => String(route.meta.surface ?? 'overview')); const projectId = computed(() => Number(route.params.id))
const project = computed(() => student.project(projectId.value))
const researchQuestionLocation = computed(() => ({
  path: '/student/ai',
  query: { projectId: String(projectId.value), researchQuestion: '1' },
}))
const tasks = computed(() => student.state.tasks.filter((item) => item.project === projectId.value).sort((a, b) => a.order - b.order))
const materials = computed(() => student.state.materials.filter((item) => item.project === projectId.value).sort((a, b) => a.report_order - b.report_order))
const reportSections = computed(() => materials.value.flatMap((material) => {
  const version = [...material.revisions].reverse().find((item) => item.status === 'approved')
  return version ? [{ material, version }] : []
}))
const typeLabel = computed(() => projectTypeLabel(project.value?.project_type))
const pageDescription = computed(() => {
  if (surface.value === 'map') return '按章节查看任务状态，打开具体任务后提交材料或查看审核意见。'
  if (surface.value === 'materials') return '按章节和状态查找已提交材料，需修订的内容可直接回到对应任务。'
  if (surface.value === 'report') return '根据已通过材料查看报告结构，满足条件后导出 Word 或 PDF。'
  return '查看项目问题、成员和当前进度，选择下一步进入研究旅程。'
})
const mayInvite = computed(() => project.value ? canInviteMember({ currentUserId: auth.user.value?.id, leaderId: project.value.leader, projectStatus: project.value.status, authorized: Boolean(auth.user.value?.authorized) }) : false)

// 研究旅程的唯一数据模型：先把任务和材料收敛成步骤，再按五个研究阶段聚合。
const journeySummary = computed(() => projectJourneySummary(tasks.value, materials.value))
const journeyChapters = computed(() => journeySummary.value.chapters)
const journeySteps = computed(() => journeyChapters.value.flatMap((chapter) => chapter.steps))
const currentChapter = computed(() => journeyChapters.value.find((chapter) => chapter.containsCurrent) ?? journeyChapters.value.at(-1) ?? null)
function chapterStatus(chapter: typeof journeyChapters.value[number]): 'completed' | 'current' | 'pending' | 'locked' {
  if (chapter.status === 'done') return 'completed'
  if (chapter.containsCurrent) return 'current'
  if (currentChapter.value && chapter.index > currentChapter.value.index) return 'locked'
  return 'pending'
}
const journeyNodes = computed<JourneyNode[]>(() => journeyChapters.value.map((chapter) => ({
  order: chapter.index,
  title: chapter.name,
  status: chapterStatus(chapter) === 'current' ? 'current' : chapterStatus(chapter) === 'completed' ? 'completed' : chapterStatus(chapter) === 'locked' ? 'locked' : 'pending',
  passed: chapter.done,
  total: chapter.total,
  hint: chapterStatus(chapter) === 'locked' ? '完成上一章并通过审核后解锁' : chapterStatus(chapter) === 'current' ? '当前章节：聚焦这一组任务' : undefined,
})))
const selectedStage = ref<number | null>(null)
watch(currentChapter, (chapter) => { if (selectedStage.value === null) selectedStage.value = chapter?.index ?? null }, { immediate: true })
watch(journeyNodes, (nodes) => {
  if (selectedStage.value === null || !nodes.some((node) => node.order === selectedStage.value)) selectedStage.value = currentChapter.value?.index ?? nodes[0]?.order ?? null
})
function selectStage(order: number) { selectedStage.value = order }
const selectedChapter = computed(() => journeyChapters.value.find((chapter) => chapter.index === selectedStage.value) ?? currentChapter.value)
function openTask(item: DeliveryItem) { void router.push(studentTaskRoute(projectId.value, item.taskId)) }
const expandedMaterialChapter = ref<number | null>(null)
const materialSearch = ref('')
type MaterialStatusFilter = 'all' | 'approved' | 'pending_review' | 'revision_required' | 'draft'
const materialChapterFilter = ref<number | 'all'>('all')
const materialStatusFilter = ref<MaterialStatusFilter>('all')
watch(currentChapter, (chapter) => {
  if (expandedMaterialChapter.value === null) expandedMaterialChapter.value = chapter?.index ?? null
})
function toggleMaterialChapter(order: number) {
  expandedMaterialChapter.value = expandedMaterialChapter.value === order ? null : order
}
function materialForStep(stepId: number) {
  return materials.value.find((item) => item.task === stepId)
}
function materialStatusForStep(step: typeof journeySteps.value[number]): MaterialStatusFilter | 'locked' {
  const material = materialForStep(step.id)
  if (material) {
    if (material.status === 'submitted') return 'pending_review'
    return material.status as MaterialStatusFilter | 'locked'
  }
  if (step.taskStatus === 'locked') return 'locked'
  if (step.taskStatus === 'revision_required') return 'revision_required'
  if (step.taskStatus === 'pending_review') return 'pending_review'
  if (step.taskStatus === 'approved' || step.taskStatus === 'completed') return 'approved'
  return 'draft'
}
const filteredJourneyChapters = computed(() => {
  const query = materialSearch.value.trim().toLowerCase()
  return journeyChapters.value
    .filter((chapter) => materialChapterFilter.value === 'all' || chapter.index === materialChapterFilter.value)
    .map((chapter) => ({
      ...chapter,
      steps: chapter.steps.filter((step) => {
        const haystack = [step.deliverable, step.title, step.reportSection].join(' ').toLowerCase()
        const matchesQuery = !query || haystack.includes(query)
        const status = materialStatusForStep(step)
        const matchesStatus = materialStatusFilter.value === 'all' || status === materialStatusFilter.value
        return matchesQuery && matchesStatus
      }),
    }))
    .filter((chapter) => chapter.steps.length)
})
watch(filteredJourneyChapters, (chapters) => {
  if (chapters.length && !chapters.some((chapter) => chapter.index === expandedMaterialChapter.value)) expandedMaterialChapter.value = chapters[0].index
}, { immediate: true })
function clearMaterialFilters() {
  materialSearch.value = ''
  materialChapterFilter.value = 'all'
  materialStatusFilter.value = 'all'
}

// 「本章推荐 AI 助手」入口：跳转思考室并预选当前查看的章节。
const recoStage = computed(() => selectedChapter.value?.index ?? currentChapter.value?.index)
const recoStageName = computed(() => selectedChapter.value?.name ?? '当前章节')

const journeyKpis = computed<JourneyKpi[]>(() => {
  const totalTasks = journeySteps.value.length
  const passedTasks = journeySteps.value.filter((step) => step.status === 'done').length
  const pending = journeySteps.value.filter((step) => step.status === 'active' || step.status === 'revision').length
  return [
    { label: '研究章节', value: journeyChapters.value.length, caption: '从任务聚合出的研究主线' },
    { label: '总任务', value: totalTasks, caption: '逐项可追踪的证据' },
    { label: '已通过', value: `${passedTasks} / ${totalTasks || 0}`, caption: '任务通过率' },
    { label: '待处理', value: pending, caption: `已交付 ${passedTasks} / ${totalTasks || 0}` },
  ]
})

interface DeliveryGroup {
  order: number
  title: string
  status: 'completed' | 'current' | 'pending' | 'locked'
  passed: number
  total: number
  items: DeliveryItem[]
}
const deliveryGroups = computed<DeliveryGroup[]>(() => journeyChapters.value.map((chapter) => {
  const status = chapterStatus(chapter)
  return {
    order: chapter.index,
    title: chapter.name,
    status,
    passed: chapter.done,
    total: chapter.total,
    items: chapter.steps.map((step) => ({
      id: `task-${step.id}`,
      taskId: step.id,
      title: step.title,
      description: step.description,
      materialLabel: step.deliverable,
      reportSection: step.reportSection,
      status: status === 'locked' ? 'locked' : step.status,
      xpReward: step.xpReward,
      stage: step.order,
    })),
  }
}))
async function handleSetPrimary() { try { await student.setPrimary(projectId.value); await student.refreshProject(projectId.value) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '主项目没有切换成功，可以重试。', '重试') } }
async function handleArchive() { if (!confirm('确定归档该项目？仅已完成项目可归档。')) return; try { await student.archive(projectId.value); router.replace('/student/projects?tab=archived') } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '归档失败，可以稍后重试。', '重试') } }
async function handleUnarchive() { try { await student.unarchive(projectId.value); await student.refreshProject(projectId.value) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '恢复失败，可以重试。', '重试') } }
async function handleTrash() { if (!confirm('确定将项目移入回收站？30 天后自动删除。')) return; try { await student.trash(projectId.value); router.replace('/student/projects?tab=trashed') } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '移入回收站失败，可以重试。', '重试') } }
async function handleRestore() { try { await student.restore(projectId.value); await student.refreshProject(projectId.value) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '恢复失败，可以重试。', '重试') } }
async function loadExports() {
  exports.value = (await getReportExports(projectId.value)).data
  window.clearTimeout(pollTimer)
  pollTimer = undefined
  if (exports.value.some((item) => shouldPollExport(item.status))) pollTimer = window.setTimeout(() => loadExports().catch(() => undefined), 1500)
}
async function load() {
  loading.value = true
  window.clearTimeout(pollTimer)
  pollTimer = undefined
  try {
    await student.refreshProject(projectId.value)
    if (surface.value === 'report') await loadExports()
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '项目数据没有加载完成，请重试。', '重试')
  } finally {
    loading.value = false
  }
}
async function queueExport(format: 'docx' | 'pdf') {
  if (!reportSections.value.length) {
    feedback.value = makeFeedback('info', '报告还没有已通过材料。', '至少有一项材料通过教师审核后，才能解锁正式导出。')
    return
  }
  exportBusy.value = true; feedback.value = null
  try { await createReportExport(projectId.value, format); await loadExports(); feedback.value = makeFeedback('success', `${format.toUpperCase()} 导出任务已排队。`, '生成完成后可以在本页历史记录下载。') }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '报告内容不会丢失，可以稍后重试。', '重试') }
  finally { exportBusy.value = false }
}
onMounted(load)
onBeforeUnmount(() => { window.clearTimeout(pollTimer) })
watch([projectId, surface], () => { void load() })
</script>
<template>
  <FeedbackBanner v-model="feedback" @action="load" />
  <p v-if="loading" class="loading-state" role="status">正在读取项目详情…</p>
  <div v-if="project && !loading" class="page project-detail-page">
    <PageHeader
      :eyebrow="surface === 'map' ? '研究旅程' : surface === 'materials' ? '材料档案' : surface === 'report' ? '研究报告' : typeLabel"
      :title="surface === 'materials' ? '材料档案' : surface === 'report' ? '研究报告' : project.title"
      :description="pageDescription"
    >
      <template #actions>
        <template v-if="surface === 'overview'">
          <ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" student-mode @primary="handleSetPrimary" @archive="handleArchive" @unarchive="handleUnarchive" @trash="handleTrash" @restore="handleRestore" />
          <StatusTag :status="project.status" />
        </template>
        <RouterLink v-else-if="surface === 'map'" class="secondary-button" :to="studentProjectRoute(project.id)">返回项目概览</RouterLink>
      </template>
    </PageHeader>

    <template v-if="surface === 'overview'">
      <div class="detail-layout demo-project-overview">
        <section class="paper-card demo-card-pad">
          <p class="eyebrow">项目问题</p><h2>{{ project.problem || '尚未确定研究问题' }}</h2>
          <RouterLink v-if="project.leader === auth.user.value?.id && auth.user.value?.authorized" class="text-link" :to="researchQuestionLocation">生成/完善研究问题 →</RouterLink>
          <div class="demo-rule" /><p class="eyebrow">初步方案</p><p class="muted">{{ project.plan || '确认研究问题后再补充初步方案。' }}</p>
          <div class="summary-line"><span>研究类型 <strong>{{ typeLabel }}</strong></span><span>整体进度 <strong>{{ journeySummary.summary.completed }} / {{ journeySummary.summary.total }} 章</strong></span><span>当前章节 <strong>{{ currentChapter?.name || '等待认领' }}</strong></span></div>
        </section>
        <aside class="paper-card demo-card-pad">
          <div class="section-heading"><div><p class="eyebrow">研究小组</p><h2>{{ project.members.length }} 位成员</h2></div><MemberInvitationDialog v-if="mayInvite" :project-id="project.id" /></div>
          <div class="demo-list"><div v-for="member in project.members" :key="member.id" class="demo-list-row"><span>{{ member.username }}</span><strong>{{ member.role === 'leader' ? '负责人' : '成员' }}</strong></div><div class="demo-list-row"><span>主指导教师</span><strong>{{ project.primary_teacher ? `教师 #${project.primary_teacher}` : '等待认领' }}</strong></div></div>
        </aside>
      </div>
      <div class="demo-journey-actions"><RouterLink class="primary-button" :to="studentProjectRoute(project.id, 'map')">进入研究旅程 →</RouterLink><RouterLink class="secondary-button" :to="studentProjectRoute(project.id, 'materials')">查看材料档案</RouterLink></div>
    </template>

    <template v-else-if="surface === 'map'">
      <section class="demo-journey-summary paper-card">
        <div class="summary-line"><span>研究类型 <strong>{{ typeLabel }}</strong></span><span>整体进度 <strong>{{ journeySummary.summary.percent }}%</strong></span><span>最近更新 <strong>今天</strong></span></div>
        <div class="demo-progress"><div class="progress-row"><span>研究进度</span><strong>{{ journeySummary.summary.completed }} / {{ journeySummary.summary.total }} 章节</strong></div><div class="progress-track"><i :style="{ width: `${journeySummary.summary.percent}%` }" /></div></div>
      </section>
      <div class="demo-section-head"><div><h2>研究章节</h2><p>点击章节查看任务和材料，不再重复展示全部节点</p></div></div>
      <section class="demo-chapter-accordion paper-card">
        <article v-for="chapter in journeyChapters" :key="chapter.index" class="demo-accordion-row" :class="[`is-${chapterStatus(chapter)}`, { 'is-open': selectedStage === chapter.index }]">
          <button type="button" class="demo-accordion-head" :aria-expanded="selectedStage === chapter.index" @click="selectedStage = selectedStage === chapter.index ? null : chapter.index">
            <span class="demo-accordion-number">{{ chapter.index }}</span><strong>{{ chapter.name }}</strong><small>{{ chapter.total }} 项任务 · {{ chapter.done }} 项已通过</small><span>⌄</span>
          </button>
          <div v-if="selectedStage === chapter.index" class="demo-accordion-body">
            <div v-for="step in chapter.steps" :key="step.id" class="demo-task-mini"><span>{{ step.title }}</span><StatusTag :status="step.taskStatus" /><RouterLink v-if="step.taskStatus !== 'locked'" class="text-link" :to="studentTaskRoute(project.id, step.id)">打开任务 →</RouterLink></div>
          </div>
        </article>
        <EmptyState v-if="!journeyChapters.length" title="等待教师认领" description="教师认领项目后，研究任务链会自动生成。" compact />
      </section>
      <div class="demo-journey-actions">
        <article class="paper-card demo-card-pad"><h2>下一步</h2><p class="muted">完成当前章节后，就可以继续进入下一项研究任务。</p><RouterLink v-if="currentChapter?.steps[0]" class="primary-button" :to="studentTaskRoute(project.id, currentChapter.steps[0].id)">继续当前任务 →</RouterLink></article>
        <article class="paper-card demo-card-pad"><h2>需要帮助？</h2><p class="muted">只针对当前章节提问，AI 会保留你的研究背景。</p><RouterLink class="secondary-button" :to="{ path: '/student/ai', query: { mode: 'research', projectId: String(project.id) } }">使用 AI 协助</RouterLink></article>
      </div>
    </template>

    <template v-else-if="surface === 'materials'">
      <section class="demo-material-archive paper-card">
        <div class="materials-filters" aria-label="材料筛选"><label class="materials-filter-search"><span class="sr-only">搜索材料</span><input v-model="materialSearch" type="search" placeholder="搜索材料名称" /></label><select v-model="materialChapterFilter"><option value="all">全部章节</option><option v-for="chapter in journeyChapters" :key="chapter.index" :value="chapter.index">{{ chapter.name }}</option></select><select v-model="materialStatusFilter"><option value="all">全部状态</option><option value="approved">已审核</option><option value="pending_review">已提交</option><option value="revision_required">需修订</option><option value="draft">未开始</option></select></div>
        <div v-for="chapter in filteredJourneyChapters" :key="chapter.index" class="demo-accordion-row" :class="[`is-${chapterStatus(chapter)}`, { 'is-open': expandedMaterialChapter === chapter.index }]">
          <button type="button" class="demo-accordion-head" :aria-expanded="expandedMaterialChapter === chapter.index" @click="toggleMaterialChapter(chapter.index)"><span class="demo-accordion-number">{{ chapter.index }}</span><strong>{{ chapter.name }}</strong><small>{{ chapter.done }} / {{ chapter.total }} 份材料</small><span>⌄</span></button>
          <div v-if="expandedMaterialChapter === chapter.index" class="demo-accordion-body"><div v-for="step in chapter.steps" :key="step.id" class="demo-task-mini"><span>{{ step.deliverable || step.title }}</span><StatusTag :status="materialForStep(step.id)?.status || 'disabled'" /><RouterLink v-if="materialForStep(step.id)?.task && ['revision_required', 'available'].includes(materialForStep(step.id)?.status ?? '')" class="text-link" :to="studentTaskRoute(project.id, materialForStep(step.id)!.task!)">去任务处理 →</RouterLink></div></div>
        </div>
        <EmptyState v-if="!filteredJourneyChapters.length" title="暂无材料" description="教师认领项目后会生成材料档案。" compact />
      </section>
    </template>

    <template v-else>
      <div class="demo-report-grid">
        <div class="demo-stack">
          <section class="paper-card demo-card-pad"><p class="eyebrow">当前状态</p><h2>还差 {{ Math.max(materials.length - reportSections.length, 0) }} 项材料</h2><p class="muted">完成并通过审核后，Word 和 PDF 导出会自动解锁。</p><div class="demo-progress"><div class="progress-row"><span>报告完成度</span><strong>{{ reportSections.length }} / {{ materials.length }}</strong></div><div class="progress-track"><i :style="{ width: `${Math.round(reportSections.length / Math.max(materials.length, 1) * 100)}%` }" /></div></div></section>
          <section class="paper-card demo-card-pad"><h2>报告章节</h2><div class="demo-list"><div v-for="chapter in journeyChapters.slice(0, 3)" :key="chapter.index" class="demo-list-row"><div><strong>{{ ['一、研究问题', '二、研究过程', '三、研究结论'][chapter.index - 1] || chapter.name }}</strong><small>{{ chapter.done ? `已完成 ${chapter.done} 项材料` : '等待材料通过审核' }}</small></div><StatusTag :status="chapter.done === chapter.total && chapter.total ? 'completed' : chapter.done ? 'active' : 'draft'" /></div></div></section>
        </div>
        <aside class="demo-stack">
          <section class="paper-card demo-card-pad"><h2>导出报告</h2><p class="muted">至少有一项材料通过审核后才能生成正式报告。</p><div class="demo-stack demo-export-actions"><button class="secondary-button" :disabled="exportBusy || !reportSections.length" type="button" @click="queueExport('docx')"><el-icon><Download /></el-icon> 导出 Word</button><button class="secondary-button" :disabled="exportBusy || !reportSections.length" type="button" @click="queueExport('pdf')">导出 PDF</button></div></section>
          <section v-if="exports.length" class="paper-card demo-card-pad"><h2>生成历史</h2><div class="demo-list"><div v-for="item in exports" :key="item.id" class="demo-list-row"><span>{{ item.format.toUpperCase() }} · {{ exportStatusLabel(item.status) }}</span><a v-if="item.download_url" class="text-link" :href="item.download_url">下载</a></div></div></section>
        </aside>
      </div>
    </template>
  </div>
  <EmptyState v-else-if="!loading" title="找不到项目" description="项目可能不存在，或不属于当前账号。" />
</template>

<style scoped>
.demo-card-pad { padding: var(--space-6); }
.demo-card-pad h2 { margin: 0 0 8px; color: var(--ink); font: 700 20px/1.25 var(--sans); letter-spacing: -.015em; }
.muted { color: var(--muted); }
.detail-layout { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(260px, .6fr); gap: var(--space-5); }
.demo-project-overview { align-items: start; }
.demo-rule { height: 1px; margin: 22px 0; background: var(--line); }
.summary-line { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 18px; color: var(--muted); font-size: 12px; }
.summary-line strong { color: var(--ink); }
.demo-list { display: grid; }
.demo-list-row { display: flex; min-width: 0; align-items: center; justify-content: space-between; gap: var(--space-4); padding: 15px 0; border-bottom: 1px solid var(--line); }
.demo-list-row:first-child { padding-top: 0; }
.demo-list-row:last-child { padding-bottom: 0; border-bottom: 0; }
.demo-list-row > div { min-width: 0; display: grid; gap: 3px; }
.demo-list-row small { color: var(--muted-light); font-size: 12px; }
.demo-journey-summary { padding: var(--space-6); }
.demo-progress { margin-top: 18px; }
.progress-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 7px; color: var(--muted); font-size: 12px; }
.progress-row strong { color: var(--ink); }
.progress-track { height: 7px; overflow: hidden; border-radius: 999px; background: var(--paper-muted); }
.progress-track i { display: block; height: 100%; border-radius: inherit; background: var(--moss); }
.demo-section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--space-4); margin: var(--space-7) 0 var(--space-4); }
.demo-section-head h2 { margin: 0; color: var(--ink); font: 700 20px/1.25 var(--sans); }
.demo-section-head p { margin: 4px 0 0; color: var(--muted-light); font-size: 12px; }
.demo-chapter-accordion, .demo-material-archive { overflow: hidden; padding: var(--space-6); }
.demo-accordion-row { border-bottom: 1px solid var(--line); }
.demo-accordion-row:last-child { border-bottom: 0; }
.demo-accordion-head { display: flex; width: 100%; align-items: center; gap: 12px; padding: 16px 0; border: 0; background: transparent; color: var(--ink); text-align: left; }
.demo-accordion-head > strong { flex: 1; font-size: 14px; }
.demo-accordion-head > small { color: var(--muted-light); font-size: 12px; }
.demo-accordion-head > span:last-child { color: var(--muted-light); transition: transform .16s ease; }
.demo-accordion-row.is-open .demo-accordion-head > span:last-child { transform: rotate(180deg); }
.demo-accordion-number { display: grid; width: 30px; height: 30px; flex: 0 0 auto; place-items: center; border-radius: 50%; background: var(--paper-muted); color: var(--muted); font-size: 12px; font-weight: 700; }
.demo-accordion-row.is-completed .demo-accordion-number { color: var(--success); background: var(--success-soft); }
.demo-accordion-row.is-current .demo-accordion-number { color: #fff; background: var(--moss); }
.demo-accordion-body { padding: 0 0 14px 42px; }
.demo-task-mini { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: 10px; padding: 10px 12px; border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--muted); font-size: 12px; }
.demo-task-mini + .demo-task-mini { margin-top: 7px; }
.demo-journey-actions { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-4); margin-top: var(--space-4); }
.demo-journey-actions > .primary-button, .demo-journey-actions > .secondary-button { justify-self: start; }
.demo-material-archive .materials-filters { margin: 0 0 var(--space-5); }
.demo-report-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-4); align-items: start; }
.demo-stack { display: grid; align-content: start; gap: var(--space-4); }
.demo-export-actions { margin-top: 18px; }
.demo-export-actions .secondary-button { width: 100%; }
.journey-rail-block { margin-top: 22px; }
.journey-delivery-block { margin-top: 22px; }
.consistency-block { margin-bottom: 22px; }
.overview-chapters { grid-column: 1 / -1; padding: 22px 24px; }
.overview-chapters .section-heading > div > p:last-child { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
.overview-chapter-list { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; list-style: none; margin: 18px 0 0; padding: 0; }
.overview-chapter-list li { display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 9px; align-items: start; min-width: 0; padding: 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); }
.overview-chapter-list li > .status-tag { grid-column: 2; justify-self: start; margin-top: 8px; }
.overview-chapter-list__index { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--moss); color: #fff; font: 700 11px var(--sans); }
.overview-chapter-list li.is-current { border-color: var(--sage-line); background: var(--sage-soft); }
.overview-chapter-list li.is-current .overview-chapter-list__index { background: #fff; color: var(--moss-dark); box-shadow: 0 0 0 1px var(--moss); }
.overview-chapter-list li.is-locked .overview-chapter-list__index { background: var(--line-dark); color: var(--muted); }
.overview-chapter-list__body { min-width: 0; display: grid; gap: 5px; }
.overview-chapter-list__body strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 700 13px/1.35 var(--sans); }
.overview-chapter-list__body small { color: var(--muted); font-size: 10px; }
.overview-chapter-list .mini-progress { height: 5px; }
.materials-chapters { display: grid; gap: 8px; margin-top: 18px; }
.materials-filters { display: grid; grid-template-columns: minmax(220px, 1fr) 190px 150px auto; gap: 8px; align-items: center; margin-top: 18px; }
.materials-filter-search input, .materials-filters select { width: 100%; min-height: 36px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); background: var(--paper); color: var(--ink); font: inherit; font-size: 12px; padding: 0 11px; }
.materials-filter-search input:focus, .materials-filters select:focus { outline: 2px solid rgba(76,114,69,.22); outline-offset: 1px; border-color: var(--moss); }
.materials-filter-clear { justify-self: end; border: 0; background: transparent; cursor: pointer; padding: 4px 0; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
.materials-chapter { overflow: hidden; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); }
.materials-chapter.is-current { border-color: var(--sage-line); }
.materials-chapter.is-locked { background: var(--paper-soft); }
.materials-chapter__toggle { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto auto 48px; align-items: center; gap: 12px; width: 100%; padding: 13px 14px; border: 0; background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
.materials-chapter__toggle:hover, .materials-chapter__toggle:focus-visible { background: var(--paper-soft); }
.materials-chapter__index { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--moss); color: #fff; font: 700 11px var(--sans); }
.materials-chapter.is-current .materials-chapter__index { background: #fff; color: var(--moss-dark); box-shadow: 0 0 0 1px var(--moss); }
.materials-chapter.is-locked .materials-chapter__index { background: var(--line-dark); color: var(--muted); }
.materials-chapter__title { display: grid; gap: 2px; min-width: 0; }
.materials-chapter__title small { color: var(--moss); font-size: 10px; font-weight: 700; }
.materials-chapter__title strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 700 14px/1.35 var(--sans); }
.materials-chapter__summary { color: var(--muted); font-size: 11px; white-space: nowrap; }
.materials-chapter__chevron { color: var(--moss-dark); font-size: 11px; font-weight: 700; text-align: right; }
.materials-chapter__body { border-top: 1px solid var(--line); }
.materials-archive-row { display: grid; grid-template-columns: 40px minmax(0, 1fr) auto auto; gap: 12px; align-items: center; padding: 13px 14px; border-bottom: 1px dashed var(--line); }
.materials-archive-row:last-child { border-bottom: 0; }
.materials-archive-row__main { display: grid; gap: 3px; min-width: 0; }
.materials-archive-row__main strong { overflow-wrap: anywhere; font-size: 12px; }
.materials-archive-row__main small { overflow: hidden; color: var(--muted); text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.materials-archive-row > a { color: var(--moss-dark); font-size: 11px; font-weight: 700; white-space: nowrap; }
.report-public-link { display: block; margin-top: 14px; }
.ai-reco-cta { display: flex; align-items: center; gap: 12px; margin-top: 18px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 12px; background: var(--paper); text-decoration: none; color: var(--ink); transition: border-color .15s, box-shadow .15s; }
.ai-reco-cta:hover { border-color: var(--moss); box-shadow: var(--shadow-soft); }
.ai-reco-icon { font-size: 20px; color: var(--moss); flex: none; }
.ai-reco-text { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.ai-reco-text strong { font-size: 14px; color: var(--moss-dark); }
.ai-reco-text small { font-size: 12px; color: var(--muted); line-height: 1.5; }
.ai-reco-go { font-size: 13px; color: var(--moss-dark); white-space: nowrap; }
.research-question-cta { display: inline-flex; margin: 4px 0 8px; color: var(--moss-dark); font-size: 12px; font-weight: 700; text-decoration: none; }
.research-question-cta:hover { color: var(--moss); text-decoration: underline; }
@media (max-width: 1024px) {
  .overview-chapter-list { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 768px) {
  .overview-chapters { padding: 18px 16px; }
  .overview-chapter-list { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .materials-table { padding: 20px 16px; }
  .materials-filters { grid-template-columns: 1fr 1fr; }
  .materials-filter-search { grid-column: 1 / -1; }
  .materials-filter-clear { justify-self: start; }
  .materials-chapter__toggle { grid-template-columns: 32px minmax(0, 1fr) auto 42px; gap: 9px; }
  .materials-chapter__summary { grid-column: 2; justify-self: start; }
  .materials-chapter__toggle > .status-tag { grid-column: 3; grid-row: 1 / span 2; }
  .materials-chapter__chevron { grid-column: 4; grid-row: 1 / span 2; }
  .materials-archive-row { grid-template-columns: 34px minmax(0, 1fr) auto; gap: 8px; }
  .materials-archive-row > .status-tag { grid-column: 2; justify-self: start; }
  .materials-archive-row > a, .materials-archive-row > .archive-read-only { grid-column: 3; grid-row: 2; }
  .ai-reco-cta { align-items: flex-start; }
  .ai-reco-go { margin-left: auto; }
}
@media (max-width: 430px) {
  .overview-chapter-list { grid-template-columns: 1fr; }
  .overview-chapter-list li { grid-template-columns: 30px minmax(0, 1fr) auto; }
  .overview-chapter-list li > .status-tag { grid-column: 3; grid-row: 1; margin-top: 0; }
  .materials-chapter__summary { font-size: 10px; }
  .materials-filters { grid-template-columns: 1fr; }
  .materials-filter-search { grid-column: auto; }
  .materials-archive-row__main small { white-space: normal; }
  .ai-reco-cta { flex-wrap: wrap; }
  .ai-reco-text { flex-basis: calc(100% - 32px); }
  .ai-reco-go { margin-left: 32px; }
}
</style>
