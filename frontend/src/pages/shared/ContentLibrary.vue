<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Collection, Search } from '@element-plus/icons-vue'
import {
  approvePublicCase,
  errorMessage,
  getAnnouncements,
  getCompetitions,
  getMaterials,
  getProjects,
  getPublicCases,
  rejectPublicCase,
  studentConsentPublicCase,
  type Announcement,
  type Competition,
  type Material,
  type Project,
  type PublicCase,
} from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import PublicCaseDialog from '../../components/PublicCaseDialog.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { operationSuccess } from '../../stores/interactionModel'
import { publicCaseAction } from '../../stores/publicCaseModel'

const route = useRoute()
const keyword = ref('')
const appliedKeyword = ref('')
const error = ref('')
const feedback = ref<FeedbackState | null>(null)
const loading = ref(false)
const cases = ref<PublicCase[]>([])
const competitions = ref<Competition[]>([])
const notices = ref<Announcement[]>([])
const projects = ref<Project[]>([])
const materials = ref<Material[]>([])
const applications = ref<PublicCase[]>([])
const rejecting = ref<PublicCase | null>(null)
const rejectComment = ref('')
const consentCase = ref<PublicCase | null>(null)
const selectedProject = ref<number | null>(null)
const surface = computed(() => String(route.meta.surface ?? 'cases'))
const isStudent = computed(() => route.path.startsWith('/student'))
const isTeacher = computed(() => route.path.startsWith('/teacher'))
const view = computed(() => surface.value === 'cases' && isStudent.value && route.query.view === 'applications' ? 'applications' : 'cases')
const selected = computed(() => projects.value.find((project) => project.id === selectedProject.value) ?? null)
const selectedApplication = computed(() => applications.value.find((item) => item.project === selectedProject.value) ?? null)
const approvedMaterials = computed(() => materials.value
  .filter((item) => item.project === selectedProject.value && item.status === 'approved')
  .map((item) => ({ id: item.id, title: item.title, reportSection: item.report_section })))
const applicationAction = computed(() => selected.value
  ? publicCaseAction({ projectStatus: selected.value.status, approvedMaterialCount: approvedMaterials.value.length, applicationStatus: selectedApplication.value?.status ?? null })
  : { enabled: false, label: '选择项目', reason: '请先创建一个项目。' })
const heading = computed(() => surface.value === 'cases'
  ? ['案例', '案例库', isTeacher.value ? '浏览已公开案例，为指导和选题提供参考。' : '浏览公开案例，并在同一页面管理项目公开展示申请。']
  : surface.value === 'competitions'
    ? ['赛事信息', '赛事信息', isTeacher.value ? '查看平台赛事信息，为学生提供参赛建议。' : '查看平台发布的赛事和截止时间，判断当前项目是否适合参加。']
    : [isTeacher.value ? '学生公告' : '校内通知', isTeacher.value ? '学生公告' : '校内通知', isTeacher.value ? '浏览学校与平台发布的公开公告；需要处理的项目动态请进入工作通知。' : '查看学校和平台发布的通知，了解与研究、活动和项目相关的安排。'])
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
      if (isStudent.value) {
        const [caseResponse, projectResponse, materialResponse] = await Promise.all([getPublicCases(), getProjects(), getMaterials()])
        cases.value = caseResponse.data
        projects.value = projectResponse.data
        materials.value = materialResponse.data
        applications.value = caseResponse.data.filter((item) => projectResponse.data.some((project) => project.id === item.project))
        const requestedProjectId = Number(route.query.projectId)
        selectedProject.value = projectResponse.data.some((project) => project.id === requestedProjectId)
          ? requestedProjectId
          : selectedProject.value && projectResponse.data.some((project) => project.id === selectedProject.value)
            ? selectedProject.value
            : projectResponse.data[0]?.id ?? null
      } else {
        cases.value = (await getPublicCases()).data
      }
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

async function giveConsent() {
  if (!consentCase.value) return
  const target = consentCase.value
  consentCase.value = null
  try {
    await studentConsentPublicCase(target.id)
    feedback.value = makeFeedback('success', '已同意全平台展示。', '申请已进入平台审核，平台通过后才会公开。')
    await load()
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '同意状态没有改变，可以重试。', '重试')
  }
}

async function handleSubmitted() {
  await load()
  feedback.value = makeFeedback('success', '公开申请已提交。', '主指导教师审核通过前，任何材料都不会对外展示。')
}

onMounted(load)
watch([surface, view, () => String(route.query.projectId ?? '')], () => {
  keyword.value = ''
  appliedKeyword.value = ''
  feedback.value = null
  rejecting.value = null
  rejectComment.value = ''
  consentCase.value = null
  void load()
})
</script>

<template>
  <div class="page library-page">
    <PageHeader :eyebrow="heading[0]" :title="heading[1]" :description="heading[2]" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="error && !feedback" class="form-error" role="alert">{{ error }}</p>
    <p v-if="surface === 'announcements'" class="content-scope-note">这里只展示公开发布的通知；需要处理的个人消息请查看顶部铃铛。</p>
    <nav v-if="surface === 'cases' && isStudent" class="library-view-tabs" role="tablist" aria-label="案例库内容">
      <RouterLink class="library-view-tab" :class="{ 'is-active': view === 'cases' }" to="/student/cases" role="tab" :aria-selected="view === 'cases'">公开案例</RouterLink>
      <RouterLink class="library-view-tab" :class="{ 'is-active': view === 'applications' }" :to="{ path: '/student/cases', query: { view: 'applications', ...(selectedProject ? { projectId: String(selectedProject) } : {}) } }" role="tab" :aria-selected="view === 'applications'">我的公开申请</RouterLink>
    </nav>
    <div v-if="surface !== 'cases' || !isStudent || view !== 'applications'" class="filter-bar demo-content-filter">
      <el-icon><Search /></el-icon><input v-model="keyword" class="input" type="search" aria-label="搜索内容" :placeholder="surface === 'cases' ? '搜索案例、学科或关键词' : surface === 'competitions' ? '搜索赛事名称' : '搜索公告标题或内容'" @keydown.enter="runSearch">
      <button class="secondary-button" type="button" @click="runSearch">筛选</button>
    </div>

    <p v-if="loading" class="loading-state" role="status">正在读取内容…</p>
    <template v-else-if="surface === 'cases' && isStudent && view === 'applications'">
      <section class="case-application-view">
        <section class="paper-card case-application-list">
          <div class="section-heading-row"><div><p class="eyebrow">申请记录</p><h2>我的公开申请</h2></div><span class="muted">仅已确认的申请会进入后续审核</span></div>
          <article v-for="item in applications" :key="item.id" class="list-row">
            <div class="row-main"><div class="row-title">{{ item.project_title }}</div><div class="row-meta">{{ item.selected_materials.length }} 项公开材料<span v-if="item.status === 'rejected' && item.review_comment"> · 教师意见：{{ item.review_comment }}</span></div></div>
            <div class="row-actions"><StatusTag :status="item.status === 'pending_teacher' ? 'pending_review' : item.status === 'offline' ? 'disabled' : item.status" /><button v-if="item.status === 'waiting_student'" class="primary-button" type="button" @click="consentCase = item">同意全平台展示</button></div>
          </article>
          <EmptyState v-if="!applications.length" title="还没有公开申请" description="项目完成并通过材料审核后，可从这里选择材料发起公开申请。" />
        </section>
        <section v-if="projects.length" class="paper-card case-application-panel">
          <div><p class="eyebrow">从项目申请</p><h2>{{ applicationAction.label }}</h2><p class="muted">{{ applicationAction.reason || `当前有 ${approvedMaterials.length} 项已通过材料可选择。` }}</p><p v-if="selectedApplication?.status === 'rejected'" class="form-error">教师意见：{{ selectedApplication.review_comment }}</p></div>
          <label>选择项目<select v-model="selectedProject"><option v-for="project in projects" :key="project.id" :value="project.id">{{ project.title }}</option></select></label>
          <PublicCaseDialog v-if="selectedProject" :project-id="selectedProject" :materials="approvedMaterials" :application="selectedApplication" :enabled="applicationAction.enabled" :label="applicationAction.label" @submitted="handleSubmitted" />
        </section>
        <EmptyState v-else title="暂无可申请项目" description="先创建项目并完成材料审核。" />
      </section>
    </template>
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
      <EmptyState v-if="!loading && !filteredNotices.length" :title="appliedKeyword ? '没有匹配的公告' : (isTeacher ? '暂无学生公告' : '暂无校内通知')" />
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
    <ConfirmDialog v-if="consentCase" :model-value="true" title="同意教师发起的全平台展示？" description="同意后，项目摘要和你选择的材料会提交给平台审核；平台通过前不会公开。" confirm-text="确认同意" @update:model-value="consentCase = null" @confirm="giveConsent" />
  </div>
</template>

<style scoped>
.library-view-tabs { display: flex; gap: 28px; margin: 0 0 20px; border-bottom: 1px solid var(--line); }
.library-view-tab { position: relative; padding: 0 2px 13px; color: var(--muted); font-size: 14px; font-weight: 700; text-decoration: none; }
.library-view-tab::after { position: absolute; right: 0; bottom: -1px; left: 0; height: 2px; background: transparent; content: ''; }
.library-view-tab.is-active { color: var(--ink); }
.library-view-tab.is-active::after { background: var(--accent); }
.case-application-view { display: grid; gap: 16px; }
.case-application-list { padding: 26px; }
.case-application-list .list-row:first-of-type { border-top: 0; }
.section-heading-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 8px; }
.section-heading-row h2 { margin: 4px 0 0; font-size: 21px; }
.case-application-panel { display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, .55fr); gap: 20px; align-items: end; padding: 26px; }
.case-application-panel h2 { margin: 5px 0 7px; font-size: 20px; }
.case-application-panel label { display: grid; gap: 7px; color: var(--muted); font-size: 12px; }
.case-application-panel select { min-height: 38px; padding: 0 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); color: var(--ink); }
.case-application-panel :deep(.secondary-button) { justify-self: end; }
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
