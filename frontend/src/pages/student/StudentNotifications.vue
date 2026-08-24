<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import EmptyState from '../../components/EmptyState.vue'
import PageHeader from '../../components/PageHeader.vue'
import { studentFixture, type StudentFixtureNotification } from '../../fixtures/portalFixtures'

const router = useRouter()
const unreadOnly = ref(false)
const notifications = ref<StudentFixtureNotification[]>(studentFixture.notifications.map((item) => ({ ...item })))
const feedback = ref('')
const visibleNotifications = computed(() => unreadOnly.value ? notifications.value.filter((item) => !item.isRead) : notifications.value)
const unreadCount = computed(() => notifications.value.filter((item) => !item.isRead).length)

function markAllRead() {
  notifications.value = notifications.value.map((item) => ({ ...item, isRead: true }))
  feedback.value = '已将全部通知标记为已读。'
}

function openNotification(item: StudentFixtureNotification) {
  notifications.value = notifications.value.map((entry) => entry.id === item.id ? { ...entry, isRead: true } : entry)
  feedback.value = '通知已读。'
  if (item.link) void router.push(item.link)
}
</script>

<template>
  <div class="page student-notifications-page">
    <PageHeader eyebrow="通知" title="通知中心" description="查看学校通知、教师反馈和项目状态变化。这里的展示状态使用确定性数据，接入真实通知 API 后保留相同交互。">
      <template #actions><button class="secondary-button" type="button" :disabled="!unreadCount" @click="markAllRead">全部已读</button></template>
    </PageHeader>
    <p v-if="feedback" class="feedback-inline" role="status">{{ feedback }}</p>
    <div class="notification-toolbar"><button type="button" class="notification-filter" :class="{ active: !unreadOnly }" @click="unreadOnly = false">全部 <span>{{ notifications.length }}</span></button><button type="button" class="notification-filter" :class="{ active: unreadOnly }" @click="unreadOnly = true">未读 <span>{{ unreadCount }}</span></button></div>
    <section v-if="visibleNotifications.length" class="paper-card student-notification-list">
      <button v-for="item in visibleNotifications" :key="item.id" type="button" class="student-notification-row" :class="{ unread: !item.isRead }" @click="openNotification(item)">
        <span class="student-notification-dot" aria-hidden="true" />
        <span class="student-notification-copy"><strong>{{ item.title }}</strong><small>{{ item.body }}</small></span>
        <span class="student-notification-state">{{ item.isRead ? '已读' : '未读' }}</span>
      </button>
    </section>
    <EmptyState v-else title="暂无通知" :description="unreadOnly ? '当前没有未读通知。' : '新的学校通知和教师反馈会显示在这里。'" />
  </div>
</template>

<style scoped>
.feedback-inline { margin: -16px 0 18px; color: var(--moss-dark); font-size: 12px; }
.notification-toolbar { display: flex; gap: 6px; margin-bottom: 16px; }
.notification-filter { min-height: 34px; padding: 0 13px; border: 1px solid var(--line); border-radius: 999px; background: var(--paper); color: var(--muted); cursor: pointer; font-size: 12px; }
.notification-filter.active { border-color: var(--moss); background: var(--sage-soft); color: var(--moss-dark); font-weight: 700; }
.notification-filter span { margin-left: 4px; font-size: 11px; }
.student-notification-list { padding: 8px 24px; }
.student-notification-row { width: 100%; display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 16px 0; border: 0; border-bottom: 1px solid var(--line); background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
.student-notification-row:last-child { border-bottom: 0; }
.student-notification-row:hover { background: var(--paper-soft); }
.student-notification-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--line-dark); }
.student-notification-row.unread .student-notification-dot { background: var(--moss); }
.student-notification-copy { display: grid; gap: 4px; min-width: 0; }
.student-notification-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.student-notification-copy small { color: var(--muted); line-height: 1.5; }
.student-notification-state { color: var(--muted-light); font-size: 11px; }
.student-notification-row.unread .student-notification-state { color: var(--moss-dark); font-weight: 700; }
</style>
