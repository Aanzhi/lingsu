<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { User } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

import { errorMessage } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { projectRiskLabel, projectTaskSummary } from '../../stores/teacherProjectModel'
import { teacherStore } from '../../stores/teacher'

const route = useRoute()
const feedback = ref<FeedbackState | null>(null)
const projectId = computed(() => Number(route.params.id))
const project = computed(() => teacherStore.state.guided.find((item) => item.id === projectId.value))
const tasks = computed(() => teacherStore.state.detail.projectId === projectId.value ? teacherStore.state.detail.tasks : [])
const materials = computed(() => teacherStore.state.detail.projectId === projectId.value ? teacherStore.state.detail.materials : [])
const summary = computed(() => projectTaskSummary(tasks.value))
const risk = computed(() => projectRiskLabel(tasks.value, materials.value))
const stages = computed(() => [...new Set(tasks.value.map((task) => task.stage_order))].sort((a, b) => a - b))

async function load() {
  try { if (!teacherStore.state.guided.length) await teacherStore.load(); await teacherStore.loadProjectDetail(projectId.value) }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '项目详情没有加载完成，可以重试。', '重试') }
}
onMounted(load)
</script>

<template>
  <div v-if="project" class="page teacher-project-detail-page">
    <PageHeader :breadcrumbs="['指导项目', project.title]" eyebrow="指导项目" :title="project.title" description="在一个页面判断团队、进度、风险和下一步指导动作."><template #actions><StatusTag :status="project.status" /></template></PageHeader>
    <FeedbackBanner v-model="feedback" @action="load" />
    <section class="teacher-project-summary paper-card"><div><p class="eyebrow">研究问题</p><h2>{{ project.problem }}</h2><p>初步方案：{{ project.plan }}</p></div><div class="teacher-project-score"><strong>{{ summary.percent }}%</strong><small>{{ summary.approved }} / {{ summary.total }} 项任务已通过</small><div class="mini-progress"><i :style="{ width: `${summary.percent}%` }" /></div></div></section>
    <div class="teacher-detail-grid"><section class="desk-panel"><div class="section-heading"><div><p class="eyebrow">阶段进度</p><h2>项目走到哪里</h2></div><span>{{ summary.needsReview }} 项需要教师处理</span></div><div v-for="stage in stages" :key="stage" class="teacher-stage-row"><div><strong>第 {{ stage }} 章 · {{ tasks.find((task) => task.stage_order === stage)?.stage_name }}</strong><small>{{ tasks.filter((task) => task.stage_order === stage && ['approved', 'completed'].includes(task.status)).length }} / {{ tasks.filter((task) => task.stage_order === stage).length }} 项已通过</small></div><div class="mini-progress"><i :style="{ width: `${tasks.filter((task) => task.stage_order === stage && ['approved', 'completed'].includes(task.status)).length / Math.max(tasks.filter((task) => task.stage_order === stage).length, 1) * 100}%` }" /></div></div><div class="teacher-material-list"><div v-for="material in materials" :key="material.id" class="teacher-material-row"><span><strong>{{ material.title }}</strong><small>{{ material.revisions.length }} 个版本 · {{ material.report_section || '未映射章节' }}</small></span><StatusTag :status="material.status" /><RouterLink v-if="material.revisions.at(-1)?.status === 'submitted'" class="text-link" :to="`/teacher/reviews/${material.revisions.at(-1)?.id}`">开始审核 →</RouterLink><span v-else class="archive-read-only">{{ material.status === 'approved' ? '已通过' : '暂无待审' }}</span></div><p v-if="!materials.length" class="form-hint">任务材料尚未生成。</p></div></section><aside class="teacher-detail-aside"><section class="desk-panel"><p class="eyebrow">指导风险</p><h2>{{ risk }}</h2><p v-if="risk === '有材料需要修订'">学生需要先处理被打回的任务，新的阶段不会跳过审核解锁。</p><p v-else-if="risk === '有材料等待审核'">有提交正在等待审核，建议优先处理最早提交的版本。</p><p v-else>当前没有需要教师立即介入的风险。</p><RouterLink class="secondary-button full" to="/teacher/reviews">打开审核队列</RouterLink></section><section class="team-card"><div class="section-heading"><div><p class="eyebrow">研究小组</p><h3>{{ project.members.length }} 位成员</h3></div><el-icon><User /></el-icon></div><div v-for="member in project.members" :key="member.id" class="member-row"><span class="avatar soft">{{ member.username.slice(0, 1) }}</span><span><strong>{{ member.username }}</strong><small>{{ member.role === 'leader' ? '项目负责人' : '项目成员' }}</small></span></div><div class="teacher-row"><small>主指导教师</small><strong>当前登录教师</strong></div></section></aside></div>
  </div>
  <EmptyState v-else title="找不到指导项目" description="项目可能已经被移除，或不属于当前教师。"><RouterLink class="secondary-button" to="/teacher/projects">返回指导项目</RouterLink></EmptyState>
</template>
