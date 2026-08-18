<script setup lang="ts">
import { computed } from 'vue'

export interface TimelineStage {
  order: number
  title: string
  description?: string
  badge?: string
  status: 'completed' | 'current' | 'locked' | 'pending'
  tasksCompleted?: number
  tasksTotal?: number
  hint?: string
}

const props = defineProps<{
  stages: TimelineStage[]
  size?: 'compact' | 'full'
}>()

const variant = computed(() => props.size ?? 'full')

function pad(order: number) {
  return String(order).padStart(2, '0')
}

function statusLabel(stage: TimelineStage) {
  if (stage.status === 'completed') return '已完成'
  if (stage.status === 'current') return '进行中'
  if (stage.status === 'locked') return '未解锁'
  return '待开始'
}
</script>

<template>
  <section class="paper-card project-timeline" :class="`project-timeline--${variant}`" aria-label="项目流程时间轴">
    <header class="project-timeline__head">
      <div>
        <p class="eyebrow">项目流程</p>
        <h2>从开题到答辩的完整时间轴</h2>
        <p class="project-timeline__sub">每个阶段对应一组任务；当前阶段会高亮，未解锁阶段会说明前置条件。</p>
      </div>
      <div v-if="stages.length" class="project-timeline__legend">
        <span class="project-timeline__dot project-timeline__dot--done" /> 已完成
        <span class="project-timeline__dot project-timeline__dot--current" /> 进行中
        <span class="project-timeline__dot project-timeline__dot--locked" /> 未解锁
      </div>
    </header>

    <ol v-if="stages.length" class="project-timeline__list">
      <li
        v-for="(stage, idx) in stages"
        :key="stage.order"
        class="project-timeline__node"
        :class="`project-timeline__node--${stage.status}`"
      >
        <span class="project-timeline__pin" aria-hidden="true">
          <span class="project-timeline__order">{{ pad(stage.order) }}</span>
        </span>
        <article class="project-timeline__card">
          <header>
            <div>
              <small>CHAPTER {{ stage.order }}</small>
              <h3>{{ stage.title }}</h3>
              <p v-if="stage.description" class="project-timeline__desc">{{ stage.description }}</p>
            </div>
            <span class="status-tag" :class="{
              success: stage.status === 'completed',
              current: stage.status === 'current' || stage.status === 'pending',
              danger: stage.status === 'locked',
            }">{{ statusLabel(stage) }}</span>
          </header>
          <div v-if="stage.tasksTotal" class="project-timeline__progress">
            <span class="project-timeline__progress-copy">
              <strong>{{ stage.tasksCompleted ?? 0 }} / {{ stage.tasksTotal }}</strong> 项任务已通过
            </span>
            <span class="project-timeline__progress-track" aria-hidden="true">
              <i :style="{ width: `${Math.min(100, ((stage.tasksCompleted ?? 0) / Math.max(stage.tasksTotal, 1)) * 100)}%` }" />
            </span>
          </div>
          <p v-if="stage.hint" class="project-timeline__hint">
            <span v-if="stage.status === 'locked'">🔒</span>
            {{ stage.hint }}
          </p>
          <p v-if="stage.badge" class="project-timeline__badge">{{ stage.badge }}</p>
        </article>
        <span v-if="idx < stages.length - 1" class="project-timeline__rail" aria-hidden="true" />
      </li>
    </ol>

    <p v-else class="empty-state project-timeline__empty">
      还没有生成流程节点，教师认领项目后会按照模板自动展开。
    </p>
  </section>
</template>

<style scoped>
.project-timeline {
  padding: 28px 30px 24px;
}
.project-timeline--compact {
  padding: 22px 24px 18px;
}
.project-timeline__head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 22px;
  padding-bottom: 18px;
  border-bottom: 1px dashed var(--line);
}
.project-timeline__head h2 {
  margin: 4px 0 6px;
  font: 700 22px/1.3 var(--serif);
  color: var(--ink);
}
.project-timeline__sub {
  margin: 0;
  color: var(--muted);
  font-size: 12.5px;
  max-width: 540px;
  line-height: 1.6;
}
.project-timeline__legend {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
}
.project-timeline__dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
.project-timeline__dot--done { background: var(--moss); }
.project-timeline__dot--current { background: #5a8a6f; box-shadow: 0 0 0 4px rgba(76, 114, 69, .18); }
.project-timeline__dot--locked { background: var(--line-dark); }

.project-timeline__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 14px;
}
.project-timeline__node {
  position: relative;
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 18px;
  align-items: stretch;
}
.project-timeline__pin {
  position: relative;
  display: grid;
  place-items: center;
  z-index: 1;
}
.project-timeline__order {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  font: 700 15px var(--serif);
  color: #fff;
  background: var(--moss);
  border: 3px solid var(--paper);
  border-radius: 50%;
  box-shadow: 0 0 0 1px var(--line);
  transition: background .2s ease, color .2s ease;
}
.project-timeline__node--completed .project-timeline__order {
  background: var(--moss);
  color: #fff;
}
.project-timeline__node--current .project-timeline__order {
  background: #fff;
  color: var(--moss-dark);
  box-shadow: 0 0 0 2px var(--moss);
}
.project-timeline__node--current .project-timeline__order::after {
  content: '';
  position: absolute;
  inset: -6px;
  border-radius: 50%;
  border: 1px dashed var(--moss);
  opacity: .55;
  animation: pulse 2.6s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: .35; }
  50% { transform: scale(1.15); opacity: 0; }
}
.project-timeline__node--locked .project-timeline__order {
  background: var(--paper-soft);
  color: var(--muted);
  box-shadow: 0 0 0 1px var(--line);
}
.project-timeline__card {
  position: relative;
  padding: 16px 20px 18px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, .6);
  border-radius: var(--radius-md);
  transition: border-color .2s ease, box-shadow .2s ease;
}
.project-timeline__node--current .project-timeline__card {
  border-color: #a8b9a0;
  background: var(--paper);
  box-shadow: 0 10px 24px rgba(76, 114, 69, .07);
}
.project-timeline__node--completed .project-timeline__card {
  background: rgba(233, 240, 229, .4);
}
.project-timeline__node--locked .project-timeline__card {
  background: var(--paper-soft);
  opacity: .86;
}
.project-timeline__card > header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}
.project-timeline__card small {
  display: block;
  color: var(--muted);
  font-size: 10px;
  letter-spacing: .14em;
  font-weight: 700;
  margin-bottom: 2px;
}
.project-timeline__card h3 {
  margin: 0;
  font: 700 17px/1.35 var(--serif);
  color: var(--ink);
}
.project-timeline__desc {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.55;
}
.project-timeline__progress {
  margin-top: 12px;
  display: grid;
  gap: 6px;
}
.project-timeline__progress-copy {
  color: var(--moss);
  font-size: 11.5px;
  font-weight: 700;
}
.project-timeline__progress-copy strong {
  font-weight: 800;
  color: var(--moss-dark);
}
.project-timeline__progress-track {
  display: block;
  height: 4px;
  background: rgba(76, 114, 69, .12);
  border-radius: 999px;
  overflow: hidden;
}
.project-timeline__progress-track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--moss), #6b9368);
  border-radius: 999px;
  transition: width .3s ease;
}
.project-timeline__hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 12px 0 0;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--muted);
  background: var(--paper-soft);
  border: 1px dashed var(--line);
  border-radius: 8px;
}
.project-timeline__badge {
  margin: 10px 0 0;
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 700;
  color: var(--moss-dark);
  background: var(--sage-soft);
  border: 1px solid #c8d8c0;
  border-radius: 999px;
}
.project-timeline__rail {
  position: absolute;
  left: 26px;
  top: 44px;
  bottom: -18px;
  width: 2px;
  background: linear-gradient(180deg, var(--moss) 0%, var(--moss) 30%, var(--line) 30%, var(--line) 100%);
  background-size: 2px 14px;
  background-repeat: repeat-y;
  z-index: 0;
}
.project-timeline__node--locked .project-timeline__rail {
  background: repeating-linear-gradient(180deg, var(--line-dark) 0 6px, transparent 6px 12px);
}
.project-timeline__node:last-child .project-timeline__rail {
  display: none;
}
.project-timeline__empty {
  margin: 0;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

@media (max-width: 720px) {
  .project-timeline { padding: 22px 18px 16px; }
  .project-timeline__node { grid-template-columns: 40px minmax(0, 1fr); gap: 12px; }
  .project-timeline__order { width: 36px; height: 36px; font-size: 13px; }
  .project-timeline__rail { left: 18px; }
}
</style>
