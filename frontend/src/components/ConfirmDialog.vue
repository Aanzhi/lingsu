<script setup lang="ts">
const props = withDefaults(defineProps<{ modelValue: boolean; title: string; description: string; confirmText?: string; danger?: boolean }>(), { confirmText: '确认', danger: false })
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; confirm: [] }>()
function close() { emit('update:modelValue', false) }
function confirm() { emit('confirm'); close() }
</script>
<template><el-dialog :model-value="props.modelValue" :title="props.title" width="460px" @close="close"><p class="confirm-description">{{ props.description }}</p><template #footer><div class="dialog-actions"><button class="secondary-button" type="button" @click="close">取消</button><button :class="props.danger ? 'return-button' : 'primary-button'" type="button" @click="confirm">{{ props.confirmText }}</button></div></template></el-dialog></template>
