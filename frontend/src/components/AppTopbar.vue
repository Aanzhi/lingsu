<script setup lang="ts">
import { Bell, CircleCheck, Key, SwitchButton } from '@element-plus/icons-vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { errorMessage, getNotifications, markAllNotificationsRead, markNotificationRead, type AppNotification } from '../api'
import { auth } from '../stores/auth'
import { personalNotifications } from '../stores/notificationModel'
import ChangePasswordDialog from './ChangePasswordDialog.vue'
import SchoolBadge from './SchoolBadge.vue'

const props = defineProps<{
  roleTone?: 'student' | 'teacher' | 'platform'
  homeMode?: boolean
}>()
const router = useRouter()
const notificationsOpen = ref(false)
const notificationLoading = ref(false)
const notificationBusy = ref(false)
const notificationError = ref('')
const notifications = ref<AppNotification[]>([])
const notificationsLoaded = ref(false)
const passwordOpen = ref(false)
const personal = computed(() => personalNotifications(notifications.value))
const unreadCount = computed(() => personal.value.filter((item) => !item.is_read).length)
const notificationTitle = computed(() => props.roleTone === 'student' ? '消息中心' : props.roleTone === 'teacher' ? '教师消息' : '工作台消息')
const homePath = computed(() => {
  const role = auth.user.value?.role
  if (!role) return '/login'
  return role === 'platform_admin' ? '/platform/home' : `/${role}/home`
})
const notificationCenterPath = computed(() => props.roleTone === 'student'
  ? '/student/notifications'
  : props.roleTone === 'teacher'
    ? '/teacher/notifications'
    : '/platform/announcements')
const workspacePath = computed(() => props.roleTone === 'teacher' ? '/teacher/projects' : '/student/projects')

async function logout() {
  await auth.logout()
  await router.replace('/login')
}

async function loadNotifications() {
  if (notificationsLoaded.value || notificationLoading.value) return
  notificationLoading.value = true
  notificationError.value = ''
  try {
    notifications.value = (await getNotifications()).data
    notificationsLoaded.value = true
  } catch (reason) { notificationError.value = errorMessage(reason) }
  finally { notificationLoading.value = false }
}

async function refreshNotifications() {
  notificationsLoaded.value = false
  await loadNotifications()
}

async function toggleNotifications() {
  notificationsOpen.value = !notificationsOpen.value
  if (notificationsOpen.value) await loadNotifications()
}

async function markRead(item: AppNotification) {
  if (item.is_read) return
  try {
    const updated = (await markNotificationRead(item.id)).data
    notifications.value = notifications.value.map((notice) => notice.id === updated.id ? updated : notice)
  } catch (reason) { notificationError.value = errorMessage(reason) }
}

async function markAllRead() {
  if (!unreadCount.value || notificationBusy.value) return
  notificationBusy.value = true
  try {
    await markAllNotificationsRead()
    notifications.value = notifications.value.map((item) => ({ ...item, is_read: true }))
  } catch (reason) { notificationError.value = errorMessage(reason) }
  finally { notificationBusy.value = false }
}

async function openNotification(item: AppNotification) {
  await markRead(item)
  notificationsOpen.value = false
  void router.push(item.link || notificationCenterPath.value)
}

function openNotificationCenter() {
  notificationsOpen.value = false
  void router.push(notificationCenterPath.value)
}

function notificationDate(value?: string) { return value ? value.slice(0, 16).replace('T', ' ') : '刚刚' }
function notificationKind(kind: string) {
  const labels: Record<string, string> = {
    invitation_pending: '项目邀请', invitation_accepted: '成员动态', invitation_rejected: '成员动态', member_assigned: '成员动态',
    material_approved: '材料审核', material_revision_required: '材料审核', review_feedback: '材料审核',
    school_announcement: '学校通知', platform_announcement: '平台公告', case_published: '成果展示', case_rejected: '成果展示',
    case_consent_required: '成果申请', case_pending_platform: '成果申请',
  }
  return labels[kind] ?? '工作台消息'
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  notificationsOpen.value = false
}
function onNotificationsChanged() { void refreshNotifications() }

onMounted(() => {
  void loadNotifications()
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('notifications:changed', onNotificationsChanged)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('notifications:changed', onNotificationsChanged)
})
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
      <RouterLink v-if="props.homeMode" class="topbar-workspace-link" :to="workspacePath">进入工作台</RouterLink>
      <div class="topbar-popover-anchor">
        <button class="icon-button" type="button" aria-label="消息" :aria-expanded="notificationsOpen" @click="void toggleNotifications()"><el-icon><Bell /></el-icon><i v-if="unreadCount" /></button>
        <section v-if="notificationsOpen" class="topbar-popover notification-popover" role="dialog" aria-modal="false" :aria-label="notificationTitle">
          <header>
            <strong>{{ notificationTitle }}</strong>
            <button class="mark-all" type="button" :disabled="notificationBusy || !unreadCount" @click="void markAllRead()">全部已读</button>
            <button type="button" aria-label="关闭消息" @click="notificationsOpen = false">×</button>
          </header>
          <p v-if="notificationLoading" class="popover-muted">正在读取消息…</p>
          <p v-else-if="notificationError" class="popover-error">{{ notificationError }}</p>
          <p v-else-if="!personal.length" class="popover-muted">暂无新的个人消息</p>
          <template v-else>
            <button v-for="item in personal.slice(0, 6)" :key="item.id" class="notification-item" :class="{ unread: !item.is_read }" type="button" @click="void openNotification(item)">
              <span>
                <small class="note-kind">{{ notificationKind(item.kind) }}</small>
                <strong>{{ item.title }}</strong>
                <small>{{ item.body || notificationDate(item.created_at) }}</small>
              </span>
              <el-icon v-if="item.is_read"><CircleCheck /></el-icon>
            </button>
            <footer class="notification-popover__footer">
              <button type="button" class="text-link" @click="openNotificationCenter">查看全部消息</button>
            </footer>
          </template>
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
            <el-dropdown-item :icon="Key" @click="passwordOpen = true">修改密码</el-dropdown-item>
            <el-dropdown-item :icon="SwitchButton" @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
  <ChangePasswordDialog v-model="passwordOpen" />
</template>
