<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { acceptMemberInvitation, errorMessage, getPendingStudentInvitations, rejectMemberInvitation, type MemberInvitation } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const invitations = ref<MemberInvitation[]>([])
const error = ref('')
const busy = ref(false)
const loading = ref(false)
const feedback = ref<FeedbackState | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    invitations.value = []
    invitations.value = (await getPendingStudentInvitations()).data
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '项目邀请没有加载完成，可以重试。', '重试')
    throw reason
  } finally {
    loading.value = false
  }
}
async function decide(id: number, accept: boolean) {
  busy.value = true
  error.value = ''
  try {
    if (accept) await acceptMemberInvitation(id)
    else await rejectMemberInvitation(id)
    await load()
    feedback.value = makeFeedback('success', accept ? '邀请已接受。' : '邀请已拒绝。', accept ? '项目会等待主指导教师确认后加入正式团队。' : '该邀请已从待处理列表移除。')
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '邀请状态没有改变，可以重试。', '重试') }
  finally { busy.value = false }
}
onMounted(() => { void load().catch(() => undefined) })
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="项目协作" title="项目邀请" description="处理同学或教师发来的项目邀请；新邀请从具体项目的成员区域发起。" />
    <FeedbackBanner v-model="feedback" @action="() => void load().catch(() => undefined)" />
    <p v-if="error && !feedback" class="form-error" role="alert">{{ error }}</p><p v-if="loading" class="loading-state" role="status">正在读取项目邀请…</p>
    <section v-else class="demo-invitation-list paper-card">
      <article v-for="invite in invitations" :key="invite.id" class="list-row"><div class="row-main"><div class="row-title">邀请你加入「{{ invite.project_title }}」</div><div class="row-meta">接受后等待主指导教师确认，才会进入正式项目团队。</div></div><div class="row-actions"><button class="secondary-button" :disabled="busy" type="button" @click="decide(invite.id, false)">拒绝</button><button class="primary-button" :disabled="busy" type="button" @click="decide(invite.id, true)">接受邀请</button></div></article>
      <EmptyState v-if="!invitations.length" title="暂无项目邀请" description="新的项目邀请会显示在这里。" />
    </section>
  </div>
</template>

<style scoped>
.demo-invitation-list { padding: 26px; }
.demo-invitation-list .list-row:first-child { border-top: 0; }
</style>
