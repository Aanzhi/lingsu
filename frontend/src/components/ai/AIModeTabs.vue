<script setup lang="ts">
import type { AIAgent } from '../../api'
import { AI_WORKBENCH_MODES, type AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

const props = defineProps<{
  modelValue: AIWorkspaceMode
  agents: AIAgent[]
  selectedAgent?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: AIWorkspaceMode): void
  (event: 'select-agent', value: AIAgent): void
  (event: 'more-agents'): void
}>()
</script>

<template>
  <section class="ai-mode-tabs" aria-label="灵思 AI 工作模式" data-mode-labels="开题 / 研究 / 答辩">
    <div class="ai-mode-tabs__row" role="tablist" aria-label="选择 AI 模式">
      <button
        v-for="mode in AI_WORKBENCH_MODES"
        :key="mode.key"
        class="ai-mode-tab"
        :class="{ active: props.modelValue === mode.key }"
        type="button"
        role="tab"
        :aria-selected="props.modelValue === mode.key"
        :disabled="props.disabled"
        @click="emit('update:modelValue', mode.key)"
      >
        <strong>{{ mode.label }}</strong>
        <small>{{ mode.description }}</small>
      </button>
    </div>
    <div class="ai-agent-strip" aria-label="当前模式的 Agent">
      <span class="ai-agent-strip__label">可用 Agent</span>
      <button
        v-for="agent in props.agents.slice(0, 6)"
        :key="agent.key"
        type="button"
        class="ai-agent-chip"
        :class="{ active: props.selectedAgent === agent.key }"
        :disabled="props.disabled"
        @click="emit('select-agent', agent)"
      >
        {{ agent.name }}
      </button>
      <button v-if="props.agents.length > 6" type="button" class="ai-agent-more" :disabled="props.disabled" @click="emit('more-agents')">更多 {{ props.agents.length - 6 }} 个</button>
      <span v-if="!props.agents.length" class="ai-agent-empty">当前模式暂无已启用 Agent</span>
    </div>
  </section>
</template>

<style scoped>
.ai-mode-tabs { display: grid; gap: 10px; margin: 0 0 18px; padding: 4px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper-soft); }
.ai-mode-tabs__row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; }
.ai-mode-tab { display: grid; gap: 3px; min-width: 0; padding: 12px 14px; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; color: var(--muted); text-align: left; cursor: pointer; }
.ai-mode-tab strong { color: var(--ink); font: 700 14px/1.25 var(--sans); }
.ai-mode-tab small { overflow: hidden; color: var(--muted); font-size: 11px; line-height: 1.45; text-overflow: ellipsis; white-space: nowrap; }
.ai-mode-tab:hover, .ai-mode-tab:focus-visible { border-color: var(--line); background: var(--paper); }
.ai-mode-tab.active { border-color: var(--sage-line); background: var(--sage-soft); color: var(--moss-dark); }
.ai-mode-tab.active strong { color: var(--moss-dark); }
.ai-mode-tab:disabled, .ai-agent-chip:disabled, .ai-agent-more:disabled { cursor: wait; opacity: .65; }
.ai-agent-strip { display: flex; align-items: center; gap: 6px; min-width: 0; padding: 0 8px 6px; overflow-x: auto; }
.ai-agent-strip__label { flex: 0 0 auto; color: var(--muted-light); font-size: 11px; }
.ai-agent-chip, .ai-agent-more { flex: 0 0 auto; min-height: 28px; padding: 5px 10px; border: 1px solid var(--line-dark); border-radius: 999px; background: var(--paper); color: var(--muted); font: inherit; font-size: 11px; cursor: pointer; }
.ai-agent-chip:hover, .ai-agent-chip:focus-visible, .ai-agent-more:hover, .ai-agent-more:focus-visible { border-color: var(--moss); color: var(--moss-dark); }
.ai-agent-chip.active { border-color: var(--moss); background: var(--moss); color: #fff; }
.ai-agent-empty { color: var(--muted-light); font-size: 11px; }
@media (max-width: 720px) { .ai-mode-tab { padding-inline: 9px; } .ai-mode-tab small { display: none; } }
</style>
