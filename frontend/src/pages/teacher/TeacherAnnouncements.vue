<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { createAnnouncement, errorMessage, getAnnouncements, type Announcement } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const open = ref(false)
const form = reactive({ title: '', body: '' })
const items = ref<Announcement[]>([])
const error = ref('')
const loading = ref(false)
const feedback = ref<FeedbackState | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  items.value = []
  try { items.value = (await getAnnouncements()).data }
  catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '公告列表没有加载完成，可以重试。', '重试'); throw reason }
  finally { loading.value = false }
}
onMounted(() => { void load().catch(() => undefined) })

async function publish() {
  error.value = ''
  if (!form.title.trim() || !form.body.trim()) { feedback.value = makeFeedback('error', '请填写公告标题和正文。', '发布前两个字段都不能为空。'); return }
  loading.value = true
  try {
    await createAnnouncement({ title: form.title.trim(), body: form.body.trim(), audience: 'students', status: 'published' })
    Object.assign(form, { title: '', body: '' }); open.value = false; await load()
    feedback.value = makeFeedback('success', '学生公告已发布。', '本校学生会在内容资源中查看这条公告。')
  } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '公告没有发布，填写内容仍保留在弹窗中，可以重试。', '重试') }
  finally { loading.value = false }
}
</script>

<template>
  <div class="page"><PageHeader eyebrow="校内沟通" title="学生通知公告" description="面向本校学生发布研究、活动和项目相关通知；平台公告由平台管理员发布。"><template #actions><button class="primary-button" type="button" @click="open = true"><el-icon><Plus /></el-icon> 创建公告</button></template></PageHeader>
    <FeedbackBanner v-model="feedback" @action="() => void load().catch(() => undefined)" /><p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-if="loading" class="loading-state" role="status">正在读取学生公告…</p>
    <div v-else class="announcement-list"><article v-for="item in items" :key="item.id" class="announcement-card"><div><span>{{ item.audience === 'students' ? '本校公告' : '系统公告' }}</span><small>{{ item.published_at?.slice(0, 10) }}</small></div><h2>{{ item.title }}</h2><p>{{ item.body }}</p></article><EmptyState v-if="!items.length" title="暂无学生公告" description="创建一条公告后，本校学生会在内容资源中看到它。" /></div>
    <el-dialog v-model="open" title="发布本校学生公告" width="560px"><form class="dialog-form" @submit.prevent="publish"><label>公告标题<input v-model="form.title" /></label><label>公告正文<textarea v-model="form.body" rows="6" /></label><div class="dialog-actions"><button type="button" class="secondary-button" @click="open = false">取消</button><button class="primary-button" :disabled="loading" type="submit">{{ loading ? '正在发布…' : '发布公告' }}</button></div></form></el-dialog>
  </div>
</template>
