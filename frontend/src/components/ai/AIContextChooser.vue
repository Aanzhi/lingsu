<script setup lang="ts">
defineProps<{ brainstorm: boolean; agentActive?: boolean; disabled?: boolean }>()
const emit = defineEmits<{
  (event: 'existing'): void
  (event: 'brainstorm'): void
  (event: 'agent'): void
}>()
</script>

<template>
  <section class="ai-context-switch" aria-label="选择 AI 使用场景">
    <button class="ai-context-choice" :class="{ selected: brainstorm && !agentActive }" type="button" :disabled="disabled" :aria-pressed="brainstorm && !agentActive" @click="emit('brainstorm')">
      <span class="ai-context-choice__index">01</span>
      <span><strong>从观察开始</strong><small>开题与选题 · 从真实观察出发，逐步形成可研究的课题</small></span>
      <span class="ai-context-choice__arrow" aria-hidden="true">→</span>
    </button>
    <button class="ai-context-choice" :class="{ selected: !brainstorm && !agentActive }" type="button" :disabled="disabled" :aria-pressed="!brainstorm && !agentActive" @click="emit('existing')">
      <span class="ai-context-choice__index">02</span>
      <span><strong>继续完善当前项目</strong><small>AI 对话完善材料 · 围绕项目持续对话，将确认后的草稿保存到材料</small></span>
      <span class="ai-context-choice__arrow" aria-hidden="true">→</span>
    </button>
    <button class="ai-context-choice" :class="{ selected: agentActive }" type="button" :disabled="disabled" :aria-pressed="Boolean(agentActive)" @click="emit('agent')">
      <span class="ai-context-choice__index">03</span>
      <span><strong>打开专用 Agent</strong><small>科创 Agent · 调用实验设计、查新、数据分析与报告写作工具</small></span>
      <span class="ai-context-choice__arrow" aria-hidden="true">→</span>
    </button>
  </section>
</template>

<style scoped>
.ai-context-switch { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0 26px 16px; padding: 4px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper-soft); }
.ai-context-choice { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; align-items: center; gap: 10px; min-width: 0; padding: 12px; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
.ai-context-choice:hover, .ai-context-choice:focus-visible { background: var(--paper); border-color: var(--line); }
.ai-context-choice.selected { border-color: var(--sage-line); background: var(--sage-soft); }
.ai-context-choice:disabled { cursor: wait; opacity: .72; }
.ai-context-choice__index { color: var(--moss); font: 700 11px var(--sans); }
.ai-context-choice strong, .ai-context-choice small { display: block; min-width: 0; overflow-wrap: anywhere; }
.ai-context-choice strong { font-size: 12px; line-height: 1.35; }
.ai-context-choice small { margin-top: 3px; color: var(--muted); font-size: 11px; line-height: 1.45; }
.ai-context-choice__arrow { color: var(--moss-dark); font-size: 16px; }
</style>
