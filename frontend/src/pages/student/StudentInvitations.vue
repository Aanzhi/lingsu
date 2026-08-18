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
const feedback = ref<FeedbackState | null>(null)

async function load() {
  invitations.value = (await getPendingStudentInvitations()).data
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
onMounted(() => load().catch((reason) => { error.value = errorMessage(reason) }))
</script>

<template><div class="page"><PageHeader eyebrow="研究小组" title="项目邀请" description="接受后还需要主指导教师确认，才会进入正式项目团队。" /><FeedbackBanner v-model="feedback" @action="load" /><p v-if="error" class="form-error" role="alert">{{ error }}</p><section class="member-queue paper-card"><article v-for="invite in invitations" :key="invite.id" class="member-approval"><span class="avatar soft">{{ invite.project_title.slice(0, 1) }}</span><div><strong>{{ invite.project_title }}</strong><small>邀请你加入项目</small></div><button class="secondary-button" :disabled="busy" type="button" @click="decide(invite.id, false)">拒绝</button><button class="primary-button" :disabled="busy" type="button" @click="decide(invite.id, true)">接受邀请</button></article><EmptyState v-if="!invitations.length" title="暂无项目邀请" description="新的项目邀请会显示在这里。" /></section></div></template>
