<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AIConversationMessage, Project } from '../../api'
import type { AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

type ProjectDraft = {
  title: string
  problem: string
  plan: string
  project_type: Project['project_type']
}

const props = withDefaults(defineProps<{
  mode: AIWorkspaceMode
  message: AIConversationMessage
  draft?: string
  openingDraft?: ProjectDraft
  saving?: boolean
  creatingProject?: boolean
  canSaveMaterial?: boolean
  canCreateProject?: boolean
}>(), {
  draft: '',
  openingDraft: () => ({ title: '', problem: '', plan: '', project_type: 'research' }),
  saving: false,
  creatingProject: false,
  canSaveMaterial: false,
  canCreateProject: false,
})

const emit = defineEmits<{
  (event: 'update:draft', value: string): void
  (event: 'update:opening-draft', value: ProjectDraft): void
  (event: 'save-material'): void
  (event: 'create-project'): void
  (event: 'retry'): void
  (event: 'copy'): void
}>()

const createConfirmationOpen = ref(false)
const verificationOpen = ref(false)

const artifact = computed(() => props.message.artifact_payload)
const isOpening = computed(() => props.mode === 'opening')
const resultTitle = computed(() => {
  if (isOpening.value) return '开题草稿'
  if (props.mode === 'defense') return '成果表达建议'
  return '研究建议'
})
const hasOpeningResult = computed(() => Boolean(artifact.value && (
  artifact.value.candidates?.length
  || artifact.value.project_title
  || artifact.value.project_plan
  || artifact.value.project_type
)))
const hasEditableResult = computed(() => Boolean(artifact.value?.draft?.trim()))
const verificationItems = computed(() => props.message.verification_items || [])
const displayDraft = computed(() => props.draft || artifact.value?.draft || props.message.content || '')

watch(() => props.message.id, () => {
  createConfirmationOpen.value = false
  verificationOpen.value = false
})

function updateOpeningField(field: keyof ProjectDraft, value: string) {
  emit('update:opening-draft', { ...props.openingDraft, [field]: value } as ProjectDraft)
}

function requestCreateProject() {
  if (!props.canCreateProject || props.creatingProject) return
  createConfirmationOpen.value = true
}

function confirmCreateProject() {
  if (!props.canCreateProject || props.creatingProject) return
  createConfirmationOpen.value = false
  emit('create-project')
}
</script>

<template>
  <section v-if="(isOpening && hasOpeningResult) || (!isOpening && hasEditableResult)" class="ai-result-card" aria-label="需要确认的 AI 内容">
    <header class="ai-result-card__header">
      <div>
        <span class="eyebrow">需要你确认</span>
        <h3>{{ resultTitle }}</h3>
      </div>
      <span class="ai-result-card__status">{{ props.message.status === 'completed' ? '已生成' : '处理中' }}</span>
    </header>

    <div v-if="isOpening" class="ai-result-card__opening">
      <label>
        <span>项目标题</span>
        <input :value="props.openingDraft.title" type="text" @input="updateOpeningField('title', ($event.target as HTMLInputElement).value)" />
      </label>
      <label>
        <span>研究问题</span>
        <textarea :value="props.openingDraft.problem" rows="3" @input="updateOpeningField('problem', ($event.target as HTMLTextAreaElement).value)" />
      </label>
      <label>
        <span>初步方案</span>
        <textarea :value="props.openingDraft.plan" rows="3" @input="updateOpeningField('plan', ($event.target as HTMLTextAreaElement).value)" />
      </label>
      <label>
        <span>项目类型</span>
        <select :value="props.openingDraft.project_type" @change="updateOpeningField('project_type', ($event.target as HTMLSelectElement).value)">
          <option value="research">研究型</option>
          <option value="invention">发明型</option>
          <option value="engineering">工程型</option>
        </select>
      </label>
      <div class="ai-result-card__actions">
        <button class="secondary-button" type="button" @click="emit('copy')">复制草稿</button>
        <button class="secondary-button" type="button" :disabled="props.creatingProject" @click="emit('retry')">重新生成</button>
        <button class="primary-button" type="button" :disabled="!props.canCreateProject || props.creatingProject" @click="requestCreateProject">{{ props.creatingProject ? '创建中…' : '确认创建项目' }}</button>
      </div>
      <div v-if="createConfirmationOpen" class="ai-result-card__confirmation" role="alertdialog" aria-label="确认创建项目">
        <strong>确认使用当前草稿创建项目？</strong>
        <p>创建后会进入项目工作区，标题、问题和方案仍可在项目中继续完善。</p>
        <div class="ai-result-card__actions">
          <button class="secondary-button" type="button" :disabled="props.creatingProject" @click="createConfirmationOpen = false">返回编辑</button>
          <button class="primary-button" type="button" :disabled="props.creatingProject" @click="confirmCreateProject">确认创建项目</button>
        </div>
      </div>
    </div>

    <div v-else class="ai-result-card__editable">
      <textarea :value="displayDraft" rows="6" aria-label="可编辑 AI 草稿" @input="emit('update:draft', ($event.target as HTMLTextAreaElement).value)" />
      <div class="ai-result-card__meta">
        <span>核验项 {{ verificationItems.length }} 项 · 内容需要你核对后再使用</span>
        <button class="text-button" type="button" @click="verificationOpen = !verificationOpen">{{ verificationOpen ? '收起核验项' : '查看核验项' }}</button>
      </div>
      <ul v-if="verificationOpen && verificationItems.length" class="ai-result-card__verification">
        <li v-for="(item, index) in verificationItems" :key="index">{{ typeof item === 'string' ? item : item.item }}</li>
      </ul>
      <div class="ai-result-card__actions">
        <button class="secondary-button" type="button" @click="emit('copy')">复制</button>
        <button class="secondary-button" type="button" :disabled="props.saving" @click="emit('retry')">重新生成</button>
        <button class="primary-button" type="button" :disabled="!props.canSaveMaterial || props.saving" @click="emit('save-material')">{{ props.saving ? '保存中…' : '保存为材料' }}</button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ai-result-card { display: grid; gap: 14px; margin: 14px 0 0; padding: 16px; border: 1px solid var(--sage-line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-soft); }
.ai-result-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.ai-result-card__header h3 { margin: 4px 0 0; color: var(--ink); font: 700 18px/1.35 var(--sans); }
.ai-result-card__status { flex: 0 0 auto; padding: 5px 9px; border: 1px solid var(--sage-line); border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); font-size: 10px; font-weight: 700; }
.ai-result-card__opening, .ai-result-card__editable { display: grid; gap: 11px; }
.ai-result-card__opening { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.ai-result-card__opening label { display: grid; gap: 5px; min-width: 0; }
.ai-result-card__opening label:nth-child(2), .ai-result-card__opening label:nth-child(3), .ai-result-card__opening .ai-result-card__actions, .ai-result-card__confirmation { grid-column: 1 / -1; }
.ai-result-card label > span { color: var(--muted); font-size: 11px; font-weight: 700; }
.ai-result-card input, .ai-result-card textarea, .ai-result-card select { width: 100%; box-sizing: border-box; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); padding: 9px 10px; background: var(--paper-soft); color: var(--ink); font: inherit; font-size: 12px; line-height: 1.55; }
.ai-result-card textarea { resize: vertical; }
.ai-result-card input:focus, .ai-result-card textarea:focus, .ai-result-card select:focus { outline: 2px solid var(--sage-line); outline-offset: 1px; border-color: var(--moss); }
.ai-result-card__editable > textarea { min-height: 132px; }
.ai-result-card__meta { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--muted); font-size: 10px; }
.ai-result-card__verification { display: grid; gap: 5px; margin: 0; padding: 10px 10px 10px 25px; border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--muted); font-size: 11px; line-height: 1.6; }
.ai-result-card__actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.ai-result-card__confirmation { display: grid; gap: 7px; padding: 12px; border: 1px solid var(--sage-line); border-radius: var(--radius-sm); background: var(--sage-soft); }
.ai-result-card__confirmation strong { color: var(--moss-dark); font-size: 12px; }
.ai-result-card__confirmation p { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.55; }
.ai-result-card .primary-button, .ai-result-card .secondary-button, .ai-result-card .text-button { min-height: 32px; padding: 7px 12px; border-radius: var(--radius-sm); font: inherit; font-size: 11px; cursor: pointer; }
.ai-result-card .primary-button { border: 1px solid var(--moss-dark); background: var(--moss); color: #fff; font-weight: 700; }
.ai-result-card .primary-button:hover:not(:disabled), .ai-result-card .primary-button:focus-visible { background: var(--moss-dark); }
.ai-result-card .secondary-button { border: 1px solid var(--line-dark); background: var(--paper); color: var(--moss-dark); }
.ai-result-card .secondary-button:hover:not(:disabled), .ai-result-card .secondary-button:focus-visible { border-color: var(--moss); background: var(--paper-soft); }
.ai-result-card .text-button { min-height: auto; padding: 0; border: 0; background: transparent; color: var(--moss-dark); text-decoration: underline; }
.ai-result-card button:disabled { cursor: wait; opacity: .55; }
@media (max-width: 720px) { .ai-result-card__opening { grid-template-columns: 1fr; } .ai-result-card__opening label:nth-child(2), .ai-result-card__opening label:nth-child(3), .ai-result-card__opening .ai-result-card__actions, .ai-result-card__confirmation { grid-column: auto; } .ai-result-card__meta { align-items: flex-start; flex-direction: column; } }
</style>
