<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download } from '@element-plus/icons-vue'
import { createReportExport, errorMessage, getReportExports, type ReportExport } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
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
const surface = computed(() => String(route.meta.surface ?? 'map')); const projectId = computed(() => Number(route.params.id))
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
  if (surface.value === 'map') return '按章节推进任务，打开具体任务提交材料并查看审核意见。'
  if (surface.value === 'report') return '根据已通过材料查看报告结构，满足条件后导出 Word 或 PDF。'
  return '查看项目问题、成员和当前进度。'
})
const mayInvite = computed(() => project.value ? canInviteMember({ currentUserId: auth.user.value?.id, leaderId: project.value.leader, projectStatus: project.value.status, authorized: Boolean(auth.user.value?.authorized) }) : false)

// 研究旅程的唯一数据模型：先把任务和材料收敛成步骤，再按五个研究阶段聚合。
const journeySummary = computed(() => projectJourneySummary(tasks.value, materials.value))
const journeyChapters = computed(() => journeySummary.value.chapters)
const journeySteps = computed(() => journeyChapters.value.flatMap((chapter) => chapter.steps))
const currentChapter = computed(() => journeyChapters.value.find((chapter) => chapter.containsCurrent) ?? journeyChapters.value.at(-1) ?? null)
const currentStep = computed(() => journeySteps.value.find((step) => step.isCurrent) ?? null)
const researchAILocation = computed(() => ({
  path: '/student/ai',
  query: {
    mode: 'research',
    projectId: String(projectId.value),
    ...(currentStep.value ? { taskId: String(currentStep.value.id) } : {}),
  },
}))
function chapterStatus(chapter: typeof journeyChapters.value[number]): 'completed' | 'current' | 'pending' | 'locked' {
  if (chapter.status === 'done') return 'completed'
  if (chapter.containsCurrent) return 'current'
  if (currentChapter.value && chapter.index > currentChapter.value.index) return 'locked'
  return 'pending'
}
const selectedStage = ref<number | null>(null)
watch(currentChapter, (chapter) => { if (selectedStage.value === null) selectedStage.value = chapter?.index ?? null }, { immediate: true })
watch(journeyChapters, (chapters) => {
  if (selectedStage.value === null || !chapters.some((chapter) => chapter.index === selectedStage.value)) selectedStage.value = currentChapter.value?.index ?? chapters[0]?.index ?? null
})
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
    await student.loadProjectShell()
    // Paint the project shell as soon as the project list is available, then
    // hydrate the slower task/material resources without hiding the shell.
    loading.value = false
    if (!project.value) return
    await student.loadProjectResources(projectId.value)
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
  <div class="page project-detail-page">
    <PageHeader
      :eyebrow="surface === 'map' ? '研究进程' : '研究报告'"
      :title="surface === 'report' ? '研究报告' : project?.title || (loading ? '正在读取项目' : '找不到项目')"
      :description="pageDescription"
    >
      <template #actions>
        <template v-if="project && surface === 'map'">
          <RouterLink class="secondary-button" :to="studentProjectRoute(project.id, 'report')">研究报告</RouterLink>
          <MemberInvitationDialog v-if="mayInvite" :project-id="project.id" />
          <ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" student-mode @primary="handleSetPrimary" @archive="handleArchive" @unarchive="handleUnarchive" @trash="handleTrash" @restore="handleRestore" />
          <StatusTag :status="project.status" />
        </template>
        <RouterLink v-else-if="project && surface === 'report'" class="secondary-button" :to="studentProjectRoute(project.id, 'map')">返回研究进程</RouterLink>
      </template>
    </PageHeader>

    <section v-if="loading && !project" class="project-detail-skeleton" role="status" aria-label="正在读取项目详情">
      <div class="project-detail-skeleton__overview"><i /><strong /><span /><span /><b /></div>
      <div class="project-detail-skeleton__workspace"><i /><i /></div>
    </section>

    <template v-else-if="project && surface === 'map'">
      <section class="journey-overview paper-card">
        <div class="journey-overview__project">
          <p class="eyebrow">项目问题</p>
          <h2>{{ project.problem || '尚未确定研究问题' }}</h2>
          <RouterLink v-if="project.leader === auth.user.value?.id && auth.user.value?.authorized" class="text-link" :to="researchQuestionLocation">生成/完善研究问题 →</RouterLink>
          <p class="journey-overview__plan"><span>初步方案</span>{{ project.plan || '确认研究问题后再补充初步方案。' }}</p>
        </div>
        <div class="journey-overview__progress">
          <div class="journey-overview__progress-heading"><div><p class="eyebrow">研究进程</p><strong>{{ journeySummary.summary.percent }}%</strong></div><span>{{ journeySummary.summary.completed }} / {{ journeySummary.summary.total }} 章节已通过</span></div>
          <div class="progress-track" aria-label="研究进度"><i :style="{ width: `${journeySummary.summary.percent}%` }" /></div>
          <div class="journey-overview__facts">
            <span><small>研究类型</small><strong>{{ typeLabel }}</strong></span>
            <span><small>研究小组</small><strong>{{ project.members.length }} 位成员</strong></span>
            <span><small>指导教师</small><strong>{{ project.primary_teacher_name || (project.primary_teacher ? '已分配' : '等待认领') }}</strong></span>
            <span><small>最近更新</small><strong>今天</strong></span>
          </div>
        </div>
      </section>

      <div class="journey-workspace">
        <section class="journey-chapters paper-card">
          <div class="journey-chapters__heading"><div><p class="eyebrow">研究路径</p><h2>研究章节</h2><p>打开章节查看任务、材料状态和审核意见。</p></div><span>{{ journeySteps.length }} 项任务</span></div>
          <section class="demo-chapter-accordion paper-card">
            <article v-for="chapter in journeyChapters" :key="chapter.index" class="demo-accordion-row" :class="[`is-${chapterStatus(chapter)}`, { 'is-open': selectedStage === chapter.index }]">
              <button type="button" class="demo-accordion-head" :aria-expanded="selectedStage === chapter.index" @click="selectedStage = selectedStage === chapter.index ? null : chapter.index">
                <span class="demo-accordion-number">{{ chapter.index }}</span><strong>{{ chapter.name }}</strong><small>{{ chapter.total }} 项任务 · {{ chapter.done }} 项已通过</small><span>⌄</span>
              </button>
              <div v-if="selectedStage === chapter.index" class="demo-accordion-body">
                <div v-for="step in chapter.steps" :key="step.id" class="demo-task-mini">
                  <div class="demo-task-mini__main"><strong>{{ step.title }}</strong><small>{{ step.deliverable || '完成任务后提交对应材料' }}</small></div>
                  <StatusTag :status="step.taskStatus" />
                  <RouterLink v-if="step.taskStatus !== 'locked'" class="text-link" :to="studentTaskRoute(project.id, step.id)">打开任务 →</RouterLink>
                </div>
              </div>
            </article>
            <EmptyState v-if="!journeyChapters.length" title="等待教师认领" description="教师认领项目后，研究任务链会自动生成。" compact />
          </section>
        </section>

        <aside class="journey-action-rail">
          <section class="paper-card journey-action-card">
            <p class="eyebrow">下一步</p>
            <h2>{{ currentStep?.title || (journeyChapters.length ? '研究章节已完成' : '等待研究任务') }}</h2>
            <p v-if="currentStep" class="muted">{{ currentStep.description || '完成当前任务并提交材料，推进研究进程。' }}</p>
            <p v-else class="muted">{{ journeyChapters.length ? '所有章节都已完成，可以查看研究报告。' : '教师认领项目后，研究任务会自动生成。' }}</p>
            <StatusTag v-if="currentStep" :status="currentStep.taskStatus" />
            <RouterLink v-if="currentStep && currentStep.taskStatus !== 'locked'" class="primary-button" :to="studentTaskRoute(project.id, currentStep.id)">继续当前任务 →</RouterLink>
          </section>
          <section class="paper-card journey-action-card journey-ai-card">
            <p class="eyebrow">灵思 AI</p>
            <h2>把当前问题说清楚</h2>
            <p class="muted">围绕当前项目和任务获取建议，内容需要你核对后再写入材料。</p>
            <RouterLink class="secondary-button" :to="researchAILocation">进入灵思 AI →</RouterLink>
          </section>
        </aside>
      </div>
    </template>

    <template v-else-if="project">
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
  <EmptyState v-if="!loading && !project" title="找不到项目" description="项目可能不存在，或不属于当前账号。" />
</template>

<style scoped>
.project-detail-skeleton { display: grid; gap: 22px; }
.project-detail-skeleton__overview, .project-detail-skeleton__workspace { display: grid; gap: 14px; padding: 28px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-soft); }
.project-detail-skeleton__overview { min-height: 190px; background: linear-gradient(115deg, var(--paper) 0%, var(--sage-soft) 100%); }
.project-detail-skeleton__workspace { grid-template-columns: minmax(0, 1fr) 280px; min-height: 260px; background: transparent; border: 0; box-shadow: none; padding: 0; }
.project-detail-skeleton i, .project-detail-skeleton strong, .project-detail-skeleton span, .project-detail-skeleton b { display: block; height: 13px; border-radius: 999px; background: var(--paper-muted); }
.project-detail-skeleton__overview strong { width: min(62%, 560px); height: 42px; margin-top: 16px; background: var(--sage-line); }
.project-detail-skeleton__overview span { width: min(78%, 700px); }
.project-detail-skeleton__overview b { width: 92%; height: 8px; margin-top: auto; }
.project-detail-skeleton__workspace i { min-height: 260px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-soft); }
.project-detail-skeleton__workspace i:last-child { min-height: 160px; }
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
.demo-progress { margin-top: 18px; }
.progress-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 7px; color: var(--muted); font-size: 12px; }
.progress-row strong { color: var(--ink); }
.progress-track { height: 7px; overflow: hidden; border-radius: 999px; background: var(--paper-muted); }
.progress-track i { display: block; height: 100%; border-radius: inherit; background: var(--moss); }
.journey-overview { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(300px, .9fr); gap: 30px; align-items: stretch; padding: 25px 28px; border-color: var(--sage-line); background: linear-gradient(115deg, var(--paper) 0%, var(--sage-soft) 100%); }
.journey-overview__project { min-width: 0; }
.journey-overview__project h2 { margin: 6px 0 8px; color: var(--ink); font: 700 21px/1.4 var(--sans); overflow-wrap: anywhere; }
.journey-overview__project .text-link { display: inline-flex; margin-bottom: 4px; }
.journey-overview__plan { display: grid; gap: 4px; margin: 17px 0 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.journey-overview__plan span { color: var(--moss); font-size: 10px; font-weight: 700; letter-spacing: .06em; }
.journey-overview__progress { display: grid; align-content: center; min-width: 0; padding-left: 28px; border-left: 1px solid var(--sage-line); }
.journey-overview__progress-heading { display: flex; align-items: end; justify-content: space-between; gap: 14px; }
.journey-overview__progress-heading .eyebrow { margin: 0 0 3px; }
.journey-overview__progress-heading strong { color: var(--moss-dark); font: 700 34px/1 var(--sans); }
.journey-overview__progress-heading > span { padding-bottom: 3px; color: var(--muted); font-size: 11px; text-align: right; }
.journey-overview__progress .progress-track { margin-top: 14px; height: 8px; }
.journey-overview__facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px 18px; margin-top: 19px; }
.journey-overview__facts span { display: grid; gap: 4px; min-width: 0; }
.journey-overview__facts small { color: var(--muted-light); font-size: 10px; }
.journey-overview__facts strong { overflow: hidden; color: var(--ink); font-size: 12px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
.journey-workspace { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 18px; align-items: start; margin-top: 22px; }
.journey-chapters { min-width: 0; padding: 24px; }
.journey-chapters__heading { display: flex; align-items: end; justify-content: space-between; gap: 18px; padding-bottom: 17px; border-bottom: 1px solid var(--line); }
.journey-chapters__heading h2 { margin: 4px 0 5px; color: var(--ink); font: 700 21px/1.25 var(--sans); }
.journey-chapters__heading p { margin: 0; color: var(--muted); font-size: 12px; }
.journey-chapters__heading > span { flex: 0 0 auto; color: var(--muted); font-size: 11px; }
.journey-chapters .demo-chapter-accordion { overflow: hidden; margin: 0; padding: 0; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
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
.demo-task-mini__main { display: grid; gap: 3px; min-width: 0; }
.demo-task-mini__main strong { overflow: hidden; color: var(--ink); text-overflow: ellipsis; white-space: nowrap; }
.demo-task-mini__main small { overflow: hidden; color: var(--muted-light); text-overflow: ellipsis; white-space: nowrap; }
.demo-task-mini + .demo-task-mini { margin-top: 7px; }
.journey-action-rail { display: grid; gap: 18px; position: sticky; top: 94px; }
.journey-action-card { display: grid; align-content: start; gap: 11px; padding: 22px; }
.journey-action-card h2 { margin: 0; color: var(--ink); font: 700 19px/1.4 var(--sans); overflow-wrap: anywhere; }
.journey-action-card p { margin: 0; }
.journey-action-card .status-tag { justify-self: start; }
.journey-action-card .primary-button, .journey-action-card .secondary-button { justify-content: center; margin-top: 5px; }
.journey-ai-card { border-color: var(--sage-line); background: linear-gradient(145deg, var(--paper) 0%, var(--sage-soft) 100%); }
.demo-report-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-4); align-items: start; }
.demo-stack { display: grid; align-content: start; gap: var(--space-4); }
.demo-export-actions { margin-top: 18px; }
.demo-export-actions .secondary-button { width: 100%; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 1024px) {
  .journey-workspace { grid-template-columns: minmax(0, 1fr) 280px; }
}
@media (max-width: 768px) {
  .project-detail-skeleton__workspace { grid-template-columns: 1fr; }
  .journey-overview { grid-template-columns: 1fr; gap: 20px; }
  .journey-overview__progress { padding: 20px 0 0; border-top: 1px solid var(--sage-line); border-left: 0; }
  .journey-workspace { grid-template-columns: 1fr; }
  .journey-action-rail { position: static; }
}
</style>
