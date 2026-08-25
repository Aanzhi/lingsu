<script setup lang="ts">
import { ArrowRight, CircleCheck, Clock, Lock, Warning } from '@element-plus/icons-vue'

import StatusTag from './StatusTag.vue'
import type { ApiTask } from '../stores/studentApiModel'
import { taskActionLabel } from '../stores/studentApiModel'
import { studentTaskRoute } from '../stores/pageContracts'

const props = defineProps<{ task: ApiTask | null; projectId: number; showAction?: boolean }>()
</script>

<template>
  <section v-if="props.task" class="next-task-card" :class="{ repair: props.task.status === 'revision_required', waiting: props.task.status === 'pending_review', locked: props.task.status === 'locked', approved: ['approved', 'completed'].includes(props.task.status) }">
    <div class="task-card-top"><p class="eyebrow">{{ props.task.status === 'revision_required' ? '优先修复任务' : props.task.status === 'pending_review' ? '等待教师审核' : props.task.status === 'locked' ? '解锁条件' : '当前行动' }}</p><StatusTag :status="props.task.status" /></div>
    <div class="task-number">{{ String(props.task.order).padStart(2, '0') }}</div>
    <h2>{{ props.task.title }}</h2>
    <p>{{ props.task.status === 'locked' ? '完成上一项任务并通过审核后，这项任务会自动解锁。' : props.task.description }}</p>
    <div class="task-card-meta"><span>第 {{ props.task.stage_order }} 章 · {{ props.task.stage_name }}</span><span v-if="props.task.due_at">截止 {{ props.task.due_at }}</span><span v-else>+{{ props.task.xp_reward }} XP</span></div>
    <RouterLink v-if="props.showAction !== false" class="primary-button full" :to="studentTaskRoute(props.projectId, props.task.id)"><el-icon><Warning v-if="props.task.status === 'revision_required'" /><Clock v-else-if="props.task.status === 'pending_review'" /><Lock v-else-if="props.task.status === 'locked'" /><CircleCheck v-else /><ArrowRight v-if="!['pending_review', 'locked', 'approved', 'completed'].includes(props.task.status)" /></el-icon>{{ taskActionLabel(props.task.status) }}</RouterLink>
  </section>
  <section v-else class="next-task-card empty-task-card"><p class="eyebrow">项目状态</p><h2>当前没有待办任务</h2><p>任务完成后会在这里显示新的行动。</p></section>
</template>
