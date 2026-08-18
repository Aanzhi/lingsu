<script setup lang="ts">
import { computed } from 'vue'

export interface DeliveryItem {
  id: string | number
  // 流程里这一步最终落到报告里的章节名（material.report_section）
  label: string
  // 对应的材料标题（material.title），让交付 = 流程 + 报告 + 材料三段对齐
  subLabel?: string
  // 流程里这一步对应的任务名（task.title）
  taskLabel?: string
  status: 'delivered' | 'in_progress' | 'pending' | 'locked'
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

const props = defineProps<{
  groups: DeliveryGroup[]
}>()

const totalItems = computed(() => props.groups.reduce((sum, group) => sum + group.items.length, 0))
const deliveredCount = computed(() => props.groups.reduce((sum, group) => sum + group.items.filter((item) => item.status === 'delivered').length, 0))
const statusLabel: Record<DeliveryItem['status'], string> = {
  delivered: '已交付',
  in_progress: '进行中',
  pending: '待开始',
  locked: '未解锁',
}
const groupStatusLabel: Record<DeliveryGroup['status'], string> = {
  completed: '已完成',
  current: '当前章',
  pending: '待开始',
  locked: '未解锁',
}
const groupTone: Record<DeliveryGroup['status'], string> = {
  completed: 'success',
  current: 'current',
  pending: 'neutral',
  locked: 'danger',
}
</script>

<template>
  <section class="paper-card journey-delivery">
    <header class="journey-delivery__head">
      <div>
        <p class="eyebrow">项目交付清单</p>
        <h2>每一章要交付什么，对应流程里哪一天</h2>
        <p>共 {{ totalItems }} 项交付物，已交付 <strong>{{ deliveredCount }}</strong> 项。下表按阶段分组，和时间轴上的圆点一一对应。</p>
      </div>
    </header>
    <div class="journey-delivery__grid">
      <article
        v-for="group in groups"
        :key="group.order"
        class="journey-delivery__group"
        :class="`is-${group.status}`"
      >
        <header class="journey-delivery__group-head">
          <div class="journey-delivery__group-id">
            <span class="journey-delivery__group-pin">{{ String(group.order).padStart(2, '0') }}</span>
            <div>
              <small>第 {{ group.order }} 章</small>
              <strong>{{ group.title }}</strong>
            </div>
          </div>
          <div class="journey-delivery__group-meta">
            <span class="status-tag" :class="groupTone[group.status]">{{ groupStatusLabel[group.status] }}</span>
            <span class="journey-delivery__group-progress">
              <strong>{{ group.passed }} / {{ group.total }}</strong>
              <small>项任务</small>
            </span>
          </div>
        </header>
        <ul v-if="group.items.length" class="journey-delivery__items">
          <li
            v-for="item in group.items"
            :key="item.id"
            class="journey-delivery__item"
            :class="`is-${item.status}`"
          >
            <span class="journey-delivery__dot" />
            <div class="journey-delivery__text">
              <span class="journey-delivery__chain">
                <span v-if="item.taskLabel" class="journey-delivery__chip journey-delivery__chip--flow">流程 {{ String(item.stage ?? group.order).padStart(2, '0') }} · {{ item.taskLabel }}</span>
                <span v-if="item.taskLabel && item.label" class="journey-delivery__arrow" aria-hidden="true">→</span>
                <span class="journey-delivery__chip journey-delivery__chip--section">报告章节 · {{ item.label }}</span>
                <span v-if="item.subLabel && item.subLabel !== item.label" class="journey-delivery__arrow" aria-hidden="true">→</span>
                <span v-if="item.subLabel && item.subLabel !== item.label" class="journey-delivery__chip journey-delivery__chip--material">材料 · {{ item.subLabel }}</span>
              </span>
              <span v-if="!item.taskLabel" class="journey-delivery__label">{{ item.label }}</span>
            </div>
            <span class="journey-delivery__status">{{ statusLabel[item.status] }}</span>
          </li>
        </ul>
        <p v-else class="journey-delivery__empty">这一章还没有可交付的内容</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.journey-delivery { padding: 24px 28px 22px; }
.journey-delivery__head { margin-bottom: 18px; }
.journey-delivery__head h2 { margin: 4px 0 6px; font: 700 20px/1.3 var(--serif); color: var(--ink); }
.journey-delivery__head p { margin: 0; color: var(--muted); font-size: 12.5px; }
.journey-delivery__head strong { color: var(--moss-dark); }

.journey-delivery__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.journey-delivery__group {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, .5);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.journey-delivery__group.is-current {
  border-color: #a8b9a0;
  background: var(--paper);
  box-shadow: 0 8px 18px rgba(76, 114, 69, .06);
}
.journey-delivery__group.is-completed { border-color: #c8d8c0; }
.journey-delivery__group.is-locked { opacity: .78; background: var(--paper-soft); }

.journey-delivery__group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px dashed var(--line);
  background: var(--sage-soft);
}
.journey-delivery__group.is-current .journey-delivery__group-head { background: var(--sage-soft); }
.journey-delivery__group.is-completed .journey-delivery__group-head { background: rgba(233, 240, 229, .55); }
.journey-delivery__group.is-locked .journey-delivery__group-head { background: var(--paper-soft); }

.journey-delivery__group-id {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.journey-delivery__group-pin {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  font: 700 12px var(--serif);
  color: #fff;
  background: var(--moss);
  border-radius: 50%;
  flex: 0 0 auto;
}
.journey-delivery__group.is-locked .journey-delivery__group-pin { background: var(--line-dark); color: var(--muted); }
.journey-delivery__group.is-current .journey-delivery__group-pin { background: #fff; color: var(--moss-dark); box-shadow: 0 0 0 2px var(--moss); }
.journey-delivery__group-id small { display: block; font-size: 10px; letter-spacing: .12em; color: var(--moss); font-weight: 700; }
.journey-delivery__group-id strong { display: block; font: 700 13px/1.3 var(--serif); color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.journey-delivery__group-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.journey-delivery__group-progress {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
}
.journey-delivery__group-progress strong { font: 700 13px var(--serif); color: var(--moss-dark); }

.journey-delivery__items {
  list-style: none;
  margin: 0;
  padding: 10px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.journey-delivery__item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  font-size: 12.5px;
  color: var(--ink);
  padding: 4px 0;
  border-bottom: 1px dashed var(--line);
}
.journey-delivery__item:last-child { border-bottom: 0; }
.journey-delivery__text { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.journey-delivery__label { font-weight: 600; color: var(--ink); }
.journey-delivery__chain {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.journey-delivery__chip {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.4;
  border: 1px solid var(--line);
  background: var(--paper);
  color: var(--ink);
  white-space: nowrap;
}
.journey-delivery__chip--flow {
  color: var(--moss-dark);
  background: var(--sage-soft);
  border-color: #c8d8c0;
}
.journey-delivery__chip--section {
  color: var(--amber);
  background: var(--amber-soft);
  border-color: #ebddc1;
}
.journey-delivery__chip--material {
  color: var(--muted);
  background: var(--paper-soft);
  border-color: var(--line);
}
.journey-delivery__item.is-locked .journey-delivery__chip { color: var(--muted); background: var(--paper-soft); border-color: var(--line); }
.journey-delivery__item.is-delivered .journey-delivery__chip--flow { background: var(--moss); color: #fff; border-color: var(--moss-dark); }
.journey-delivery__item.is-delivered .journey-delivery__chip--section { color: #fff; background: var(--amber); border-color: var(--amber); }
.journey-delivery__arrow {
  color: var(--muted);
  font-weight: 700;
  font-size: 12px;
  letter-spacing: .04em;
}
.journey-delivery__item.is-delivered .journey-delivery__arrow { color: var(--moss-dark); }
.journey-delivery__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--moss);
}
.journey-delivery__item.is-pending .journey-delivery__dot { background: var(--line-dark); }
.journey-delivery__item.is-locked .journey-delivery__dot { background: var(--line); border: 1px dashed var(--muted); }
.journey-delivery__item.is-in_progress .journey-delivery__dot {
  background: #fff;
  border: 2px solid var(--moss);
  box-shadow: 0 0 0 3px rgba(76, 114, 69, .12);
}
.journey-delivery__item.is-pending,
.journey-delivery__item.is-locked { color: var(--muted); }
.journey-delivery__status {
  font-size: 10.5px;
  color: var(--muted);
  white-space: nowrap;
  font-weight: 600;
}
.journey-delivery__item.is-delivered .journey-delivery__status { color: var(--moss-dark); }
.journey-delivery__item.is-in_progress .journey-delivery__status { color: var(--amber); }
.journey-delivery__empty {
  margin: 0;
  padding: 14px;
  font-size: 12px;
  color: var(--muted);
  text-align: center;
}
</style>
