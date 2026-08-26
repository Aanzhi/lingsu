<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'

import HeroHomeShell from '../components/HeroHomeShell.vue'
import WorkspaceShell from '../components/WorkspaceShell.vue'

const route = useRoute()
</script>

<template>
  <HeroHomeShell v-if="route.meta.layout === 'hero'" role-tone="student" section-label="学生工作台" />
  <WorkspaceShell v-else role="student" role-tone="student" section-label="学生工作台" />
</template>
