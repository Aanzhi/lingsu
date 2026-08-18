<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Check, Document, Download, RefreshLeft, UploadFilled } from '@element-plus/icons-vue'
import { errorMessage, resetMaterialReference, setMaterialReference, type Material } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { teacherStore } from '../../stores/teacher'
import type { ApiTask } from '../../stores/studentApiModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { auth } from '../../stores/auth'

const route = useRoute(); const router = useRouter(); const feedback = ref<FeedbackState | null>(null); const busy = ref<number | null>(null)
const projectId = computed(() => Number(route.params.id))
const project = computed(() => teacherStore.state.guided.find((item) => item.id === projectId.value)
  ?? teacherStore.state.archived.find((item) => item.id === projectId.value)
  ?? teacherStore.state.trashed.find((item) => item.id === projectId.value))

interface MaterialDraft { guidance: string; file: File | null }
const drafts = reactive<Record<number, MaterialDraft>>({})

const tasks = computed<ApiTask[]>(() => teacherStore.state.detail.tasks)
const materials = computed<Material[]>(() => teacherStore.state.detail.materials)
const isPrimary = computed(() => project.value?.primary_teacher === auth.user.value?.id)

const groups = computed(() => {
  const byStage = new Map<number, { stageOrder: number; stageName: string; items: { task: ApiTask; material: Material }[] }>()
  tasks.value.forEach((task) => {
    const material = materials.value.find((m) => m.task === task.id)
    if (!material) return
    const entry = byStage.get(task.stage_order) ?? { stageOrder: task.stage_order, stageName: task.stage_name, items: [] }
    entry.items.push({ task, material })
    byStage.set(task.stage_order, entry)
  })
  return [...byStage.values()].sort((a, b) => a.stageOrder - b.stageOrder)
})

function initDrafts() {
  materials.value.forEach((material) => {
    if (!(material.id in drafts)) drafts[material.id] = { guidance: material.guidance ?? '', file: null }
    else drafts[material.id].guidance = material.guidance ?? ''
  })
}

async function load() {
  feedback.value = null
  try { await teacherStore.loadProjectDetail(projectId.value); initDrafts() }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '项目材料没有加载完成，请重试。', '重试') }
}
async function save(material: Material) {
  busy.value = material.id; feedback.value = null
  try {
    await setMaterialReference(material.id, { guidance: drafts[material.id]?.guidance ?? '', reference_file: drafts[material.id]?.file ?? undefined })
    await teacherStore.loadProjectDetail(projectId.value); initDrafts()
    feedback.value = makeFeedback('success', '材料参考范本已更新。', '学生端会立即看到新的指引与范本。')
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
  <div v-if="project" class="page teacher-template-page">
    <PageHeader
      :breadcrumbs="['指导项目', project.title, '材料模板']"
      :eyebrow="`${project.project_type} · ${isPrimary ? '主指导教师' : '协导'}`"
      :title="`材料参考范本配置`"
      :description="project.title"
    >
      <template #actions>
        <RouterLink class="secondary-button" :to="`/teacher/projects/${project.id}`">← 返回项目</RouterLink>
        <StatusTag :status="project.status" />
      </template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="!isPrimary" class="read-only-banner">只有主指导教师可以修改本项目材料的参考范本。</p>
    <EmptyState v-if="!groups.length" title="暂无材料" description="教师认领项目后，研究旅程会自动生成材料清单。" />
    <section v-for="group in groups" :key="group.stageOrder" class="template-stage paper-card">
      <header class="template-stage__head">
        <span class="template-stage__pin">{{ String(group.stageOrder).padStart(2, '0') }}</span>
        <h2>{{ group.stageName }}</h2>
      </header>
      <article v-for="{ task, material } in group.items" :key="material.id" class="template-material">
        <div class="template-material__head">
          <strong>{{ material.title }}</strong>
          <small>{{ task.title }} · 报告章节：{{ material.report_section || '—' }}</small>
        </div>
        <label class="template-material__label">材料指引（学生端「需要上传什么」会显示这段）</label>
        <el-input
          v-model="drafts[material.id].guidance"
          type="textarea"
          :rows="3"
          :disabled="!isPrimary || busy === material.id"
          placeholder="说明这份材料要写什么、包含哪些要点……"
        />
        <div class="template-material__file">
          <span class="template-material__file-meta">
            <el-icon><Document /></el-icon>
            <template v-if="material.reference">
              当前范本：<a :href="material.reference.url" :download="material.reference.original_name">{{ material.reference.original_name }}</a>
            </template>
            <template v-else>暂无自定义范本，将使用系统动态生成的空白范本。</template>
          </span>
          <label class="secondary-button" :class="{ 'is-disabled': !isPrimary }">
            <input type="file" accept=".docx,.md,.pdf" :disabled="!isPrimary" @change="pickFile(material.id, $event)">
            <el-icon><UploadFilled /></el-icon> 选择范本文件
          </label>
          <span v-if="drafts[material.id]?.file" class="template-material__file-picked">{{ drafts[material.id].file!.name }}</span>
        </div>
        <div class="template-material__actions">
          <button class="primary-button" type="button" :disabled="!isPrimary || busy === material.id" @click="save(material)">
            <el-icon><Check /></el-icon> {{ busy === material.id ? '保存中…' : '保存修改' }}
          </button>
          <button class="ghost-button" type="button" :disabled="!isPrimary || busy === material.id" @click="reset(material)">
            <el-icon><RefreshLeft /></el-icon> 恢复系统默认
          </button>
          <a v-if="material.reference" class="text-button" :href="material.reference.url" :download="material.reference.original_name">
            <el-icon><Download /></el-icon> 下载当前范本
          </a>
        </div>
      </article>
    </section>
  </div>
  <EmptyState v-else title="项目不可用" description="项目可能不存在，或你无权访问。" />
</template>

<style scoped>
.teacher-template-page { max-width: 920px; margin: 0 auto; }
.read-only-banner {
  margin-bottom: 18px; padding: 10px 14px; border: 1px solid var(--amber-line); background: var(--amber-soft);
  border-radius: var(--radius-md); color: var(--clay-deep); font-size: 12.5px;
}
.template-stage { padding: 18px 22px; margin-bottom: 18px; }
.template-stage__head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.template-stage__pin {
  width: 30px; height: 30px; display: grid; place-items: center; font: 700 12px var(--serif);
  color: #fff; background: linear-gradient(135deg, var(--moss, #4c7245), var(--moss-dark, #315833));
  border-radius: 50%; flex: 0 0 auto;
}
.template-stage__head h2 { margin: 0; font: 700 16px/1.3 var(--serif); color: var(--ink, #2c3327); }
.template-material { padding: 14px 0; border-top: 1px dashed var(--line); }
.template-material:first-of-type { border-top: 0; padding-top: 0; }
.template-material__head { display: flex; flex-direction: column; gap: 2px; margin-bottom: 8px; }
.template-material__head strong { font-size: 14px; color: var(--ink, #2c3327); }
.template-material__head small { color: var(--muted, #7a7d70); font-size: 12px; }
.template-material__label { display: block; margin: 6px 0 6px; font-size: 12px; font-weight: 700; color: var(--moss-dark, #315833); }
.template-material__file {
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin-top: 10px; padding: 10px 12px; border: 1px dashed var(--sage-line); border-radius: 8px; background: var(--paper, #fff);
}
.template-material__file-meta { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--muted, #7a7d70); min-width: 0; }
.template-material__file-meta a { color: var(--moss-dark, #315833); font-weight: 600; }
.template-material__file .secondary-button { display: inline-flex; align-items: center; gap: 6px; margin: 0; }
.template-material__file .secondary-button.is-disabled { opacity: .55; pointer-events: none; }
.template-material__file .secondary-button input { display: none; }
.template-material__file-picked { font-size: 12px; color: var(--moss-dark, #315833); font-weight: 600; }
.template-material__actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
.template-material__actions .primary-button, .template-material__actions .ghost-button {
  display: inline-flex; align-items: center; gap: 6px;
}
.template-material__actions .ghost-button {
  background: transparent; border: 1px solid var(--line, #d8d8cf); color: var(--muted, #7a7d70);
  border-radius: 999px; padding: 7px 14px; font: 700 13px var(--sans, sans-serif); cursor: pointer;
}
.template-material__actions .ghost-button:hover:not(:disabled) { border-color: var(--clay, #b5654a); color: var(--clay, #b5654a); }
.template-material__actions .text-button {
  display: inline-flex; align-items: center; gap: 5px; color: var(--moss-dark, #315833);
  font-size: 12.5px; font-weight: 600; text-decoration: none;
}
.template-material__actions button:disabled { opacity: .55; cursor: not-allowed; }
</style>
