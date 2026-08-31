<script setup lang="ts">
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'

const emit = defineEmits<{ 'toggle-sidebar': [] }>()

withDefaults(defineProps<{
  theme?: 'user' | 'management'
  layout?: 'workspace' | 'hero'
  navigationLabel?: string
  showSidebar?: boolean
  edgeToEdge?: boolean
  sidebarCollapsible?: boolean
  sidebarCollapsed?: boolean
}>(), {
  theme: 'user',
  layout: 'workspace',
  navigationLabel: '工作区导航',
  showSidebar: true,
  edgeToEdge: false,
  sidebarCollapsible: false,
  sidebarCollapsed: false,
})
</script>

<template>
  <div class="workspace-frame" :data-workspace-theme="theme">
    <slot name="topbar" />
    <div class="workspace-shell" :class="{ 'workspace-shell--full': !showSidebar, 'workspace-shell--hero': layout === 'hero', 'workspace-shell--sidebar-collapsible': sidebarCollapsible, 'workspace-shell--sidebar-collapsed': sidebarCollapsible && sidebarCollapsed }">
      <aside v-if="showSidebar" class="workspace-sidebar" :class="{ 'workspace-sidebar--collapsed': sidebarCollapsible && sidebarCollapsed }" :aria-label="navigationLabel">
        <slot name="sidebar" />
        <button
          v-if="sidebarCollapsible"
          class="workspace-sidebar__toggle"
          type="button"
          :aria-expanded="!sidebarCollapsed"
          :aria-label="sidebarCollapsed ? '展开学生工作台导航' : '收起学生工作台导航'"
          :title="sidebarCollapsed ? '展开导航' : '收起导航'"
          @click="emit('toggle-sidebar')"
        >
          <span class="workspace-sidebar__toggle-icon" aria-hidden="true"><component :is="sidebarCollapsed ? ArrowRight : ArrowLeft" /></span>
          <span class="workspace-sidebar__toggle-label">{{ sidebarCollapsed ? '展开' : '收起' }}</span>
        </button>
      </aside>
      <main class="workspace-main" :class="{ 'workspace-main--edge': edgeToEdge }"><slot /></main>
    </div>
  </div>
</template>
