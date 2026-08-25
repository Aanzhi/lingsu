<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { errorMessage, getNotifications, markAllNotificationsRead, markNotificationRead, type AppNotification } from '../api'
import EmptyState from './EmptyState.vue'
import FeedbackBanner from './FeedbackBanner.vue'
import PageHeader from './PageHeader.vue'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'

const props = defineProps<{ role: 'student' | 'teacher' }>()
const router = useRouter()
const unreadOnly = ref(false)
const notifications = ref<AppNotification[]>([])
const feedback = ref<FeedbackState | null>(null)
const error = ref('')
const loading = ref(false)
const busy = ref(false)
const copy = computed(() => props.role === 'teacher'
  ? {
      title: '教师通知中心',
      description: '查看项目池、材料审核和学校公告的重要变化。',
      loading: '正在读取教师通知…',
      empty: '新的项目池和审核动态会显示在这里。',
      success: '已将全部教师通知标记为已读。',
    }
  : {
      title: '通知中心',
      description: '查看系统、学校、教师反馈和项目状态变化；需要处理的邀请进入项目邀请。',
      loading: '正在读取通知…',
      empty: '新的学校通知和教师反馈会显示在这里。',
      success: '已将全部通知标记为已读。',
    })
const visible = computed(() => unreadOnly.value ? notifications.value.filter((item) => !item.is_read) : notifications.value)
const unreadCount = computed(() => notifications.value.filter((item) => !item.is_read).length)
function emitNotificationsChanged() { window.dispatchEvent(new Event('notifications:changed')) }

async function load() {
  loading.value = true
  error.value = ''
  try { notifications.value = (await getNotifications()).data }
  catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '通知没有加载完成，可以重试。', '重试')
  }
  finally { loading.value = false }
}

async function markAllRead() {
  if (!unreadCount.value || busy.value) return
  busy.value = true
  try {
    await markAllNotificationsRead()
    notifications.value = notifications.value.map((item) => ({ ...item, is_read: true }))
    emitNotificationsChanged()
    feedback.value = makeFeedback('success', copy.value.success)
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '通知状态没有改变，可以重试。', '重试') }
  finally { busy.value = false }
}

async function open(item: AppNotification) {
  if (!item.is_read) {
    try {
      const response = await markNotificationRead(item.id)
      notifications.value = notifications.value.map((entry) => entry.id === item.id ? response.data : entry)
      emitNotificationsChanged()
    } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '通知已打开，但已读状态没有同步，可以稍后重试。') }
  }
  if (item.link) void router.push(item.link)
}

function notificationDate(value?: string) { return value ? value.slice(0, 16).replace('T', ' ') : '刚刚' }
function notificationKind(kind: string) {
  const labels: Record<string, string> = {
    invitation_pending: '项目邀请', invitation_accepted: '成员动态', invitation_rejected: '成员动态', member_assigned: '成员动态',
    material_approved: '材料审核', material_revision_required: '材料审核', review_feedback: '材料审核',
    school_announcement: '学校通知', platform_announcement: '平台公告', case_published: '成果展示', case_rejected: '成果展示',
    case_consent_required: '成果申请', case_pending_platform: '成果申请',
  }
  return labels[kind] ?? '工作台通知'
}

onMounted(() => { void load() })
</script>

<template>
  <div class="page notification-center-page" :class="`notification-center-page--${role}`">
    <PageHeader eyebrow="通知" :title="copy.title" :description="copy.description">
      <template #actions><button class="secondary-button" type="button" :disabled="busy || !unreadCount" @click="void markAllRead()">全部已读</button></template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="() => void load()" />
    <p v-if="error && !feedback" class="form-error" role="alert">{{ error }}</p>
    <p v-if="loading" class="loading-state" role="status">{{ copy.loading }}</p>
    <div class="notification-toolbar" aria-label="通知筛选">
      <button type="button" class="notification-filter" :class="{ active: !unreadOnly }" @click="unreadOnly = false">全部 <span>{{ notifications.length }}</span></button>
      <button type="button" class="notification-filter" :class="{ active: unreadOnly }" @click="unreadOnly = true">未读 <span>{{ unreadCount }}</span></button>
    </div>
    <section v-if="!loading && visible.length" class="paper-card notification-list">
      <button v-for="item in visible" :key="item.id" type="button" class="notification-row" :class="{ unread: !item.is_read }" @click="void open(item)">
        <span class="notification-row__dot" aria-hidden="true" />
        <span class="notification-row__copy">
          <span class="notification-row__kind">{{ notificationKind(item.kind) }}</span>
          <strong>{{ item.title }}</strong>
          <small>{{ item.body }}</small>
          <em>{{ notificationDate(item.created_at) }}</em>
        </span>
        <span class="notification-row__state">{{ item.is_read ? '已读' : '未读' }}</span>
      </button>
    </section>
    <EmptyState v-else-if="!loading" title="暂无通知" :description="unreadOnly ? '当前没有未读通知。' : copy.empty" />
  </div>
</template>

<style scoped>
.notification-toolbar { display: flex; gap: 6px; margin-bottom: 16px; }
.notification-filter { min-height: 34px; padding: 0 13px; border: 1px solid var(--line); border-radius: 999px; background: var(--paper); color: var(--muted); cursor: pointer; font-size: 12px; }
.notification-filter.active { border-color: var(--moss); background: var(--sage-soft); color: var(--moss-dark); font-weight: 700; }
.notification-filter span { margin-left: 4px; font-size: 11px; }
.notification-list { padding: 8px 24px; }
.notification-row { width: 100%; display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 16px 0; border: 0; border-bottom: 1px solid var(--line); background: transparent; color: var(--ink); text-align: left; cursor: pointer; }
.notification-row:last-child { border-bottom: 0; }
.notification-row:hover { background: var(--paper-soft); }
.notification-row__dot { width: 8px; height: 8px; border-radius: 50%; background: var(--line-dark); }
.notification-row.unread .notification-row__dot { background: var(--moss); }
.notification-row__copy { display: grid; gap: 4px; min-width: 0; }
.notification-row__copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.notification-row__copy small { color: var(--muted); line-height: 1.5; }
.notification-row__copy em { color: var(--muted-light); font-size: 11px; font-style: normal; }
.notification-row__kind { width: fit-content; padding: 2px 7px; border: 1px solid var(--sage-line); border-radius: 999px; color: var(--moss-dark); background: var(--sage-soft); font-size: 10px; font-weight: 700; }
.notification-row__state { color: var(--muted-light); font-size: 11px; }
.notification-row.unread .notification-row__state { color: var(--moss-dark); font-weight: 700; }
</style>
