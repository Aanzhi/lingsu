<script setup lang="ts">
import { ref } from 'vue'
import type { AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

const props = defineProps<{
  mode: AIWorkspaceMode
  status: string
  canSaveMaterial: boolean
  canCreateProject: boolean
  saving?: boolean
}>()

const emit = defineEmits<{
  (event: 'save-material'): void
  (event: 'create-project'): void
}>()

const confirmation = ref<'save_material' | 'create_project' | null>(null)
function request(action: 'save_material' | 'create_project') {
  confirmation.value = confirmation.value === action ? null : action
}
function confirmAction() {
  if (confirmation.value === 'save_material') emit('save-material')
  if (confirmation.value === 'create_project') emit('create-project')
  confirmation.value = null
}
</script>

<template>
  <div v-if="props.status === 'completed' && (props.canSaveMaterial || props.canCreateProject)" class="ai-draft-actions">
    <div class="ai-draft-actions__buttons">
      <button v-if="props.canSaveMaterial" type="button" class="save-draft" :disabled="props.saving" @click="request('save_material')">保存为材料</button>
      <button v-if="props.canCreateProject" type="button" class="save-draft" :disabled="props.saving" @click="request('create_project')">用此报告创建项目</button>
    </div>
    <div v-if="confirmation" class="ai-draft-actions__confirm" role="alertdialog" aria-label="确认 AI 草稿操作">
      <strong>{{ confirmation === 'save_material' ? '确认保存这份草稿？' : '确认用此报告创建项目？' }}</strong>
      <small>{{ confirmation === 'save_material' ? '保存前请核对内容、引用和实验数据。' : '项目创建后会进入项目旅程，AI 不会替你提交审核。' }}</small>
      <div><button type="button" class="secondary-button" @click="confirmation = null">取消</button><button type="button" class="primary-button" :disabled="props.saving" @click="confirmAction">确认{{ confirmation === 'save_material' ? '保存' : '创建' }}</button></div>
    </div>
  </div>
</template>

<style scoped>
.ai-draft-actions { display: grid; gap: 8px; }
.ai-draft-actions__buttons { display: flex; flex-wrap: wrap; gap: 7px; }
.ai-draft-actions__confirm { display: grid; gap: 5px; padding: 10px; border: 1px solid var(--sage-line); border-radius: var(--radius-sm); background: var(--sage-soft); }
.ai-draft-actions__confirm strong { color: var(--moss-dark); font-size: 12px; }
.ai-draft-actions__confirm small { color: var(--muted); font-size: 11px; line-height: 1.5; }
.ai-draft-actions__confirm > div { display: flex; gap: 7px; justify-content: flex-end; }
.save-draft { border: 1px solid var(--line-dark); border-radius: var(--radius-sm); background: var(--paper); color: var(--moss-dark); padding: 6px 9px; font: inherit; font-size: 11px; cursor: pointer; }
.save-draft:hover, .save-draft:focus-visible { border-color: var(--moss); background: var(--sage-soft); }
.save-draft:disabled { cursor: wait; opacity: .65; }
</style>
