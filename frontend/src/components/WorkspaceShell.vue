<script setup lang="ts">
import { computed, type Component } from 'vue'
import { Bell, Briefcase, Collection, DocumentChecked, FolderOpened, House, MagicStick, Medal, Reading, Setting } from '@element-plus/icons-vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { isNavigationActive, navigationChildren, primaryNavigation, utilityNavigation, type NavigationIcon, type NavigationRole } from '../stores/navigationRegistry'
import { auth } from '../stores/auth'
import AppTopbar from './AppTopbar.vue'
import WorkspaceFrame from './WorkspaceFrame.vue'

const props = defineProps<{
  role: NavigationRole
  roleTone: 'student' | 'teacher' | 'platform'
  sectionLabel: string
}>()
const route = useRoute()
const nav = computed(() => primaryNavigation(props.role, auth.user.value?.primaryProject))
const utilityNav = computed(() => utilityNavigation(props.role, auth.user.value?.primaryProject))
const iconMap: Record<NavigationIcon, Component> = {
  home: House, projects: FolderOpened, journey: Collection, review: DocumentChecked,
  members: Briefcase, content: props.role === 'platform_admin' ? Medal : Reading,
  schools: Collection, ai: MagicStick, settings: Setting, bell: Bell,
}
function isNavActive(item: (typeof nav.value)[number]) { return isNavigationActive(props.role, item, route.path, route.query) }
function isUtilityActive(to: string) {
  const path = to.split('?')[0]
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<template>
  <WorkspaceFrame :theme="role === 'platform_admin' ? 'management' : 'user'" :navigation-label="`${sectionLabel}导航`">
    <template #topbar><AppTopbar :role-tone="roleTone" /></template>
    <template #sidebar>
      <p class="workspace-sidebar__label">{{ sectionLabel }}</p>
      <template v-for="item in nav" :key="item.key">
        <RouterLink :to="item.to" active-class="" exact-active-class="" :class="{ 'workspace-router-active': isNavActive(item) }" :aria-current="isNavActive(item) ? 'page' : undefined">
          <el-icon aria-hidden="true"><component :is="iconMap[item.icon]" /></el-icon><span>{{ item.label }}</span>
        </RouterLink>
        <div v-if="navigationChildren(role, item).length" class="workspace-sidebar__subnav" :aria-label="`${item.label}子页面`">
          <RouterLink v-for="child in navigationChildren(role, item)" :key="child.key" :to="child.to" :class="{ 'router-link-active': route.path === child.to || route.path.startsWith(`${child.to}/`) }" :aria-current="route.path === child.to || route.path.startsWith(`${child.to}/`) ? 'page' : undefined"><span>{{ child.label }}</span></RouterLink>
        </div>
      </template>
      <template v-if="utilityNav.length">
        <p class="workspace-sidebar__label workspace-sidebar__section-label">更多页面</p>
        <RouterLink v-for="item in utilityNav" :key="item.key" :to="item.to" :class="{ 'router-link-active': isUtilityActive(item.to) }" :aria-current="isUtilityActive(item.to) ? 'page' : undefined">
          <el-icon aria-hidden="true"><component :is="iconMap[item.icon]" /></el-icon><span>{{ item.label }}</span>
        </RouterLink>
      </template>
    </template>
    <RouterView />
  </WorkspaceFrame>
</template>
