<script setup lang="ts">
import { computed, ref } from 'vue'
import { Document } from '@element-plus/icons-vue'
import type { JourneyStep, StepStatus } from '../stores/studentApiModel'
import { STEP_STATUS_LABEL } from '../stores/studentApiModel'

const props = defineProps<{
  steps: JourneyStep[]
}>()

const emit = defineEmits<{
  (e: 'open', step: JourneyStep): void
  (e: 'reference', step: JourneyStep): void
}>()

const expanded = ref(false)

const deliveredCount = computed(() => props.steps.filter((s) => s.status === 'done').length)
const totalCount = computed(() => props.steps.length)
</script>

<template>
  <section class="manifest paper-card">
    <header class="manifest__head" @click="expanded = !expanded" role="button" :aria-expanded="expanded" tabindex="0">
      <div>
        <p class="eyebrow">全程交付清单</p>
        <h2>共 {{ totalCount }} 项交付物，已交付 <strong>{{ deliveredCount }}</strong> 项</h2>
      </div>
      <span class="manifest__toggle">{{ expanded ? '收起' : '展开' }}</span>
    </header>

    <transition name="manifest-expand">
      <ul v-if="expanded" class="manifest__list">
        <li
          v-for="step in steps"
          :key="step.id"
          class="manifest__item"
          :class="[`is-${step.status}`, { 'is-clickable': step.status !== 'locked' }]"
        >
          <!-- 状态圆点 -->
          <span class="manifest__dot" />
          <!-- 交付物名 + 所属步骤 -->
          <div class="manifest__text">
            <span class="manifest__name">{{ step.deliverable || '—' }}</span>
            <span class="manifest__origin">STEP {{ String(step.order).padStart(2, '0') }} · {{ step.title }}</span>
          </div>
          <!-- 状态 -->
          <span class="manifest__status">{{ STEP_STATUS_LABEL[step.status] }}</span>
          <!-- 参考范本按钮 -->
          <button
            v-if="step.hasReference && step.status !== 'locked'"
            type="button"
            class="manifest__ref"
            @click.stop="emit('reference', step)"
          >范本</button>
        </li>
      </ul>
    </transition>

    <!-- 折叠时的紧凑进度条 -->
    <div v-if="!expanded" class="manifest__bar">
      <div class="manifest__bar-fill" :style="{ width: `${totalCount ? (deliveredCount / totalCount) * 100 : 0}%` }" />
      <span class="manifest__bar-label">{{ deliveredCount }} / {{ totalCount }}</span>
    </div>
  </section>
</template>

<style scoped>
.manifest { padding: 20px 24px 18px; }

.manifest__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
  gap: 14px;
}
.manifest__head:hover h2 { color: var(--moss-dark); }
.manifest__head h2 { margin: 4px 0 0; font: 700 17px/1.3 var(--serif); transition: color .15s; }
.manifest__head h2 strong { color: var(--moss-dark); }

.manifest__toggle {
  font: 700 12px var(--sans, sans-serif);
  color: var(--moss);
  background: var(--sage-soft);
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  padding: 4px 14px;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background .15s ease;
}
.manifest__head:hover .manifest__toggle { background: var(--moss); color: #fff; border-color: var(--moss-dark); }

/* ── 展开列表 ── */
.manifest__list {
  list-style: none;
  margin: 14px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.manifest__item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto auto;
  gap: 10px;
  align-items: center;
  font-size: 12.5px;
  color: var(--ink);
  padding: 7px 8px;
  border-radius: 6px;
  transition: background .12s ease;
}
.manifest__item.is-clickable { cursor: pointer; }
.manifest__item.is-clickable:hover { background: var(--sage-soft); }
.manifest__item + .manifest__item { border-top: 1px dashed var(--line); }

.manifest__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--moss);
  flex-shrink: 0;
}
.manifest__item.is-active .manifest__dot { background: #fff; border: 2px solid var(--moss); box-shadow: 0 0 0 3px rgba(76, 114, 69, .12); }
.manifest__item.is-locked .manifest__dot { background: var(--line); border: 1px dashed var(--muted); }
.manifest__item.is-done .manifest__dot { background: var(--sage); }

.manifest__text { min-width: 0; display: flex; flex-direction: column; gap: 1px; }

.manifest__name { font-weight: 600; color: var(--ink); }
.manifest__origin { font-size: 10.5px; color: var(--muted); }
.manifest__item.is-locked .manifest__name,
.manifest__item.is-locked .manifest__origin { color: var(--line-dark); }
.manifest__item.is-done .manifest__name { color: var(--sage, #6b8a62); }

.manifest__status {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
}
.manifest__item.is-done .manifest__status { color: var(--moss-dark); }
.manifest__item.is-active .manifest__status { color: var(--amber); }

.manifest__ref {
  font: 700 10.5px var(--sans, sans-serif);
  color: var(--moss-dark, #315833);
  background: var(--paper);
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  padding: 3px 10px;
  cursor: pointer;
  white-space: nowrap;
  transition: background .15s ease, color .15s ease;
}
.manifest__ref:hover { background: var(--moss); color: #fff; border-color: var(--moss-dark); }

/* ── 折叠进度条 ── */
.manifest__bar {
  position: relative;
  margin-top: 14px;
  height: 8px;
  background: var(--paper-soft);
  border-radius: 999px;
  overflow: hidden;
}
.manifest__bar-fill {
  position: absolute;
  inset: 0 0 0 0;
  background: linear-gradient(90deg, var(--moss), var(--sage));
  border-radius: 999px;
  transition: width .4s ease;
}
.manifest__bar-label {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font: 800 9.5px/1 var(--system-ui);
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,.2);
}

/* ── 展开/折叠过渡动画 ── */
.manifest-expand-enter-active,
.manifest-expand-leave-active {
  transition: all .25s ease;
  overflow: hidden;
}
.manifest-expand-enter-from,
.manifest-expand-leave-to {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}
.manifest-expand-enter-to,
.manifest-expand-leave-from {
  opacity: 1;
  max-height: 600px;
}

@media (max-width: 720px) {
  .manifest { padding: 16px 16px 14px; }
  .manifest__item { grid-template-columns: 8px minmax(0, 1fr) auto; font-size: 11.5px; }
  .manifest__ref { display: none; } /* 移动端隐藏范本按钮，节省空间 */
}
</style>
