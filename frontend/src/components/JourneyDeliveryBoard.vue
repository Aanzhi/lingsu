<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { StepStatus } from '../stores/studentApiModel'

export interface DeliveryItem {
  id: string | number
  taskId: number
  title: string
  description?: string
  materialLabel?: string
  reportSection?: string
  status: StepStatus
  xpReward?: number
  href?: string
  stage?: number
}

export interface DeliveryGroup {
  order: number
  title: string
  status: 'completed' | 'current' | 'pending' | 'locked'
  passed: number
  total: number
  items: DeliveryItem[]
}

const props = defineProps<{ groups: DeliveryGroup[] }>()
const emit = defineEmits<{ (e: 'open', item: DeliveryItem): void }>()
const expandedOrder = ref<number | null>(null)
const initialized = ref(false)

const totalItems = computed(() => props.groups.reduce((sum, group) => sum + group.items.length, 0))
const deliveredCount = computed(() => props.groups.reduce((sum, group) => sum + group.passed, 0))
const currentGroup = computed(() => props.groups.find((group) => group.status === 'current') || props.groups.find((group) => group.status !== 'completed' && group.status !== 'locked') || props.groups[0])
const statusLabel: Record<StepStatus, string> = { done: '已交付', active: '进行中', revision: '需修订', locked: '未解锁' }
const groupStatusLabel: Record<DeliveryGroup['status'], string> = { completed: '已完成', current: '当前章', pending: '待开始', locked: '未解锁' }
const groupTone: Record<DeliveryGroup['status'], string> = { completed: 'success', current: 'current', pending: 'neutral', locked: 'danger' }

watch(() => props.groups, (groups) => {
  if (!groups.length) { expandedOrder.value = null; return }
  if (!initialized.value || !groups.some((group) => group.order === expandedOrder.value)) {
    expandedOrder.value = currentGroup.value?.order ?? groups[0].order
    initialized.value = true
  }
}, { immediate: true, deep: true })

function toggleGroup(order: number) {
  expandedOrder.value = expandedOrder.value === order ? null : order
}
function isOpen(group: DeliveryGroup) { return expandedOrder.value === group.order }
function canOpen(item: DeliveryItem) { return item.status !== 'locked' }
</script>

<template>
  <section class="paper-card journey-delivery">
    <header class="journey-delivery__head">
      <div>
        <p class="eyebrow">项目交付清单</p>
        <h2>按研究章节查看要完成的任务</h2>
        <p>共 {{ totalItems }} 项任务，已完成 <strong>{{ deliveredCount }}</strong> 项。每项任务只保留一个入口，材料和报告归属在同一行说明。</p>
      </div>
    </header>
    <div class="journey-delivery__chapters">
      <article
        v-for="group in groups"
        :key="group.order"
        class="journey-delivery__chapter"
        :class="[`is-${group.status}`, { 'is-expanded': isOpen(group) }]"
      >
        <button
          type="button"
          class="journey-delivery__chapter-toggle"
          :aria-expanded="isOpen(group)"
          :aria-controls="`journey-chapter-${group.order}`"
          @click="toggleGroup(group.order)"
        >
          <span class="journey-delivery__chapter-pin">{{ String(group.order).padStart(2, '0') }}</span>
          <span class="journey-delivery__chapter-title"><small>第 {{ group.order }} 章</small><strong>{{ group.title }}</strong></span>
          <span class="journey-delivery__chapter-summary"><span class="status-tag" :class="groupTone[group.status]">{{ groupStatusLabel[group.status] }}</span><strong>{{ group.passed }} / {{ group.total }}</strong><small>项已完成</small></span>
          <span class="journey-delivery__chevron" aria-hidden="true">{{ isOpen(group) ? '收起' : '展开' }}</span>
        </button>
        <div v-if="isOpen(group)" :id="`journey-chapter-${group.order}`" class="journey-delivery__chapter-body">
          <div class="journey-delivery__columns" aria-hidden="true"><span>任务</span><span>交付材料</span><span>报告章节</span><span>状态</span><span>操作</span></div>
          <ul v-if="group.items.length" class="journey-delivery__items">
            <li v-for="item in group.items" :key="item.id" class="journey-delivery__item" :class="`is-${item.status}`">
              <div class="journey-delivery__task"><span class="journey-delivery__dot" /><div><strong>{{ item.title }}</strong><small v-if="item.description">{{ item.description }}</small></div></div>
              <div class="journey-delivery__field"><span class="journey-delivery__field-label">材料</span><span>{{ item.materialLabel || '待配置材料' }}</span></div>
              <div class="journey-delivery__field"><span class="journey-delivery__field-label">报告章节</span><span>{{ item.reportSection || '待映射章节' }}</span></div>
              <span class="journey-delivery__status" :class="`is-${item.status}`">{{ statusLabel[item.status] }}</span>
              <button v-if="canOpen(item)" class="secondary-button journey-delivery__open" type="button" @click="emit('open', item)">打开任务</button>
              <span v-else class="journey-delivery__locked">未解锁</span>
            </li>
          </ul>
          <p v-else class="journey-delivery__empty">这一章还没有安排任务。</p>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.journey-delivery { padding: 24px 28px 22px; }
.journey-delivery__head { margin-bottom: 18px; }
.journey-delivery__head h2 { margin: 4px 0 6px; font: 700 20px/1.3 var(--sans); color: var(--ink); }
.journey-delivery__head p { margin: 0; color: var(--muted); font-size: 12.5px; line-height: 1.55; }
.journey-delivery__head strong { color: var(--moss-dark); }
.journey-delivery__chapters { display: grid; gap: 8px; }
.journey-delivery__chapter { border: 1px solid var(--line); border-radius: var(--radius-md); overflow: hidden; background: var(--paper); transition: border-color .15s ease, box-shadow .15s ease; }
.journey-delivery__chapter.is-current { border-color: var(--sage-line); box-shadow: var(--shadow-soft); }
.journey-delivery__chapter.is-completed { border-color: var(--sage-line); }
.journey-delivery__chapter.is-locked { background: var(--paper-soft); }
.journey-delivery__chapter-toggle { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto 48px; align-items: center; gap: 12px; width: 100%; padding: 13px 15px; border: 0; background: var(--paper); color: var(--ink); text-align: left; cursor: pointer; }
.journey-delivery__chapter.is-current .journey-delivery__chapter-toggle { background: var(--sage-soft); }
.journey-delivery__chapter.is-completed .journey-delivery__chapter-toggle { background: var(--sage-soft); }
.journey-delivery__chapter.is-locked .journey-delivery__chapter-toggle { background: var(--paper-soft); }
.journey-delivery__chapter-toggle:hover { background: var(--paper-soft); }
.journey-delivery__chapter-pin { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; background: var(--moss); color: #fff; font: 700 12px var(--sans); }
.is-current > .journey-delivery__chapter-toggle .journey-delivery__chapter-pin { background: #fff; color: var(--moss-dark); box-shadow: 0 0 0 2px var(--moss); }
.is-locked > .journey-delivery__chapter-toggle .journey-delivery__chapter-pin { background: var(--line-dark); color: var(--muted); }
.journey-delivery__chapter-title { display: grid; gap: 2px; min-width: 0; }
.journey-delivery__chapter-title small { color: var(--moss); font-size: 10px; font-weight: 700; letter-spacing: .08em; }
.journey-delivery__chapter-title strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 700 14px/1.35 var(--sans); }
.journey-delivery__chapter-summary { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 11px; white-space: nowrap; }
.journey-delivery__chapter-summary strong { color: var(--moss-dark); font: 700 14px var(--sans); }
.journey-delivery__chapter-summary small { font-size: 10px; }
.journey-delivery__chevron { color: var(--moss-dark); font-size: 11px; font-weight: 700; text-align: right; }
.journey-delivery__chapter-body { border-top: 1px solid var(--line); }
.journey-delivery__columns, .journey-delivery__item { display: grid; grid-template-columns: minmax(220px, 1.7fr) minmax(130px, 1fr) minmax(120px, 1fr) 72px 86px; gap: 12px; align-items: center; }
.journey-delivery__columns { padding: 9px 15px; background: var(--paper-soft); color: var(--muted); font-size: 10px; font-weight: 700; }
.journey-delivery__columns span:first-child { padding-left: 20px; }
.journey-delivery__items { list-style: none; margin: 0; padding: 0 15px; }
.journey-delivery__item { min-width: 0; padding: 12px 0; border-bottom: 1px dashed var(--line); font-size: 11.5px; }
.journey-delivery__item:last-child { border-bottom: 0; }
.journey-delivery__task { display: flex; align-items: flex-start; gap: 9px; min-width: 0; }
.journey-delivery__task > div { min-width: 0; display: grid; gap: 3px; }
.journey-delivery__task strong { color: var(--ink); font-size: 12px; line-height: 1.4; }
.journey-delivery__task small { display: -webkit-box; overflow: hidden; color: var(--muted); line-height: 1.4; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.journey-delivery__dot { flex: 0 0 auto; width: 8px; height: 8px; margin-top: 4px; border-radius: 50%; background: var(--moss); }
.journey-delivery__item.is-active .journey-delivery__dot { background: #fff; border: 2px solid var(--moss); box-shadow: 0 0 0 3px var(--color-focus-ring); }
.journey-delivery__item.is-revision .journey-delivery__dot { background: var(--clay); }
.journey-delivery__item.is-locked .journey-delivery__dot { background: var(--line); border: 1px dashed var(--muted); }
.journey-delivery__field { display: grid; gap: 2px; min-width: 0; color: var(--ink); line-height: 1.4; }
.journey-delivery__field > span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.journey-delivery__field-label { display: none; color: var(--muted); font-size: 10px; }
.journey-delivery__status { font-size: 11px; font-weight: 700; white-space: nowrap; }
.journey-delivery__status.is-done { color: var(--moss-dark); }
.journey-delivery__status.is-active { color: var(--moss-dark); }
.journey-delivery__status.is-revision { color: var(--clay); }
.journey-delivery__status.is-locked, .journey-delivery__locked { color: var(--muted); }
.journey-delivery__open { min-height: 30px; padding: 5px 8px; font-size: 11px; white-space: nowrap; }
.journey-delivery__empty { margin: 0; padding: 14px 15px; color: var(--muted); font-size: 12px; }
@media (max-width: 900px) {
  .journey-delivery { padding: 20px 18px; }
  .journey-delivery__columns, .journey-delivery__item { grid-template-columns: minmax(180px, 1.6fr) minmax(110px, 1fr) minmax(100px, 1fr) 64px 78px; gap: 8px; }
}
@media (max-width: 768px) {
  .journey-delivery { padding: 18px 14px; }
  .journey-delivery__chapter-toggle { grid-template-columns: 32px minmax(0, 1fr) auto; gap: 9px; padding: 12px; }
  .journey-delivery__chapter-summary { grid-column: 2; justify-self: start; }
  .journey-delivery__chevron { grid-column: 3; grid-row: 1 / span 2; align-self: center; }
  .journey-delivery__columns { display: none; }
  .journey-delivery__items { padding: 0 12px; }
  .journey-delivery__item { grid-template-columns: minmax(0, 1fr) auto; gap: 8px 12px; padding: 13px 0; }
  .journey-delivery__task { grid-column: 1 / -1; }
  .journey-delivery__field { display: flex; align-items: baseline; gap: 5px; min-width: 0; }
  .journey-delivery__field-label { display: inline; flex: 0 0 auto; }
  .journey-delivery__status { justify-self: start; }
  .journey-delivery__open, .journey-delivery__locked { justify-self: end; }
}
@media (max-width: 430px) {
  .journey-delivery__head h2 { font-size: 18px; }
  .journey-delivery__chapter-summary small { display: none; }
  .journey-delivery__field { font-size: 11px; }
}
</style>
