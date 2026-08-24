<script setup lang="ts">
import { Bell, CircleCheck, Reading, SwitchButton } from '@element-plus/icons-vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorMessage, getAnnouncements, getPendingStudentInvitations, markAnnouncementRead, type Announcement, type MemberInvitation } from '../api'
import { auth } from '../stores/auth'
import SchoolBadge from './SchoolBadge.vue'

const props = defineProps<{ roleTone?: 'student' | 'teacher' | 'platform' }>()
const router = useRouter()
const notificationsOpen = ref(false)
const notificationLoading = ref(false)
const notificationError = ref('')
const announcements = ref<Announcement[]>([])
const invitations = ref<MemberInvitation[]>([])
const notificationsLoaded = ref(false)
const unreadCount = computed(() => announcements.value.filter((item) => item.is_read === false).length + invitations.value.length)
const homePath = computed(() => {
  const role = auth.user.value?.role
  if (!role) return '/login'
  return role === 'platform_admin' ? '/platform/home' : `/${role}/home`
})
const announcementsPath = computed(() => props.roleTone === 'student'
  ? '/student/announcements'
  : props.roleTone === 'teacher'
    ? '/teacher/announcements'
    : '/platform/announcements')
async function logout() {
  await auth.logout()
  await router.replace('/login')
}
async function toggleNotifications() {
  notificationsOpen.value = !notificationsOpen.value
  if (!notificationsOpen.value || notificationsLoaded.value) return
  notificationLoading.value = true
  notificationError.value = ''
  try {
    const [announcementResponse, invitationResponse] = await Promise.all([
      getAnnouncements(),
      auth.user.value?.role === 'student' ? getPendingStudentInvitations() : Promise.resolve({ data: [] as MemberInvitation[] }),
    ])
    announcements.value = announcementResponse.data.slice(0, 6)
    invitations.value = invitationResponse.data
    notificationsLoaded.value = true
  }
  catch (reason) { notificationError.value = errorMessage(reason) }
  finally { notificationLoading.value = false }
}
async function markRead(item: Announcement) {
  if (item.is_read !== false) return
  try { const updated = (await markAnnouncementRead(item.id)).data; announcements.value = announcements.value.map((notice) => notice.id === updated.id ? updated : notice) }
  catch (reason) { notificationError.value = errorMessage(reason) }
}
async function openAnnouncement(item: Announcement) {
  await markRead(item)
  notificationsOpen.value = false
  void router.push(announcementsPath.value)
}
function openInvitations() { notificationsOpen.value = false; void router.push('/student/invitations') }
function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  notificationsOpen.value = false
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <header class="app-topbar">
    <button class="brand-lockup brand-home-button" type="button" aria-label="返回灵溯首页" @click="router.push(homePath)">
      <span class="brand-mark" aria-hidden="true">溯</span>
      <strong>灵溯</strong>
      <span class="brand-divider" />
      <span class="brand-subtitle">青少年科学创新项目工作台</span>
    </button>
    <div class="topbar-actions">
      <SchoolBadge class="topbar-school" />
      <div class="topbar-popover-anchor">
        <button class="icon-button" type="button" aria-label="通知" :aria-expanded="notificationsOpen" @click="toggleNotifications"><el-icon><Bell /></el-icon><i v-if="unreadCount" /></button>
        <section v-if="notificationsOpen" class="topbar-popover notification-popover" role="dialog" aria-modal="false" aria-label="通知中心">
          <header><strong>通知中心</strong><button type="button" aria-label="关闭通知" @click="notificationsOpen = false">×</button></header>
          <p v-if="notificationLoading" class="popover-muted">正在读取通知…</p>
          <p v-else-if="notificationError" class="popover-error">{{ notificationError }}</p>
          <p v-else-if="!announcements.length && !invitations.length" class="popover-muted">暂无新通知</p>
          <button v-for="invite in invitations" :key="`invite-${invite.id}`" class="notification-item unread" type="button" @click="openInvitations">
            <span><strong>项目邀请：{{ invite.project_title }}</strong><small>接受后还需主指导教师确认</small></span><el-icon><Reading /></el-icon>
          </button>
          <button v-for="item in announcements" :key="item.id" class="notification-item" :class="{ unread: item.is_read === false }" type="button" @click="void openAnnouncement(item)">
            <span><strong>{{ item.title }}</strong><small>{{ item.published_at?.slice(0, 10) ?? '刚刚' }}</small></span><el-icon v-if="item.is_read !== false"><CircleCheck /></el-icon>
          </button>
        </section>
      </div>
      <span class="topbar-divider" />
      <el-dropdown trigger="click">
        <button class="profile-button" type="button" aria-haspopup="menu">
          <span class="avatar">{{ auth.user.value?.displayName.slice(0, 1) }}</span>
          <span>{{ auth.user.value?.displayName }}</span>
          <span class="chevron">⌄</span>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item :icon="SwitchButton" @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>
