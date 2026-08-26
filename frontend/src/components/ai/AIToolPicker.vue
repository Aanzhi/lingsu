<script setup lang="ts">
import type { AIAgent } from '../../api'
import type { AgentCategoryGroup } from '../../stores/aiConversationModel'

defineProps<{
  categories: string[]
  groups: AgentCategoryGroup<AIAgent>[]
  search: string
  category: string
  sending: boolean
}>()
const emit = defineEmits<{
  (event: 'update:search', value: string): void
  (event: 'update:category', value: string): void
  (event: 'choose', agent: AIAgent): void
  (event: 'close'): void
}>()
</script>

<template>
  <Teleport to="body">
    <div class="agent-picker-overlay" role="presentation" @click.self="emit('close')">
      <section id="agent-menu" class="agent-menu agent-menu--wide agent-picker-drawer" role="dialog" aria-modal="true" aria-label="选择 AI 工具（平台模板）">
        <header class="agent-picker-header">
          <div><span class="eyebrow">平台能力</span><h2>选择 AI 工具</h2><p>按当前研究方式选择一个 Agent，选中后可直接输入目标。</p></div>
          <button type="button" class="agent-picker-close" aria-label="关闭 AI 工具选择" @click="emit('close')">×</button>
        </header>
        <div class="agent-menu__filters"><label><span class="sr-only">搜索 AI 工具</span><input :value="search" type="search" placeholder="搜索 AI 工具" aria-label="搜索 AI 工具" @input="emit('update:search', ($event.target as HTMLInputElement).value)" /></label><label><span class="sr-only">筛选 AI 工具分类</span><select :value="category" aria-label="筛选 AI 工具分类" @change="emit('update:category', ($event.target as HTMLSelectElement).value)"><option v-for="item in categories" :key="item" :value="item">{{ item === 'all' ? '全部分类' : item }}</option></select></label></div>
        <div v-if="!groups.length" class="agent-empty">没有匹配的 AI 工具</div>
        <div v-else class="agent-picker-groups"><section v-for="group in groups" :key="group.category" class="agent-group"><h3>{{ group.category }}</h3><button v-for="agent in group.agents" :key="agent.key" type="button" :disabled="sending" @click="emit('choose', agent)"><strong>{{ agent.name }}</strong><small>{{ agent.description }}</small></button></section></div>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.agent-picker-overlay { position: fixed; inset: 0; z-index: 120; display: grid; place-items: start center; padding: calc(var(--topbar-height) + 24px) 24px 24px; background: rgba(30, 45, 38, .1); }
.agent-picker-drawer { width: min(720px, calc(100vw - 48px)); max-height: calc(100vh - 104px); overflow: hidden; padding: 20px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: 0 18px 48px rgba(35, 51, 31, .18); }
.agent-picker-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding-bottom: 16px; border-bottom: 1px solid var(--line); }
.agent-picker-header h2 { margin: 4px 0 5px; color: var(--ink); font: 700 22px/1.25 var(--sans); }
.agent-picker-header p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.agent-picker-close { display: grid; place-items: center; width: 32px; height: 32px; flex: 0 0 auto; border: 1px solid var(--line); border-radius: 50%; background: var(--paper); color: var(--muted); font-size: 20px; line-height: 1; cursor: pointer; }
.agent-picker-close:hover, .agent-picker-close:focus-visible { border-color: var(--moss); background: var(--sage-soft); color: var(--moss-dark); }
.agent-menu__filters { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(180px, .6fr); gap: 8px; padding: 16px 0 12px; }
.agent-menu__filters label, .agent-menu__filters input, .agent-menu__filters select { width: 100%; box-sizing: border-box; }
.agent-menu__filters input, .agent-menu__filters select { min-height: 38px; padding: 7px 10px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--ink); }
.agent-menu__filters input:focus, .agent-menu__filters select:focus { border-color: var(--moss); outline: 3px solid var(--color-focus-ring); outline-offset: 1px; }
.agent-picker-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.agent-group { min-width: 0; padding: 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); }
.agent-group h3 { margin: 0 0 6px; color: var(--moss); font-size: 11px; letter-spacing: .06em; }
.agent-group button { display: grid; width: 100%; gap: 3px; padding: 9px; border: 1px solid transparent; border-radius: var(--radius-sm); background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
.agent-group button:hover, .agent-group button:focus-visible { border-color: var(--sage-line); background: var(--paper); }
.agent-group button:disabled { cursor: wait; opacity: .58; }
.agent-menu strong, .agent-menu small { display: block; overflow-wrap: anywhere; }
.agent-menu strong { font-size: 12px; }
.agent-menu small { color: var(--muted); font-size: 11px; line-height: 1.4; }
.agent-empty { padding: 36px 10px 20px; color: var(--muted); font-size: 12px; text-align: center; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@media (max-width: 900px) { .agent-picker-overlay { padding-inline: 16px; } .agent-picker-groups { grid-template-columns: 1fr; } }
@media (max-width: 620px) { .agent-picker-overlay { padding: calc(var(--topbar-height) + 12px) 12px 12px; } .agent-picker-drawer { width: 100%; padding: 16px; } .agent-menu__filters { grid-template-columns: 1fr; } }
</style>
