<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowRight, CircleCheck, Clock, Download, Lock, MagicStick, Paperclip, UploadFilled, Warning } from '@element-plus/icons-vue'
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

const route = useRoute(); const loading = ref(false); const body = ref(''); const truth = ref(false); const files = ref<File[]>([]); const feedback = ref<FeedbackState | null>(null); const aiAgents = ref<AIAgent[]>([])
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
onMounted(() => {
  student.refreshProject(projectId.value).catch((reason) => { feedback.value = makeFeedback('error', errorMessage(reason), '请刷新页面重试。', '重试') })
  getAIAgents().then((response) => { aiAgents.value = response.data }).catch(() => { aiAgents.value = [] })
})
watch(material, (value) => { body.value = value?.revisions.at(-1)?.content ?? ''; truth.value = false; files.value = [] }, { immediate: true })
function addFiles(event: Event) { files.value = Array.from((event.target as HTMLInputElement).files ?? []) }
function retry() { feedback.value = null; student.refreshProject(projectId.value).catch((reason) => { feedback.value = makeFeedback('error', errorMessage(reason), '请稍后重试。', '重试') }) }
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
  <div v-if="task && project && material" class="page task-page">
    <PageHeader :breadcrumbs="['我的项目', project.title, '研究旅程', task.title]" :eyebrow="`第 ${task.stage_order} 章 · ${task.stage_name}`" :title="task.title" :description="task.description">
      <template #actions><StatusTag :status="task.status" /></template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="feedback?.actionLabel === '回到研究旅程' ? $router.push(`/student/projects/${project.id}/map`) : retry()" />
    <section class="task-progress-panel paper-card" aria-label="项目任务进度">
      <div><span class="eyebrow">项目完成度</span><strong>{{ progress.completed }} / {{ progress.total }} 项任务已通过</strong></div>
      <div class="task-progress-track" aria-hidden="true"><i :style="{ width: `${progress.percent}%` }" /></div>
      <span class="task-progress-percent">{{ progress.percent }}%</span>
      <small>当前任务：{{ taskActionLabel(task.status) }}</small>
    </section>
    <div class="task-workspace">
      <aside class="task-rail">
        <RouterLink :to="`/student/projects/${project.id}/map`">← 返回任务地图</RouterLink>
        <p class="eyebrow">需要上传什么</p>
        <div v-if="material.guidance" class="upload-guide"><p>{{ material.guidance }}</p></div>
        <template v-else>
          <div v-for="(evidence, index) in task.evidence_requirements" :key="evidence" class="evidence-item"><span>{{ index + 1 }}</span><p>{{ evidence }}</p></div>
          <p v-if="!task.evidence_requirements.length">请提交与任务目标直接相关的文字或附件证据。</p>
        </template>
        <section v-if="material.reference" class="reference-box">
          <p class="eyebrow">参考模板</p>
          <a class="secondary-button" :href="material.reference.url" :download="material.reference.original_name">
            <el-icon><Download /></el-icon> 下载空白范本
          </a>
          <small>已按上面指引排好章节，下载后直接填写。</small>
        </section>
        <div class="reward-seal"><small>完成奖励</small><strong>+{{ task.xp_reward }} XP</strong></div>
        <section class="task-ai-quick" aria-label="任务 AI 快捷入口">
          <p class="eyebrow">AI 共创</p>
          <RouterLink v-for="agent in quickAgents" :key="agent.id" :to="aiQuickEntryLocation(projectId, taskId, agent.workflow || '', agent.key, project.project_type)">{{ agent.quick_tasks?.[0] || agent.name }}</RouterLink>
          <small v-if="!quickAgents.length">当前阶段暂无可用快捷工具，可前往共创中心选择。</small>
        </section>
      </aside>
      <section class="task-paper paper-card" :class="{ 'task-paper--read-only': !canEdit }">
        <div v-if="material.status !== 'submitted' && !['approved', 'completed'].includes(task.status)" class="task-state-summary" :class="task.status">
          <el-icon><Warning v-if="task.status === 'revision_required'" /><Clock v-else-if="task.status === 'pending_review'" /><Lock v-else-if="task.status === 'locked'" /><CircleCheck v-else /></el-icon>
          <div><strong>{{ taskActionLabel(task.status) }}</strong><p>{{ statusMessage }}</p></div>
          <StatusTag :status="task.status" />
        </div>
        <div v-if="material.status === 'revision_required'" class="teacher-feedback"><strong>老师反馈 · 修订任务</strong><p>{{ material.revisions.at(-1)?.review_comment || '请根据教师意见补充证据。' }}</p><small>新提交会创建独立版本，旧版本完整保留。</small></div>
        <div v-else-if="material.status === 'submitted'" class="submitted-state"><el-icon><Clock /></el-icon><div><strong>已提交，等待教师审核</strong><p>你可以离开此页面；审核结果会通过通知中心和任务地图同步。</p><div v-if="body" class="submitted-copy"><small>已提交版本</small><p>{{ body }}</p></div></div></div>
        <div v-else-if="['approved', 'completed'].includes(task.status)" class="approved-state"><el-icon><CircleCheck /></el-icon><div><strong>任务已通过</strong><p>{{ nextTask ? `下一项：${nextTask.title}` : '所有任务都已完成，可以进入报告装配。' }}</p></div><RouterLink v-if="nextTask" class="secondary-button" :to="`/student/projects/${project.id}/tasks/${nextTask.id}`">下一项 <ArrowRight /></RouterLink></div>
        <div v-if="teamDraft" class="teacher-feedback"><strong>成员草稿 · 等待负责人确认</strong><p>{{ teamDraft.author_name }} 已完成一份草稿。请核对事实、数据和附件后再正式提交。</p><small>这会提交成员的原始版本，不会另建重复材料。</small><div v-if="teamDraft.content" class="submitted-copy"><small>草稿内容</small><p>{{ teamDraft.content }}</p></div></div>
        <div v-if="!canEdit && permission.reason && !['submitted', 'approved'].includes(material.status) && !['approved', 'completed', 'locked'].includes(task.status)" class="task-state-summary" :class="task.status"><el-icon><Lock /></el-icon><div><strong>协作权限</strong><p>{{ permission.reason }}</p></div><StatusTag :status="task.status" /></div>
        <template v-if="editingMode">
          <label class="editor-label">我的观察与思考<textarea v-model="body" rows="12" placeholder="用自己的语言写下观察、过程、数据与思考……" /><span>{{ body.length }} / 3000</span></label>
          <div class="attachment-box"><div><el-icon><UploadFilled /></el-icon><span><strong>选择任务附件</strong><small>文件将上传至受权限保护的项目空间</small></span></div><label class="secondary-button"><input type="file" multiple @change="addFiles">选择文件</label><div v-for="file in files" :key="`${file.name}-${file.size}`" class="file-chip"><el-icon><Paperclip /></el-icon>{{ file.name }}<button type="button" @click="files = files.filter((item) => item !== file)">×</button></div></div>
        </template>
        <template v-if="canEdit">
          <label v-if="isLeader" class="truth-check"><input v-model="truth" type="checkbox"><span><strong>我已按真实项目核对以上内容</strong><small>材料中的事实、数据和引用已经过人工确认。</small></span></label>
        <footer class="task-submit-row"><span>{{ teamDraft ? '成员草稿会原样进入审核，确认前请完成事实核对。' : isLeader ? '提交后教师可以查看完整版本历史。' : '你的草稿会保留在项目中，等待负责人确认。' }}</span><button v-if="teamDraft" class="primary-button" type="button" :disabled="loading" @click="submitTeamDraft">{{ loading ? '正在提交…' : '确认并提交成员草稿' }}</button><button v-else-if="isLeader" class="primary-button" type="button" :disabled="loading" @click="submit">{{ loading ? '正在上传并提交…' : task.status === 'revision_required' ? '重新提交任务' : '提交任务材料' }}</button><button v-else class="secondary-button" type="button" :disabled="loading" @click="saveDraft">{{ loading ? '正在保存…' : '保存我的草稿' }}</button></footer></template>
      </section>
      <aside class="ai-companion">
        <p class="eyebrow">AI 共创中心</p>
        <h2>围绕当前任务共创</h2>
        <p>使用结构化草稿、核对项与下一步行动，生成后可保存为材料草稿。</p>
        <RouterLink class="primary-button" :to="aiCenterEntry">打开任务工具 →</RouterLink>
      </aside>
    </div>
  </div>
  <EmptyState v-else title="任务尚不可用" description="项目可能尚未被教师认领，或你无权访问该任务。" />
</template>
<style scoped>
.task-ai-quick { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--line); display: grid; gap: 7px; }
.task-ai-quick .eyebrow { margin: 0 0 2px; }
.task-ai-quick a { border: 1px solid var(--line-dark); color: var(--moss-dark); border-radius: var(--radius-sm); padding: 7px 9px; font-size: 12px; text-decoration: none; background: var(--paper); }
.task-ai-quick a:hover { background: var(--sage-soft); border-color: var(--moss); }
</style>
