<script setup lang="ts">
withDefaults(defineProps<{
  theme?: 'user' | 'management'
  layout?: 'workspace' | 'hero'
  navigationLabel?: string
  showSidebar?: boolean
  edgeToEdge?: boolean
}>(), {
  theme: 'user',
  layout: 'workspace',
  navigationLabel: '工作区导航',
  showSidebar: true,
  edgeToEdge: false,
})
</script>

<template>
  <div class="workspace-frame" :data-workspace-theme="theme">
    <slot name="topbar" />
    <div class="workspace-shell" :class="{ 'workspace-shell--full': !showSidebar, 'workspace-shell--hero': layout === 'hero' }">
      <aside v-if="showSidebar" class="workspace-sidebar" :aria-label="navigationLabel">
        <slot name="sidebar" />
      </aside>
      <main class="workspace-main" :class="{ 'workspace-main--edge': edgeToEdge }"><slot /></main>
    </div>
  </div>
</template>
