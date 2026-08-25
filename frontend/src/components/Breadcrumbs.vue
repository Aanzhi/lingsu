<script setup lang="ts">
defineProps<{ items: string[] }>()
</script>
<template><nav class="breadcrumbs" aria-label="面包屑"><template v-for="(item, index) in items" :key="`${item}-${index}`"><span :class="{ current: index === items.length - 1 }" :aria-current="index === items.length - 1 ? 'page' : undefined">{{ item }}</span><b v-if="index < items.length - 1" aria-hidden="true">/</b></template></nav></template>
