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
}>()
</script>

<template>
  <div id="agent-menu" class="agent-menu" role="dialog" aria-label="选择 AI 工具">
    <div class="agent-menu__filters"><input :value="search" type="search" placeholder="搜索 AI 工具" aria-label="搜索 AI 工具" @input="emit('update:search', ($event.target as HTMLInputElement).value)" /><select :value="category" aria-label="筛选 AI 工具分类" @change="emit('update:category', ($event.target as HTMLSelectElement).value)"><option v-for="item in categories" :key="item" :value="item">{{ item === 'all' ? '全部分类' : item }}</option></select></div>
    <div v-if="!groups.length" class="agent-empty">没有匹配的 AI 工具</div>
    <section v-for="group in groups" :key="group.category" class="agent-group"><h3>{{ group.category }}</h3><button v-for="agent in group.agents" :key="agent.key" type="button" :disabled="sending" @click="emit('choose', agent)"><strong>{{ agent.name }}</strong><small>{{ agent.description }}</small></button></section>
  </div>
</template>

<style scoped>
.agent-menu { position: absolute; right: 26px; top: 90px; z-index: 30; width: 280px; max-height: min(520px, calc(100dvh - 260px)); overflow-y: auto; overflow-x: hidden; padding: 8px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-hover); }
.agent-menu__filters { display: grid; gap: 7px; padding: 2px 0 8px; border-bottom: 1px solid var(--line); }
.agent-menu__filters input, .agent-menu__filters select { width: 100%; box-sizing: border-box; padding: 7px 8px; }
.agent-group + .agent-group { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--line); }
.agent-group h3 { margin: 2px 8px 6px; color: var(--moss); font-size: 11px; letter-spacing: .06em; }
.agent-menu button { width: 100%; border: 0; border-radius: var(--radius-sm); background: transparent; color: var(--ink); padding: 10px; text-align: left; cursor: pointer; }
.agent-menu button:hover, .agent-menu button:focus-visible { background: var(--sage-soft); }
.agent-menu strong, .agent-menu small { display: block; overflow-wrap: anywhere; }
.agent-menu small { margin-top: 4px; color: var(--muted); font-size: 11px; line-height: 1.45; }
.agent-empty { padding: 18px 10px; color: var(--muted); font-size: 12px; text-align: center; }
@media (max-width: 900px) { .agent-menu { right: 16px; max-width: calc(100% - 32px); } }
@media (max-width: 480px) { .agent-menu { left: 12px; right: 12px; width: auto; max-height: min(420px, calc(100dvh - 210px)); } }
</style>
