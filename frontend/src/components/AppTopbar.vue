<script setup lang="ts">
import { Bell, CircleCheck, InfoFilled, Reading, SwitchButton } from '@element-plus/icons-vue'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorMessage, getAnnouncements, markAnnouncementRead, type Announcement } from '../api'
import { auth } from '../stores/auth'
import SchoolBadge from './SchoolBadge.vue'

const props = defineProps<{ roleLabel: string; roleTone?: 'student' | 'teacher' | 'platform' }>()
const router = useRouter()
const notificationsOpen = ref(false)
const helpOpen = ref(false)
const notificationLoading = ref(false)
const notificationError = ref('')
const announcements = ref<Announcement[]>([])
const unreadCount = computed(() => announcements.value.filter((item) => item.is_read === false).length)
const helpCopy = computed(() => props.roleTone === 'student'
  ? { title: '学生端使用提示', body: '从“今日旅程”进入唯一优先任务，完成证据后提交审核。被打回的任务会自动置顶。' }
  : props.roleTone === 'teacher'
    ? { title: '教师端使用提示', body: '从工作台处理待审核、待认领和成员确认；打回材料时请填写下一步可执行意见。' }
    : { title: '平台端使用提示', body: '平台端只负责学校授权、全局内容治理和服务状态，不进入学校项目材料。' })
async function logout() {
  await auth.logout()
  await router.replace('/login')
}
async function toggleNotifications() {
  helpOpen.value = false
  notificationsOpen.value = !notificationsOpen.value
  if (!notificationsOpen.value || announcements.value.length) return
  notificationLoading.value = true
  notificationError.value = ''
  try { announcements.value = (await getAnnouncements()).data.slice(0, 6) }
  catch (reason) { notificationError.value = errorMessage(reason) }
  finally { notificationLoading.value = false }
}
async function markRead(item: Announcement) {
  if (item.is_read !== false) return
  try { const updated = (await markAnnouncementRead(item.id)).data; announcements.value = announcements.value.map((notice) => notice.id === updated.id ? updated : notice) }
  catch (reason) { notificationError.value = errorMessage(reason) }
}
function toggleHelp() { notificationsOpen.value = false; helpOpen.value = !helpOpen.value }
</script>

<template>
  <header class="app-topbar">
    <button class="brand-lockup brand-home-button" type="button" aria-label="返回灵溯首页" @click="router.push(auth.user.value ? (auth.user.value.role === 'platform_admin' ? '/platform/home' : `/${auth.user.value.role}/home`) : '/login')">
      <span class="brand-mark" aria-hidden="true">S</span>
      <strong>灵溯</strong>
      <span class="brand-divider" />
      <span class="brand-subtitle">青少年科学创新项目工作台</span>
      <span class="role-chip" :class="roleTone">{{ roleLabel }}</span>
    </button>
    <div class="topbar-actions">
      <SchoolBadge class="topbar-school" />
      <div class="topbar-popover-anchor">
        <button class="icon-button" type="button" aria-label="通知" :aria-expanded="notificationsOpen" @click="toggleNotifications"><el-icon><Bell /></el-icon><i v-if="unreadCount" /></button>
        <section v-if="notificationsOpen" class="topbar-popover notification-popover">
          <header><strong>通知中心</strong><button type="button" aria-label="关闭通知" @click="notificationsOpen = false">×</button></header>
          <p v-if="notificationLoading" class="popover-muted">正在读取通知…</p>
          <p v-else-if="notificationError" class="popover-error">{{ notificationError }}</p>
          <p v-else-if="!announcements.length" class="popover-muted">暂无新通知</p>
          <button v-for="item in announcements" v-else :key="item.id" class="notification-item" :class="{ unread: item.is_read === false }" type="button" @click="markRead(item)">
            <span><strong>{{ item.title }}</strong><small>{{ item.published_at?.slice(0, 10) ?? '刚刚' }}</small></span><el-icon v-if="item.is_read !== false"><CircleCheck /></el-icon>
          </button>
        </section>
      </div>
      <div class="topbar-popover-anchor">
        <button class="icon-button" type="button" aria-label="帮助中心" :aria-expanded="helpOpen" @click="toggleHelp"><el-icon><Reading /></el-icon></button>
        <section v-if="helpOpen" class="topbar-popover help-popover">
          <header><strong>{{ helpCopy.title }}</strong><button type="button" aria-label="关闭帮助" @click="helpOpen = false">×</button></header>
          <el-icon><InfoFilled /></el-icon><p>{{ helpCopy.body }}</p>
        </section>
      </div>
      <span class="topbar-divider" />
      <el-dropdown trigger="click">
        <button class="profile-button" type="button">
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
