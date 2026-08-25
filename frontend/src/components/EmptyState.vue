<script setup lang="ts">
import { Document } from '@element-plus/icons-vue'
withDefaults(defineProps<{ title: string; description?: string; compact?: boolean }>(), { compact: false })
</script>
<template><div class="empty-state" :class="{ 'empty-state--compact': compact }"><span class="empty-icon"><el-icon><Document /></el-icon></span><h3>{{ title }}</h3><p v-if="description">{{ description }}</p><slot /></div></template>
