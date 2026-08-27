<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Collection, Search } from '@element-plus/icons-vue'
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
  ? ['案例库', '案例库', isTeacher.value ? '浏览已公开案例，为指导和选题提供参考。' : '浏览已公开的学生项目案例，按研究方向参考过程和成果。']
  : surface.value === 'competitions'
    ? ['赛事信息', '赛事信息', isTeacher.value ? '查看平台赛事信息，为学生提供参赛建议。' : '查看平台发布的赛事和截止时间，判断当前项目是否适合参加。']
    : [isTeacher.value ? '学生公告' : '平台公告', isTeacher.value ? '学生公告' : '平台公告', isTeacher.value ? '浏览学校与平台发布的公开公告；需要处理的项目动态请进入工作通知。' : '浏览平台发布的公告和学校公开通知；需要处理的个人事项请进入工作通知。'])
const filteredCases = computed(() => cases.value.filter((item) => (
  item.status === 'published' || (isTeacher.value && item.status === 'pending_teacher')
) && `${item.project_title}${item.tags.join('')}${item.discipline}${item.application_scene}`.toLowerCase().includes(appliedKeyword.value.toLowerCase())))
const filteredCompetitions = computed(() => competitions.value.filter((item) => `${item.title}${item.description}`.toLowerCase().includes(appliedKeyword.value.toLowerCase())))
const filteredNotices = computed(() => notices.value.filter((item) => `${item.title}${item.body}`.toLowerCase().includes(appliedKeyword.value.toLowerCase())))

function runSearch() {
  appliedKeyword.value = keyword.value.trim()
  feedback.value = makeFeedback('success', operationSuccess('search'), appliedKeyword.value ? `已按“${appliedKeyword.value}”筛选。` : '当前显示全部内容。')
}

async function load() {
  loading.value = true
  error.value = ''
  feedback.value = null
  try {
    if (surface.value === 'cases') {
      cases.value = []
      cases.value = (await getPublicCases()).data
    } else if (surface.value === 'competitions') {
      competitions.value = []
      competitions.value = (await getCompetitions()).data
    } else {
      notices.value = []
      notices.value = (await getAnnouncements()).data
    }
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '内容列表没有加载完成，可以重试。', '重试')
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
watch(surface, () => {
  keyword.value = ''
  appliedKeyword.value = ''
  feedback.value = null
  rejecting.value = null
  rejectComment.value = ''
  void load()
})
</script>

<template>
  <div class="page library-page">
    <PageHeader :eyebrow="heading[0]" :title="heading[1]" :description="heading[2]" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="error && !feedback" class="form-error" role="alert">{{ error }}</p>
    <p v-if="surface === 'announcements'" class="content-scope-note">这里只展示公开发布的内容；需要处理的项目动态请进入工作通知。</p>
    <div class="filter-bar demo-content-filter">
      <el-icon><Search /></el-icon><input v-model="keyword" class="input" type="search" aria-label="搜索内容" :placeholder="surface === 'cases' ? '搜索案例、学科或关键词' : surface === 'competitions' ? '搜索赛事名称' : '搜索公告标题或内容'" @keydown.enter="runSearch">
      <button class="secondary-button" type="button" @click="runSearch">筛选</button>
    </div>

    <p v-if="loading" class="loading-state" role="status">正在读取内容…</p>
    <div v-else-if="surface === 'cases'" class="demo-content-grid">
      <article v-for="item in filteredCases.slice(0, 3)" :key="item.id" class="demo-content-card paper-card">
        <p class="eyebrow">{{ isTeacher ? '指导参考' : '与你的项目相关' }}</p><h3>{{ item.project_title }}</h3><p class="muted">{{ item.public_summary }}</p>
        <div class="tag-row"><span v-for="tag in item.tags.slice(0, 3)" :key="tag">{{ tag }}</span></div>
        <div v-if="isTeacher && item.status === 'pending_teacher'" class="case-review-actions"><button class="secondary-button" :disabled="loading" type="button" @click="rejecting = item">驳回修改</button><button class="primary-button" :disabled="loading" type="button" @click="approve(item)">审核通过</button></div>
      </article>
      <EmptyState v-if="!loading && !filteredCases.length" title="暂无公开案例" description="教师审核通过的项目会在这里展示。" />
    </div>
    <div v-else-if="surface === 'competitions'" class="demo-content-grid">
      <article v-for="item in filteredCompetitions.slice(0, 3)" :key="item.id" class="demo-content-card paper-card">
        <p class="eyebrow">即将截止</p><h3>{{ item.title }}</h3><p class="muted">{{ item.description }}</p><p class="demo-content-meta">报名截止：{{ item.registration_deadline?.slice(0, 10) ?? '时间待定' }}</p>
      </article>
      <EmptyState v-if="!loading && !filteredCompetitions.length" title="暂无赛事" />
    </div>
    <div v-else class="demo-content-grid">
      <article v-for="item in filteredNotices" :key="item.id" class="demo-content-card paper-card"><p class="eyebrow">{{ item.audience === 'all' ? '平台公告' : '本校公告' }}</p><h3>{{ item.title }}</h3><p class="muted">{{ item.body }}</p><p class="demo-content-meta">{{ item.published_at?.slice(0, 10) }}</p></article>
      <EmptyState v-if="!loading && !filteredNotices.length" :title="appliedKeyword ? '没有匹配的公告' : (isTeacher ? '暂无学生公告' : '暂无平台公告')" />
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

<style scoped>
.demo-content-filter { position: relative; margin-bottom: 20px; }
.content-scope-note { margin: -7px 0 16px; color: var(--muted); font-size: 12px; line-height: 1.6; }
.demo-content-filter > .el-icon { position: absolute; z-index: 1; left: 13px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.demo-content-filter .input { padding-left: 36px; }
.demo-content-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.demo-content-card { display: flex; min-height: 210px; flex-direction: column; align-items: flex-start; padding: 26px; }
.demo-content-card h3 { margin: 7px 0 10px; font-size: 18px; line-height: 1.4; }
.demo-content-card .muted { flex: 1; margin: 0 0 18px; line-height: 1.7; }
.demo-content-card .secondary-button, .demo-content-card .case-review-actions { margin-top: auto; }
.demo-content-meta { color: var(--muted); font-size: 12px; }
.case-review-actions { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
