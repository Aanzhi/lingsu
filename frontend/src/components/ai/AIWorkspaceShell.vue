<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import AppTopbar from '../AppTopbar.vue'
import type { AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

const props = withDefaults(defineProps<{
  mode: AIWorkspaceMode
  projectLabel?: string
  historyOpen?: boolean
  contextOpen?: boolean
  agentOpen?: boolean
  loading?: boolean
  roleTone?: 'student' | 'teacher'
}>(), {
  projectLabel: '',
  historyOpen: false,
  contextOpen: false,
  agentOpen: false,
  loading: false,
  roleTone: 'student',
})

const emit = defineEmits<{
  (event: 'toggle-history'): void
  (event: 'toggle-context'): void
  (event: 'close-drawers'): void
}>()

const drawerOpen = computed(() => props.historyOpen || props.contextOpen || props.agentOpen)

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && drawerOpen.value) emit('close-drawers')
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="ai-workspace-shell" :class="{ 'is-drawer-open': drawerOpen }" data-ai-workspace="full-screen">
    <AppTopbar :role-tone="props.roleTone" />
    <main class="ai-workspace-shell__main">
      <div class="ai-workspace-shell__toolbar" aria-label="灵思 AI 工作台操作">
        <div class="ai-workspace-shell__context">
          <span class="ai-workspace-shell__status" aria-hidden="true" />
          <span>{{ props.projectLabel || (props.mode === 'opening' ? '开题工作区' : '灵思 AI') }}</span>
        </div>
        <div class="ai-workspace-shell__actions">
          <button class="ai-workspace-shell__action" type="button" :aria-expanded="props.historyOpen" aria-controls="conversation-history" @click="emit('toggle-history')">历史对话</button>
          <button class="ai-workspace-shell__action" type="button" :aria-expanded="props.contextOpen" aria-controls="ai-context-drawer" @click="emit('toggle-context')">当前上下文</button>
        </div>
      </div>
      <slot />
    </main>
    <div v-if="drawerOpen" class="ai-workspace-shell__backdrop" aria-hidden="true" @click="emit('close-drawers')" />
    <slot name="history" />
    <slot name="context" />
    <slot name="agent" />
  </div>
</template>

<style scoped>
.ai-workspace-shell {
  --ai-shell-topbar: 66px;
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  background: var(--paper-muted, #f4f6f1);
  color: var(--ink);
}
.ai-workspace-shell__main {
  position: relative;
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: hidden;
}
.ai-workspace-shell__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 48px;
  padding: 0 max(24px, calc((100vw - 1120px) / 2));
  border-bottom: 1px solid var(--line);
  background: rgba(255, 255, 255, .72);
}
.ai-workspace-shell__context,
.ai-workspace-shell__actions {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 8px;
}
.ai-workspace-shell__context {
  color: var(--moss-dark);
  font-size: 12px;
  font-weight: 700;
}
.ai-workspace-shell__context span:last-child {
  max-width: min(460px, 52vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-workspace-shell__status {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--moss);
}
.ai-workspace-shell__actions { flex: 0 0 auto; }
.ai-workspace-shell__action {
  min-height: 30px;
  padding: 5px 9px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}
.ai-workspace-shell__action:hover,
.ai-workspace-shell__action:focus-visible,
.ai-workspace-shell__action[aria-expanded="true"] {
  border-color: var(--sage-line);
  background: var(--sage-soft);
  color: var(--moss-dark);
}
.ai-workspace-shell__backdrop {
  position: fixed;
  inset: var(--ai-shell-topbar) 0 0;
  z-index: 40;
  background: rgba(35, 51, 31, .08);
}
@media (max-width: 1279px) {
  .ai-workspace-shell__toolbar { padding-inline: 24px; }
}
@media (max-width: 720px) {
  .ai-workspace-shell__toolbar { padding-inline: 16px; }
  .ai-workspace-shell__action { font-size: 10px; }
}
</style>
