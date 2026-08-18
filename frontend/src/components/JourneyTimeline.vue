<script setup lang="ts">
import { computed } from 'vue'

export interface JourneyNode {
  order: number
  title: string
  status: 'completed' | 'current' | 'pending' | 'locked'
  hint?: string
  passed?: number
  total?: number
}

const props = defineProps<{
  nodes: JourneyNode[]
  active?: number
}>()

const emit = defineEmits<{
  (e: 'select', order: number): void
}>()

const enrichedNodes = computed(() => props.nodes.map((node) => ({ ...node })))
</script>

<template>
  <section v-if="enrichedNodes.length" class="journey-rail" aria-label="研究旅程时间轴">
    <ol class="journey-rail__track">
      <li
        v-for="(node, idx) in enrichedNodes"
        :key="node.order"
        class="journey-rail__node"
        :class="[`is-${node.status}`, { 'is-active': active === node.order }]"
        :aria-current="active === node.order ? 'step' : undefined"
      >
        <button
          type="button"
          class="journey-rail__btn"
          :aria-label="`跳转到第 ${node.order} 阶段：${node.title}`"
          @click="emit('select', node.order)"
        >
          <span class="journey-rail__pin">{{ String(node.order).padStart(2, '0') }}</span>
        </button>
        <div class="journey-rail__caption">
          <strong>{{ node.title }}</strong>
          <small v-if="node.total">{{ node.passed ?? 0 }} / {{ node.total }} 项</small>
          <small v-else-if="node.hint">{{ node.hint }}</small>
        </div>
        <span v-if="idx < enrichedNodes.length - 1" class="journey-rail__line" :class="`is-${node.status}`" aria-hidden="true" />
      </li>
    </ol>
  </section>
</template>

<style scoped>
.journey-rail {
  padding: 24px 24px 22px;
  border: 1px solid var(--line);
  background: var(--paper);
  border-radius: var(--radius-md);
  overflow-x: auto;
}
.journey-rail__track {
  list-style: none;
  margin: 0;
  padding: 8px 0 16px;
  display: flex;
  gap: 0;
  min-width: max-content;
}
.journey-rail__node {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1 0 calc(100% / 10);
  min-width: 90px;
}
.journey-rail__btn {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border: 0;
  background: transparent;
  cursor: pointer;
  padding: 0;
}
.journey-rail__pin {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  font: 700 14px var(--serif);
  color: #fff;
  background: var(--moss);
  border: 3px solid var(--paper);
  border-radius: 50%;
  box-shadow: 0 0 0 1px var(--line);
  transition: transform .18s ease, box-shadow .18s ease, background .2s ease;
}
.journey-rail__node.is-completed .journey-rail__pin { background: var(--moss); color: #fff; }
.journey-rail__node.is-current .journey-rail__pin {
  background: #fff;
  color: var(--moss-dark);
  box-shadow: 0 0 0 2px var(--moss);
}
.journey-rail__node.is-pending .journey-rail__pin { background: #a8b9a0; color: #fff; }
.journey-rail__node.is-locked .journey-rail__pin {
  background: var(--paper-soft);
  color: var(--muted);
  box-shadow: 0 0 0 1px var(--line);
}
.journey-rail__node.is-active .journey-rail__pin {
  transform: scale(1.1);
  box-shadow: 0 0 0 2px var(--moss), 0 0 0 7px rgba(76, 114, 69, .15);
}
.journey-rail__btn:hover .journey-rail__pin { transform: scale(1.06); }

.journey-rail__caption {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 3px;
  max-width: 140px;
}
.journey-rail__caption strong {
  font: 700 13.5px/1.4 var(--serif);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.journey-rail__node.is-locked .journey-rail__caption strong { color: var(--muted); }
.journey-rail__node.is-current .journey-rail__caption strong { color: var(--moss-dark); }
.journey-rail__caption small {
  font-size: 11px;
  color: var(--muted);
}

.journey-rail__line {
  position: absolute;
  top: 24px;
  left: calc(50% + 24px);
  right: calc(-50% + 24px);
  height: 2px;
  background: var(--moss);
  z-index: 0;
}
.journey-rail__node.is-completed .journey-rail__line { background: var(--moss); }
.journey-rail__node.is-current .journey-rail__line {
  background: repeating-linear-gradient(90deg, var(--moss) 0 6px, transparent 6px 12px);
}
.journey-rail__node.is-pending .journey-rail__line { background: var(--line-dark); }
.journey-rail__node.is-locked .journey-rail__line { background: var(--line-dark); }
</style>
