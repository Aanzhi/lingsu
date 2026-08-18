<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import {
  approvePublicCase,
  errorMessage,
  getAnnouncements,
  getCompetitions,
  getPublicCases,
  rejectPublicCase,
  type Announcement,
  type Competition,
  type PublicCase,
} from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { operationSuccess } from '../../stores/interactionModel'

const route = useRoute()
const keyword = ref('')
const appliedKeyword = ref('')
const error = ref('')
const feedback = ref<FeedbackState | null>(null)
const loading = ref(false)
const cases = ref<PublicCase[]>([])
const competitions = ref<Competition[]>([])
const notices = ref<Announcement[]>([])
const rejecting = ref<PublicCase | null>(null)
const rejectComment = ref('')
const surface = computed(() => String(route.meta.surface ?? 'cases'))
const isTeacher = computed(() => route.path.startsWith('/teacher'))
const heading = computed(() => surface.value === 'cases'
  ? ['案例库', '从真实路径中获得开题灵感', '只展示经过教师审核、明确选择公开的摘要和材料。']
  : surface.value === 'competitions'
    ? ['赛事信息', '把握适合项目的展示机会', '赛事信息由平台统一发布，教师与学生均为只读。']
    : ['通知公告', '与你的研究相关的提醒', '同时查看平台系统公告与本校教师公告。'])
const filteredCases = computed(() => cases.value.filter((item) => (
  item.status === 'published' || (isTeacher.value && item.status === 'pending_teacher')
) && `${item.project_title}${item.tags.join('')}${item.discipline}${item.application_scene}`.toLowerCase().includes(appliedKeyword.value.toLowerCase())))
const filteredCompetitions = computed(() => competitions.value.filter((item) => `${item.title}${item.description}`.toLowerCase().includes(appliedKeyword.value.toLowerCase())))

function runSearch() {
  appliedKeyword.value = keyword.value.trim()
  feedback.value = makeFeedback('success', operationSuccess('search'), appliedKeyword.value ? `已按“${appliedKeyword.value}”筛选。` : '当前显示全部内容。')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (surface.value === 'cases') cases.value = (await getPublicCases()).data
    else if (surface.value === 'competitions') competitions.value = (await getCompetitions()).data
    else notices.value = (await getAnnouncements()).data
  } catch (reason) {
    error.value = errorMessage(reason)
  } finally {
    loading.value = false
  }
}

async function approve(item: PublicCase) {
  loading.value = true
  error.value = ''
  feedback.value = null
  try {
    await approvePublicCase(item.id)
    await load()
    feedback.value = makeFeedback('success', '案例已审核通过并发布。', '师生现在可以在案例库中检索到公开摘要与已选材料。')
  }
  catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '案例状态没有改变，可以稍后重试。', '重试')
  }
  finally { loading.value = false }
}

async function reject() {
  if (!rejecting.value) return
  if (!rejectComment.value.trim()) {
    error.value = '请填写明确、可执行的修改意见。'
    feedback.value = makeFeedback('error', error.value, '请说明学生下一步应补充、删除或核对什么。')
    return
  }
  loading.value = true
  error.value = ''
  feedback.value = null
  try {
    await rejectPublicCase(rejecting.value.id, rejectComment.value.trim())
    rejecting.value = null
    rejectComment.value = ''
    await load()
    feedback.value = makeFeedback('success', '公开申请已打回修改。', '学生会收到具体意见；原始项目材料仍保持私密。')
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '修改意见仍保留在弹窗中，可以修正后重试。', '重试')
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(surface, load)
</script>

<template>
  <div class="page library-page">
    <PageHeader :eyebrow="heading[0]" :title="heading[1]" :description="heading[2]" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <div v-if="surface !== 'announcements'" class="library-search">
      <el-icon><Search /></el-icon>
      <input v-model="keyword" :placeholder="surface === 'cases' ? '搜索学科、项目类型、关键词或场景' : '搜索赛事名称'">
      <button class="primary-button" type="button" @click="runSearch">搜索</button>
    </div>

    <div v-if="surface === 'cases'" class="case-grid">
      <article v-for="item in filteredCases" :key="item.id" class="case-card">
        <div class="case-cover"><span>{{ item.project_title.slice(0, 1) }}</span><i>❧</i></div>
        <div>
          <p>{{ item.discipline || '综合实践' }} · {{ item.outcome_form || '科创项目' }}</p>
          <h2>{{ item.project_title }}</h2>
          <p>{{ item.public_summary }}</p>
          <div class="tag-row"><span v-for="tag in item.tags" :key="tag">{{ tag }}</span></div>
          <footer>
            <span>{{ item.school_name }} · {{ item.selected_material_summaries.length }} 项公开材料</span>
            <div v-if="isTeacher && item.status === 'pending_teacher'" class="case-review-actions">
              <button class="secondary-button" :disabled="loading" type="button" @click="rejecting = item">驳回修改</button>
              <button class="primary-button" :disabled="loading" type="button" @click="approve(item)">审核通过并发布</button>
            </div>
            <StatusTag v-else status="published" />
          </footer>
        </div>
      </article>
      <EmptyState v-if="!loading && !filteredCases.length" title="暂无公开案例" description="教师审核通过的项目会在这里展示。" />
    </div>
    <div v-else-if="surface === 'competitions'" class="competition-list">
      <article v-for="item in filteredCompetitions" :key="item.id" class="competition-card">
        <div class="date-block"><strong>{{ item.registration_deadline?.slice(5, 10).replace('-', '/') ?? '--/--' }}</strong><small>截止日期</small></div>
        <div><div><span>平台赛事</span><small>{{ item.starts_at?.slice(0, 10) ?? '时间待定' }}</small></div><h2>{{ item.title }}</h2><p>{{ item.description }}</p></div>
        <StatusTag status="published" />
      </article>
      <EmptyState v-if="!loading && !filteredCompetitions.length" title="暂无赛事" />
    </div>
    <div v-else class="announcement-timeline">
      <article v-for="item in notices" :key="item.id"><span class="timeline-dot" /><div><small>{{ item.audience === 'all' ? '平台系统公告' : '本校教师公告' }} · {{ item.published_at?.slice(0, 10) }}</small><h2>{{ item.title }}</h2><p>{{ item.body }}</p></div></article>
      <EmptyState v-if="!loading && !notices.length" title="暂无通知" />
    </div>

    <el-dialog :model-value="Boolean(rejecting)" title="驳回公开申请" width="520px" @close="rejecting = null">
      <form class="dialog-form" @submit.prevent="reject">
        <p class="dialog-hint">请说明需要移除的隐私信息、补充的证据或版权问题。</p>
        <label>修改意见<textarea v-model="rejectComment" rows="6" placeholder="例：请移除过程照片中的学生姓名后重新申请。" /></label>
        <div class="dialog-actions">
          <button class="secondary-button" type="button" @click="rejecting = null">取消</button>
          <button class="return-button" :disabled="loading" type="submit">{{ loading ? '正在驳回…' : '驳回并发送意见' }}</button>
        </div>
      </form>
    </el-dialog>
  </div>
</template>
