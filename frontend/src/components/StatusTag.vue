<script setup lang="ts">
import { computed } from 'vue'
import { CaretRight, CircleCheck, CircleClose, Clock, Lock, RefreshRight, Warning } from '@element-plus/icons-vue'

import type { UnifiedStatus } from '../stores/status'

const props = defineProps<{ status: UnifiedStatus | 'published' | 'offline' | 'risk' | 'waiting_student' | 'waiting_teacher' | 'joined' | 'rejected' }>()
const values: Record<string, { label: string; tone: string; icon: unknown }> = {
  draft: { label: '草稿', tone: 'neutral', icon: Clock }, unclaimed: { label: '待认领', tone: 'neutral', icon: Clock },
  active: { label: '进行中', tone: 'success', icon: RefreshRight }, available: { label: '可开始', tone: 'current', icon: CaretRight },
  locked: { label: '待解锁', tone: 'muted', icon: Lock }, pending_review: { label: '待审核', tone: 'warning', icon: Clock },
  submitted: { label: '待审核', tone: 'warning', icon: Clock },
  revision_required: { label: '需修订', tone: 'danger', icon: Warning }, approved: { label: '已通过', tone: 'success', icon: CircleCheck },
  completed: { label: '已完成', tone: 'success', icon: CircleCheck }, expired: { label: '已过期', tone: 'danger', icon: CircleClose },
  disabled: { label: '已停用', tone: 'muted', icon: CircleClose }, published: { label: '已发布', tone: 'success', icon: CircleCheck },
  offline: { label: '已下架', tone: 'muted', icon: CircleClose }, risk: { label: '风险标记', tone: 'danger', icon: Warning },
  waiting_student: { label: '待学生确认', tone: 'warning', icon: Clock }, waiting_teacher: { label: '待教师确认', tone: 'warning', icon: Clock },
  joined: { label: '已加入', tone: 'success', icon: CircleCheck }, rejected: { label: '已拒绝', tone: 'muted', icon: CircleClose },
}
const value = computed(() => values[props.status] ?? values.draft)
</script>

<template><span class="status-tag" :class="value.tone"><el-icon><component :is="value.icon" /></el-icon>{{ value.label }}</span></template>
