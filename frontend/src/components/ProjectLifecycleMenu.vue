<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowDown, Delete, Folder, RefreshRight, Star } from '@element-plus/icons-vue'

import type { Project } from '../api'

const props = defineProps<{
  project: Project
  authorized?: boolean
  studentMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'primary'): void
  (e: 'archive'): void
  (e: 'unarchive'): void
  (e: 'trash'): void
  (e: 'restore'): void
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const panel = ref<HTMLElement | null>(null)
const menuId = `lifecycle-menu-${props.project.id}`

function toggle() {
  open.value = !open.value
  if (open.value) void nextTick(() => panel.value?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus())
}
function close(restoreFocus = false) {
  open.value = false
  if (restoreFocus) void nextTick(() => trigger.value?.focus())
}
function handle(target: 'primary' | 'archive' | 'unarchive' | 'trash' | 'restore') {
  close()
  ;(emit as (event: typeof target) => void)(target)
}

function onDocumentClick(event: MouseEvent) {
  if (!root.value) return
  if (!root.value.contains(event.target as Node)) close()
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && open.value) close(true)
}

onMounted(() => document.addEventListener('mousedown', onDocumentClick))
onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocumentClick)
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div ref="root" class="lifecycle-menu" v-on:click.stop>
    <button
      class="lifecycle-menu__trigger secondary-button"
      ref="trigger"
      type="button"
      :aria-expanded="open"
      aria-haspopup="menu"
      :aria-controls="menuId"
      :disabled="!authorized"
      @click="toggle"
    >
      管理项目 <el-icon><ArrowDown /></el-icon>
    </button>
    <ul v-if="open" ref="panel" :id="menuId" class="lifecycle-menu__panel" role="menu" aria-label="项目操作">
      <li v-if="studentMode && !project.is_primary && !project.deleted_at && !project.is_archived" role="none">
        <button type="button" role="menuitem" @click="handle('primary')">
          <el-icon><Star /></el-icon>
          <span>
            <strong>设为主项目</strong>
            <small>主项目会在工作台和首页置顶展示</small>
          </span>
        </button>
      </li>
      <li v-if="!project.is_archived && !project.deleted_at && project.status === 'completed'" role="none">
        <button type="button" role="menuitem" @click="handle('archive')">
          <el-icon><Folder /></el-icon>
          <span>
            <strong>归档项目</strong>
            <small>仅已完成项目可归档，保留证据与版本</small>
          </span>
        </button>
      </li>
      <li v-if="project.is_archived && !project.deleted_at" role="none">
        <button type="button" role="menuitem" @click="handle('unarchive')">
          <el-icon><RefreshRight /></el-icon>
          <span>
            <strong>恢复为进行中</strong>
            <small>取消归档，重新回到工作台</small>
          </span>
        </button>
      </li>
      <li v-if="!project.deleted_at" role="none">
        <button type="button" role="menuitem" class="lifecycle-menu__danger" @click="handle('trash')">
          <el-icon><Delete /></el-icon>
          <span>
            <strong>移入回收站</strong>
            <small>30 天内可恢复，到期后自动删除</small>
          </span>
        </button>
      </li>
      <li v-else role="none">
        <button type="button" role="menuitem" @click="handle('restore')">
          <el-icon><RefreshRight /></el-icon>
          <span>
            <strong>恢复项目</strong>
            <small v-if="project.days_until_purge !== null">剩余 {{ project.days_until_purge }} 天后将自动删除</small>
          </span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.lifecycle-menu {
  position: relative;
  display: inline-block;
}
.lifecycle-menu__trigger {
  min-height: 36px;
  padding: 0 14px;
  font-size: 12px;
}
.lifecycle-menu__panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 30;
  min-width: 260px;
  margin: 0;
  padding: 6px;
  list-style: none;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-hover);
}
.lifecycle-menu__panel li { margin: 0; }
.lifecycle-menu__panel button {
  width: 100%;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 10px;
  align-items: flex-start;
  padding: 9px 10px;
  border: 0;
  background: transparent;
  text-align: left;
  border-radius: 8px;
  color: var(--ink);
  cursor: pointer;
  transition: background .15s ease;
}
.lifecycle-menu__panel button:hover { background: var(--paper-soft); }
.lifecycle-menu__panel button .el-icon { color: var(--moss); margin-top: 2px; }
.lifecycle-menu__panel button strong {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
}
.lifecycle-menu__panel button small {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.5;
}
.lifecycle-menu__danger .el-icon { color: var(--clay); }
.lifecycle-menu__danger strong { color: var(--clay); }
</style>
