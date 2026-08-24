<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown, Check, Document, Download, RefreshLeft, UploadFilled } from '@element-plus/icons-vue'
import { errorMessage, resetMaterialReference, setMaterialReference, type Material, type ProjectTask } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { teacherStore } from '../../stores/teacher'
import { projectJourneySummary, type ApiTask } from '../../stores/studentApiModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { auth } from '../../stores/auth'
import { projectTypeLabel } from '../../stores/presentationModel'

const route = useRoute(); const feedback = ref<FeedbackState | null>(null); const busy = ref<number | null>(null); const loading = ref(true)
const openStage = ref<number | null>(1)
const editingMaterialId = ref<number | null>(null)
const projectId = computed(() => Number(route.params.id))
const project = computed(() => teacherStore.state.guided.find((item) => item.id === projectId.value)
  ?? teacherStore.state.archived.find((item) => item.id === projectId.value)
  ?? teacherStore.state.trashed.find((item) => item.id === projectId.value))

interface MaterialDraft { guidance: string; file: File | null }
const drafts = reactive<Record<number, MaterialDraft>>({})

const tasks = computed(() => teacherStore.state.detail.projectId === projectId.value ? teacherStore.state.detail.tasks : [])
const materials = computed(() => teacherStore.state.detail.projectId === projectId.value ? teacherStore.state.detail.materials : [])
const isPrimary = computed(() => project.value?.primary_teacher === auth.user.value?.id)

function compatTaskStatus(task: ProjectTask) {
  if (task.legacy_status === 'locked') return 'locked'
  return task.status === 'in_progress' ? 'available' : task.status
}

const legacyTasks = computed<ApiTask[]>(() => tasks.value.map((task) => ({ ...task, status: compatTaskStatus(task) })))

const journey = computed(() => projectJourneySummary(legacyTasks.value, materials.value))
const groups = computed(() => journey.value.chapters.map((chapter) => ({
  stageOrder: chapter.index,
  stageName: chapter.name,
  items: chapter.steps.flatMap((step) => {
    const task = tasks.value.find((item) => item.id === step.id)
    const material = materials.value.find((item) => item.id === step.materialId)
    return task && material ? [{ task, material }] : []
  }),
})))
const selectedTemplateEntry = computed(() => groups.value.flatMap((group) => group.items).find(({ material }) => material.id === editingMaterialId.value) ?? null)

function draftFor(material: Material) {
  if (!(material.id in drafts)) {
    drafts[material.id] = { guidance: material.guidance ?? '', file: null }
  }
  return drafts[material.id]
}

function initDrafts() {
  materials.value.forEach((material) => {
    const draft = draftFor(material)
    draft.guidance = material.guidance ?? ''
    draft.file = null
  })
}

async function load() {
  loading.value = true
  feedback.value = null
  try {
    await Promise.all([teacherStore.load(), teacherStore.loadArchived(), teacherStore.loadTrashed()])
    await teacherStore.loadProjectDetail(projectId.value)
    initDrafts()
    openStage.value = groups.value[0]?.stageOrder ?? null
  }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '项目材料没有加载完成，请重试。', '重试') }
  finally { loading.value = false }
}
async function save(material: Material) {
  busy.value = material.id; feedback.value = null
  try {
    await setMaterialReference(material.id, { guidance: drafts[material.id]?.guidance ?? '', reference_file: drafts[material.id]?.file ?? undefined })
    await teacherStore.loadProjectDetail(projectId.value); initDrafts()
    feedback.value = makeFeedback('success', '材料参考范本已更新。', '学生端会立即看到新的指引与范本。')
    editingMaterialId.value = null
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '修改没有保存，可以重试。', '重试')
  } finally { busy.value = null }
}
async function reset(material: Material) {
  busy.value = material.id; feedback.value = null
  try {
    await resetMaterialReference(material.id)
    await teacherStore.loadProjectDetail(projectId.value); initDrafts()
    feedback.value = makeFeedback('success', '已恢复为系统默认范本。', '覆盖内容已清除，学生将看到模板自带指引。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '重置没有生效，可以重试。', '重试')
  } finally { busy.value = null }
}
function pickFile(materialId: number, event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null
  if (!(materialId in drafts)) drafts[materialId] = { guidance: '', file }
  drafts[materialId].file = file
}
onMounted(load); watch(projectId, load)
</script>

<template>
  <p v-if="loading" class="loading-state" role="status">正在读取材料模板…</p>
  <div v-if="project && !loading" class="page teacher-template-page">
    <PageHeader
      eyebrow="材料范本"
      title="配置材料范本"
      description="范本只定义学生需要提交的材料，不重复呈现项目进度和审核列表。"
    >
      <template #actions>
        <RouterLink class="secondary-button" :to="`/teacher/projects/${project.id}`">返回指导项目</RouterLink>
      </template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="!isPrimary" class="read-only-banner">只有主指导教师可以修改本项目材料的参考范本。</p>
    <div class="demo-template-layout"><div class="demo-template-main"><section class="paper-card demo-template-intro"><p class="eyebrow">当前项目 · {{ project.title }}</p><h2>五章节材料范本</h2><p class="muted">学生会按下面的结构看到任务要求，你可以在这里调整说明和必填项。</p></section>
    <EmptyState v-if="!groups.length" title="暂无材料" description="教师认领项目后，研究旅程会自动生成材料清单。" />
    <section v-for="group in groups" :key="group.stageOrder" class="template-stage template-accordion paper-card" :class="{ 'is-open': openStage === group.stageOrder }">
      <button class="template-stage__head" type="button" :aria-expanded="openStage === group.stageOrder" :aria-controls="`template-stage-${group.stageOrder}`" @click="openStage = openStage === group.stageOrder ? null : group.stageOrder">
        <span class="template-stage__pin">{{ String(group.stageOrder).padStart(2, '0') }}</span>
        <h2>{{ group.stageName }}</h2>
        <span class="template-stage__count">{{ group.items.length }} 项材料</span>
        <el-icon class="template-stage__chevron" aria-hidden="true"><ArrowDown /></el-icon>
      </button>
      <div v-show="openStage === group.stageOrder" :id="`template-stage-${group.stageOrder}`" class="template-stage__body">
      <article v-for="{ task, material } in group.items" :key="material.id" class="template-material-row">
        <div class="template-material__head"><strong>{{ material.title }}</strong><small>{{ task.title }} · 报告章节：{{ material.report_section || '—' }}</small></div>
        <span class="template-material-row__state">{{ material.reference ? '已有自定义范本' : '使用系统范本' }}</span>
        <button class="text-link" type="button" :disabled="!isPrimary" @click="editingMaterialId = material.id">编辑</button>
      </article>
      </div>
    </section>
    </div><aside class="demo-template-status paper-card"><h2>范本状态</h2><div class="demo-template-status-row"><span>学生可见</span><StatusTag status="published" /></div><div class="demo-template-status-row"><span>最近更新</span><strong>今天</strong></div><button class="primary-button" type="button" :disabled="!isPrimary">保存范本</button></aside></div>

    <el-dialog :model-value="Boolean(selectedTemplateEntry)" title="编辑材料参考范本" width="680px" @close="editingMaterialId = null">
      <template v-if="selectedTemplateEntry">
        <div class="template-dialog-heading"><p class="eyebrow">{{ selectedTemplateEntry.task.title }}</p><h2>{{ selectedTemplateEntry.material.title }}</h2><small>报告章节：{{ selectedTemplateEntry.material.report_section || '—' }}</small></div>
        <label class="template-material__label">材料指引（学生端「需要上传什么」会显示这段）</label>
        <el-input v-model="draftFor(selectedTemplateEntry.material).guidance" type="textarea" :rows="5" :disabled="!isPrimary || busy === selectedTemplateEntry.material.id" placeholder="说明这份材料要写什么、包含哪些要点……" />
        <div class="template-material__file">
          <span class="template-material__file-meta">
            <el-icon><Document /></el-icon>
            <template v-if="selectedTemplateEntry.material.reference">
              当前范本：<a :href="selectedTemplateEntry.material.reference.url" :download="selectedTemplateEntry.material.reference.original_name">{{ selectedTemplateEntry.material.reference.original_name }}</a>
            </template>
            <template v-else>暂无自定义范本，将使用系统动态生成的空白范本。</template>
          </span>
          <label class="secondary-button" :class="{ 'is-disabled': !isPrimary }">
            <input type="file" accept=".docx,.md,.pdf" :disabled="!isPrimary" @change="pickFile(selectedTemplateEntry.material.id, $event)">
            <el-icon><UploadFilled /></el-icon> 选择范本文件
          </label>
          <span v-if="drafts[selectedTemplateEntry.material.id]?.file" class="template-material__file-picked">{{ drafts[selectedTemplateEntry.material.id].file!.name }}</span>
        </div>
        <div class="template-material__actions">
          <button class="primary-button" type="button" :disabled="!isPrimary || busy === selectedTemplateEntry.material.id" @click="save(selectedTemplateEntry.material)">
            <el-icon><Check /></el-icon> {{ busy === selectedTemplateEntry.material.id ? '保存中…' : '保存修改' }}
          </button>
          <button class="ghost-button" type="button" :disabled="!isPrimary || busy === selectedTemplateEntry.material.id" @click="reset(selectedTemplateEntry.material)">
            <el-icon><RefreshLeft /></el-icon> 恢复系统默认
          </button>
          <a v-if="selectedTemplateEntry.material.reference" class="text-button" :href="selectedTemplateEntry.material.reference.url" :download="selectedTemplateEntry.material.reference.original_name">
            <el-icon><Download /></el-icon> 下载当前范本
          </a>
        </div>
      </template>
    </el-dialog>
  </div>
  <EmptyState v-else-if="!loading" title="项目不可用" description="项目可能不存在，或你无权访问。"><RouterLink class="secondary-button" to="/teacher/projects">返回指导项目</RouterLink></EmptyState>
</template>

<style scoped>
.teacher-template-page { max-width: 1120px; margin: 0 auto; }
.demo-template-layout { display: grid; grid-template-columns: minmax(0, 1fr) 270px; gap: 20px; align-items: start; }
.demo-template-main { display: grid; gap: 10px; }
.demo-template-intro, .demo-template-status { padding: 26px; }
.demo-template-intro h2, .demo-template-status h2 { margin: 5px 0 7px; font-size: 20px; }
.demo-template-status { display: grid; gap: 0; }
.demo-template-status-row { display: flex; align-items: center; justify-content: space-between; min-height: 48px; border-top: 1px solid var(--line); font-size: 12px; }
.demo-template-status-row:first-of-type { margin-top: 10px; }
.demo-template-status .primary-button { width: 100%; margin-top: 18px; }
.read-only-banner {
  margin-bottom: 18px; padding: 10px 14px; border: 1px solid var(--amber-line); background: var(--amber-soft);
  border-radius: var(--radius-md); color: var(--clay-deep); font-size: 12.5px;
}
.template-stage { padding: 0; margin-bottom: 10px; overflow: hidden; }
.template-stage__head { width: 100%; display: flex; align-items: center; gap: 10px; padding: 15px 18px; border: 0; background: var(--paper); color: inherit; cursor: pointer; text-align: left; }
.template-stage.is-open .template-stage__head { background: var(--sage-soft); }
.template-stage__pin {
  width: 30px; height: 30px; display: grid; place-items: center; font: 700 12px var(--sans);
  color: #fff; background: var(--moss);
  border-radius: 50%; flex: 0 0 auto;
}
.template-stage__head h2 { margin: 0; font: 700 16px/1.3 var(--sans); color: var(--ink); }
.template-stage__count { margin-left: auto; color: var(--muted); font-size: 11px; }
.template-stage__chevron { color: var(--moss-dark); font-size: 18px; transition: transform .18s ease; }
.template-stage.is-open .template-stage__chevron { transform: rotate(180deg); }
.template-stage__body { padding: 0 18px 12px; }
.template-material-row { display: grid; grid-template-columns: minmax(0, 1fr) auto 54px; gap: 16px; align-items: center; min-height: 58px; padding: 9px 4px; border-top: 1px solid var(--line); }
.template-material-row__state { color: var(--muted); font-size: 11px; }
.template-material__head { display: flex; flex-direction: column; gap: 2px; margin-bottom: 8px; }
.template-material__head strong { font-size: 14px; color: var(--ink); }
.template-material__head small { color: var(--muted); font-size: 12px; }
.template-material-row .template-material__head { margin-bottom: 0; }
.template-dialog-heading { margin-bottom: 18px; }
.template-dialog-heading h2 { margin: 4px 0; font: 700 20px/1.35 var(--sans); color: var(--ink); }
.template-dialog-heading small { color: var(--muted); }
.template-material__label { display: block; margin: 6px 0 6px; font-size: 12px; font-weight: 700; color: var(--moss-dark); }
.template-material__file {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin-top: 10px; padding: 10px 12px; border: 1px dashed var(--sage-line); border-radius: var(--radius-sm); background: var(--paper);
}
.template-material__file-meta { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--muted); min-width: 0; }
.template-material__file-meta a { color: var(--moss-dark); font-weight: 600; }
.template-material__file .secondary-button { display: inline-flex; align-items: center; gap: 6px; margin: 0; }
.template-material__file .secondary-button.is-disabled { opacity: .55; pointer-events: none; }
.template-material__file .secondary-button input { display: none; }
.template-material__file-picked { font-size: 12px; color: var(--moss-dark); font-weight: 600; }
.template-material__actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
.template-material__actions .primary-button, .template-material__actions .ghost-button {
  display: inline-flex; align-items: center; gap: 6px;
}
.template-material__actions .ghost-button {
  background: transparent; border: 1px solid var(--line); color: var(--muted);
  border-radius: var(--radius-sm); padding: 7px 14px; font: 700 13px var(--sans); cursor: pointer;
}
.template-material__actions .ghost-button:hover:not(:disabled) { border-color: var(--clay); color: var(--clay); }
.template-material__actions .text-button {
  display: inline-flex; align-items: center; gap: 5px; color: var(--moss-dark);
  font-size: 12.5px; font-weight: 600; text-decoration: none;
}
.template-material__actions button:disabled { opacity: .55; cursor: not-allowed; }
</style>
