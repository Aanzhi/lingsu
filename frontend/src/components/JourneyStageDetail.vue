<script setup lang="ts">
import { CircleCheck, Lock, Paperclip } from '@element-plus/icons-vue'

export interface JourneyTaskRow {
  id: number
  order: number
  title: string
  description?: string
  status: 'available' | 'in_progress' | 'submitted' | 'pending_review' | 'revision_required' | 'approved' | 'completed' | 'locked'
  xpReward: number
  evidence: string[]
  href?: string
  // 报告章节名（material.report_section）
  deliveryLabel?: string
  // 材料标题（material.title）
  deliverySubLabel?: string
  // 当前阶段序号（用于把流程步骤显式标在任务行上）
  stageOrder?: number
}

const props = defineProps<{
  order: number
  title: string
  status: 'completed' | 'current' | 'pending' | 'locked'
  summary?: string
  tasks: JourneyTaskRow[]
  passed: number
  total: number
}>()

const emit = defineEmits<{
  (e: 'open', task: JourneyTaskRow): void
}>()

const statusLabel: Record<JourneyTaskRow['status'], string> = {
  available: '可开始',
  in_progress: '进行中',
  submitted: '已提交',
  pending_review: '审核中',
  revision_required: '需修订',
  approved: '已通过',
  completed: '已通过',
  locked: '未解锁',
}

const statusTone: Record<JourneyTaskRow['status'], 'success' | 'current' | 'warning' | 'danger' | 'neutral'> = {
  available: 'current',
  in_progress: 'current',
  submitted: 'warning',
  pending_review: 'warning',
  revision_required: 'danger',
  approved: 'success',
  completed: 'success',
  locked: 'neutral',
}

function isIconCheck(status: JourneyTaskRow['status']) {
  return status === 'approved' || status === 'completed'
}
function isIconLock(status: JourneyTaskRow['status']) {
  return status === 'locked'
}
function isIconPaperclip(status: JourneyTaskRow['status']) {
  return !isIconCheck(status) && !isIconLock(status)
}
</script>

<template>
  <section class="paper-card journey-stage-detail" :class="`is-${status}`">
    <header class="journey-stage-detail__head">
      <div class="journey-stage-detail__id">
        <span class="journey-stage-detail__badge">第 {{ order }} 章</span>
        <h2>{{ title }}</h2>
        <p v-if="summary">{{ summary }}</p>
      </div>
      <div class="journey-stage-detail__meta">
        <span class="status-tag" :class="status === 'completed' ? 'success' : status === 'current' ? 'current' : status === 'locked' ? 'danger' : 'neutral'">
          {{ status === 'completed' ? '已完成' : status === 'current' ? '进行中' : status === 'locked' ? '未解锁' : '待开始' }}
        </span>
        <span class="journey-stage-detail__progress">
          <strong>{{ passed }} / {{ total }}</strong>
          <small>项已通过</small>
        </span>
      </div>
    </header>

    <ol v-if="tasks.length" class="journey-stage-detail__rows">
      <li
        v-for="task in tasks"
        :key="task.id"
        class="journey-stage-detail__row"
        :class="`is-${task.status}`"
      >
        <span class="journey-stage-detail__order">{{ String(task.order).padStart(2, '0') }}</span>
        <div class="journey-stage-detail__main">
          <div>
            <strong>{{ task.title }}</strong>
            <p>{{ task.description }}</p>
            <ul v-if="task.evidence.length" class="journey-stage-detail__evidence">
              <li v-for="(item, idx) in task.evidence" :key="idx">
                <el-icon><Paperclip /></el-icon>{{ item }}
              </li>
            </ul>
          </div>
          <div class="journey-stage-detail__side">
            <span class="status-tag" :class="statusTone[task.status]">{{ statusLabel[task.status] }}</span>
            <span class="journey-stage-detail__xp">+{{ task.xpReward }} XP</span>
            <div v-if="task.deliveryLabel || task.deliverySubLabel" class="journey-stage-detail__chain">
              <span class="journey-stage-detail__chip journey-stage-detail__chip--flow">流程 {{ String(task.stageOrder ?? order).padStart(2, '0') }} · {{ task.title }}</span>
              <span v-if="task.deliveryLabel" class="journey-stage-detail__arrow" aria-hidden="true">→</span>
              <span v-if="task.deliveryLabel" class="journey-stage-detail__chip journey-stage-detail__chip--section">报告章节 · {{ task.deliveryLabel }}</span>
              <span v-if="task.deliverySubLabel && task.deliverySubLabel !== task.deliveryLabel" class="journey-stage-detail__arrow" aria-hidden="true">→</span>
              <span v-if="task.deliverySubLabel && task.deliverySubLabel !== task.deliveryLabel" class="journey-stage-detail__chip journey-stage-detail__chip--material">材料 · {{ task.deliverySubLabel }}</span>
            </div>
          </div>
          <button
            v-if="task.status !== 'locked'"
            class="secondary-button journey-stage-detail__open"
            type="button"
            @click="emit('open', task)"
          >
            打开任务 <el-icon><Paperclip /></el-icon>
          </button>
          <span v-else class="journey-stage-detail__lock"><el-icon><Lock /></el-icon>先完成上一项</span>
        </div>
        <span class="journey-stage-detail__icon" aria-hidden="true">
          <CircleCheck v-if="isIconCheck(task.status)" />
          <Lock v-else-if="isIconLock(task.status)" />
          <Paperclip v-else />
        </span>
      </li>
    </ol>
    <p v-else class="empty-state journey-stage-detail__empty">这个阶段还没有安排任务，教师可在此添加。</p>
  </section>
</template>

<style scoped>
.journey-stage-detail {
  padding: 22px 26px 20px;
}
.journey-stage-detail.is-locked { opacity: .86; }
.journey-stage-detail__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  padding-bottom: 18px;
  margin-bottom: 18px;
  border-bottom: 1px dashed var(--line);
}
.journey-stage-detail__id { display: flex; flex-direction: column; gap: 6px; }
.journey-stage-detail__badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .12em;
  color: var(--moss-dark);
  background: var(--sage-soft);
  border: 1px solid #c8d8c0;
  border-radius: 999px;
  width: fit-content;
}
.journey-stage-detail__id h2 {
  margin: 0;
  font: 700 22px/1.3 var(--serif);
  color: var(--ink);
}
.journey-stage-detail__id p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.6; }
.journey-stage-detail__meta {
  display: flex;
  align-items: center;
  gap: 14px;
}
.journey-stage-detail__progress {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  font-size: 11.5px;
  color: var(--muted);
}
.journey-stage-detail__progress strong {
  font: 700 18px/1 var(--serif);
  color: var(--moss-dark);
}

.journey-stage-detail__rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.journey-stage-detail__row {
  position: relative;
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 30px;
  gap: 14px;
  align-items: stretch;
  padding: 12px 14px 12px 0;
  border: 1px solid var(--line);
  background: var(--paper);
  border-radius: 10px;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.journey-stage-detail__row:not(.is-locked):hover {
  border-color: #b8c7b1;
  box-shadow: 0 5px 14px rgba(61, 68, 53, .06);
}
.journey-stage-detail__row.is-locked { opacity: .68; background: var(--paper-soft); }
.journey-stage-detail__row.is-revision_required { border-color: #dfb6a8; background: #fffaf7; }

.journey-stage-detail__order {
  display: grid;
  place-items: center;
  font: 700 13px var(--serif);
  color: #fff;
  background: var(--moss);
  border-radius: 10px 0 0 10px;
  letter-spacing: .04em;
}
.journey-stage-detail__row.is-locked .journey-stage-detail__order { background: var(--line-dark); color: var(--muted); }
.journey-stage-detail__row.is-revision_required .journey-stage-detail__order { background: var(--clay); }

.journey-stage-detail__main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px 14px;
  align-items: start;
  padding: 4px 6px 0 0;
}
.journey-stage-detail__main strong { font: 700 15px/1.4 var(--serif); color: var(--ink); }
.journey-stage-detail__main p { margin: 4px 0 0; color: var(--muted); font-size: 12.5px; line-height: 1.55; }
.journey-stage-detail__evidence {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: grid;
  gap: 4px;
}
.journey-stage-detail__evidence li {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--moss-dark);
}
.journey-stage-detail__evidence li .el-icon { color: var(--moss); }

.journey-stage-detail__side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.journey-stage-detail__xp {
  color: var(--moss);
  font: 700 12px var(--serif);
  background: var(--sage-soft);
  border: 1px solid #c8d8c0;
  border-radius: 999px;
  padding: 2px 8px;
}
.journey-stage-detail__chain {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 5px;
  max-width: 320px;
}
.journey-stage-detail__chip {
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
.journey-stage-detail__chip--flow {
  color: var(--moss-dark);
  background: var(--sage-soft);
  border-color: #c8d8c0;
}
.journey-stage-detail__chip--section {
  color: var(--amber);
  background: var(--amber-soft);
  border-color: #ebddc1;
}
.journey-stage-detail__chip--material {
  color: var(--muted);
  background: var(--paper-soft);
  border-color: var(--line);
}
.journey-stage-detail__row.is-locked .journey-stage-detail__chip { color: var(--muted); background: var(--paper-soft); border-color: var(--line); }
.journey-stage-detail__row.is-approved .journey-stage-detail__chip--flow,
.journey-stage-detail__row.is-completed .journey-stage-detail__chip--flow { background: var(--moss); color: #fff; border-color: var(--moss-dark); }
.journey-stage-detail__row.is-approved .journey-stage-detail__chip--section,
.journey-stage-detail__row.is-completed .journey-stage-detail__chip--section { color: #fff; background: var(--amber); border-color: var(--amber); }
.journey-stage-detail__arrow {
  color: var(--muted);
  font-weight: 700;
  font-size: 12px;
}
.journey-stage-detail__row.is-approved .journey-stage-detail__arrow,
.journey-stage-detail__row.is-completed .journey-stage-detail__arrow { color: var(--moss-dark); }

.journey-stage-detail__open {
  grid-column: 1 / -1;
  justify-self: end;
  margin-top: 4px;
}
.journey-stage-detail__lock {
  grid-column: 1 / -1;
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--muted);
}

.journey-stage-detail__icon {
  display: grid;
  place-items: center;
  color: var(--moss);
  font-size: 18px;
}
.journey-stage-detail__row.is-locked .journey-stage-detail__icon { color: var(--muted); }
.journey-stage-detail__row.is-revision_required .journey-stage-detail__icon { color: var(--clay); }
.journey-stage-detail__empty {
  text-align: center;
  font-size: 12.5px;
  color: var(--muted);
  margin: 0;
}

@media (max-width: 720px) {
  .journey-stage-detail { padding: 18px 16px; }
  .journey-stage-detail__head { flex-direction: column; align-items: flex-start; }
  .journey-stage-detail__row { grid-template-columns: 36px minmax(0, 1fr); }
  .journey-stage-detail__icon { display: none; }
  .journey-stage-detail__main { grid-template-columns: 1fr; }
  .journey-stage-detail__side { flex-direction: row; flex-wrap: wrap; }
}
</style>
