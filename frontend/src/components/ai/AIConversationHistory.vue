<script setup lang="ts">
import type { AIConversation } from '../../api'
import { conversationDisplayTitle, type ConversationDisplayGroup } from '../../stores/presentationModel'

defineProps<{
  groups: ConversationDisplayGroup<AIConversation>[]
  selectedId: number | null
  sending: boolean
  search: string
  showArchived: boolean
}>()
const emit = defineEmits<{
  (event: 'update:search', value: string): void
  (event: 'new'): void
  (event: 'select', item: AIConversation): void
  (event: 'toggle-archived'): void
  (event: 'close'): void
}>()

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

function itemTitle(item: AIConversation, index: number) {
  const title = conversationDisplayTitle(item)
  return title === '未命名对话' ? `未命名对话 · 第 ${index + 1} 段` : title
}
</script>

<template>
  <aside id="conversation-history" class="conversation-history-drawer" aria-label="历史对话">
    <div class="history-heading"><strong>历史对话</strong><button type="button" aria-label="关闭历史对话" @click="emit('close')">×</button></div>
    <button class="new-conversation" type="button" :disabled="sending" @click="emit('new')">＋ 新建对话</button>
    <label class="conversation-search"><span class="sr-only">搜索历史对话</span><input :value="search" :disabled="sending" type="search" placeholder="搜索对话或项目" @input="emit('update:search', ($event.target as HTMLInputElement).value)" /></label>
    <div class="conversation-list">
      <template v-for="group in groups" :key="group.key">
        <button v-if="group.count === 1" class="conversation-item" :class="{ active: group.items[0].id === selectedId }" type="button" :disabled="sending" @click="emit('select', group.items[0])">
          <strong>{{ group.title }}</strong><small>{{ group.project_title || '未绑定项目' }} · {{ group.is_archived ? '已归档' : '进行中' }} · {{ formatDate(group.updated_at) }}</small>
        </button>
        <details v-else class="conversation-group">
          <summary class="conversation-item" :class="{ active: group.items.some((item) => item.id === selectedId) }"><strong>{{ group.title }}</strong><small>{{ group.project_title || '未绑定项目' }} · 已合并 {{ group.count }} 段对话 · {{ group.is_archived ? '已归档' : '进行中' }} · {{ formatDate(group.updated_at) }}</small></summary>
          <div class="conversation-group__items"><button v-for="(item, index) in group.items" :key="item.id" class="conversation-item" :class="{ active: item.id === selectedId }" type="button" :disabled="sending" @click="emit('select', item)"><strong>{{ itemTitle(item, index) }}</strong><small>{{ item.project_title || '未绑定项目' }} · {{ item.is_archived ? '已归档' : '进行中' }} · {{ formatDate(item.updated_at) }}</small></button></div>
        </details>
      </template>
      <p v-if="!groups.length" class="empty-small">{{ search ? '没有匹配的对话' : '暂无对话' }}</p>
    </div>
    <button class="archive-toggle" type="button" :disabled="sending" @click="emit('toggle-archived')">{{ showArchived ? '隐藏已归档' : '查看已归档' }}</button>
  </aside>
</template>

<style scoped>
.conversation-history-drawer { position: fixed; top: 112px; right: 24px; bottom: 24px; z-index: 80; display: flex; flex-direction: column; gap: 12px; width: min(320px, calc(100vw - 48px)); padding: 16px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: 0 16px 42px rgba(35,51,31,.16); }
.history-heading { display: flex; align-items: center; justify-content: space-between; color: var(--moss-dark); font: 700 16px var(--sans); }
.history-heading button { border: 0; background: transparent; color: var(--muted); font-size: 20px; cursor: pointer; }
.new-conversation { min-height: 40px; border: 1px solid var(--moss-dark); border-radius: var(--radius-sm); background: var(--moss); color: #fff; cursor: pointer; }
.conversation-search input { width: 100%; box-sizing: border-box; min-height: 38px; padding: 8px 9px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); color: var(--ink); }
.conversation-list { min-height: 0; flex: 1; overflow-y: auto; display: grid; align-content: start; gap: 5px; }
.conversation-item { width: 100%; display: block; border: 1px solid transparent; background: transparent; color: var(--ink); text-align: left; padding: 10px; border-radius: var(--radius-sm); cursor: pointer; }
.conversation-item.active, .conversation-item:hover, .conversation-item:focus-visible { border-color: var(--sage-line); background: var(--sage-soft); }
.conversation-item strong, .conversation-item small { display: block; overflow-wrap: anywhere; }
.conversation-item small { margin-top: 4px; color: var(--muted); font-size: 11px; line-height: 1.4; }
.conversation-group > summary { position: relative; list-style: none; cursor: pointer; padding-right: 34px; }
.conversation-group > summary::-webkit-details-marker { display: none; }
.conversation-group > summary::after { content: '展开'; position: absolute; right: 10px; top: 50%; transform: translateY(-50%); color: var(--moss-dark); font-size: 10px; font-weight: 700; }
.conversation-group[open] > summary::after { content: '收起'; }
.conversation-group__items { display: grid; gap: 4px; margin: 2px 0 0 9px; padding-left: 7px; border-left: 1px solid var(--line-dark); }
.conversation-group__items .conversation-item { padding: 8px 9px; }
.archive-toggle { border: 0; background: transparent; color: var(--moss-dark); padding: 6px; cursor: pointer; }
.empty-small, .muted { color: var(--muted); font-size: 12px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@media (max-width: 900px) { .conversation-history-drawer { top: 94px; right: 16px; bottom: 16px; } }
@media (max-width: 620px) { .conversation-history-drawer { left: 12px; right: 12px; width: auto; } }
</style>
