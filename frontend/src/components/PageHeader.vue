<script setup lang="ts">
import Breadcrumbs from './Breadcrumbs.vue'
defineProps<{ eyebrow?: string; title: string; description?: string; breadcrumbs?: string[] }>()
</script>

<template>
  <header class="page-header">
    <Breadcrumbs v-if="breadcrumbs?.length" :items="breadcrumbs" />
    <div class="page-header-row">
      <div>
        <p v-if="eyebrow" class="eyebrow">{{ eyebrow }}</p>
        <h1>{{ title }}</h1>
        <p v-if="description" class="page-description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="page-actions"><slot name="actions" /></div>
    </div>
  </header>
</template>
