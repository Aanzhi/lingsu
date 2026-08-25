<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowRight, CircleCheck, Clock, Download, Lock, Paperclip, UploadFilled, Warning } from '@element-plus/icons-vue'
import { errorMessage, getAIAgents, type AIAgent } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { student } from '../../stores/student'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { auth } from '../../stores/auth'
import { taskPermission } from '../../stores/projectPermissions'
import { selectPriorityTask, taskActionLabel, taskCompletion, validateTaskSubmission } from '../../stores/studentApiModel'
import { aiQuickEntryLocation, taskQuickEntryAgents } from '../../stores/aiModel'
import { studentProjectRoute, studentTaskRoute } from '../../stores/pageContracts'

const route = useRoute(); const loading = ref(false); const dataLoading = ref(true); const body = ref(''); const truth = ref(false); const files = ref<File[]>([]); const feedback = ref<FeedbackState | null>(null); const aiAgents = ref<AIAgent[]>([])
const projectId = computed(() => Number(route.params.id)); const taskId = computed(() => Number(route.params.taskId))
const project = computed(() => student.project(projectId.value)); const task = computed(() => student.task(taskId.value)); const material = computed(() => student.materialForTask(taskId.value))
const projectTasks = computed(() => student.state.tasks.filter((item) => item.project === projectId.value).sort((a, b) => a.order - b.order))
const quickAgents = computed(() => task.value && project.value ? taskQuickEntryAgents(aiAgents.value, task.value, project.value.project_type) : [])
const aiCenterEntry = computed(() => {
  const agent = quickAgents.value[0]
  return aiQuickEntryLocation(
    projectId.value,
    taskId.value,
    agent?.workflow || 'proposal_topic',
    agent?.key || 'proposal-topic',
    project.value?.project_type || 'research',
  )
})
const progress = computed(() => taskCompletion(projectTasks.value))
const nextTask = computed(() => selectPriorityTask(projectTasks.value.filter((item) => item.id !== taskId.value)))
const permission = computed(() => task.value && material.value && project.value
  ? taskPermission({ isLeader: project.value.leader === auth.user.value?.id, taskStatus: task.value.status, materialStatus: material.value.status })
  : { canDraft: false, canSubmit: false, reason: '' })
const canEdit = computed(() => permission.value.canDraft)
const isLeader = computed(() => project.value?.leader === auth.user.value?.id)
const teamDraft = computed(() => {
  if (!project.value || !material.value || !isLeader.value) return null
  return [...material.value.revisions].reverse().find((revision) => revision.status === 'draft' && revision.author !== project.value!.leader) ?? null
})
const editingMode = computed(() => canEdit.value && !teamDraft.value)
const statusMessage = computed(() => {
  if (!task.value || !material.value) return ''
  if (task.value.status === 'revision_required') return '教师已指出需要修改的地方，修订后会创建新的版本。'
  if (task.value.status === 'pending_review' || material.value.status === 'submitted') return '材料已提交，当前无需重复操作；教师审核后会在这里反馈。'
  if (['approved', 'completed'].includes(task.value.status)) return '这项任务已通过，核心证据已进入项目成果。'
  if (task.value.status === 'locked') return '先完成上一项任务并通过审核，才能解锁这项任务。'
  return '完成证据清单后确认真实性，再提交给主指导教师。'
})
async function load() {
  dataLoading.value = true
  try {
    await student.refreshProject(projectId.value)
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '请刷新页面重试。', '重试')
  } finally {
    dataLoading.value = false
  }
}
onMounted(() => {
  void load()
  getAIAgents().then((response) => { aiAgents.value = response.data }).catch(() => { aiAgents.value = [] })
})
watch(material, (value) => { body.value = value?.revisions.at(-1)?.content ?? ''; truth.value = false; files.value = [] }, { immediate: true })
watch([projectId, taskId], () => { void load() })
function addFiles(event: Event) { files.value = Array.from((event.target as HTMLInputElement).files ?? []) }
function retry() { feedback.value = null; void load() }
async function submit() {
  if (!task.value || !material.value) return
  const validationError = validateTaskSubmission(task.value, body.value, files.value, truth.value)
  if (validationError) { feedback.value = makeFeedback('error', validationError, '请根据提示补充后再提交。'); return }
  if (!permission.value.canSubmit) { feedback.value = makeFeedback('info', permission.value.reason); return }
  loading.value = true
  feedback.value = null
  try {
    await student.submitMaterial(material.value.id, body.value, files.value, material.value.status === 'revision_required' ? '根据教师意见重新提交' : '')
    feedback.value = makeFeedback('success', '材料已提交给主指导教师审核。', '提交版本已保存，审核结果会同步到任务地图。', '回到研究旅程')
    truth.value = false; files.value = []
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '内容和附件仍保留在当前页面，可以修正后重试。', '重试') }
  finally { loading.value = false }
}
async function saveDraft() {
  if (!task.value || !material.value || !permission.value.canDraft) return
  if (!body.value.trim() && !files.value.length) { feedback.value = makeFeedback('error', '请填写正文或选择附件后再保存。'); return }
  loading.value = true; feedback.value = null
  try {
    await student.saveMaterialDraft(material.value.id, body.value, files.value, '成员草稿，等待负责人确认')
    feedback.value = makeFeedback('success', '草稿已保存到项目材料。', '项目负责人核对真实性后，才能正式提交给教师审核。')
    files.value = []
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '草稿未保存，当前输入仍保留，可以重试。', '重试') }
  finally { loading.value = false }
}
async function submitTeamDraft() {
  if (!material.value || !teamDraft.value) return
  if (!truth.value) { feedback.value = makeFeedback('error', '提交前必须确认材料真实性。', '请核对成员草稿后再提交给教师。'); return }
  loading.value = true; feedback.value = null
  try {
    await student.formallySubmitDraft(material.value.id, teamDraft.value.id)
    feedback.value = makeFeedback('success', '成员草稿已正式提交给主指导教师。', '提交版本已保存，审核结果会同步到任务地图。', '回到研究旅程')
    truth.value = false
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '成员草稿仍保留，处理完附件安全检查或内容问题后可以重试。', '重试') }
  finally { loading.value = false }
}
</script>
<template>
  <FeedbackBanner v-model="feedback" @action="feedback?.actionLabel === '回到研究旅程' ? $router.push(studentProjectRoute(projectId, 'map')) : retry()" />
  <p v-if="dataLoading" class="loading-state" role="status">正在读取任务材料…</p>
  <div v-if="task && project && material && !dataLoading" class="page task-page">
    <PageHeader :eyebrow="`研究旅程 / ${task.stage_name}`" :title="task.title" :description="'完成当前任务要求，补充证据后提交给指导教师审核。'">
      <template #actions><RouterLink class="secondary-button" :to="studentProjectRoute(project.id, 'map')">返回研究旅程</RouterLink></template>
    </PageHeader>
    <div class="task-layout demo-task-layout">
      <section class="demo-task-main paper-card" :class="{ 'task-paper--read-only': !canEdit }">
        <div class="task-label">需要提交什么</div>
        <div class="callout demo-task-guidance">
          <strong>{{ material.guidance || task.evidence_requirements[0] || '提交与任务目标直接相关的文字或附件证据。' }}</strong>
          <span v-for="evidence in task.evidence_requirements.slice(material.guidance ? 0 : 1)" :key="evidence">{{ evidence }}</span>
        </div>
        <a v-if="material.reference" class="secondary-button demo-reference-download" :href="material.reference.url" :download="material.reference.original_name"><el-icon><Download /></el-icon> 下载参考范本</a>
        <div v-if="material.status !== 'submitted' && !['approved', 'completed'].includes(task.status)" class="task-state-summary" :class="task.status">
          <el-icon><Warning v-if="task.status === 'revision_required'" /><Clock v-else-if="task.status === 'pending_review'" /><Lock v-else-if="task.status === 'locked'" /><CircleCheck v-else /></el-icon>
          <div><strong>{{ taskActionLabel(task.status) }}</strong><p>{{ statusMessage }}</p></div>
          <StatusTag :status="task.status" />
        </div>
        <div v-if="material.status === 'revision_required'" class="teacher-feedback"><strong>老师反馈 · 修订任务</strong><p>{{ material.revisions.at(-1)?.review_comment || '请根据教师意见补充证据。' }}</p><small>新提交会创建独立版本，旧版本完整保留。</small></div>
        <div v-else-if="material.status === 'submitted'" class="submitted-state"><el-icon><Clock /></el-icon><div><strong>已提交，等待教师审核</strong><p>你可以离开此页面；审核结果会通过通知中心和任务地图同步。</p><div v-if="body" class="submitted-copy"><small>已提交版本</small><p>{{ body }}</p></div></div></div>
        <div v-else-if="['approved', 'completed'].includes(task.status)" class="approved-state"><el-icon><CircleCheck /></el-icon><div><strong>任务已通过</strong><p>{{ nextTask ? `下一项：${nextTask.title}` : '所有任务都已完成，可以进入报告装配。' }}</p></div><RouterLink v-if="nextTask" class="secondary-button" :to="studentTaskRoute(project.id, nextTask.id)">下一项 <ArrowRight /></RouterLink></div>
        <div v-if="teamDraft" class="teacher-feedback"><strong>成员草稿 · 等待负责人确认</strong><p>{{ teamDraft.author_name }} 已完成一份草稿。请核对事实、数据和附件后再正式提交。</p><small>这会提交成员的原始版本，不会另建重复材料。</small><div v-if="teamDraft.content" class="submitted-copy"><small>草稿内容</small><p>{{ teamDraft.content }}</p></div></div>
        <div v-if="!canEdit && permission.reason && !['submitted', 'approved'].includes(material.status) && !['approved', 'completed', 'locked'].includes(task.status)" class="task-state-summary" :class="task.status"><el-icon><Lock /></el-icon><div><strong>协作权限</strong><p>{{ permission.reason }}</p></div><StatusTag :status="task.status" /></div>
        <template v-if="editingMode">
          <label class="editor-label demo-task-editor">我的记录<textarea v-model="body" rows="10" placeholder="在这里填写你的任务记录……" /><span>{{ body.length }} / 3000</span></label>
          <div class="attachment-box"><div><el-icon><UploadFilled /></el-icon><span><strong>选择任务附件</strong><small>文件将上传至受权限保护的项目空间</small></span></div><label class="secondary-button"><input type="file" multiple @change="addFiles">选择文件</label><div v-for="file in files" :key="`${file.name}-${file.size}`" class="file-chip"><el-icon><Paperclip /></el-icon>{{ file.name }}<button type="button" @click="files = files.filter((item) => item !== file)">×</button></div></div>
        </template>
        <template v-if="canEdit">
          <label v-if="isLeader" class="truth-check"><input v-model="truth" type="checkbox"><span><strong>我已按真实项目核对以上内容</strong><small>材料中的事实、数据和引用已经过人工确认。</small></span></label>
        <footer class="task-submit-row"><span>{{ teamDraft ? '成员草稿会原样进入审核，确认前请完成事实核对。' : isLeader ? '提交后教师可以查看完整版本历史。' : '你的草稿会保留在项目中，等待负责人确认。' }}</span><button v-if="teamDraft" class="primary-button" type="button" :disabled="loading" @click="submitTeamDraft">{{ loading ? '正在提交…' : '确认并提交成员草稿' }}</button><button v-else-if="isLeader" class="primary-button" type="button" :disabled="loading" @click="submit">{{ loading ? '正在上传并提交…' : task.status === 'revision_required' ? '重新提交任务' : '保存并提交' }}</button><button v-else class="secondary-button" type="button" :disabled="loading" @click="saveDraft">{{ loading ? '正在保存…' : '保存草稿' }}</button></footer></template>
      </section>
      <aside class="demo-task-aside">
        <section class="paper-card demo-task-side-card">
          <p class="eyebrow">当前章节</p><h2>{{ task.stage_name }}</h2><p class="muted">第 {{ task.stage_order }} 章 · {{ taskActionLabel(task.status) }}</p>
          <div class="demo-task-progress"><div class="progress-row"><span>章节任务</span><strong>{{ progress.completed }} / {{ progress.total }}</strong></div><div class="progress-track"><div class="progress-value" :style="{ width: `${progress.percent}%` }" /></div></div>
        </section>
        <section class="paper-card demo-task-side-card">
          <h2>需要一点思路？</h2><p class="muted">AI 只会围绕这项任务提问和给建议，不会替你直接提交。</p>
          <RouterLink class="primary-button" :to="aiCenterEntry">使用 AI 协助本任务 →</RouterLink>
          <details v-if="quickAgents.length" class="task-ai-options"><summary>选择其他任务工具</summary><div class="task-ai-options__list"><RouterLink v-for="agent in quickAgents" :key="agent.id" :to="aiQuickEntryLocation(projectId, taskId, agent.workflow || '', agent.key, project.project_type)"><strong>{{ agent.name }}</strong><small>{{ agent.quick_tasks?.[0] || '围绕当前任务开始一次结构化共创。' }}</small></RouterLink></div></details>
        </section>
      </aside>
    </div>
  </div>
  <EmptyState v-else-if="!dataLoading" title="任务尚不可用" description="项目可能尚未被教师认领，或你无权访问该任务。"><RouterLink class="secondary-button" :to="studentProjectRoute(projectId, 'map')">返回研究旅程</RouterLink></EmptyState>
</template>
<style scoped>
.demo-task-layout { display: grid; grid-template-columns: minmax(0, 1.58fr) minmax(260px, .72fr); gap: 20px; align-items: start; }
.demo-task-main, .demo-task-side-card { padding: 26px; }
.demo-task-main { min-width: 0; }
.demo-task-guidance { display: grid; gap: 6px; margin-top: 8px; }
.demo-task-guidance span { color: var(--muted); font-size: 12px; }
.demo-reference-download { width: fit-content; margin-top: 12px; }
.demo-task-editor { margin-top: 22px; }
.demo-task-aside { display: grid; gap: 14px; }
.demo-task-side-card h2 { margin: 5px 0 7px; font-size: 20px; }
.demo-task-side-card .primary-button { width: 100%; margin-top: 16px; box-sizing: border-box; }
.demo-task-progress { margin-top: 18px; }
.task-ai-options { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }
.task-ai-options summary { color: var(--moss-dark); cursor: pointer; font-size: 12px; font-weight: 700; }
.task-ai-options__list { display: grid; gap: 7px; margin-top: 10px; }
.task-ai-options__list a { display: grid; gap: 3px; border: 1px solid var(--line-dark); color: var(--moss-dark); border-radius: var(--radius-sm); padding: 8px 9px; font-size: 12px; text-decoration: none; background: var(--paper); }
.task-ai-options__list a:hover, .task-ai-options__list a:focus-visible { background: var(--sage-soft); border-color: var(--moss); }
.task-ai-options__list small, .task-ai-options__empty { color: var(--color-text-muted); line-height: 1.5; }
</style>
