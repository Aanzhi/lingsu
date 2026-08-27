<script setup lang="ts">
import { Bell, Briefcase, Collection, DocumentChecked, FolderOpened, House, MagicStick } from '@element-plus/icons-vue'
import { computed, type Component } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { auth } from '../stores/auth'
import { studentTopNavigation, type NavigationIcon } from '../stores/navigationRegistry'
import { studentProjectRoute } from '../stores/pageContracts'
import AppTopbar from './AppTopbar.vue'

const route = useRoute()
const router = useRouter()
const studentTopNavigationLabels = ['首页', '我的项目', '灵思 AI', '研究进程', '项目邀请', '成果申请', '案例库', '赛事信息', '校内通知']
const navItems = computed(() => studentTopNavigation(auth.user.value?.primaryProject)
  .filter((item) => studentTopNavigationLabels.includes(item.label)))
const projectTarget = computed(() => auth.user.value?.primaryProject ? studentProjectRoute(auth.user.value.primaryProject) : '/student/projects')
const projectLabel = computed(() => auth.user.value?.primaryProjectTitle ?? '我的项目')

const iconMap: Record<NavigationIcon, Component> = {
  home: House,
  projects: FolderOpened,
  journey: Collection,
  review: DocumentChecked,
  members: Briefcase,
  content: Collection,
  schools: Collection,
  ai: MagicStick,
  settings: Collection,
  bell: Bell,
}

function isActive(to: string) {
  const [path, queryString] = to.split('?')
  if (path === '/student/projects') {
    const focus = new URLSearchParams(queryString || '').get('focus')
    return route.path === path && (focus ? route.query.focus === focus : !route.query.focus)
  }
  if (path === '/student/public-applications') {
    const projectId = new URLSearchParams(queryString || '').get('projectId')
    return route.path === path && (projectId ? String(route.query.projectId) === projectId : true)
  }
  return route.path === path || route.path.startsWith(`${path}/`)
}

function goToProject(to: string) {
  void router.push(to)
}
</script>

<template>
  <div class="student-portal-shell">
    <AppTopbar role-tone="student" />
    <nav class="student-top-navigation" aria-label="学生顶部导航">
      <div class="student-nav-scroll">
        <label class="student-project-select">
          <span>当前项目</span>
          <el-select :model-value="projectTarget" size="small" @change="goToProject">
            <el-option v-if="auth.user.value?.primaryProject" :label="projectLabel" :value="projectTarget" />
            <el-option label="查看全部项目" value="/student/projects" />
          </el-select>
        </label>
        <RouterLink
          v-for="item in navItems"
          :key="item.key"
          class="student-nav-link"
          :to="item.to"
          :class="{ 'router-link-active': isActive(item.to) }"
          :aria-current="isActive(item.to) ? 'page' : undefined"
        >
          <el-icon aria-hidden="true"><component :is="iconMap[item.icon]" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>
    <main class="student-main">
      <RouterView />
    </main>
  </div>
</template>
