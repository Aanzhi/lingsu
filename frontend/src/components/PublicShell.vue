<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { auth } from '../stores/auth'
import { routeForAuthRole } from '../stores/authModel'

const restoring = ref(true)

onMounted(async () => {
  await auth.restore()
  restoring.value = false
})

const workspacePath = computed(() => auth.user.value ? routeForAuthRole(auth.user.value.role) : '/login')
const workspaceLabel = computed(() => auth.user.value ? '进入我的工作台' : '登录工作台')
</script>

<template>
  <div class="public-shell">
    <header class="app-topbar public-shell__topbar">
      <RouterLink class="auth-brand" to="/" aria-label="返回灵溯首页">
        <span class="brand-mark">溯</span>
        <strong>灵溯</strong>
        <span class="brand-divider" />
        <span class="brand-subtitle">青少年科学创新项目工作台</span>
      </RouterLink>
      <div class="public-shell__actions">
        <RouterLink v-if="!auth.user.value" class="secondary-button" to="/login">登录</RouterLink>
        <RouterLink class="primary-button" :to="workspacePath">{{ restoring ? '正在确认…' : workspaceLabel }}</RouterLink>
      </div>
    </header>
    <main class="public-shell__main">
      <RouterView />
    </main>
  </div>
</template>
