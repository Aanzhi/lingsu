<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import type { AIConversation } from '../../api'
import type { AIWorkspaceMode } from '../../stores/aiWorkbenchModel'
import { conversationDisplayTitle, type ConversationDisplayGroup } from '../../stores/presentationModel'

type HistoryModeFilter = AIWorkspaceMode

const props = withDefaults(defineProps<{
  groups: ConversationDisplayGroup<AIConversation>[]
  selectedId: number | null
  sending: boolean
  search: string
  showArchived: boolean
  modeFilter?: HistoryModeFilter
  deletingId?: number | null
  deleteError?: string
}>(), { modeFilter: 'opening', deletingId: null, deleteError: '' })
const emit = defineEmits<{
  (event: 'update:search', value: string): void
  (event: 'update:mode-filter', value: HistoryModeFilter): void
  (event: 'new'): void
  (event: 'select', item: AIConversation): void
  (event: 'delete', item: AIConversation): void
  (event: 'clear-delete-error'): void
  (event: 'toggle-archived'): void
  (event: 'close'): void
}>()

const pendingDelete = ref<AIConversation | null>(null)
const deleteCancelButton = ref<HTMLButtonElement | null>(null)

function itemTitle(item: AIConversation) {
  return conversationDisplayTitle(item, item.preview || '')
}

interface ConversationHistorySection {
  key: string
  label: string
  items: AIConversation[]
}

function startOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime()
}

function historyDateKey(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'unknown'
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatHistoryDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未标注时间'
  const dayDelta = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86_400_000)
  if (dayDelta === 0) return '今天'
  if (dayDelta === 1) return '昨天'
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  if (date.getHours() === 0 && date.getMinutes() === 0) return ''
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

const conversationItems = computed(() => props.groups.flatMap((group) => group.items))
const conversationCount = computed(() => conversationItems.value.length)
const modeOptions: Array<{ key: HistoryModeFilter; label: string }> = [
  { key: 'opening', label: '开题' },
  { key: 'research', label: '研究' },
  { key: 'defense', label: '成果表达' },
]
const historyModeLabel = computed(() => modeOptions.find((option) => option.key === props.modeFilter)?.label ?? '当前')
const historySections = computed<ConversationHistorySection[]>(() => {
  const sections: ConversationHistorySection[] = []
  for (const item of conversationItems.value) {
    const key = historyDateKey(item.updated_at)
    let section = sections.find((candidate) => candidate.key === key)
    if (!section) {
      section = { key, label: formatHistoryDate(item.updated_at), items: [] }
      sections.push(section)
    }
    section.items.push(item)
  }
  return sections
})

function requestDelete(item: AIConversation) {
  emit('clear-delete-error')
  pendingDelete.value = item
}

function cancelDelete() {
  if (props.deletingId !== null) return
  pendingDelete.value = null
}

function confirmDelete() {
  if (!pendingDelete.value || props.deletingId !== null) return
  emit('delete', pendingDelete.value)
}

watch(pendingDelete, async (item) => {
  if (!item) return
  await nextTick()
  deleteCancelButton.value?.focus()
})

watch(() => props.groups, (groups) => {
  if (!pendingDelete.value || props.deletingId !== null) return
  const stillExists = groups.some((group) => group.items.some((item) => item.id === pendingDelete.value?.id))
  if (!stillExists) pendingDelete.value = null
}, { deep: true })
</script>

<template>
  <Teleport to="body">
    <button class="conversation-history-backdrop" type="button" aria-label="关闭历史对话" @click="emit('close')" />
    <aside id="conversation-history" class="conversation-history-drawer" role="dialog" aria-modal="true" aria-label="历史对话">
      <header class="history-drawer__header">
        <div>
          <span class="eyebrow">灵思 AI</span>
          <h2>历史对话</h2>
          <p>选择一段对话继续，或从新的研究问题开始。</p>
        </div>
        <button class="history-drawer__close" type="button" aria-label="关闭历史对话" @click="emit('close')">×</button>
      </header>

      <div class="history-drawer__actions">
        <button class="new-conversation" type="button" :disabled="sending" @click="emit('new')">＋ 新建对话</button>
        <label class="conversation-search">
          <span class="sr-only">搜索历史对话</span>
          <input :value="search" :disabled="sending" type="search" placeholder="搜索对话或项目" @input="emit('update:search', ($event.target as HTMLInputElement).value)" />
        </label>
      </div>

      <div class="history-mode-filter" role="group" aria-label="按模式筛选历史对话">
        <button v-for="option in modeOptions" :key="option.key" class="history-mode-filter__item" :class="{ active: props.modeFilter === option.key }" type="button" :aria-pressed="props.modeFilter === option.key" :disabled="sending" @click="emit('update:mode-filter', option.key)">{{ option.label }}</button>
      </div>

      <div class="history-drawer__list-header">
        <div class="history-drawer__section">
          <span class="history-drawer__list-eyebrow">当前模式会话</span>
          <strong>{{ historyModeLabel }}会话</strong>
        </div>
        <small>{{ conversationCount }} 段 · 最近更新</small>
      </div>
      <div class="conversation-list">
        <template v-for="section in historySections" :key="section.key">
          <div class="conversation-list__section">
            <div class="conversation-list__section-heading">
              <span>{{ section.label }}</span>
              <small>{{ section.items.length }} 段</small>
            </div>
            <div class="conversation-list__section-items">
              <div v-for="item in section.items" :key="item.id" class="conversation-item" :class="{ active: item.id === selectedId }">
                <button class="conversation-item__select" type="button" :title="itemTitle(item)" :disabled="sending || deletingId !== null" @click="emit('select', item)">
                  <span class="conversation-item__content">
                    <span class="conversation-item__title-row">
                      <strong>{{ itemTitle(item) }}</strong>
                      <time :datetime="item.updated_at">{{ formatTime(item.updated_at) }}</time>
                    </span>
                    <span class="conversation-item__meta">
                      <span class="conversation-item__meta-project">{{ item.project_title || '未绑定项目' }}</span>
                      <span class="conversation-item__meta-side">
                        <span v-if="item.id === selectedId" class="conversation-item__current">当前</span>
                      </span>
                    </span>
                  </span>
                </button>
                <button class="conversation-item__delete" type="button" :disabled="sending || deletingId !== null" :aria-label="`永久删除会话：${itemTitle(item)}`" :title="`永久删除会话：${itemTitle(item)}`" @click.stop="requestDelete(item)">
                  <el-icon class="conversation-item__delete-icon" aria-hidden="true"><Delete /></el-icon>
                  <span class="sr-only">{{ deletingId === item.id ? '删除中…' : '删除' }}</span>
                </button>
              </div>
            </div>
          </div>
        </template>
        <p v-if="!historySections.length" class="empty-small">{{ search ? '没有匹配的对话' : '暂无对话' }}</p>
      </div>

      <footer class="history-drawer__footer">
        <button class="archive-toggle" type="button" :disabled="sending" @click="emit('toggle-archived')">{{ showArchived ? '隐藏已归档' : '查看已归档' }}</button>
        <span>历史对话随时可打开</span>
      </footer>
    </aside>
    <div v-if="pendingDelete" class="conversation-delete-backdrop" role="presentation" @click.self="cancelDelete">
      <section class="conversation-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="conversation-delete-title" aria-describedby="conversation-delete-description" @keydown.esc="cancelDelete">
        <span class="eyebrow">灵思 AI · 历史会话</span>
        <h2 id="conversation-delete-title">永久删除这段对话？</h2>
        <p id="conversation-delete-description">“{{ itemTitle(pendingDelete) }}”删除后对话和消息不可恢复。</p>
        <p v-if="deleteError" class="conversation-delete-error" role="alert">{{ deleteError }}</p>
        <footer>
          <button ref="deleteCancelButton" class="secondary-button" type="button" :disabled="deletingId !== null" @click="cancelDelete">取消</button>
          <button class="danger-button" type="button" :disabled="deletingId === pendingDelete.id" @click="confirmDelete">{{ deletingId === pendingDelete.id ? '删除中…' : '永久删除' }}</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.conversation-history-backdrop { position: fixed; inset: var(--topbar-height) 0 0; z-index: 100; border: 0; background: rgba(35, 51, 31, .08); cursor: default; }
.conversation-history-drawer { position: fixed; top: calc(var(--topbar-height) + 16px); right: 24px; bottom: 24px; z-index: 101; display: flex; flex-direction: column; gap: 12px; width: min(392px, calc(100vw - 48px)); box-sizing: border-box; padding: 18px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: 0 22px 58px rgba(35, 51, 31, .2); }
.history-drawer__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--line); }
.history-drawer__header h2 { margin: 4px 0 5px; color: var(--ink); font: 700 22px/1.2 var(--sans); letter-spacing: -.03em; }
.history-drawer__header p { max-width: 270px; margin: 0; color: var(--muted); font-size: 11px; line-height: 1.55; }
.history-drawer__close { width: 30px; height: 30px; flex: 0 0 auto; border: 1px solid var(--line); border-radius: 50%; background: var(--paper); color: var(--muted); font-size: 20px; line-height: 1; cursor: pointer; }
.history-drawer__close:hover, .history-drawer__close:focus-visible { border-color: var(--moss); background: var(--sage-soft); color: var(--moss-dark); }
.history-drawer__actions { display: grid; gap: 8px; }
.new-conversation { min-height: 38px; border: 1px solid var(--moss-dark); border-radius: var(--radius-sm); background: var(--moss); color: #fff; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
.new-conversation:hover:not(:disabled), .new-conversation:focus-visible { background: var(--moss-dark); }
.new-conversation:disabled, .archive-toggle:disabled, .conversation-item__select:disabled, .conversation-item__delete:disabled { cursor: wait; opacity: .55; }
.conversation-search input { width: 100%; box-sizing: border-box; min-height: 38px; padding: 8px 11px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); outline: 0; background: var(--paper-soft); color: var(--ink); font: inherit; font-size: 12px; }
.conversation-search input:focus { border-color: var(--moss); box-shadow: 0 0 0 3px rgba(79, 119, 91, .12); }
.history-mode-filter { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 3px; padding: 3px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); }
.history-mode-filter__item { min-width: 0; min-height: 29px; padding: 5px 4px; border: 0; border-radius: 5px; background: transparent; color: var(--muted); font: inherit; font-size: 10px; font-weight: 700; cursor: pointer; }
.history-mode-filter__item.active, .history-mode-filter__item:hover:not(:disabled), .history-mode-filter__item:focus-visible { background: var(--paper); color: var(--moss-dark); outline: 0; box-shadow: 0 1px 3px rgba(35, 51, 31, .08); }
.history-mode-filter__item:disabled { cursor: wait; opacity: .55; }
.history-drawer__list-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; padding-top: 2px; }
.history-drawer__list-header > div { display: grid; gap: 3px; min-width: 0; }
.history-drawer__list-eyebrow { color: var(--muted-light); font-size: 9px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.history-drawer__list-header strong { color: var(--moss-dark); font-size: 12px; line-height: 1.3; }
.history-drawer__list-header > small { color: var(--muted); font-size: 10px; white-space: nowrap; }
.conversation-list { min-height: 0; flex: 1; overflow-y: auto; display: grid; align-content: start; gap: 8px; padding: 0 2px 2px 0; scrollbar-width: thin; }
.conversation-list__section { display: grid; gap: 5px; }
.conversation-list__section + .conversation-list__section { margin-top: 8px; }
.conversation-list__section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 4px; color: var(--moss-dark); font-size: 10px; font-weight: 700; }
.conversation-list__section-heading small { color: var(--muted-light); font-size: 9px; font-weight: 500; }
.conversation-list__section-items { display: grid; gap: 4px; }
.conversation-item { position: relative; display: block; min-width: 0; border: 1px solid transparent; border-radius: 8px; background: transparent; }
.conversation-item.active, .conversation-item:hover, .conversation-item:focus-within { border-color: var(--sage-line); background: var(--sage-soft); }
.conversation-item__select { width: 100%; min-width: 0; display: block; box-sizing: border-box; border: 0; background: transparent; color: var(--ink); text-align: left; padding: 10px 42px 10px 12px; border-radius: 7px; cursor: pointer; }
.conversation-item__select:focus { outline: 0; }
.conversation-item__select:focus-visible { box-shadow: 0 0 0 2px rgba(79, 119, 91, .2); }
.conversation-item__content { display: block; min-width: 0; }
.conversation-item__title-row { display: flex; align-items: flex-start; gap: 10px; min-width: 0; padding-right: 34px; }
.conversation-item__title-row strong { flex: 1 1 auto; min-width: 0; display: -webkit-box; max-height: 34px; overflow: hidden; text-overflow: ellipsis; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow-wrap: anywhere; font-size: 12px; line-height: 1.42; }
.conversation-item__title-row time { flex: 0 0 auto; color: var(--muted-light); font-size: 10px; line-height: 1.5; white-space: nowrap; }
.conversation-item__meta { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; margin-top: 8px; color: var(--muted); font-size: 10px; line-height: 1.35; white-space: nowrap; overflow: hidden; }
.conversation-item__meta-project { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.conversation-item__meta-side { display: flex; align-items: center; gap: 6px; flex: 0 0 auto; }
.conversation-item__current { padding: 2px 5px; border: 1px solid var(--sage-line); border-radius: 999px; background: var(--paper); color: var(--moss-dark); font-size: 9px; font-weight: 700; line-height: 1.2; white-space: nowrap; }
.conversation-item__delete { position: absolute; top: 7px; right: 7px; display: grid; place-items: center; width: 28px; height: 28px; min-width: 0; min-height: 0; padding: 0; border: 1px solid transparent; border-radius: 6px; background: transparent; color: var(--muted); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .15s ease, visibility .15s ease, color .15s ease, background .15s ease, border-color .15s ease; cursor: pointer; }
.conversation-item:hover .conversation-item__delete, .conversation-item:focus-within .conversation-item__delete { opacity: 1; visibility: visible; pointer-events: auto; }
.conversation-item__delete:hover:not(:disabled), .conversation-item__delete:focus-visible { border-color: #d8b2a9; background: #fff7f4; color: var(--clay-deep); outline: 0; }
.conversation-item__delete-icon { display: grid; width: 14px; height: 14px; place-items: center; }
.conversation-item__delete-icon svg { width: 14px; height: 14px; }
.archive-toggle { border: 0; background: transparent; color: var(--moss-dark); padding: 5px 0; font: inherit; font-size: 10px; font-weight: 700; cursor: pointer; }
.history-drawer__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-top: 12px; border-top: 1px solid var(--line); }
.history-drawer__footer > span { color: var(--muted-light); font-size: 10px; text-align: right; }
.conversation-delete-backdrop { position: fixed; inset: 0; z-index: 110; display: grid; place-items: center; padding: 24px; background: rgba(35, 51, 31, .18); }
.conversation-delete-dialog { display: grid; gap: 12px; width: min(100%, 390px); box-sizing: border-box; padding: 22px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-hover); }
.conversation-delete-dialog h2, .conversation-delete-dialog p { margin: 0; }
.conversation-delete-dialog h2 { color: var(--ink); font: 700 20px/1.3 var(--sans); }
.conversation-delete-dialog p { color: var(--muted); font-size: 12px; line-height: 1.6; }
.conversation-delete-dialog footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
.danger-button { min-height: 34px; padding: 7px 13px; border: 1px solid var(--clay-deep); border-radius: var(--radius-sm); background: var(--clay-deep); color: #fff; font: inherit; font-size: 11px; font-weight: 700; cursor: pointer; }
.danger-button:hover:not(:disabled), .danger-button:focus-visible { background: #8e4438; }
.danger-button:disabled { cursor: wait; opacity: .6; }
.conversation-delete-error { padding: 9px 10px; border-radius: var(--radius-sm); background: #fff7f4; color: var(--clay-deep) !important; }
.empty-small, .muted { color: var(--muted); font-size: 12px; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
@media (max-width: 900px) { .conversation-history-drawer { top: calc(var(--topbar-height) + 12px); right: 16px; bottom: 16px; } }
@media (max-width: 620px) { .conversation-history-drawer { left: 12px; right: 12px; width: auto; } }
</style>
