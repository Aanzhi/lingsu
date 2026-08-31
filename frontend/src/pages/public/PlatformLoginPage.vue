<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage } from '../../api'
import { auth } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const form = reactive({ username: '', password: '' })
const error = ref('')

async function submit() {
  error.value = ''
  if (!form.username.trim() || !form.password) {
    error.value = '请输入平台管理员账号和密码'
    return
  }
  try {
    const user = await auth.login(form.username.trim(), form.password)
    if (user.role !== 'platform_admin') {
      await auth.logout()
      error.value = '该入口仅供平台管理员使用，学生和教师请返回普通登录。'
      return
    }
    const target = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/platform/')
      ? route.query.redirect
      : '/platform/home'
    await router.replace(target)
  } catch (reason) {
    error.value = errorMessage(reason, '平台管理员账号或密码错误')
  }
}
</script>

<template>
  <main class="auth-page public-auth-page platform-auth-page" data-workspace-theme="management">
    <header class="auth-topbar">
      <RouterLink class="auth-brand" to="/"><span class="brand-mark">溯</span><strong>灵溯</strong></RouterLink>
      <RouterLink class="text-link" to="/login">返回普通登录</RouterLink>
    </header>
    <section class="auth-page-header">
      <p class="eyebrow">平台管理</p>
      <h1>进入平台管理工作台。</h1>
      <p>平台管理员在这里管理学校空间、Skills、赛事公告和公开案例。</p>
    </section>
    <div class="auth-two-col">
        <form class="auth-card paper-card" @submit.prevent="submit">
          <p class="eyebrow">独立入口</p>
          <h2>进入平台管理工作台</h2>
          <p>仅限公司平台管理员账号使用。</p>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <label>平台管理员账号<input v-model="form.username" autocomplete="username" placeholder="请输入平台管理员账号"></label>
          <label>密码<input v-model="form.password" type="password" autocomplete="current-password" placeholder="请输入密码"></label>
          <button class="primary-button full" type="submit" :disabled="auth.loading.value">{{ auth.loading.value ? '正在登录…' : '登录平台工作台' }}</button>
        </form>
        <aside class="auth-support paper-card"><p class="eyebrow">普通用户</p><h2>学生与教师登录</h2><p>学生和教师继续使用学校空间账号，不通过平台管理入口。</p></aside>
    </div>
  </main>
</template>
