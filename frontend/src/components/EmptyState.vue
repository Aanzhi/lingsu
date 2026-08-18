<script setup lang="ts">
import { Document } from '@element-plus/icons-vue'
defineProps<{ title: string; description?: string }>()
</script>
<template><div class="empty-state"><span class="empty-icon"><el-icon><Document /></el-icon></span><h3>{{ title }}</h3><p v-if="description">{{ description }}</p><slot /></div></template>
