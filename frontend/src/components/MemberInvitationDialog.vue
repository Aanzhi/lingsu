<script setup lang="ts">
import { ref } from 'vue'

import { createMemberInvitation, errorMessage, searchStudents, type StudentDirectoryEntry } from '../api'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'
import FeedbackBanner from './FeedbackBanner.vue'

const props = withDefaults(defineProps<{
  projectId: number
  buttonLabel?: string
  buttonClass?: string
}>(), {
  buttonLabel: '邀请项目成员',
  buttonClass: 'secondary-button',
})
const emit = defineEmits<{ invited: [] }>()
const open = ref(false)
const keyword = ref('')
const results = ref<StudentDirectoryEntry[]>([])
const error = ref('')
const busy = ref(false)
const feedback = ref<FeedbackState | null>(null)

async function search() {
  error.value = ''
  feedback.value = null
  if (keyword.value.trim().length < 2) {
    results.value = []
    error.value = '请输入至少 2 个字符。'
    return
  }
  busy.value = true
  try { results.value = (await searchStudents(keyword.value.trim())).data }
  catch (reason) { error.value = errorMessage(reason); feedback.value = makeFeedback('error', error.value, '搜索条件仍保留，可以修改后重试。', '重试') }
  finally { busy.value = false }
}

async function invite(studentId: number) {
  busy.value = true
  error.value = ''
  feedback.value = null
  try {
    await createMemberInvitation(props.projectId, studentId)
    open.value = false
    keyword.value = ''
    results.value = []
    feedback.value = makeFeedback('success', '项目邀请已发出。', '对方接受后，还需要主指导教师确认。')
    emit('invited')
  } catch (reason) { error.value = errorMessage(reason); feedback.value = makeFeedback('error', error.value, '邀请没有发出，可以稍后重试。', '重试') }
  finally { busy.value = false }
}
</script>

<template>
  <FeedbackBanner v-model="feedback" @action="search" />
  <button :class="props.buttonClass" type="button" @click="open = true">{{ props.buttonLabel }}</button>
  <el-dialog v-model="open" title="邀请本校学生" width="560px">
    <p class="dialog-hint">受邀学生先确认，再由主指导教师批准后正式加入项目。</p>
    <form class="member-search" @submit.prevent="search">
      <label>姓名或账号<input v-model="keyword" placeholder="输入至少 2 个字符"></label>
      <button class="primary-button" :disabled="busy" type="submit">搜索</button>
    </form>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="member-search-results">
      <article v-for="item in results" :key="item.id">
        <span class="avatar soft">{{ item.display_name.slice(0, 1) }}</span>
        <div><strong>{{ item.display_name }}</strong><small>{{ item.username }}</small></div>
        <button class="primary-button" :disabled="busy" type="button" @click="invite(item.id)">发出邀请</button>
      </article>
      <p v-if="!results.length && !error" class="dialog-hint">搜索结果只包含当前学校的学生账号。</p>
    </div>
  </el-dialog>
</template>
