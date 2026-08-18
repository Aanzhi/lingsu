<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorMessage } from '../../api'
import { auth } from '../../stores/auth'
import { routeForAuthRole } from '../../stores/authModel'

const router = useRouter(); const error = ref('')
const form = reactive({ role: 'student' as 'student' | 'teacher', invite_code: '', display_name: '', username: '', password: '' })
async function submit() {
  error.value = ''
  if (!form.invite_code.trim() || !form.display_name.trim() || !form.username.trim() || form.password.length < 10) { error.value = '请完整填写信息，密码至少 10 位且不能为纯数字或常见密码'; return }
  try { const user = await auth.register({ ...form }); await router.replace(routeForAuthRole(user.role)) }
  catch (reason) { error.value = errorMessage(reason, '注册失败，请检查邀请码和账号信息') }
}
</script>
<template><main class="auth-page compact-auth"><section class="auth-story"><div class="auth-brand"><span class="brand-mark">S</span><strong>灵溯</strong></div><h1>加入一段<br>可信的研究旅程。</h1><p>学生与教师都通过学校邀请码加入对应学校空间。</p></section><section class="auth-panel"><form class="auth-card paper-card" @submit.prevent="submit"><p class="eyebrow">创建账号</p><h2>注册学生或教师身份</h2><div class="role-segment"><button type="button" :class="{ active: form.role === 'student' }" @click="form.role = 'student'">我是学生</button><button type="button" :class="{ active: form.role === 'teacher' }" @click="form.role = 'teacher'">我是教师</button></div><p v-if="error" class="form-error" role="alert">{{ error }}</p><label>学校邀请码<input v-model="form.invite_code" autocomplete="off" placeholder="由学校或平台提供"></label><label>姓名<input v-model="form.display_name" autocomplete="name" placeholder="请输入真实姓名"></label><label>账号<input v-model="form.username" autocomplete="username" placeholder="建议使用学号或工号"></label><label>密码<input v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 10 位，不能使用常见密码"></label><button class="primary-button full" type="submit" :disabled="auth.loading.value">{{ auth.loading.value ? '正在创建…' : '创建账号' }}</button><RouterLink class="text-link" to="/login">返回登录</RouterLink></form></section></main></template>
