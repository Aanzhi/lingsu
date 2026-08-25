<script setup lang="ts">
import { reactive, ref } from 'vue'

import { changePassword, errorMessage } from '../api'

defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const form = reactive({ old_password: '', new_password: '', confirm_password: '' })
const error = ref('')
const saving = ref(false)
const saved = ref(false)

function reset() {
  Object.assign(form, { old_password: '', new_password: '', confirm_password: '' })
  error.value = ''
  saved.value = false
}

function close() {
  if (saving.value) return
  reset()
  emit('update:modelValue', false)
}

async function submit() {
  error.value = ''
  if (form.new_password.length < 10) {
    error.value = '新密码至少需要 10 位。'
    return
  }
  if (form.new_password !== form.confirm_password) {
    error.value = '两次输入的新密码不一致。'
    return
  }
  saving.value = true
  try {
    await changePassword({ ...form })
    saved.value = true
  } catch (reason) {
    error.value = errorMessage(reason)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="修改密码" width="480px" @close="close">
    <div v-if="saved" class="password-success" role="status">
      <strong>密码已修改。</strong>
      <p>当前登录会话仍然有效，下次登录请使用新密码。</p>
    </div>
    <form v-else class="dialog-form" @submit.prevent="submit">
      <label>当前密码<input v-model="form.old_password" type="password" autocomplete="current-password" required></label>
      <label>新密码<input v-model="form.new_password" type="password" autocomplete="new-password" minlength="10" required><small>至少 10 位，不能使用常见密码。</small></label>
      <label>确认新密码<input v-model="form.confirm_password" type="password" autocomplete="new-password" required></label>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <div class="dialog-actions">
        <button class="secondary-button" type="button" @click="close">取消</button>
        <button class="primary-button" :disabled="saving" type="submit">{{ saving ? '正在保存…' : '保存新密码' }}</button>
      </div>
    </form>
    <div v-if="saved" class="dialog-actions">
      <button class="primary-button" type="button" @click="close">完成</button>
    </div>
  </el-dialog>
</template>

<style scoped>
.password-success { display: grid; gap: 8px; padding: 12px 0 8px; }
.password-success strong { color: var(--moss-dark); }
.password-success p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.6; }
.dialog-form small { color: var(--muted); font-size: 11px; }
</style>
