<script setup lang="ts">
import { Document, Paperclip, ArrowRight } from '@element-plus/icons-vue'
import type { JourneyStep, StepStatus } from '../stores/studentApiModel'
import { STEP_STATUS_LABEL } from '../stores/studentApiModel'

const props = defineProps<{
  step: JourneyStep
}>()

const emit = defineEmits<{
  (e: 'open', step: JourneyStep): void
  (e: 'reference', step: JourneyStep): void
}>()

const statusLabel = STEP_STATUS_LABEL

/** 详细目标：优先用材料指引（"这份材料要写什么"），缺失时回退任务描述 */
const objective = (step: JourneyStep): string => step.guidance?.trim() || step.description?.trim() || ''
</script>

<template>
  <article
    class="deliverable-card"
    :class="[`is-${step.status}`, { 'is-current': step.isCurrent }]"
  >
    <!-- 顶部：状态 + XP（弱化序号，强调目标） -->
    <header class="deliverable-card__top">
      <span class="deliverable-card__status" :class="`tone-${step.status}`">{{ statusLabel[step.status] }}</span>
      <span v-if="step.isCurrent" class="deliverable-card__current-tag">进行中</span>
      <span class="deliverable-card__xp">+{{ step.xpReward }} XP</span>
    </header>

    <!-- 主标题：交付物名（视觉重心） -->
    <h3 class="deliverable-card__deliverable">{{ step.deliverable || '—' }}</h3>
    <!-- 副标题：这一步要做什么 -->
    <p class="deliverable-card__action">{{ step.title }}</p>

    <!-- 详细目标区 -->
    <div class="deliverable-card__objective">
      <span class="deliverable-card__objective-label">交付目标</span>
      <p class="deliverable-card__objective-text">{{ objective(step) }}</p>
    </div>

    <!-- 证据清单 -->
    <ul v-if="step.evidence.length" class="deliverable-card__evidence">
      <li v-for="(item, idx) in step.evidence" :key="idx">
        <el-icon><Paperclip /></el-icon>{{ item }}
      </li>
    </ul>

    <!-- 进入报告章节提示 -->
    <p v-if="step.reportSection" class="deliverable-card__report">进入报告：{{ step.reportSection }}</p>

    <!-- 操作 -->
    <div class="deliverable-card__actions">
      <button type="button" class="deliverable-card__cta" @click="emit('open', step)">
        {{ step.status === 'revision' ? '去修订' : step.status === 'done' ? '查看成果' : '打开任务' }}
        <el-icon><ArrowRight /></el-icon>
      </button>
      <button
        v-if="step.hasReference"
        type="button"
        class="deliverable-card__ref-btn"
        @click.stop="emit('reference', step)"
      >
        <el-icon><Document /></el-icon> 参考范本
      </button>
    </div>
  </article>
</template>

<style scoped>
.deliverable-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 16px 14px;
  border: 1px solid var(--line);
  border-top: 3px solid var(--line);
  border-radius: 12px;
  background: var(--paper);
  transition: border-color .2s ease, box-shadow .2s ease, transform .15s ease;
}
.deliverable-card:not(.is-done):hover {
  border-color: #b8c7b1;
  box-shadow: 0 6px 22px rgba(61, 68, 53, .07);
  transform: translateY(-1px);
}

/* 状态上色（顶部条） */
.deliverable-card.is-done { border-top-color: var(--sage, #6b8a62); opacity: .92; }
.deliverable-card.is-active { border-top-color: var(--moss, #4c7245); }
.deliverable-card.is-revision { border-top-color: var(--clay, #c4846a); background: #fffaf7; }
.deliverable-card.is-current {
  border-color: var(--moss, #4c7245);
  box-shadow: 0 4px 20px rgba(76, 114, 69, .1), 0 0 0 1px rgba(76, 114, 69, .08);
}

.deliverable-card__top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.deliverable-card__status {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  font-size: 10.5px;
  font-weight: 700;
  border-radius: 999px;
}
.deliverable-card__status.tone-done { background: #e8f0e3; color: #4a6e42; }
.deliverable-card__status.tone-active { background: var(--sage-soft); color: #315833; }
.deliverable-card__status.tone-revision { background: #fdf0eb; color: #a85a3a; }
.deliverable-card__status.tone-locked { background: #f5f4ef; color: #9a9d90; }

.deliverable-card__current-tag {
  font: 700 9.5px/1 var(--system-ui, sans-serif);
  color: var(--moss-dark, #315833);
  background: var(--sage-soft);
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  padding: 2px 8px;
}
.deliverable-card__xp {
  margin-left: auto;
  font: 700 11px var(--serif);
  color: var(--moss);
  background: var(--sage-soft);
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}

.deliverable-card__deliverable {
  margin: 2px 0 0;
  font: 700 17px/1.35 var(--serif);
  color: var(--moss-dark, #315833);
}
.deliverable-card.is-done .deliverable-card__deliverable { color: var(--sage, #6b8a62); }

.deliverable-card__action {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--ink);
}

.deliverable-card__objective {
  background: linear-gradient(160deg, var(--sage-soft) 0%, #e4eadc 100%);
  border: 1px solid #d4e0cc;
  border-radius: 8px;
  padding: 9px 11px;
}
.deliverable-card__objective-label {
  display: block;
  font: 700 9.5px/1 var(--system-ui, sans-serif);
  letter-spacing: .1em;
  color: var(--moss);
  margin-bottom: 4px;
}
.deliverable-card__objective-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--moss-dark, #315833);
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.deliverable-card__evidence {
  list-style: none;
  margin: 2px 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}
.deliverable-card__evidence li {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--moss-dark, #315833);
}
.deliverable-card__evidence li .el-icon { color: var(--moss); font-size: 12px; }

.deliverable-card__report {
  margin: 0;
  font-size: 10.5px;
  color: var(--muted);
}

.deliverable-card__actions {
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.deliverable-card__cta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  font: 700 12.5px var(--serif);
  color: #fff;
  background: linear-gradient(135deg, var(--moss), var(--moss-dark, #315833));
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: 0 3px 10px rgba(49, 88, 51, .2);
  transition: transform .15s ease, box-shadow .15s ease;
}
.deliverable-card__cta:hover { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(49, 88, 51, .28); }
.deliverable-card__cta .el-icon { font-size: 13px; }

.deliverable-card__ref-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  font: 600 11.5px var(--sans, sans-serif);
  color: var(--moss-dark, #315833);
  background: var(--paper);
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease;
}
.deliverable-card__ref-btn:hover { background: var(--moss); color: #fff; border-color: var(--moss-dark, #315833); }
.deliverable-card__ref-btn .el-icon { font-size: 13px; }

/* 目标到达高亮 */
.deliverable-card.is-target { animation: target-pulse 1.5s ease-out; }
@keyframes target-pulse {
  0% { box-shadow: 0 0 0 0 rgba(76, 114, 69, .25); }
  50% { box-shadow: 0 0 0 6px rgba(76, 114, 69, .08); }
  100% { box-shadow: none; }
}

@media (max-width: 768px) {
  .deliverable-card { padding: 14px 14px 12px; }
  .deliverable-card__deliverable { font-size: 16px; }
}
</style>
