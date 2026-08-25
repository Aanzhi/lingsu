<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage } from '../../api'
import { auth } from '../../stores/auth'
import { routeForAuthRole } from '../../stores/authModel'

const route = useRoute(); const router = useRouter()
const form = reactive({ username: '', password: '' })
const error = ref('')

async function submit() {
  error.value = ''
  if (!form.username.trim() || !form.password) { error.value = '请输入账号和密码'; return }
  try {
    const user = await auth.login(form.username.trim(), form.password)
    const target = typeof route.query.redirect === 'string' && route.query.redirect.startsWith(`/${user.role === 'platform_admin' ? 'platform' : user.role}`)
      ? route.query.redirect : routeForAuthRole(user.role)
    await router.replace(target)
  } catch (reason) { error.value = errorMessage(reason, '账号或密码错误') }
}
</script>
<template>
  <main class="auth-page public-auth-page">
    <header class="auth-topbar">
      <RouterLink class="auth-brand" to="/"><span class="brand-mark">溯</span><strong>灵溯</strong></RouterLink>
    </header>
    <section class="auth-page-header">
      <p class="eyebrow">登录</p>
      <h1>欢迎回到灵溯。</h1>
      <p>登录后会进入与你身份匹配的工作台，继续处理项目或指导任务。</p>
    </section>
    <div class="auth-two-col">
        <form class="auth-card paper-card" @submit.prevent="submit">
          <p class="eyebrow">登录工作台</p>
          <h2>继续你的研究旅程</h2>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <label>账号<input v-model="form.username" autocomplete="username" placeholder="请输入账号"></label>
          <label>密码<input v-model="form.password" type="password" autocomplete="current-password" placeholder="请输入密码"></label>
          <button class="primary-button full" type="submit" :disabled="auth.loading.value">{{ auth.loading.value ? '正在登录…' : '登录' }}</button>
        </form>
        <aside class="auth-support paper-card"><h2>还没有账号？</h2><p>学生和教师可以通过学校邀请码注册。平台管理员由系统统一创建。</p><div class="auth-support__actions"><RouterLink class="secondary-button" to="/register">创建学生 / 教师账号</RouterLink><RouterLink class="text-link" to="/platform/login">平台管理员登录</RouterLink></div></aside>
    </div>
  </main>
</template>
