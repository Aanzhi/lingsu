<script setup lang="ts">
import { useRoute } from 'vue-router'

import HeroHomeShell from '../components/HeroHomeShell.vue'
import WorkspaceShell from '../components/WorkspaceShell.vue'

const route = useRoute()
</script>
<template>
  <RouterView v-if="route.meta.layout === 'ai'" />
  <HeroHomeShell v-else-if="route.meta.layout === 'hero'" role-tone="teacher" section-label="指导工作台" />
  <WorkspaceShell v-else role="teacher" role-tone="teacher" section-label="指导工作台" />
</template>
