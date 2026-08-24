<script setup lang="ts">
withDefaults(defineProps<{
  theme?: 'user' | 'management'
  navigationLabel?: string
  showSidebar?: boolean
  edgeToEdge?: boolean
}>(), {
  theme: 'user',
  navigationLabel: '工作区导航',
  showSidebar: true,
  edgeToEdge: false,
})
</script>

<template>
  <div class="workspace-frame" :data-workspace-theme="theme">
    <slot name="topbar" />
    <div class="workspace-shell" :class="{ 'workspace-shell--full': !showSidebar }">
      <aside v-if="showSidebar" class="workspace-sidebar" :aria-label="navigationLabel">
        <slot name="sidebar" />
      </aside>
      <main class="workspace-main" :class="{ 'workspace-main--edge': edgeToEdge }"><slot /></main>
    </div>
  </div>
</template>
