<script setup lang="ts">
import { RouterView } from 'vue-router'

import AppTopbar from './AppTopbar.vue'
import WorkspaceFrame from './WorkspaceFrame.vue'

defineProps<{
  roleTone: 'student' | 'teacher'
  sectionLabel: string
}>()
</script>

<template>
  <WorkspaceFrame
    theme="user"
    layout="hero"
    :show-sidebar="false"
    edge-to-edge
    :navigation-label="`${sectionLabel}导航`"
  >
    <template #topbar><AppTopbar :role-tone="roleTone" home-mode /></template>
    <RouterView />
  </WorkspaceFrame>
</template>
