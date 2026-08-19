<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Download, MagicStick, User } from '@element-plus/icons-vue'
import { createReportExport, errorMessage, getReportExports, type ReportExport } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import JourneyDeliveryBoard, { type DeliveryItem } from '../../components/JourneyDeliveryBoard.vue'
import JourneyHero, { type JourneyKpi } from '../../components/JourneyHero.vue'
import JourneyStageDetail, { type JourneyTaskRow } from '../../components/JourneyStageDetail.vue'
import JourneyTimeline, { type JourneyNode } from '../../components/JourneyTimeline.vue'
import PageHeader from '../../components/PageHeader.vue'
import ProjectLifecycleMenu from '../../components/ProjectLifecycleMenu.vue'
import ProjectTimeline, { type TimelineStage } from '../../components/ProjectTimeline.vue'
import StatusTag from '../../components/StatusTag.vue'
import ConsistencyCheckCard from '../../components/ConsistencyCheckCard.vue'
import MemberInvitationDialog from '../../components/MemberInvitationDialog.vue'
import { student } from '../../stores/student'
import type { ApiTask } from '../../stores/studentApiModel'
import { exportStatusLabel, shouldPollExport } from '../../stores/reportModel'
import { auth } from '../../stores/auth'
import { canInviteMember } from '../../stores/memberModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const route = useRoute(); const router = useRouter(); const error = ref(''); const feedback = ref<FeedbackState | null>(null); const exports = ref<ReportExport[]>([]); const exportBusy = ref(false); let pollTimer: number | undefined
const surface = computed(() => String(route.meta.surface ?? 'overview')); const projectId = computed(() => Number(route.params.id))
const project = computed(() => student.project(projectId.value))
const tasks = computed(() => student.state.tasks.filter((item) => item.project === projectId.value).sort((a, b) => a.order - b.order))
const materials = computed(() => student.state.materials.filter((item) => item.project === projectId.value).sort((a, b) => a.report_order - b.report_order))
const stages = computed(() => [...new Map(tasks.value.map((task) => [task.stage_order, task.stage_name])).entries()].sort((a, b) => a[0] - b[0]))
const currentStage = computed(() => tasks.value.find((task) => !['completed', 'approved'].includes(task.status))?.stage_order ?? stages.value.at(-1)?.[0] ?? 1)
const reportSections = computed(() => materials.value.flatMap((material) => {
  const version = [...material.revisions].reverse().find((item) => item.status === 'approved')
  return version ? [{ material, version }] : []
}))
const typeLabel = computed(() => ({ research: '研究型', invention: '发明型', engineering: '工程型' }[project.value?.project_type ?? 'research']))
const mayInvite = computed(() => project.value ? canInviteMember({ currentUserId: auth.user.value?.id, leaderId: project.value.leader, projectStatus: project.value.status, authorized: Boolean(auth.user.value?.authorized) }) : false)
const timelineStages = computed<TimelineStage[]>(() => {
  if (!stages.value.length) return []
  return stages.value.map(([order, title]) => {
    const stageTasks = tasks.value.filter((task) => task.stage_order === order)
    const passed = stageTasks.filter((task) => ['approved', 'completed'].includes(task.status)).length
    const isCurrent = order === currentStage.value
    const allPassed = passed === stageTasks.length && stageTasks.length > 0
    let status: TimelineStage['status'] = 'pending'
    if (allPassed) status = 'completed'
    else if (isCurrent) status = 'current'
    else if (order > currentStage.value) status = 'locked'
    return {
      order,
      title,
      status,
      tasksCompleted: passed,
      tasksTotal: stageTasks.length,
      hint: status === 'locked' ? '完成上一阶段并通过审核后解锁' : (status === 'current' ? '当前阶段：聚焦这一组任务' : undefined),
      badge: isCurrent ? '当前阶段' : undefined,
    }
  })
})

// ── 研究旅程 (map) ───────────────────────────────────────────────
// 流程-交付对应：每个任务对应 1 个交付物（即一份材料 → 一个报告章节）
// - 名称优先取 material.report_section（这就是报告里出现的章节名）；
//   若 material.report_section 为空，则退回 material.title。
// - 副名用 material.title，让用户看到"流程里这一步 → 报告里这一节 → 这份材料"。
// - 状态映射：material 审核通过 → delivered；material 存在但未通过 → in_progress；
//   task 进入提交流程但无 material → in_progress；其余按 task 状态映射。
// - evidence_requirements 不再被截断，task.title 作为最后兜底。
type DeliveryBindingStatus = DeliveryItem['status']
interface DeliveryBinding {
  taskId: number
  stageOrder: number
  stageTitle: string
  taskTitle: string
  taskStatus: ApiTask['status']
  deliveryLabel: string   // 流程里这一步最终落到报告里的章节名（report_section）
  deliverySubLabel: string // 对应的材料标题（material.title）
  status: DeliveryBindingStatus
  materialId: number | null
}
const deliveryByTask = computed<Record<number, DeliveryBinding>>(() => {
  const map: Record<number, DeliveryBinding> = {}
  tasks.value.forEach((task) => {
    const linkedMaterial = materials.value.find((m) => m.task === task.id)
    let status: DeliveryBindingStatus = 'pending'
    let deliveryLabel = task.title
    let deliverySubLabel = task.evidence_requirements?.[0] ?? ''
    if (linkedMaterial) {
      // 流程对应交付：主名 = 报告章节（这是用户在报告页真正看到的），副名 = 材料标题
      deliveryLabel = linkedMaterial.report_section || linkedMaterial.title
      deliverySubLabel = linkedMaterial.title
      status = linkedMaterial.status === 'approved' ? 'delivered' : 'in_progress'
    } else if (task.status === 'approved' || task.status === 'completed') {
      status = 'delivered'
    } else if (['pending_review', 'submitted', 'revision_required'].includes(task.status)) {
      status = 'in_progress'
    } else if (task.status === 'locked') {
      status = 'locked'
    }
    map[task.id] = {
      taskId: task.id,
      stageOrder: task.stage_order,
      stageTitle: task.stage_name,
      taskTitle: task.title,
      taskStatus: task.status,
      deliveryLabel,
      deliverySubLabel,
      status,
      materialId: linkedMaterial?.id ?? null,
    }
  })
  return map
})

const journeyNodes = computed<JourneyNode[]>(() => timelineStages.value.map((stage) => ({
  order: stage.order,
  title: stage.title,
  status: stage.status === 'current' ? 'current' : stage.status === 'completed' ? 'completed' : stage.status === 'locked' ? 'locked' : 'pending',
  passed: stage.tasksCompleted,
  total: stage.tasksTotal,
  hint: stage.hint,
})))
const selectedStage = ref<number | null>(null)
watch(currentStage, (order) => { if (selectedStage.value === null) selectedStage.value = order }, { immediate: true })
watch(journeyNodes, (nodes) => {
  if (selectedStage.value === null || !nodes.some((node) => node.order === selectedStage.value)) {
    selectedStage.value = currentStage.value ?? nodes[0]?.order ?? null
  }
})
function selectStage(order: number) { selectedStage.value = order }
function isStageUnlocked(order: number) {
  return order <= currentStage.value
}
const selectedStageDetail = computed(() => {
  if (selectedStage.value === null) return null
  const stageOrder = selectedStage.value
  const stageTitle = stages.value.find(([order]) => order === stageOrder)?.[1] ?? `第 ${stageOrder} 阶段`
  const stageTasks = tasks.value
    .filter((task) => task.stage_order === stageOrder)
    .sort((a, b) => a.order - b.order)
  const rows: JourneyTaskRow[] = stageTasks.map((task) => {
    const stage = timelineStages.value.find((s) => s.order === stageOrder)
    const isCurrentStage = stage?.status === 'current'
    let status: JourneyTaskRow['status'] = task.status as JourneyTaskRow['status']
    if (!isStageUnlocked(stageOrder) && status === 'available') status = 'locked'
    const binding = deliveryByTask.value[task.id]
    return {
      id: task.id,
      order: task.order,
      title: task.title,
      description: task.description,
      status,
      xpReward: task.xp_reward,
      evidence: task.evidence_requirements,
      deliveryLabel: binding?.deliveryLabel,
      deliverySubLabel: binding?.deliverySubLabel,
      stageOrder,
    }
  })
  const passed = stageTasks.filter((t) => ['approved', 'completed'].includes(t.status)).length
  const total = stageTasks.length
  const stageStatus = (timelineStages.value.find((s) => s.order === stageOrder)?.status ?? 'pending') as 'completed' | 'current' | 'pending' | 'locked'
  return { order: stageOrder, title: stageTitle, status: stageStatus, rows, passed, total }
})
function openTask(task: JourneyTaskRow) { router.push(`/student/projects/${projectId.value}/tasks/${task.id}`) }

// 「本阶段推荐 AI 助手」入口：跳转思考室并预选当前查看的阶段
const recoStage = computed(() => selectedStage.value ?? currentStage.value)
const recoStageName = computed(() => stages.value.find(([o]) => o === recoStage.value)?.[1] ?? '当前阶段')

// KPI 修复：四项 = 阶段 / 任务 / 已通过 / 剩余交付物
const journeyKpis = computed<JourneyKpi[]>(() => {
  const totalTasks = tasks.value.length
  const passedTasks = tasks.value.filter((t) => ['approved', 'completed'].includes(t.status)).length
  const bindings = Object.values(deliveryByTask.value)
  const delivered = bindings.filter((b) => b.status === 'delivered').length
  const pending = bindings.filter((b) => b.status === 'pending' || b.status === 'in_progress').length
  return [
    { label: '总阶段', value: stages.value.length, caption: '拆成可执行的几章' },
    { label: '总任务', value: totalTasks, caption: '逐项可追踪的证据' },
    { label: '已通过', value: `${passedTasks} / ${totalTasks || 0}`, caption: '任务通过率' },
    { label: '待交付', value: pending, caption: `已交付 ${delivered} / ${bindings.length || 0}` },
  ]
})

// 交付清单：按阶段分组，每组显示「第 N 章 + 章名 + 该章交付物列表 + 该章完成度」
interface DeliveryGroup {
  order: number
  title: string
  status: 'completed' | 'current' | 'pending' | 'locked'
  passed: number
  total: number
  items: DeliveryItem[]
}
const deliveryGroups = computed<DeliveryGroup[]>(() => {
  const groupsByStage: Record<number, DeliveryBinding[]> = {}
  Object.values(deliveryByTask.value).forEach((binding) => {
    ;(groupsByStage[binding.stageOrder] ??= []).push(binding)
  })
  return stages.value.map(([order, title]) => {
    const stageTasks = tasks.value.filter((task) => task.stage_order === order)
    const passed = stageTasks.filter((t) => ['approved', 'completed'].includes(t.status)).length
    const stageTimeline = timelineStages.value.find((s) => s.order === order)
    const status: DeliveryGroup['status'] = (stageTimeline?.status ?? 'pending') as DeliveryGroup['status']
    const bindings = (groupsByStage[order] ?? []).sort((a, b) => a.taskId - b.taskId)
    return {
      order,
      title,
      status,
      passed,
      total: stageTasks.length,
      items: bindings.map((binding) => ({
        id: `t-${binding.taskId}`,
        label: binding.deliveryLabel,
        subLabel: binding.deliverySubLabel,
        taskLabel: binding.taskTitle,
        status: binding.status,
        stage: binding.stageOrder,
      })),
    }
  })
})
async function handleSetPrimary() { try { await student.setPrimary(projectId.value); await student.refreshProject(projectId.value) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '主项目没有切换成功，可以重试。', '重试') } }
async function handleArchive() { if (!confirm('确定归档该项目？仅已完成项目可归档。')) return; try { await student.archive(projectId.value); router.replace('/student/projects?tab=archived') } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '归档失败，可以稍后重试。', '重试') } }
async function handleUnarchive() { try { await student.unarchive(projectId.value); await student.refreshProject(projectId.value) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '恢复失败，可以重试。', '重试') } }
async function handleTrash() { if (!confirm('确定将项目移入回收站？30 天后自动删除。')) return; try { await student.trash(projectId.value); router.replace('/student/projects?tab=trashed') } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '移入回收站失败，可以重试。', '重试') } }
async function handleRestore() { try { await student.restore(projectId.value); await student.refreshProject(projectId.value) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '恢复失败，可以重试。', '重试') } }
async function loadExports() {
  exports.value = (await getReportExports(projectId.value)).data
  window.clearTimeout(pollTimer)
  if (exports.value.some((item) => shouldPollExport(item.status))) pollTimer = window.setTimeout(() => loadExports().catch(() => undefined), 1500)
}
async function load() { try { await student.refreshProject(projectId.value); if (surface.value === 'report') await loadExports() } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '项目数据没有加载完成，请重试。', '重试') } }
async function queueExport(format: 'docx' | 'pdf') { exportBusy.value = true; feedback.value = null; try { await createReportExport(projectId.value, format); await loadExports(); feedback.value = makeFeedback('success', `${format.toUpperCase()} 导出任务已排队。`, '生成完成后可以在本页历史记录下载。') } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '报告内容不会丢失，可以稍后重试。', '重试') } finally { exportBusy.value = false } }
onMounted(load); watch(projectId, load)
</script>
<template><div v-if="project" class="page project-detail-page"><PageHeader :breadcrumbs="['我的项目', project.title, surface === 'map' ? '研究旅程' : surface === 'materials' ? '材料档案' : surface === 'report' ? '报告装配' : '项目概览']" :eyebrow="typeLabel" :title="project.title" :description="project.problem"><template #actions><span v-if="project.is_primary" class="status-tag current">主项目</span><ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" student-mode @primary="handleSetPrimary" @archive="handleArchive" @unarchive="handleUnarchive" @trash="handleTrash" @restore="handleRestore" /><StatusTag :status="project.status" /></template></PageHeader><FeedbackBanner v-model="feedback" @action="load" /><nav class="project-tabs"><RouterLink :to="`/student/projects/${project.id}`">项目概览</RouterLink><RouterLink :to="`/student/projects/${project.id}/map`">研究旅程</RouterLink><RouterLink :to="`/student/projects/${project.id}/materials`">材料档案</RouterLink><RouterLink :to="`/student/projects/${project.id}/report`">报告装配</RouterLink></nav><template v-if="surface === 'overview'"><div class="overview-grid"><section class="paper-card overview-paper"><p class="eyebrow">项目问题</p><h2>{{ project.problem }}</h2><div class="paper-rule" /><p class="eyebrow">初步方案</p><p>{{ project.plan }}</p><div class="stage-summary"><div><small>当前阶段</small><strong>{{ stages.find(([order]) => order === currentStage)?.[1] ?? (project.status === 'unclaimed' ? '等待认领' : '准备中') }}</strong></div><div><small>项目进度</small><strong>{{ tasks.filter((task) => ['approved', 'completed'].includes(task.status)).length }} / {{ tasks.length }} 项任务</strong></div><div><small>下一行动</small><strong>{{ tasks.find((task) => ['revision_required', 'available'].includes(task.status))?.title ?? '等待审核' }}</strong></div></div></section><aside class="team-card"><div class="section-heading"><div><p class="eyebrow">研究小组</p><h3>{{ project.members.length }} 位成员</h3></div><MemberInvitationDialog v-if="mayInvite" :project-id="project.id" /></div><div v-for="member in project.members" :key="member.id" class="member-row"><span class="avatar soft"><el-icon><User /></el-icon></span><span><strong>{{ member.username }}</strong><small>{{ member.role === 'leader' ? '项目负责人' : '项目成员' }}</small></span></div><div class="teacher-row"><small>主指导教师</small><strong>{{ project.primary_teacher ? `教师 #${project.primary_teacher}` : '等待教师认领' }}</strong></div></aside><section class="activity-card"><p class="eyebrow">项目风险与最近活动</p><div v-for="task in tasks.filter((item) => ['revision_required', 'pending_review'].includes(item.status)).slice(0, 4)" :key="task.id" class="activity-row"><span class="activity-dot" :class="task.status" /><div><strong>{{ task.title }}</strong><small>{{ task.status === 'revision_required' ? '需要修订教师意见' : '已提交，等待审核' }}</small></div><StatusTag :status="task.status" /></div><p v-if="!tasks.some((task) => ['revision_required', 'pending_review'].includes(task.status))">当前没有待处理风险，继续完成下一项任务。</p></section></div><ProjectTimeline class="project-overview-timeline" :stages="timelineStages" size="compact" /></template><template v-else-if="surface === 'map'">
  <JourneyHero
    eyebrow="研究旅程"
    title="从立项到答辩的真实节奏"
    subtitle="每一章都对应真实证据；上一章没通过审核，下一章不会自动开始。"
    :kpis="journeyKpis"
    :level="project.growth.level"
    :level-title="project.growth.title"
    :total-xp="project.growth.experience"
  />
  <JourneyTimeline :nodes="journeyNodes" :active="selectedStage ?? undefined" @select="selectStage" class="journey-rail-block" />
  <JourneyStageDetail
    v-if="selectedStageDetail"
    :order="selectedStageDetail.order"
    :title="selectedStageDetail.title"
    :status="selectedStageDetail.status"
    :passed="selectedStageDetail.passed"
    :total="selectedStageDetail.total"
    :tasks="selectedStageDetail.rows"
    @open="openTask"
  />
  <RouterLink class="ai-reco-cta" :to="{ path: '/student/ai', query: { stage: recoStage ?? undefined } }">
    <el-icon class="ai-reco-icon"><MagicStick /></el-icon>
    <span class="ai-reco-text">
      <strong>本阶段推荐 AI 助手</strong>
      <small>针对「{{ recoStageName }}」，在思考室直接调用对口助手、读取本阶段材料与草稿</small>
    </span>
    <span class="ai-reco-go">打开思考室 →</span>
  </RouterLink>
  <EmptyState v-if="!stages.length" title="等待教师认领" description="教师认领项目后，研究任务链会自动生成。" />
  <JourneyDeliveryBoard v-else :groups="deliveryGroups" class="journey-delivery-block" />
</template><template v-else-if="surface === 'materials'"><ConsistencyCheckCard :project-id="projectId" class="consistency-block" /><section class="materials-table paper-card"><div class="section-heading"><div><p class="eyebrow">只读档案</p><h2>材料版本与审核结果</h2></div><span>{{ materials.filter((item) => item.status === 'approved').length }} / {{ materials.length }} 项已通过</span></div><p class="archive-intro">这里记录每一项材料的版本，不负责编辑；需要修改时进入对应任务。</p><div v-for="material in materials" :key="material.id" class="material-row"><span class="file-glyph">{{ String(material.report_order).padStart(2, '0') }}</span><div><strong>{{ material.title }}</strong><small>{{ material.report_section }} · {{ material.revisions.length ? `V${material.revisions.length}` : '尚无版本' }}</small></div><StatusTag :status="material.status" /><RouterLink v-if="material.task && ['revision_required', 'available'].includes(material.status)" :to="`/student/projects/${project.id}/tasks/${material.task}`">去任务处理 →</RouterLink><span v-else class="archive-read-only">只读记录</span></div><EmptyState v-if="!materials.length" title="暂无材料" description="教师认领项目后会从项目模板生成材料清单。" /></section></template><template v-else><div class="report-layout"><section class="paper-card report-paper"><div class="report-title"><p>灵溯 · 项目报告预览</p><h1>{{ project.title }}</h1><small>本预览只装配最新已通过材料</small></div><article v-for="({ material, version }, index) in reportSections" :key="material.id"><span>第 {{ index + 1 }} 节</span><h2>{{ material.report_section || material.title }}</h2><h3>{{ material.title }} · V{{ material.revisions.indexOf(version) + 1 }}</h3><p>{{ version.content }}</p></article><EmptyState v-if="!reportSections.length" title="暂无可装配章节" description="材料通过教师审核后，会按模板章节自动进入报告。" /></section><aside class="report-aside"><section><p class="eyebrow">正式完成度</p><div class="report-score"><strong>{{ Math.round((reportSections.length / Math.max(materials.length, 1)) * 100) }}%</strong><span>{{ reportSections.length }} / {{ materials.length }} 项已通过</span></div><small>待审核和需修订材料不会进入正式报告。</small></section><section><p class="eyebrow">正式导出</p><p>后台只装配最新已通过材料，生成结果保留版本与材料清单。</p><button class="primary-button full" :disabled="exportBusy" type="button" @click="queueExport('docx')"><el-icon><Download /></el-icon> {{ exportBusy ? '正在排队…' : '生成 Word' }}</button><button class="secondary-button full" :disabled="exportBusy" type="button" @click="queueExport('pdf')">生成 PDF</button></section><section v-if="exports.length"><p class="eyebrow">生成历史</p><div v-for="item in exports" :key="item.id" class="export-row"><span>{{ item.format.toUpperCase() }}</span><b>{{ exportStatusLabel(item.status) }}</b><a v-if="item.download_url" :href="item.download_url">下载</a><small v-if="item.status === 'failed'">{{ item.error_message }}</small></div></section></aside></div></template></div><EmptyState v-else title="找不到项目" description="项目可能不存在，或不属于当前账号。" /></template>

<style scoped>
.project-overview-timeline { margin-top: 24px; }
.journey-rail-block { margin-top: 22px; }
.journey-delivery-block { margin-top: 22px; }
.consistency-block { margin-bottom: 22px; }
.ai-reco-cta { display: flex; align-items: center; gap: 12px; margin-top: 18px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 12px; background: linear-gradient(180deg, rgba(76,114,69,.07), rgba(76,114,69,.02)); text-decoration: none; color: var(--ink); transition: border-color .15s, box-shadow .15s; }
.ai-reco-cta:hover { border-color: var(--moss); box-shadow: 0 2px 10px rgba(76,114,69,.12); }
.ai-reco-icon { font-size: 20px; color: var(--moss); flex: none; }
.ai-reco-text { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.ai-reco-text strong { font-size: 14px; color: var(--moss-dark); }
.ai-reco-text small { font-size: 12px; color: var(--muted); line-height: 1.5; }
.ai-reco-go { font-size: 13px; color: var(--moss-dark); white-space: nowrap; }
</style>
