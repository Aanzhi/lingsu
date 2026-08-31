<script setup lang="ts">
import { computed, onMounted, ref, type Component, watch } from 'vue'
import { Bell, Briefcase, Collection, DocumentChecked, FolderOpened, House, MagicStick, MapLocation, Medal, Reading, Setting, Trophy, User } from '@element-plus/icons-vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { isNavigationActive, navigationChildren, primaryNavigation, resolveStudentNavigationProject, utilityNavigation, type NavigationIcon, type NavigationRole } from '../stores/navigationRegistry'
import { auth } from '../stores/auth'
import { readSidebarPreference, writeSidebarPreference } from '../stores/sidebarPreference'
import { student } from '../stores/student'
import AppTopbar from './AppTopbar.vue'
import WorkspaceFrame from './WorkspaceFrame.vue'

const props = withDefaults(defineProps<{
  role: NavigationRole
  roleTone: 'student' | 'teacher' | 'platform'
  sectionLabel: string
  collapsibleSidebar?: boolean
}>(), {
  collapsibleSidebar: false,
})
const route = useRoute()
const sidebarCollapsed = ref(true)
let sidebarPreferenceReady = false

onMounted(() => {
  if (!props.collapsibleSidebar) return
  try {
    sidebarCollapsed.value = readSidebarPreference(window.localStorage)
  } catch {
    sidebarCollapsed.value = true
  }
  sidebarPreferenceReady = true
})

watch(sidebarCollapsed, (collapsed) => {
  if (!props.collapsibleSidebar || !sidebarPreferenceReady) return
  try {
    writeSidebarPreference(window.localStorage, collapsed)
  } catch {
    // Blocked or private storage must not prevent navigation.
  }
}, { flush: 'sync' })

function toggleSidebar() {
  if (!props.collapsibleSidebar) return
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function routeProjectId(value: unknown) {
  const candidate = Array.isArray(value) ? value[0] : value
  const projectId = Number(candidate)
  return Number.isInteger(projectId) && projectId > 0 ? projectId : null
}
const navigationProject = computed(() => props.role === 'student'
  ? resolveStudentNavigationProject(auth.user.value?.primaryProject, student.state.projects, routeProjectId(route.params.id ?? route.query.projectId))
  : auth.user.value?.primaryProject ?? null)
const nav = computed(() => primaryNavigation(props.role, navigationProject.value))
const utilityNav = computed(() => utilityNavigation(props.role, navigationProject.value))
const iconMap: Record<NavigationIcon, Component> = {
  home: House, projects: FolderOpened, journey: MapLocation, review: DocumentChecked,
  members: props.role === 'student' ? User : Briefcase,
  content: props.role === 'platform_admin' ? Medal : Reading,
  cases: Reading, competitions: Trophy, announcements: Bell,
  schools: Collection, ai: MagicStick, settings: Setting, bell: Bell,
}
function isNavActive(item: (typeof nav.value)[number]) { return isNavigationActive(props.role, item, route.path, route.query) }
function isUtilityActive(to: string) {
  const path = to.split('?')[0]
  return route.path === path || route.path.startsWith(`${path}/`)
}
</script>

<template>
  <!-- WorkspaceFrame owns the aria-expanded state on the sidebar toggle. -->
  <WorkspaceFrame
    :theme="role === 'platform_admin' ? 'management' : 'user'"
    :navigation-label="`${sectionLabel}导航`"
    :sidebar-collapsible="props.collapsibleSidebar"
    :sidebar-collapsed="props.collapsibleSidebar && sidebarCollapsed"
    @toggle-sidebar="toggleSidebar"
  >
    <template #topbar><AppTopbar :role-tone="roleTone" /></template>
    <template #sidebar>
      <p class="workspace-sidebar__label">{{ sectionLabel }}</p>
      <template v-for="item in nav" :key="item.key">
        <RouterLink
          :to="item.to"
          active-class=""
          exact-active-class=""
          :class="{ 'workspace-router-active': isNavActive(item) }"
          :aria-current="isNavActive(item) ? 'page' : undefined"
          :aria-label="props.collapsibleSidebar && sidebarCollapsed ? item.label : undefined"
          :title="props.collapsibleSidebar && sidebarCollapsed ? item.label : undefined"
        >
          <el-icon aria-hidden="true"><component :is="iconMap[item.icon]" /></el-icon><span>{{ item.label }}</span>
        </RouterLink>
        <div v-if="navigationChildren(role, item).length" class="workspace-sidebar__subnav" :aria-label="`${item.label}子页面`">
          <RouterLink v-for="child in navigationChildren(role, item)" :key="child.key" :to="child.to" :class="{ 'router-link-active': route.path === child.to || route.path.startsWith(`${child.to}/`) }" :aria-current="route.path === child.to || route.path.startsWith(`${child.to}/`) ? 'page' : undefined"><span>{{ child.label }}</span></RouterLink>
        </div>
      </template>
      <template v-if="utilityNav.length">
        <p class="workspace-sidebar__label workspace-sidebar__section-label">更多页面</p>
        <RouterLink
          v-for="item in utilityNav"
          :key="item.key"
          :to="item.to"
          :class="{ 'router-link-active': isUtilityActive(item.to) }"
          :aria-current="isUtilityActive(item.to) ? 'page' : undefined"
          :aria-label="props.collapsibleSidebar && sidebarCollapsed ? item.label : undefined"
          :title="props.collapsibleSidebar && sidebarCollapsed ? item.label : undefined"
        >
          <el-icon aria-hidden="true"><component :is="iconMap[item.icon]" /></el-icon><span>{{ item.label }}</span>
        </RouterLink>
      </template>
    </template>
    <RouterView />
  </WorkspaceFrame>
</template>
