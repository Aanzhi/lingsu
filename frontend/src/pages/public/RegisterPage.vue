<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { errorMessage } from '../../api'
import { auth } from '../../stores/auth'
import { routeForAuthRole } from '../../stores/authModel'

const route = useRoute(); const router = useRouter(); const error = ref('')
const form = reactive({ role: route.query.role === 'teacher' ? 'teacher' as const : 'student' as const, invite_code: '', display_name: '', username: '', password: '' })
watch(() => route.query.role, (role) => {
  form.role = role === 'teacher' ? 'teacher' : 'student'
})
async function submit() {
  error.value = ''
  if (!form.invite_code.trim() || !form.display_name.trim() || !form.username.trim() || form.password.length < 10) { error.value = '请完整填写信息，密码至少 10 位且不能为纯数字或常见密码'; return }
  try { const user = await auth.register({ ...form }); await router.replace(routeForAuthRole(user.role)) }
  catch (reason) { error.value = errorMessage(reason, '注册失败，请检查邀请码和账号信息') }
}
</script>
<template>
  <main class="auth-page public-auth-page compact-auth">
    <header class="auth-topbar">
      <RouterLink class="auth-brand" to="/"><span class="brand-mark">溯</span><strong>灵溯</strong></RouterLink>
      <RouterLink class="text-link" to="/login">返回登录</RouterLink>
    </header>
    <section class="auth-page-header auth-page-header--action">
      <div><p class="eyebrow">注册</p><h1>创建你的工作台账号。</h1><p>选择身份后填写最少必要信息，注册完成即可开始。</p></div>
    </section>
      <div class="auth-register-grid">
      <button class="auth-role-card auth-role-card--student paper-card" data-role="student" type="button" :class="{ active: form.role === 'student' }" :aria-pressed="form.role === 'student'" @click="form.role = 'student'"><span class="auth-role-card__topline"><span class="role-badge role-badge--student">学生端 · 注册</span><span v-if="form.role === 'student'" class="auth-role-card__selected">当前选择</span></span><h2>加入研究旅程</h2><p class="auth-role-card__description">填写学校邀请码，创建项目或接受项目邀请。</p><span class="primary-button auth-role-card__action">以学生身份注册</span></button>
      <button class="auth-role-card auth-role-card--teacher paper-card" data-role="teacher" type="button" :class="{ active: form.role === 'teacher' }" :aria-pressed="form.role === 'teacher'" @click="form.role = 'teacher'"><span class="auth-role-card__topline"><span class="role-badge role-badge--teacher">教师端 · 注册</span><span v-if="form.role === 'teacher'" class="auth-role-card__selected">当前选择</span></span><h2>开始指导项目</h2><p class="auth-role-card__description">使用学校邀请码，进入项目池和审核工作台。</p><span class="primary-button auth-role-card__action">以教师身份注册</span></button>
      <aside class="auth-support paper-card"><p class="eyebrow">邀请码</p><h2>邀请码从哪里来？</h2><p>请联系学校管理员获取邀请码。平台不会在这里要求额外的复杂配置。</p></aside>
    </div>
    <div class="auth-two-col auth-two-col--form">
        <form class="auth-card paper-card" @submit.prevent="submit">
          <p class="eyebrow">创建账号</p>
          <h2>注册学生或教师身份</h2>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <label>学校邀请码<input v-model="form.invite_code" autocomplete="off" placeholder="由学校或平台提供"></label>
          <label>姓名<input v-model="form.display_name" autocomplete="name" placeholder="请输入真实姓名"></label>
          <label>账号<input v-model="form.username" autocomplete="username" placeholder="建议使用学号或工号"></label>
          <label>密码<input v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 10 位，不能使用常见密码"></label>
          <button class="primary-button full" type="submit" :disabled="auth.loading.value">{{ auth.loading.value ? '正在创建…' : '创建账号' }}</button>
        </form>
        <aside class="auth-support paper-card"><p class="eyebrow">当前身份</p><h2>{{ form.role === 'student' ? '学生账号' : '教师账号' }}</h2><p>{{ form.role === 'student' ? '可创建项目、完成研究任务并申请公开成果。' : '可认领项目、审核材料并维护项目范本。' }}</p></aside>
    </div>
  </main>
</template>
