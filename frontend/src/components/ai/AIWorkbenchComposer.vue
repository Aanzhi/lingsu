<script setup lang="ts">
import type { AIAgentInputField } from '../../api'
import type { AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

const props = defineProps<{
  draft: string
  mode: AIWorkspaceMode
  agentName?: string
  projectLabel?: string
  inputSchema?: AIAgentInputField[]
  inputValues?: Record<string, string>
  inputHelp?: string
  disabled?: boolean
  canSend?: boolean
  referencedCount?: number
  sending?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:draft', value: string): void
  (event: 'update:input', key: string, value: string): void
  (event: 'send'): void
  (event: 'cite-material'): void
}>()
</script>

<template>
  <footer class="ai-workbench-composer">
    <div class="ai-workbench-composer__meta">
      <span>{{ props.agentName || (props.mode === 'opening' ? '开题伙伴' : '灵思 AI') }}</span>
      <span>{{ props.projectLabel || (props.mode === 'opening' ? '不读取项目材料' : '等待当前项目') }}</span>
    </div>
    <details v-if="props.inputSchema?.length" class="ai-workbench-composer__inputs">
      <summary>补充信息（可选）</summary>
      <p class="ai-workbench-composer__help">{{ props.inputHelp || '填写后可让 AI 工具更准确；不填写也可以直接提问。' }}</p>
      <label v-for="field in props.inputSchema" :key="field.key">
        {{ field.label }}
        <textarea v-if="field.type === 'textarea'" :value="props.inputValues?.[field.key] || ''" :placeholder="field.placeholder" rows="2" @input="emit('update:input', field.key, ($event.target as HTMLTextAreaElement).value)" />
        <input v-else :value="props.inputValues?.[field.key] || ''" :placeholder="field.placeholder" @input="emit('update:input', field.key, ($event.target as HTMLInputElement).value)" />
      </label>
    </details>
    <textarea
      class="ai-workbench-composer__textarea"
      :value="props.draft"
      :disabled="props.disabled"
      :placeholder="props.mode === 'opening' ? '先写下一个观察，或继续追问研究问题…' : '输入问题，引用材料，或让 Agent 帮你继续完善…'"
      rows="4"
      @input="emit('update:draft', ($event.target as HTMLTextAreaElement).value)"
      @keydown.enter.exact.prevent="emit('send')"
    />
    <div class="ai-workbench-composer__footer">
      <button class="composer-tool-button" type="button" :disabled="props.disabled || props.mode === 'opening'" @click="emit('cite-material')">＋ 引用项目材料<span v-if="props.referencedCount"> · {{ props.referencedCount }}</span></button>
      <span class="composer-hint">Enter 发送 · Shift+Enter 换行</span>
      <button class="send-button" type="button" :disabled="props.disabled || !props.canSend" @click="emit('send')">{{ props.sending ? '生成中…' : '发送' }}</button>
    </div>
  </footer>
</template>

<style scoped>
.ai-workbench-composer { display: grid; gap: 8px; margin: 0 26px 24px; padding: 12px 14px 10px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); }
.ai-workbench-composer__meta, .ai-workbench-composer__footer { display: flex; align-items: center; gap: 10px; min-width: 0; color: var(--muted); font-size: 11px; }
.ai-workbench-composer__meta { justify-content: space-between; }
.ai-workbench-composer__meta span { min-width: 0; overflow-wrap: anywhere; }
.ai-workbench-composer__textarea { width: 100%; min-height: 88px; box-sizing: border-box; border: 0; padding: 9px 0; background: transparent; color: var(--ink); font: inherit; line-height: 1.6; resize: vertical; box-shadow: none; }
.ai-workbench-composer__textarea:focus { outline: none; }
.ai-workbench-composer__inputs { display: grid; gap: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--line); }
.ai-workbench-composer__inputs summary { color: var(--moss-dark); cursor: pointer; font-size: 12px; font-weight: 700; }
.ai-workbench-composer__help { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.5; }
.ai-workbench-composer__inputs label { display: grid; gap: 4px; color: var(--muted); font-size: 12px; }
.ai-workbench-composer__inputs input, .ai-workbench-composer__inputs textarea { min-height: 34px; box-sizing: border-box; border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 7px 8px; font: inherit; }
.ai-workbench-composer__footer { align-items: flex-end; }
.composer-tool-button { min-height: 30px; border: 0; padding: 0; background: transparent; color: var(--moss-dark); font: inherit; font-size: 11px; cursor: pointer; }
.composer-tool-button:hover, .composer-tool-button:focus-visible { text-decoration: underline; }
.composer-tool-button:disabled { cursor: not-allowed; color: var(--muted-light); }
.composer-hint { margin-left: auto; color: var(--muted-light); }
.send-button { min-width: 72px; min-height: 36px; padding: 8px 13px; border: 1px solid var(--moss-dark); border-radius: var(--radius-sm); background: var(--moss); color: #fff; font: inherit; font-size: 12px; cursor: pointer; }
.send-button:hover, .send-button:focus-visible { background: var(--moss-dark); }
.send-button:disabled { cursor: wait; opacity: .62; }
@media (max-width: 680px) { .ai-workbench-composer__footer { align-items: stretch; flex-wrap: wrap; } .composer-hint { order: 3; width: 100%; margin-left: 0; } }
</style>
