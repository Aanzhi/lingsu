<script setup lang="ts">
import { computed } from 'vue'

import { auth } from '../stores/auth'

const schoolName = computed(() => auth.user.value?.schoolName ?? '未绑定学校')
const authorized = computed(() => auth.user.value?.authorized ?? false)
const isPlatformAdmin = computed(() => auth.user.value?.role === 'platform_admin')
</script>

<template>
  <span v-if="isPlatformAdmin" class="school-badge school-badge--admin">
    <span class="school-badge__dot" />
    <span class="school-badge__label">平台管理员</span>
  </span>
  <span v-else class="school-badge" :class="{ 'school-badge--warn': !authorized }">
    <span class="school-badge__dot" />
    <span class="school-badge__label">所属学校</span>
    <strong class="school-badge__name">{{ schoolName }}</strong>
  </span>
</template>

<style scoped>
.school-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 280px;
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--paper-soft);
  color: var(--ink);
  font-size: 12px;
  line-height: 1.2;
}
.school-badge__dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--moss);
  flex: 0 0 auto;
}
.school-badge__label {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.05em;
}
.school-badge__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font: 600 13px var(--sans);
  color: var(--moss-dark);
}
.school-badge--warn {
  background: #f6eddc;
  border-color: #ebddc1;
}
.school-badge--warn .school-badge__dot {
  background: var(--amber);
}
.school-badge--warn .school-badge__name {
  color: #775f34;
}
.school-badge--admin {
  background: #e8ecea;
  border-color: #d6ddd8;
}
.school-badge--admin .school-badge__dot {
  background: #53615f;
}
.school-badge--admin .school-badge__label {
  color: #3f5652;
  font-weight: 700;
  letter-spacing: 0.12em;
}
</style>
