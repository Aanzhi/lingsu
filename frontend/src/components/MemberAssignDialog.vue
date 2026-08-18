<script setup lang="ts">
import { ref } from 'vue'

import { errorMessage, searchStudents, type StudentDirectoryEntry } from '../api'
import { teacherStore } from '../stores/teacher'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'
import FeedbackBanner from './FeedbackBanner.vue'

const props = defineProps<{ projectId: number; existingMemberIds: number[] }>()
const emit = defineEmits<{ assigned: []; close: [] }>()
const open = ref(true)
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
  try {
    results.value = (await searchStudents(keyword.value.trim())).data.filter(
      (student) => !props.existingMemberIds.includes(student.id),
    )
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '搜索条件仍保留，可以修改后重试。', '重试')
  } finally {
    busy.value = false
  }
}

async function assign(studentId: number) {
  busy.value = true
  error.value = ''
  feedback.value = null
  try {
    await teacherStore.addMember(props.projectId, studentId)
    open.value = false
    keyword.value = ''
    results.value = []
    feedback.value = makeFeedback('success', '已将该同学加入项目。', '对方无需再次确认，立即成为正式成员。')
    emit('assigned')
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '分配没有完成，可以稍后重试。', '重试')
  } finally {
    busy.value = false
  }
}

function close() {
  open.value = false
  emit('close')
}
</script>

<template>
  <FeedbackBanner v-model="feedback" @action="search" />
  <el-dialog v-model="open" title="分配组员" width="560px" @close="close">
    <p class="dialog-hint">将本校学生直接加入该项目，对方无需再次确认。</p>
    <form class="member-search" @submit.prevent="search">
      <label>姓名或账号<input v-model="keyword" placeholder="输入至少 2 个字符"></label>
      <button class="primary-button" :disabled="busy" type="submit">搜索</button>
    </form>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div class="member-search-results">
      <article v-for="item in results" :key="item.id">
        <span class="avatar soft">{{ item.display_name.slice(0, 1) }}</span>
        <div><strong>{{ item.display_name }}</strong><small>{{ item.username }}</small></div>
        <button class="primary-button" :disabled="busy" type="button" @click="assign(item.id)">加入项目</button>
      </article>
      <p v-if="!results.length && !error" class="dialog-hint">搜索结果只包含当前学校的学生账号，已加入的成员会自动排除。</p>
    </div>
  </el-dialog>
</template>
