<script setup lang="ts">
import { CircleCheck, CircleClose, InfoFilled } from '@element-plus/icons-vue'

import { feedbackTitle, feedbackToneClass, type FeedbackState } from '../stores/feedbackModel'

const props = defineProps<{ modelValue: FeedbackState | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: FeedbackState | null]; action: [] }>()
function close() { emit('update:modelValue', null) }
</script>

<template>
  <Transition name="notice">
    <aside v-if="props.modelValue" class="feedback-banner" :class="feedbackToneClass(props.modelValue.tone)" role="status" aria-live="polite">
      <el-icon aria-hidden="true"><CircleCheck v-if="props.modelValue.tone === 'success'" /><CircleClose v-else-if="props.modelValue.tone === 'error'" /><InfoFilled v-else /></el-icon>
      <span class="feedback-copy"><strong>{{ feedbackTitle(props.modelValue.tone) }}</strong><span>{{ props.modelValue.message }}</span><small v-if="props.modelValue.detail">{{ props.modelValue.detail }}</small></span>
      <button v-if="props.modelValue.actionLabel" class="feedback-action" type="button" @click="emit('action')">{{ props.modelValue.actionLabel }}</button>
      <button class="feedback-close" type="button" aria-label="关闭提示" @click="close">×</button>
    </aside>
  </Transition>
</template>
