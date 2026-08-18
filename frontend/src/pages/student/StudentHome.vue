<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Calendar, MagicStick, Medal, RefreshRight } from '@element-plus/icons-vue'

import { errorMessage } from '../../api'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import EmptyState from '../../components/EmptyState.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import TaskStatusCard from '../../components/TaskStatusCard.vue'
import { auth } from '../../stores/auth'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { student } from '../../stores/student'
import { selectHomeTask, taskCompletion } from '../../stores/studentApiModel'

const feedback = ref<FeedbackState | null>(null)
const loading = ref(false)
const project = computed(() => {
  const primary = student.state.projects.find((item) => item.is_primary)
  if (primary) return primary
  return student.state.projects.find((item) => item.status === 'active') ?? student.state.projects[0]
})
const projectTasks = computed(() => student.state.tasks.filter((task) => task.project === project.value?.id).sort((a, b) => a.order - b.order))
const progress = computed(() => taskCompletion(projectTasks.value))
const next = computed(() => selectHomeTask(projectTasks.value) ?? null)
const announcements = computed(() => student.state.announcements.filter((notice) => notice.is_read === false).slice(0, 2))
const waitCount = computed(() => projectTasks.value.filter((task) => task.status === 'pending_review').length)
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
    <PageHeader eyebrow="今日行动台" :title="`${auth.user.value?.displayName ?? '同学'}，今天先完成一件事`" description="只显示当前最优先的研究行动；每次提交都会留下版本和审核结果。">
      <template #actions><RouterLink class="secondary-button" to="/student/projects">管理项目</RouterLink></template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="load" />
    <div v-if="loading" class="loading-state" role="status">正在读取你的研究进度…</div>
    <EmptyState v-else-if="!project" title="先创建一个研究项目" description="创建草稿后，项目会进入本校教师项目池，认领后才会生成任务地图。"><RouterLink class="primary-button" to="/student/projects">创建项目</RouterLink></EmptyState>
    <template v-else>
      <section class="student-progress-strip paper-card" aria-label="项目完成度">
        <div class="progress-project"><span class="project-kicker">当前项目</span><strong>{{ project.title }}</strong><span v-if="project.is_primary" class="status-tag current">主项目</span><StatusTag :status="project.status" /></div>
        <div class="progress-summary"><strong>{{ progress.completed }} / {{ progress.total }}</strong><span>项任务已通过</span></div>
        <div class="home-progress-track" aria-hidden="true"><i :style="{ width: `${progress.percent}%` }" /></div>
        <strong class="progress-percent">{{ progress.percent }}%</strong>
        <span class="waiting-summary" v-if="waitCount"><RefreshRight /> {{ waitCount }} 项等待审核</span><span v-else>继续沿着证据前进</span>
      </section>
      <div class="student-home-grid">
        <section class="journey-hero paper-card">
          <div class="hero-top"><div><span class="project-kicker">研究旅程</span><h2>{{ project.title }}</h2><p>{{ project.problem }}</p></div><StatusTag :status="project.status" /></div>
          <div class="growth-row"><div><small>成长等级</small><strong>Lv.{{ project.growth.level }}</strong><span>{{ project.growth.title }}</span></div><div class="xp-track"><i :style="{ width: `${Math.min(100, project.growth.experience / 7)}%` }" /></div><b>{{ project.growth.experience }} XP</b><span><el-icon><RefreshRight /></el-icon> 连续 {{ project.growth.streak_days }} 天</span></div>
          <div class="hero-actions"><RouterLink class="primary-button" :to="`/student/projects/${project.id}/map`">打开研究旅程</RouterLink><RouterLink class="secondary-button" :to="`/student/projects/${project.id}/report`">查看报告</RouterLink></div>
        </section>
        <TaskStatusCard :task="next" :project-id="project.id" />
        <section class="home-panel home-ai-panel"><div class="section-heading"><div><p class="eyebrow">灵思 AI</p><h3>围绕当前任务思考</h3></div><el-icon><MagicStick /></el-icon></div><p>AI 只生成可编辑建议，事实、数据和引用仍需你按真实项目核对。</p><RouterLink class="text-link" to="/student/ai">打开当前任务辅导 →</RouterLink></section>
        <section class="home-panel"><div class="section-heading"><div><p class="eyebrow">等待与提醒</p><h3>{{ announcements.length ? '有新的通知' : '暂时没有未读提醒' }}</h3></div><el-icon><Calendar /></el-icon></div><RouterLink v-if="student.state.competitions[0]" class="notice-row" to="/student/competitions"><el-icon><Medal /></el-icon><span><strong>{{ student.state.competitions[0].title }}</strong><small>{{ student.state.competitions[0].registration_deadline?.slice(0, 10) ?? '查看详情' }}</small></span></RouterLink><RouterLink v-for="notice in announcements" :key="notice.id" class="notice-row" to="/student/announcements"><span class="notice-dot" /><span><strong>{{ notice.title }}</strong><small>{{ notice.published_at?.slice(5, 10) }}</small></span></RouterLink><RouterLink v-if="!announcements.length && !student.state.competitions.length" class="text-link" to="/student/announcements">查看通知中心 →</RouterLink></section>
      </div>
    </template>
  </div>
</template>
