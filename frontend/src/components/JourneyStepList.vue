<script setup lang="ts">
import { ref } from 'vue'
import JourneyDeliverableCard from './JourneyDeliverableCard.vue'
import type { JourneyChapter, JourneyStep } from '../stores/studentApiModel'

const props = defineProps<{
  chapters: JourneyChapter[]
  activeOrder: number | null   // 当前高亮的步骤 order
}>()

const emit = defineEmits<{
  (e: 'open', step: JourneyStep): void
  (e: 'reference', step: JourneyStep): void
}>()

const CHINESE_NUM = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
function chapterLabel(i: number) { return CHINESE_NUM[i - 1] ?? String(i) }

// 折叠状态：默认全部展开；记录被折叠的 chapter index
const collapsed = ref<number[]>([])
function toggle(index: number) {
  const idx = collapsed.value.indexOf(index)
  if (idx >= 0) collapsed.value.splice(idx, 1)
  else collapsed.value.push(index)
}

// 每个卡的 ref 用于 scrollIntoView
const cardRefs = ref<Map<number, HTMLElement>>(new Map())
function registerRef(order: number, el: HTMLElement | null) {
  if (el) cardRefs.value.set(order, el)
  else cardRefs.value.delete(order)
}

/** 外部调用：滚动到指定步骤并高亮 */
function scrollToStep(order: number) {
  const el = cardRefs.value.get(order)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
/** 外部调用：滚动到指定章节的第一张交付物卡 */
function scrollToChapter(index: number) {
  const ch = props.chapters.find((c) => c.index === index)
  const first = ch?.steps[0]
  if (first) scrollToStep(first.order)
}
defineExpose({ scrollToStep, scrollToChapter })

function statusText(c: JourneyChapter) {
  return c.status === 'done' ? '已通关' : c.status === 'active' ? '进行中' : '待开始'
}
</script>

<template>
  <section class="chapter-list">
    <article
      v-for="ch in chapters"
      :key="ch.index"
      class="chapter-card"
      :class="[`is-${ch.status}`, { 'is-current': ch.containsCurrent }]"
    >
      <!-- 章节头部：印章 + 标题 + 进度 + 折叠 -->
      <header
        class="chapter-card__head"
        role="button"
        :aria-expanded="!collapsed.includes(ch.index)"
        :tabindex="0"
        @click="toggle(ch.index)"
        @keydown.enter.prevent="toggle(ch.index)"
        @keydown.space.prevent="toggle(ch.index)"
      >
        <div class="chapter-card__seal">
          <span class="chapter-card__seal-num">{{ ch.index }}</span>
          <span class="chapter-card__seal-label">第{{ chapterLabel(ch.index) }}章</span>
        </div>

        <div class="chapter-card__info">
          <div class="chapter-card__titlerow">
            <p class="chapter-card__eyebrow">关卡 {{ ch.index }} · CHAPTER</p>
            <span class="chapter-card__status" :class="`tone-${ch.status}`">{{ statusText(ch) }}</span>
          </div>
          <h2 class="chapter-card__name">{{ ch.name }}</h2>
          <div class="chapter-card__progress">
            <div class="chapter-card__bar">
              <div class="chapter-card__bar-fill" :style="{ width: ch.percent + '%' }" />
            </div>
            <span class="chapter-card__count">{{ ch.done }} / {{ ch.total }} 交付物</span>
          </div>
        </div>

        <div class="chapter-card__right">
          <span class="chapter-card__xp">+{{ ch.xp }} XP</span>
          <span class="chapter-card__caret" :class="{ 'is-open': !collapsed.includes(ch.index) }">▾</span>
        </div>

        <span v-if="ch.containsCurrent" class="chapter-card__flag">当前关卡</span>
      </header>

      <!-- 章节正文：该章交付物目标看板（网格同时陈列，无编号顺序） -->
      <div v-show="!collapsed.includes(ch.index)" class="chapter-card__body">
        <JourneyDeliverableCard
          v-for="step in ch.steps"
          :key="step.id"
          :ref="(el: any) => registerRef(step.order, el)"
          :step="step"
          class="chapter-card__task"
          :class="{ 'is-target': activeOrder === step.order }"
          @open="(s) => emit('open', s)"
          @reference="(s) => emit('reference', s)"
        />
      </div>
    </article>
  </section>
</template>

<style scoped>
.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ── 章节卡片 ── */
.chapter-card {
  position: relative;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
  overflow: hidden;
  transition: border-color .2s ease, box-shadow .2s ease;
}
.chapter-card.is-current {
  border-color: var(--moss, #4c7245);
  box-shadow: 0 6px 24px rgba(76, 114, 69, .1);
}
.chapter-card.is-done { background: linear-gradient(180deg, #f3f7ef 0%, var(--paper) 40%); }

/* 头部 */
.chapter-card__head {
  position: relative;
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) auto;
  gap: 14px;
  align-items: center;
  padding: 16px 20px 16px 16px;
  cursor: pointer;
  user-select: none;
  background: linear-gradient(90deg, rgba(238,243,234,.55) 0%, transparent 70%);
}
.chapter-card.is-done .chapter-card__head { background: linear-gradient(90deg, rgba(232,240,227,.6) 0%, transparent 70%); }
.chapter-card__head:hover { background: linear-gradient(90deg, rgba(238,243,234,.9) 0%, rgba(238,243,234,.3) 70%); }

/* 章节印章 */
.chapter-card__seal {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 1px;
  background: linear-gradient(160deg, var(--moss), var(--moss-dark, #315833));
  color: #fff;
  box-shadow: 0 3px 10px rgba(49, 88, 51, .25), inset 0 0 0 2px rgba(255,255,255,.18);
  flex-shrink: 0;
}
.chapter-card.is-done .chapter-card__seal { background: linear-gradient(160deg, var(--sage, #6b8a62), #4f6c47); }
.chapter-card.is-todo .chapter-card__seal {
  background: linear-gradient(160deg, #e9e8e0, #d6d5cb);
  color: var(--muted);
  box-shadow: 0 2px 6px rgba(0,0,0,.08), inset 0 0 0 2px rgba(255,255,255,.4);
}
.chapter-card__seal-num {
  font: 800 24px/1 var(--serif);
}
.chapter-card__seal-label {
  font: 700 9px/1 var(--system-ui, sans-serif);
  letter-spacing: .08em;
  opacity: .92;
}

/* 标题区 */
.chapter-card__info { min-width: 0; }
.chapter-card__titlerow {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.chapter-card__eyebrow {
  margin: 0;
  font: 700 9.5px/1 var(--system-ui, sans-serif);
  letter-spacing: .12em;
  color: var(--moss);
  text-transform: uppercase;
}
.chapter-card__name {
  margin: 4px 0 8px;
  font: 700 19px/1.3 var(--serif);
  color: var(--ink);
}
.chapter-card__progress {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chapter-card__bar {
  flex: 1;
  max-width: 240px;
  height: 8px;
  background: var(--paper-soft, #f0efe9);
  border-radius: 999px;
  overflow: hidden;
}
.chapter-card__bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--moss), var(--sage));
  border-radius: 999px;
  transition: width .4s ease;
}
.chapter-card.is-done .chapter-card__bar-fill { background: linear-gradient(90deg, var(--sage), #4f6c47); }
.chapter-card__count {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  white-space: nowrap;
}

/* 右侧：XP + 折叠箭头 */
.chapter-card__right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}
.chapter-card__xp {
  font: 700 12px var(--serif);
  color: var(--moss-dark, #315833);
  background: var(--sage-soft);
  border: 1px solid var(--sage-line);
  border-radius: 999px;
  padding: 2px 10px;
  white-space: nowrap;
}
.chapter-card__caret {
  font-size: 12px;
  color: var(--moss);
  transition: transform .2s ease;
}
.chapter-card__caret.is-open { transform: rotate(180deg); }

/* 当前关卡旗标 */
.chapter-card__flag {
  position: absolute;
  top: 12px;
  right: 14px;
  font: 700 10px/1 var(--system-ui, sans-serif);
  color: #fff;
  background: var(--amber, #b8860b);
  border-radius: 999px;
  padding: 3px 9px;
  box-shadow: 0 1px 4px rgba(0,0,0,.15);
}

/* 状态药丸 */
.chapter-card__status {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  font-size: 10.5px;
  font-weight: 700;
  border-radius: 999px;
}
.chapter-card__status.tone-done { background: #e8f0e3; color: #4a6e42; }
.chapter-card__status.tone-active { background: var(--sage-soft); color: #315833; }
.chapter-card__status.tone-todo { background: #f5f4ef; color: #9a9d90; }

/* 正文：交付物目标看板网格（同时陈列、无编号顺序） */
.chapter-card__body {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  padding: 16px 18px 18px;
  border-top: 1px dashed var(--line);
}

@media (max-width: 768px) {
  .chapter-card__head { grid-template-columns: 52px minmax(0, 1fr); row-gap: 10px; padding: 14px 14px 14px 12px; }
  .chapter-card__seal { width: 52px; height: 52px; }
  .chapter-card__seal-num { font-size: 20px; }
  .chapter-card__name { font-size: 16px; }
  .chapter-card__right { grid-column: 2; flex-direction: row; align-items: center; justify-content: space-between; width: 100%; }
  .chapter-card__flag { top: auto; bottom: 12px; right: 14px; }
  .chapter-card__body { grid-template-columns: 1fr; padding: 14px 12px; gap: 10px; }
}
</style>
