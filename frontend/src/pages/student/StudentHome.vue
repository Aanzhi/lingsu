<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { errorMessage } from '../../api'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import EmptyState from '../../components/EmptyState.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { auth } from '../../stores/auth'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { studentProjectRoute, studentProjectsPath } from '../../stores/pageContracts'
import { student } from '../../stores/student'
import { projectJourneySummary, selectHomeTask, selectPriorityTask, studentPrimaryAction } from '../../stores/studentApiModel'

const feedback = ref<FeedbackState | null>(null)
const loading = ref(false)
const project = computed(() => {
  const primary = student.state.projects.find((item) => item.is_primary)
  if (primary) return primary
  return student.state.projects.find((item) => item.status === 'active') ?? student.state.projects[0]
})
const projectTasks = computed(() => student.state.tasks.filter((task) => task.project === project.value?.id).sort((a, b) => a.order - b.order))
const projectMaterials = computed(() => student.state.materials.filter((material) => material.project === project.value?.id))
const journey = computed(() => projectJourneySummary(projectTasks.value, projectMaterials.value))
const next = computed(() => selectHomeTask(projectTasks.value) ?? null)
const primaryTask = computed(() => selectPriorityTask(projectTasks.value) ?? null)
const currentChapter = computed(() => journey.value.chapters.find((chapter) => chapter.containsCurrent) ?? journey.value.chapters.at(-1) ?? null)
const reportReady = computed(() => projectMaterials.value.some((material) => material.revisions.some((revision) => revision.status === 'approved')))
const primaryAction = computed(() => studentPrimaryAction({
  currentTaskId: primaryTask.value?.id ?? null,
  projectId: project.value?.id ?? 0,
  reportReady: reportReady.value,
}))
const waitCount = computed(() => projectTasks.value.filter((task) => task.status === 'pending_review').length)
const recentMaterials = computed(() => projectMaterials.value
  .map((material) => ({ material, latest: material.revisions.at(-1) ?? null }))
  .sort((left, right) => {
    const leftTime = left.latest?.created_at ? Date.parse(left.latest.created_at) : 0
    const rightTime = right.latest?.created_at ? Date.parse(right.latest.created_at) : 0
    return rightTime - leftTime || left.material.report_order - right.material.report_order
  })
  .slice(0, 3))
const reminderLocation = computed(() => project.value ? { path: '/student/ai', query: { projectId: String(project.value.id) } } : '/student/ai')
const chapterDescriptions = ['把兴趣变成可研究的问题', '找到可信的证据和来源', '决定如何验证你的想法', '执行、记录并修正方案', '把过程和发现讲清楚']
async function load() {
  loading.value = true
  feedback.value = null
  try { await student.load() }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '项目数据没有加载完成，请重试。', '重试') }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="page student-home-page">
    <PageHeader eyebrow="当前项目" title="继续当前研究" description="从当前项目的待办开始，查看进度、材料状态和下一项可完成任务。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <div v-if="loading" class="loading-state" role="status">正在读取你的研究进度…</div>
    <EmptyState v-else-if="!project" title="先创建一个研究项目" description="已有课题可以直接创建；还没有课题也可以从一个观察开始，让 AI 一步步帮你找到研究方向。"><RouterLink class="primary-button" :to="`${studentProjectsPath()}?create=1`">创建项目</RouterLink></EmptyState>
    <template v-else>
      <div class="pilot-hero-grid">
        <section class="pilot-card pilot-hero-card">
          <p class="eyebrow">当前项目</p>
          <h2>{{ project.title }}</h2>
          <p class="pilot-hero-question"><span>研究问题</span>{{ project.problem || '还没有填写研究问题，进入项目概览补充后再开始任务。' }}</p>
          <div class="pilot-hero-meta"><span>进行中 · 第 {{ currentChapter?.index ?? 1 }} 章 / 共 {{ journey.chapters.length || 5 }} 章</span><span v-if="waitCount">{{ waitCount }} 项正在等待审核</span></div>
        </section>
        <section class="pilot-card pilot-next-card">
          <div class="pilot-next-card__kicker"><span>优先处理</span><StatusTag :status="next?.status ?? 'draft'" /></div>
          <div class="pilot-next-card__title">{{ next?.title ?? '查看研究旅程' }}</div>
          <div class="pilot-next-card__text">{{ next?.description || '查看当前章节，完成下一项可执行任务。' }}</div>
          <div class="pilot-progress-row"><span>章节进度</span><strong>{{ currentChapter?.done ?? 0 }} / {{ currentChapter?.total ?? 0 }}</strong></div>
          <div class="pilot-progress-track" aria-hidden="true"><i :style="{ width: `${currentChapter?.percent ?? 0}%` }" /></div>
          <RouterLink class="primary-button" :to="primaryAction.to">开始任务 →</RouterLink>
        </section>
      </div>
      <div class="pilot-section-head"><div><h2>我的项目</h2><p>只展示最需要你关注的信息</p></div><RouterLink class="secondary-button pilot-subtle-action" to="/student/projects">打开项目 →</RouterLink></div>
      <section>
        <div class="pilot-chapter-grid">
          <article v-for="chapter in journey.chapters" :key="chapter.index" class="pilot-card pilot-chapter-card" :class="{ 'is-current': chapter.containsCurrent, 'is-done': chapter.status === 'done' }">
            <span class="pilot-chapter-index">{{ chapter.index }}</span>
            <h3>{{ chapter.name }}</h3><p>{{ chapterDescriptions[chapter.index - 1] ?? `${chapter.done} / ${chapter.total} 项任务` }}</p><StatusTag :status="chapter.status === 'done' ? 'completed' : chapter.containsCurrent ? 'active' : 'draft'" />
          </article>
        </div>
      </section>
      <div class="pilot-two-col student-home-support">
        <section class="pilot-card pilot-list-card">
          <div class="student-support-head"><div><h2>最近材料</h2><p>按研究章节自动归档</p></div><RouterLink class="secondary-button pilot-subtle-action" :to="studentProjectRoute(project.id, 'materials')">查看全部</RouterLink></div>
          <div v-if="recentMaterials.length"><div v-for="item in recentMaterials" :key="item.material.id" class="pilot-list-row"><div class="pilot-list-row__main"><div class="pilot-list-row__title">{{ item.material.title }}</div><div class="pilot-list-row__meta">{{ item.material.report_section || '待映射章节' }} · {{ item.latest ? item.latest.created_at.slice(0, 10) : '尚无版本' }}</div></div><StatusTag :status="item.material.status" /></div></div>
          <EmptyState v-else title="还没有材料记录" description="完成研究旅程中的第一项任务后，材料会自动出现在这里。" compact />
        </section>
        <section class="pilot-card pilot-content-card student-reminder"><h2>研究小提醒</h2><div class="student-reminder__callout"><strong>先问“为什么”，再急着找答案。</strong><span>一个清晰的问题，比一堆没有方向的资料更有价值。</span></div><RouterLink class="secondary-button" :to="reminderLocation">请 AI 帮我想一想</RouterLink></section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.pilot-subtle-action { border-color: transparent; background: transparent; color: var(--moss); }
.pilot-subtle-action:hover { background: var(--sage-soft); }
.student-home-support { margin-top: var(--space-4); }
.pilot-hero-question { display: flex; flex-direction: column; gap: 5px; }
.pilot-hero-question span { color: rgba(255,255,255,.62); font-size: 11px; font-weight: 700; letter-spacing: .08em; }
.student-support-head { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--space-4); margin-bottom: var(--space-4); }
.student-support-head h2 { margin: 0; font: 700 20px/1.25 var(--sans); }
.student-support-head p { margin: 4px 0 0; color: var(--muted-light); font-size: 12px; }
.student-reminder__callout { margin: 16px 0; padding: var(--space-4); border-left: 3px solid var(--moss); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; background: var(--sage-soft); color: var(--muted); font-size: 13px; }
.student-reminder__callout strong, .student-reminder__callout span { display: block; }
.student-reminder__callout strong { margin-bottom: 4px; color: var(--moss-dark); }
</style>
