<script setup lang="ts">
import { computed } from 'vue'
import type { AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

const props = defineProps<{
  draft: string
  mode: AIWorkspaceMode
  agentName?: string
  projectLabel?: string
  disabled?: boolean
  canSend?: boolean
  selectedMaterialIds?: number[]
  canCiteMaterials?: boolean
  sending?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:draft', value: string): void
  (event: 'send'): void
  (event: 'stop'): void
  (event: 'cite-material'): void
}>()

const placeholder = computed(() => {
  if (props.mode === 'opening') return '写下你的观察或研究想法…'
  if (props.mode === 'defense') return '告诉我你想如何准备成果表达…'
  return '描述你要继续完成的研究任务…'
})
const canCiteMaterials = computed(() => props.canCiteMaterials ?? props.mode !== 'opening')
</script>

<template>
  <footer class="ai-workbench-composer">
    <div class="ai-workbench-composer__meta">
      <span class="ai-workbench-composer__agent">当前 Agent · <strong>{{ props.agentName || (props.mode === 'opening' ? '开题伙伴' : '灵思 AI') }}</strong></span>
      <span class="ai-workbench-composer__context">{{ props.projectLabel || (props.mode === 'opening' ? '开题 · 不读取项目材料' : '等待当前项目') }}</span>
    </div>
    <textarea
      class="ai-workbench-composer__textarea"
      :value="props.draft"
      :disabled="props.disabled"
      :placeholder="placeholder"
      rows="3"
      @input="emit('update:draft', ($event.target as HTMLTextAreaElement).value)"
      @keydown.enter.exact.prevent="emit('send')"
    />
    <div class="ai-workbench-composer__footer">
      <button class="composer-tool-button selected-material" type="button" :disabled="props.disabled || !canCiteMaterials" @click="emit('cite-material')">＋ 引用材料<span v-if="props.selectedMaterialIds?.length"> · 已选 {{ props.selectedMaterialIds.length }}</span></button>
      <span class="composer-hint">Enter 发送 · Shift+Enter 换行</span>
      <button v-if="props.sending" class="send-button send-button--stop" type="button" @click="emit('stop')">停止</button>
      <button v-else class="send-button" type="button" :disabled="props.disabled || !props.canSend" @click="emit('send')">发送</button>
    </div>
  </footer>
</template>

<style scoped>
.ai-workbench-composer { display: grid; gap: 7px; min-width: 0; padding: 12px 14px 10px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); }
.ai-workbench-composer__meta, .ai-workbench-composer__footer { display: flex; align-items: center; gap: 9px; min-width: 0; color: var(--muted); font-size: 10px; }
.ai-workbench-composer__meta { justify-content: space-between; padding-bottom: 3px; }
.ai-workbench-composer__meta span { min-width: 0; overflow-wrap: anywhere; }
.ai-workbench-composer__agent strong { color: var(--moss-dark); font-weight: 750; }
.ai-workbench-composer__context { overflow: hidden; color: var(--muted-light); text-overflow: ellipsis; white-space: nowrap; }
.ai-workbench-composer__textarea { width: 100%; height: 76px; min-height: 76px; box-sizing: border-box; border: 0; padding: 5px 0 7px; background: transparent; color: var(--ink); font: inherit; font-size: 13px; line-height: 1.6; resize: vertical; box-shadow: none; }
.ai-workbench-composer__textarea::placeholder { color: var(--muted-light); opacity: 1; }
.ai-workbench-composer__textarea:focus { outline: none; }
.ai-workbench-composer__footer { align-items: flex-end; }
.composer-tool-button { min-height: 28px; border: 0; padding: 0; background: transparent; color: var(--moss-dark); font: inherit; font-size: 10px; cursor: pointer; }
.composer-tool-button:hover:not(:disabled), .composer-tool-button:focus-visible { text-decoration: underline; }
.composer-tool-button:disabled { cursor: not-allowed; color: var(--muted-light); }
.composer-hint { margin-left: auto; color: var(--muted-light); }
.send-button { min-width: 70px; min-height: 34px; padding: 7px 12px; border: 1px solid var(--moss-dark); border-radius: var(--radius-sm); background: var(--moss); color: #fff; font: inherit; font-size: 11px; font-weight: 700; cursor: pointer; }
.send-button:hover:not(:disabled), .send-button:focus-visible { background: var(--moss-dark); }
.send-button:disabled { cursor: wait; opacity: .62; }
.send-button--stop { background: var(--clay-deep); border-color: var(--clay-deep); }
@media (max-width: 680px) { .ai-workbench-composer__footer { align-items: stretch; flex-wrap: wrap; } .composer-hint { order: 3; width: 100%; margin-left: 0; } }
</style>
