<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage } from '../../api'
import { auth } from '../../stores/auth'
import { routeForAuthRole } from '../../stores/authModel'

const route = useRoute(); const router = useRouter()
const form = reactive({ username: '', password: '' })
const error = ref('')

// 演示账号仅用于本地开发构建（生产构建 import.meta.env.DEV 为 false，明文口令不会进入产物）。
const demoAccounts = import.meta.env.DEV
  ? [
      { label: '学生', username: 'demo-student', password: 'lingsu-demo-2026' },
      { label: '教师', username: 'demo-teacher', password: 'lingsu-demo-2026' },
      { label: '平台管理员', username: 'demo-platform', password: 'lingsu-demo-2026' },
    ]
  : []

function fillDemo(acc: { username: string; password: string }) {
  form.username = acc.username
  form.password = acc.password
  error.value = ''
}

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
<template><main class="auth-page"><section class="auth-story"><div class="auth-brand"><span class="brand-mark">S</span><strong>灵溯</strong></div><p class="eyebrow">YOUTH SCIENCE JOURNEY</p><h1>让每一次探索，<br>都有迹可循。</h1><p>从一个真实问题开始，完成研究、制作、验证与表达。AI 是你的思考伙伴，材料和过程仍由你亲手完成。</p><div class="botanical-line" aria-hidden="true">❧ ──── ❧ ──── ❧</div></section><section class="auth-panel"><form class="auth-card paper-card" @submit.prevent="submit"><p class="eyebrow">欢迎回来</p><h2>进入你的研究工作台</h2><p>登录后会根据真实账号身份进入学生端、教师端或平台端。</p><p v-if="error" class="form-error" role="alert">{{ error }}</p><label>账号<input v-model="form.username" autocomplete="username" placeholder="请输入账号"></label><label>密码<input v-model="form.password" type="password" autocomplete="current-password" placeholder="请输入密码"></label><button class="primary-button full" type="submit" :disabled="auth.loading.value">{{ auth.loading.value ? '正在登录…' : '登录' }}</button><RouterLink class="text-link" to="/register">没有账号？使用学校邀请码注册</RouterLink><div v-if="demoAccounts.length" class="demo-hint"><span class="demo-hint__title">演示账号</span><div class="demo-hint__list"><button v-for="acc in demoAccounts" :key="acc.username" type="button" class="demo-hint__chip" @click="fillDemo(acc)">{{ acc.label }} · {{ acc.username }}</button></div><span class="demo-hint__pw">密码统一：lingsu-demo-2026（点击上方芯片自动填充）</span></div></form></section></main></template>
