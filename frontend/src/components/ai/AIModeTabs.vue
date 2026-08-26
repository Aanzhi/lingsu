<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AIAgent } from '../../api'
import { AI_WORKBENCH_MODES, type AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

const props = defineProps<{
  modelValue: AIWorkspaceMode
  agents: AIAgent[]
  selectedAgent?: string
  disabled?: boolean
  modes?: AIWorkspaceMode[]
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: AIWorkspaceMode): void
  (event: 'select-agent', value: AIAgent): void
  (event: 'more-agents'): void
}>()

const agentOffset = ref(0)
const visibleAgentCount = 4
const visibleAgents = computed(() => props.agents.slice(agentOffset.value, agentOffset.value + visibleAgentCount))
const canMoveAgentBack = computed(() => agentOffset.value > 0)
const canMoveAgentForward = computed(() => agentOffset.value + visibleAgentCount < props.agents.length)

watch(() => [props.modelValue, props.agents.map((agent) => agent.key).join('|')], () => { agentOffset.value = 0 })
function moveAgents(step: number) {
  agentOffset.value = Math.min(Math.max(agentOffset.value + step, 0), Math.max(props.agents.length - visibleAgentCount, 0))
}

function goalLabel(agent: AIAgent) {
  const text = `${agent.name} ${agent.description} ${agent.category} ${agent.workflow || ''}`
  if (/开题|选题|问题/.test(text)) return '梳理研究问题'
  if (/实验|方法/.test(text)) return '设计下一步实验'
  if (/日志/.test(text)) return '整理实验日志'
  if (/数据/.test(text)) return '检查数据与证据'
  if (/答辩|展示|成果|汇报/.test(text)) return '准备成果表达'
  if (/材料|写作|报告/.test(text)) return '完善当前材料'
  return '继续推进研究'
}
</script>

<template>
  <section class="ai-mode-tabs" aria-label="灵思 AI 工作模式" data-mode-labels="开题 / 研究 / 成果表达">
    <div class="ai-mode-tabs__row ai-mode-tabs__row--segmented" :class="{ 'ai-mode-tabs__row--two': props.modes?.length === 2 }" role="tablist" aria-label="选择 AI 模式">
      <button
        v-for="mode in AI_WORKBENCH_MODES.filter((item) => !props.modes || props.modes.includes(item.key))"
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
    <div class="ai-agent-rail" data-agent-rail aria-label="当前模式的 Agent（平台模板）" title="Agent 由平台 AI 助手模板管理">
      <button class="ai-agent-arrow" type="button" aria-label="查看前面的 Agent" :disabled="props.disabled || !canMoveAgentBack" @click="moveAgents(-1)">‹</button>
      <div class="ai-agent-viewport">
        <div class="ai-agent-strip">
          <span class="ai-agent-strip__label">我想完成什么</span>
          <button
            v-for="agent in visibleAgents"
            :key="agent.key"
            type="button"
            class="ai-agent-chip"
            :class="{ active: props.selectedAgent === agent.key }"
            :disabled="props.disabled"
            @click="emit('select-agent', agent)"
          >
            <strong>{{ agent.name }}</strong>
            <small>{{ goalLabel(agent) }}</small>
          </button>
          <button type="button" class="ai-agent-more" :disabled="props.disabled" @click="emit('more-agents')">更多能力</button>
          <span v-if="!props.agents.length" class="ai-agent-empty">当前模式暂无可用能力</span>
        </div>
      </div>
      <button class="ai-agent-arrow" type="button" aria-label="查看后面的 Agent" :disabled="props.disabled || !canMoveAgentForward" @click="moveAgents(1)">›</button>
    </div>
  </section>
</template>

<style scoped>
.ai-mode-tabs { display: grid; gap: 8px; margin: 0; padding: 0; border: 0; background: transparent; }
.ai-mode-tabs__row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; overflow: hidden; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); }
.ai-mode-tabs__row--two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.ai-mode-tab { display: grid; align-content: center; gap: 2px; min-width: 0; min-height: 48px; padding: 8px 15px; border: 0; border-right: 1px solid var(--line); background: var(--paper); color: var(--muted); text-align: left; cursor: pointer; transition: background-color var(--transition-fast), color var(--transition-fast); }
.ai-mode-tab:last-child { border-right: 0; }
.ai-mode-tab strong { color: var(--ink); font: 700 13px/1.25 var(--sans); }
.ai-mode-tab small { overflow: hidden; color: var(--muted-light); font-size: 9px; line-height: 1.3; text-overflow: ellipsis; white-space: nowrap; }
.ai-mode-tab:hover, .ai-mode-tab:focus-visible { background: var(--paper-soft); }
.ai-mode-tab.active { background: var(--sage-soft); color: var(--moss-dark); box-shadow: inset 0 -2px 0 var(--moss); }
.ai-mode-tab.active strong { color: var(--moss-dark); }
.ai-mode-tab:disabled, .ai-agent-chip:disabled, .ai-agent-more:disabled { cursor: wait; opacity: .65; }
.ai-agent-rail { display: grid; grid-template-columns: 28px minmax(0, 1fr) 28px; align-items: center; gap: 6px; min-width: 0; padding: 0 2px; }
.ai-agent-viewport { min-width: 0; overflow: hidden; }
.ai-agent-strip { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 1px 0 3px; overflow: hidden; }
.ai-agent-arrow { display: grid; place-items: center; width: 28px; height: 28px; border: 1px solid var(--line-dark); border-radius: 50%; background: var(--paper); color: var(--moss-dark); font: 700 16px/1 var(--sans); cursor: pointer; transition: border-color var(--transition-fast), background-color var(--transition-fast); }
.ai-agent-arrow:hover:not(:disabled), .ai-agent-arrow:focus-visible { border-color: var(--moss); background: var(--sage-soft); }
.ai-agent-arrow:disabled { cursor: default; opacity: .35; }
.ai-agent-strip__label { flex: 0 0 auto; color: var(--muted-light); font-size: 11px; white-space: nowrap; }
.ai-agent-chip, .ai-agent-more { flex: 0 0 auto; min-height: 34px; padding: 5px 10px; border: 1px solid var(--line-dark); border-radius: 999px; background: var(--paper); color: var(--muted); font: inherit; font-size: 10px; cursor: pointer; transition: border-color var(--transition-fast), background-color var(--transition-fast), color var(--transition-fast); }
.ai-agent-chip { display: inline-grid; gap: 1px; min-width: 118px; text-align: left; }
.ai-agent-chip strong { color: var(--ink); font: 700 10px/1.2 var(--sans); }
.ai-agent-chip small { color: var(--muted-light); font-size: 9px; line-height: 1.2; }
.ai-agent-chip:hover, .ai-agent-chip:focus-visible, .ai-agent-more:hover, .ai-agent-more:focus-visible { border-color: var(--moss); color: var(--moss-dark); }
.ai-agent-chip.active { border-color: var(--moss); background: var(--moss); color: #fff; }
.ai-agent-chip.active strong, .ai-agent-chip.active small { color: #fff; }
.ai-agent-empty { color: var(--muted-light); font-size: 11px; white-space: nowrap; }
@media (max-width: 720px) { .ai-mode-tab { padding-inline: 11px; } .ai-mode-tab small { display: none; } .ai-agent-strip__label { display: none; } }
</style>
