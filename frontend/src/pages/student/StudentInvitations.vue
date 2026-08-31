<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  acceptMemberInvitation,
  cancelMemberInvitation,
  errorMessage,
  getMemberInvitations,
  rejectMemberInvitation,
  type MemberInvitation,
} from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import { auth } from '../../stores/auth'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const invitations = ref<MemberInvitation[]>([])
const error = ref('')
const loading = ref(false)
const busyId = ref<number | null>(null)
const feedback = ref<FeedbackState | null>(null)
const cancelConfirm = ref<MemberInvitation | null>(null)

const currentUserId = computed(() => auth.user.value?.id ?? null)
const receivedInvitations = computed(() => invitations.value.filter((invite) => (
  invite.invitee === currentUserId.value && invite.status === 'pending_student'
)))
const sentInvitations = computed(() => invitations.value.filter((invite) => invite.inviter === currentUserId.value))

function invitationDate(value: string) {
  return value.slice(0, 10)
}

function sentStatus(status: MemberInvitation['status']) {
  const labels: Record<MemberInvitation['status'], string> = {
    pending_student: '等待对方接受',
    pending_teacher: '等待教师确认',
    approved: '已加入项目',
    rejected: '邀请已结束',
  }
  return labels[status]
}

function sentStatusTone(status: MemberInvitation['status']) {
  if (status === 'approved') return 'is-success'
  if (status === 'rejected') return 'is-muted'
  return 'is-pending'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    await auth.restore()
    invitations.value = (await getMemberInvitations()).data
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '项目邀请没有加载完成，可以重试。', '重试')
    throw reason
  } finally {
    loading.value = false
  }
}

async function decide(id: number, accept: boolean) {
  busyId.value = id
  error.value = ''
  try {
    if (accept) await acceptMemberInvitation(id)
    else await rejectMemberInvitation(id)
    await load()
    feedback.value = makeFeedback(
      'success',
      accept ? '邀请已接受。' : '邀请已拒绝。',
      accept ? '项目会等待主指导教师确认后加入正式团队。' : '该邀请已从待处理列表移除。',
    )
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '邀请状态没有改变，可以重试。', '重试')
  } finally {
    busyId.value = null
  }
}

function askCancel(invite: MemberInvitation) {
  cancelConfirm.value = invite
}

async function cancel() {
  const invite = cancelConfirm.value
  if (!invite) return
  cancelConfirm.value = null
  busyId.value = invite.id
  error.value = ''
  try {
    await cancelMemberInvitation(invite.id)
    await load()
    feedback.value = makeFeedback('success', '邀请已取消。', '对方将不会再看到这条待处理邀请。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '邀请没有取消，可以重试。', '重试')
  } finally {
    busyId.value = null
  }
}

onMounted(() => { void load().catch(() => undefined) })
</script>

<template>
  <div class="page student-invitations-page">
    <PageHeader eyebrow="项目协作" title="项目邀请" description="在这里处理收到的加入邀请，也能查看自己发出的邀请进度。" />
    <FeedbackBanner v-model="feedback" @action="() => void load().catch(() => undefined)" />
    <p v-if="error && !feedback" class="form-error" role="alert">{{ error }}</p>
    <p v-if="loading" class="loading-state" role="status">正在读取项目邀请…</p>

    <section v-else class="invite-columns" aria-label="项目邀请">
      <section class="invite-panel paper-card">
        <header class="invite-panel__header">
          <div>
            <p class="eyebrow">需要你处理</p>
            <h2>收到的邀请</h2>
            <p>来自同学或教师的加入请求</p>
          </div>
          <span class="invite-panel__count">{{ receivedInvitations.length }} 项</span>
        </header>

        <div v-if="receivedInvitations.length" class="invite-list">
          <article v-for="invite in receivedInvitations" :key="invite.id" class="invite-row">
            <span class="invite-row__mark">{{ invite.project_title?.slice(0, 1) || '项' }}</span>
            <div class="invite-row__main">
              <h3>邀请你加入「{{ invite.project_title }}」</h3>
              <p>项目成员发起 · {{ invitationDate(invite.created_at) }}</p>
            </div>
            <div class="invite-row__rail">
              <span class="invite-row__status"><i aria-hidden="true" />等待你决定</span>
              <div class="invite-row__actions">
                <button class="invite-row__button" :disabled="busyId !== null" type="button" @click="decide(invite.id, false)">拒绝</button>
                <button class="invite-row__button is-primary" :disabled="busyId !== null" type="button" @click="decide(invite.id, true)">接受邀请</button>
              </div>
            </div>
          </article>
        </div>
        <EmptyState v-else compact title="暂无收到的邀请" description="新的项目加入请求会显示在这里。" />
      </section>

      <section class="invite-panel paper-card invite-panel--sent">
        <header class="invite-panel__header">
          <div>
            <p class="eyebrow">项目成员</p>
            <h2>我发出的邀请</h2>
            <p>查看被邀请人的处理进度</p>
          </div>
          <span class="invite-panel__count">{{ sentInvitations.length }} 项</span>
        </header>

        <div v-if="sentInvitations.length" class="invite-list">
          <article v-for="invite in sentInvitations" :key="invite.id" class="invite-row">
            <span class="invite-row__mark">{{ invite.invitee_name?.slice(0, 1) || '人' }}</span>
            <div class="invite-row__main">
              <h3>邀请 {{ invite.invitee_name }} 加入「{{ invite.project_title }}」</h3>
              <p>发出时间 · {{ invitationDate(invite.created_at) }}</p>
            </div>
            <div class="invite-row__rail">
              <span class="invite-row__status" :class="sentStatusTone(invite.status)"><i aria-hidden="true" />{{ sentStatus(invite.status) }}</span>
              <div class="invite-row__actions">
                <button v-if="invite.status === 'pending_student'" class="invite-row__button" :disabled="busyId !== null" type="button" @click="askCancel(invite)">取消邀请</button>
              </div>
            </div>
          </article>
        </div>
        <EmptyState v-else compact title="暂无发出的邀请" description="从项目成员区域发出的邀请会显示在这里。" />
      </section>
    </section>

    <ConfirmDialog
      v-if="cancelConfirm"
      :model-value="true"
      title="取消这条邀请？"
      description="取消后，对方将无法继续接受这条邀请；如果需要，之后可以重新发起。"
      confirm-text="确认取消"
      danger
      @update:model-value="cancelConfirm = null"
      @confirm="cancel"
    />
  </div>
</template>

<style scoped>
.invite-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-5);
  align-items: stretch;
}

.invite-panel {
  min-width: 0;
  min-height: 440px;
  padding: var(--space-5);
}

.invite-panel__header {
  min-height: 72px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.invite-panel__header .eyebrow {
  margin-bottom: 5px;
}

.invite-panel__header h2 {
  margin: 0;
  color: var(--ink);
  font: 700 18px/1.3 var(--sans);
}

.invite-panel__header p:not(.eyebrow) {
  margin: 5px 0 0;
  color: var(--muted-light);
  font-size: 12px;
}

.invite-panel__count {
  flex: 0 0 auto;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.invite-list {
  display: grid;
}

.invite-row {
  min-width: 0;
  min-height: 116px;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 158px;
  align-items: center;
  gap: var(--space-3);
  padding: 16px 0;
  border-bottom: 1px solid var(--line);
}

.invite-row:last-child {
  border-bottom: 0;
}

.invite-row__mark {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 11px;
  color: var(--moss-dark);
  background: var(--sage-soft);
  font: 700 16px/1 var(--sans);
}

.invite-row__main {
  min-width: 0;
}

.invite-row__main h3 {
  margin: 0;
  color: var(--ink);
  font: 700 14px/1.45 var(--sans);
  overflow-wrap: anywhere;
}

.invite-row__main p {
  margin: 5px 0 0;
  color: var(--muted-light);
  font-size: 11px;
  line-height: 1.5;
}

.invite-row__rail {
  min-width: 0;
  min-height: 72px;
  display: grid;
  grid-template-rows: 24px 32px;
  align-content: center;
  justify-items: end;
  gap: 6px;
}

.invite-row__status {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  color: var(--moss);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.invite-row__status i {
  width: 6px;
  height: 6px;
  flex: 0 0 6px;
  border-radius: 50%;
  background: currentColor;
}

.invite-row__status.is-pending {
  color: #946f43;
}

.invite-row__status.is-success {
  color: var(--moss);
}

.invite-row__status.is-muted {
  color: var(--muted-light);
}

.invite-row__actions {
  min-height: 32px;
  display: flex;
  justify-content: flex-end;
  gap: 7px;
}

.invite-row__button {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--line-dark);
  border-radius: var(--radius-sm);
  color: var(--ink-soft);
  background: var(--paper);
  font: 600 11px/1 var(--sans);
  white-space: nowrap;
  cursor: pointer;
}

.invite-row__button:hover:not(:disabled) {
  border-color: var(--moss);
  color: var(--moss-dark);
  background: var(--paper-soft);
}

.invite-row__button.is-primary {
  border-color: var(--moss);
  color: #fff;
  background: var(--moss);
}

.invite-row__button.is-primary:hover:not(:disabled) {
  border-color: var(--moss-dark);
  background: var(--moss-dark);
}

.invite-row__button:disabled {
  cursor: wait;
  opacity: .55;
}

.invite-panel :deep(.empty-state) {
  min-height: 280px;
  margin-top: 16px;
}
</style>
