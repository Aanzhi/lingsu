<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
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
import { studentCaseRoute } from '../../stores/pageContracts'
import { publicCaseAction } from '../../stores/publicCaseModel'

const route = useRoute()
const router = useRouter()
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
const caseQueryId = computed(() => {
  const raw = Array.isArray(route.query.caseId) ? route.query.caseId[0] : route.query.caseId
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
})
const selected = computed(() => projects.value.find((project) => project.id === selectedProject.value) ?? null)
const selectedApplication = computed(() => applications.value.find((item) => item.project === selectedProject.value) ?? null)
const approvedMaterials = computed(() => materials.value
  .filter((item) => item.project === selectedProject.value && item.status === 'approved')
  .map((item) => ({ id: item.id, title: item.title, reportSection: item.report_section })))
const applicationAction = computed(() => selected.value
  ? publicCaseAction({ projectStatus: selected.value.status, approvedMaterialCount: approvedMaterials.value.length, applicationStatus: selectedApplication.value?.status ?? null })
  : { enabled: false, label: '选择项目', reason: '请先创建一个项目。' })
const selectedCase = computed(() => view.value === 'cases' && isStudent.value
  ? filteredCases.value.find((item) => item.id === caseQueryId.value) ?? null
  : null)
const heading = computed(() => surface.value === 'cases'
  ? isStudent.value && view.value === 'applications'
    ? ['公开申请', '我的公开申请', '选择已完成项目并确认公开材料，查看提交后的审核状态。']
    : isStudent.value && selectedCase.value
      ? ['公开成果', '案例详情', '查看已完成并公开的研究成果及授权内容。']
    : ['案例', '案例库', isTeacher.value ? '浏览已公开案例，为指导和选题提供参考。' : '浏览已完成并公开的研究成果，公开申请从页面右上角进入管理。']
  : surface.value === 'competitions'
    ? ['赛事信息', '赛事信息', isTeacher.value ? '查看平台赛事信息，为学生提供参赛建议。' : '按截止时间查看赛事安排，判断当前项目是否适合参加。']
    : [isTeacher.value ? '学生公告' : '校内通知', isTeacher.value ? '学生公告' : '校内通知', isTeacher.value ? '浏览学校与平台发布的公开公告；审核、项目和成员事项在消息中心处理。' : '查看学校和平台发布的研究、活动与项目安排；审核、邀请等个人事项在消息中心处理。'])
const filteredCases = computed(() => cases.value.filter((item) => (
  (item.status === 'published' && (item.project_status === undefined || item.project_status === null || item.project_status === 'completed'))
  || (isTeacher.value && item.status === 'pending_teacher')
) && `${item.project_title}${item.tags.join('')}${item.discipline}${item.application_scene}`.toLowerCase().includes(appliedKeyword.value.toLowerCase())))
const filteredCompetitions = computed(() => competitions.value.filter((item) => `${item.title}${item.description}`.toLowerCase().includes(keyword.value.trim().toLowerCase())))
const filteredNotices = computed(() => notices.value.filter((item) => `${item.title}${item.body}`.toLowerCase().includes(keyword.value.trim().toLowerCase())))
const featuredCompetition = computed(() => filteredCompetitions.value[0] ?? null)
const remainingCompetitions = computed(() => filteredCompetitions.value.slice(1))
const projectTypeLabels: Record<Project['project_type'], string> = { research: '研究型', invention: '发明型', engineering: '工程型' }

function caseProject(item: PublicCase) {
  return projects.value.find((project) => project.id === item.project) ?? null
}

function caseInitial(item: PublicCase) {
  return item.project_title.trim().slice(0, 1) || '研'
}

function caseType(item: PublicCase) {
  const project = caseProject(item)
  return project ? projectTypeLabels[project.project_type] : item.discipline || '研究成果'
}

function caseQuestion(item: PublicCase) {
  return caseProject(item)?.problem?.trim() || item.application_scene || item.public_summary
}

function caseMethod(item: PublicCase) {
  return caseProject(item)?.plan?.trim() || item.outcome_form || '公开摘要与已选材料'
}

function publicMaterialCount(item: PublicCase) {
  return item.selected_material_summaries.length || item.selected_materials.length
}

function visibilityLabel(item: PublicCase) {
  return item.visibility_scope === 'platform' ? '全平台公开' : '校内公开'
}

function casePublishedDate(item: PublicCase) {
  return item.student_consent_at?.slice(0, 10) || '已公开'
}

function formatResourceDate(value?: string) {
  return value?.slice(0, 10) || '时间待定'
}

function formatCompetitionMonth(value?: string) {
  if (!value) return '待定'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '待定' : `${date.getUTCMonth() + 1}月`
}

function formatCompetitionDay(value?: string) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : String(date.getUTCDate()).padStart(2, '0')
}

function competitionStatus(item: Competition) {
  if (item.status === 'draft') return '未发布'
  const now = Date.now()
  const registrationDeadline = item.registration_deadline ? Date.parse(item.registration_deadline) : Number.NaN
  const startsAt = item.starts_at ? Date.parse(item.starts_at) : Number.NaN
  const endsAt = item.ends_at ? Date.parse(item.ends_at) : Number.NaN
  if (!Number.isNaN(endsAt) && endsAt < now) return '已结束'
  if (!Number.isNaN(registrationDeadline) && registrationDeadline >= now) return '报名进行中'
  if (!Number.isNaN(startsAt) && startsAt > now) return '即将开始'
  if (!Number.isNaN(startsAt) && startsAt <= now) return '进行中'
  return item.status === 'published' ? '已发布' : '状态待定'
}

function competitionAudience(item: Competition) {
  return item.audience === 'students' ? '面向学生' : item.audience === 'teachers' ? '面向教师' : '面向全校'
}

function announcementSource(item: Announcement) {
  return item.audience === 'all' ? '平台公告' : item.audience === 'teachers' ? '教师通知' : '校内通知'
}

async function normalizeCaseRoute() {
  if (surface.value !== 'cases' || !isStudent.value || view.value !== 'cases') return
  const raw = Array.isArray(route.query.caseId) ? route.query.caseId[0] : route.query.caseId
  if (raw === undefined) return
  if (caseQueryId.value && filteredCases.value.some((item) => item.id === caseQueryId.value)) return
  const { caseId: _caseId, ...query } = route.query
  await router.replace({ path: '/student/cases', query })
  feedback.value = makeFeedback('error', '案例不存在或已下架。', '已返回案例库列表。')
}

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
        await normalizeCaseRoute()
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
watch(() => String(route.query.caseId ?? ''), () => {
  if (cases.value.length) void normalizeCaseRoute()
})
</script>

<template>
  <div class="page library-page">
    <PageHeader :eyebrow="heading[0]" :title="heading[1]" :description="heading[2]">
      <template #actions>
        <RouterLink v-if="surface === 'cases' && isStudent && view === 'cases' && selectedCase" class="secondary-button case-library-header-link" to="/student/cases">返回案例库</RouterLink>
        <RouterLink v-else-if="surface === 'cases' && isStudent && view === 'cases'" class="secondary-button case-library-header-link" :to="{ path: '/student/cases', query: { view: 'applications', ...(selectedProject !== null ? { projectId: String(selectedProject) } : {}) } }">
          <span>我的公开申请</span><span class="case-library-header-count">{{ applications.length }}</span><span aria-hidden="true">→</span>
        </RouterLink>
        <RouterLink v-else-if="surface === 'cases' && isStudent" class="secondary-button case-library-header-link" to="/student/cases">返回案例库</RouterLink>
      </template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="load" />
    <p v-if="error && !feedback" class="form-error" role="alert">{{ error }}</p>
    <div v-if="(surface !== 'cases' || !isStudent || view !== 'applications') && !selectedCase" class="filter-bar demo-content-filter" :class="{ 'demo-content-filter--resource': surface !== 'cases' }">
      <el-icon><Search /></el-icon><input v-model="keyword" class="input" type="search" aria-label="搜索内容" :placeholder="surface === 'cases' ? '搜索案例、学科或关键词' : surface === 'competitions' ? '搜索赛事名称' : '搜索公告标题或内容'" @keydown.enter="runSearch">
      <button v-if="surface === 'cases'" class="secondary-button" type="button" @click="runSearch">筛选</button>
    </div>

    <p v-if="loading" class="loading-state" role="status">正在读取内容…</p>
    <template v-else-if="surface === 'cases' && isStudent && view === 'applications'">
      <section class="case-application-view">
        <div v-if="projects.length" class="case-application-workspace">
          <section class="paper-card case-application-list">
            <div class="section-heading-row">
              <div><p class="eyebrow">申请记录</p><h2>已提交的申请</h2></div>
              <span class="case-application-count">{{ applications.length }} 条记录</span>
            </div>
            <p class="case-application-hint">教师和平台处理后，申请状态会在这里更新。</p>
            <div class="case-application-records">
              <article v-for="item in applications" :key="item.id" class="list-row">
                <div class="row-main"><div class="row-title">{{ item.project_title }}</div><div class="row-meta">{{ publicMaterialCount(item) }} 项公开材料<span v-if="item.status === 'rejected' && item.review_comment"> · 教师意见：{{ item.review_comment }}</span></div></div>
                <div class="row-actions"><StatusTag :status="item.status === 'pending_teacher' ? 'pending_review' : item.status === 'offline' ? 'disabled' : item.status" /><button v-if="item.status === 'waiting_student'" class="primary-button" type="button" @click="consentCase = item">同意全平台展示</button></div>
              </article>
              <EmptyState v-if="!applications.length" compact title="还没有公开申请" description="确认要公开的材料后，可以从右侧发起申请。" />
            </div>
          </section>
          <section class="paper-card case-application-panel">
            <div class="case-application-panel__header"><p class="eyebrow">发起公开申请</p><h2>确认项目和公开材料</h2><p class="muted">只提交已完成项目中已经通过审核的材料，审核通过前不会对外展示。</p></div>
            <div class="case-application-selection">
              <label>项目<select v-model="selectedProject"><option v-for="project in projects" :key="project.id" :value="project.id">{{ project.title }}</option></select></label>
              <div class="case-application-project-meta"><span>当前项目</span><strong>{{ selected?.title || '请选择项目' }}</strong><StatusTag v-if="selectedApplication" :status="selectedApplication.status === 'pending_teacher' ? 'pending_review' : selectedApplication.status === 'offline' ? 'disabled' : selectedApplication.status" /></div>
            </div>
            <p v-if="selectedApplication?.status === 'rejected'" class="form-error">教师意见：{{ selectedApplication.review_comment }}</p>
            <div class="case-application-action"><p class="case-application-action__reason">{{ applicationAction.reason || `当前有 ${approvedMaterials.length} 项已通过材料可选择。` }}</p><PublicCaseDialog v-if="selectedProject" :project-id="selectedProject" :materials="approvedMaterials" :application="selectedApplication" :enabled="applicationAction.enabled" :label="applicationAction.label" @submitted="handleSubmitted" /></div>
          </section>
        </div>
        <section v-else class="paper-card case-application-empty"><EmptyState compact title="暂无可申请项目" description="先创建项目并完成材料审核，之后可以在这里发起公开申请。" /></section>
      </section>
    </template>
    <section v-else-if="surface === 'cases' && isStudent" class="case-showcase">
      <div class="case-showcase__heading">
        <div><p class="eyebrow">公开成果</p><h2>已完成公开案例</h2><p class="muted">只展示已完成、审核通过并获得授权的研究成果。</p></div>
        <span class="case-showcase__count">{{ filteredCases.length }} 个成果</span>
      </div>
      <div v-if="selectedCase" class="case-detail-view" aria-label="公开成果详情">
        <article class="paper-card case-detail-view__sheet">
          <header class="case-detail-view__identity">
            <div class="case-showcase-card__identity">
              <span class="case-showcase-card__mark">{{ caseInitial(selectedCase) }}</span>
              <div><p class="case-showcase-card__type">{{ caseType(selectedCase) }} · {{ selectedCase.school_name }}</p><h2>{{ selectedCase.project_title }}</h2></div>
            </div>
            <span class="case-showcase-card__scope">{{ visibilityLabel(selectedCase) }}</span>
          </header>
          <div class="case-detail__grid">
            <section class="case-detail__section"><p class="case-detail__label">研究问题</p><h3>{{ caseQuestion(selectedCase) }}</h3></section>
            <section class="case-detail__section"><p class="case-detail__label">研究方法</p><p>{{ caseMethod(selectedCase) }}</p></section>
          </div>
          <section class="case-detail__section case-detail__section--plain"><p class="case-detail__label">公开摘要</p><p>{{ selectedCase.public_summary || '该案例未填写公开摘要。' }}</p></section>
          <section class="case-detail__section case-detail__section--plain"><div class="case-detail__section-heading"><p class="case-detail__label">已公开材料</p><span>{{ publicMaterialCount(selectedCase) }} 项</span></div><div v-if="selectedCase.selected_material_summaries.length" class="case-detail__materials"><article v-for="material in selectedCase.selected_material_summaries" :key="material.material_id" class="case-detail__material"><strong>{{ material.title }}</strong><span>{{ material.report_section || '研究材料' }}</span><p>{{ material.content || '该材料已授权公开，但暂无正文摘要。' }}</p></article></div><p v-else class="muted">已选择公开材料，正文摘要暂不可用。</p></section>
          <dl class="case-detail-view__facts">
            <div><dt>成果形式</dt><dd>{{ selectedCase.outcome_form || '研究成果' }}</dd></div>
            <div><dt>学校</dt><dd>{{ selectedCase.school_name }}</dd></div>
            <div><dt>公开时间</dt><dd>{{ casePublishedDate(selectedCase) }}</dd></div>
          </dl>
          <div v-if="selectedCase.tags.length" class="case-detail__tags"><span v-for="tag in selectedCase.tags" :key="tag">{{ tag }}</span></div>
        </article>
      </div>
      <div v-else class="case-showcase__main">
        <div class="case-showcase__grid">
          <RouterLink v-for="item in filteredCases" :key="item.id" class="case-showcase-card paper-card" :to="studentCaseRoute(item.id)">
            <div class="case-showcase-card__top">
              <div class="case-showcase-card__identity"><span class="case-showcase-card__mark">{{ caseInitial(item) }}</span><div><p class="case-showcase-card__type">{{ caseType(item) }} · {{ item.school_name }}</p><h3>{{ item.project_title }}</h3></div></div>
              <span class="case-showcase-card__scope">{{ visibilityLabel(item) }}</span>
            </div>
            <div class="case-showcase-card__copy"><p class="case-showcase-card__label">研究问题</p><h4>{{ caseQuestion(item) }}</h4><p class="case-showcase-card__label">研究方法</p><p class="case-showcase-card__method">{{ caseMethod(item) }}</p></div>
            <div class="case-showcase-card__facts"><span><small>公开材料</small><strong>{{ publicMaterialCount(item) }} 项</strong></span><span><small>公开时间</small><strong>{{ casePublishedDate(item) }}</strong></span></div>
            <div class="case-showcase-card__footer"><span>公开成果</span><span class="case-showcase-card__open">查看案例详情 <span aria-hidden="true">→</span></span></div>
          </RouterLink>
        </div>
        <EmptyState v-if="!loading && !filteredCases.length" title="暂无已完成公开案例" description="通过审核并获得授权的项目成果会在这里展示。" />
      </div>
    </section>
    <div v-else-if="surface === 'cases'" class="demo-content-grid">
      <article v-for="item in filteredCases" :key="item.id" class="demo-content-card paper-card">
        <p class="eyebrow">{{ isTeacher ? '指导参考' : '与你的项目相关' }}</p><h3>{{ item.project_title }}</h3><p class="muted">{{ item.public_summary }}</p>
        <div class="tag-row"><span v-for="tag in item.tags.slice(0, 3)" :key="tag">{{ tag }}</span></div>
        <div v-if="isTeacher && item.status === 'pending_teacher'" class="case-review-actions"><button class="secondary-button" :disabled="loading" type="button" @click="rejecting = item">驳回修改</button><button class="primary-button" :disabled="loading" type="button" @click="approve(item)">审核通过</button></div>
      </article>
      <EmptyState v-if="!loading && !filteredCases.length" title="暂无公开案例" description="教师审核通过的项目会在这里展示。" />
    </div>
    <section v-else-if="surface === 'competitions'" class="resource-content-page resource-content-page--competitions">
      <div class="resource-section-heading">
        <div><p class="eyebrow">参赛信息</p><h2>当前赛事</h2><p class="muted">按时间和面向对象了解赛事安排，决定是否加入当前研究计划。</p></div>
        <span class="resource-count">{{ filteredCompetitions.length }} 项赛事</span>
      </div>
      <div v-if="featuredCompetition" class="competition-stream">
        <article class="competition-feature paper-card">
          <div class="competition-feature__date" aria-hidden="true"><span>{{ formatCompetitionMonth(featuredCompetition.starts_at || featuredCompetition.registration_deadline) }}</span><strong>{{ formatCompetitionDay(featuredCompetition.starts_at || featuredCompetition.registration_deadline) }}</strong></div>
          <div class="competition-feature__body">
            <div class="resource-card-meta"><span class="resource-status">{{ competitionStatus(featuredCompetition) }}</span><span>{{ competitionAudience(featuredCompetition) }}</span></div>
            <h2>{{ featuredCompetition.title }}</h2>
            <p>{{ featuredCompetition.description || '赛事说明暂未发布。' }}</p>
            <dl class="competition-facts">
              <div><dt>报名截止</dt><dd>{{ formatResourceDate(featuredCompetition.registration_deadline) }}</dd></div>
              <div><dt>赛事时间</dt><dd>{{ formatResourceDate(featuredCompetition.starts_at) }}<span v-if="featuredCompetition.ends_at"> — {{ formatResourceDate(featuredCompetition.ends_at) }}</span></dd></div>
              <div><dt>面向对象</dt><dd>{{ competitionAudience(featuredCompetition) }}</dd></div>
            </dl>
          </div>
        </article>
        <div v-if="remainingCompetitions.length" class="competition-list" aria-label="其他赛事">
          <article v-for="item in remainingCompetitions" :key="item.id" class="competition-list-row paper-card">
            <div class="competition-list-row__date" aria-hidden="true"><span>{{ formatCompetitionMonth(item.starts_at || item.registration_deadline) }}</span><strong>{{ formatCompetitionDay(item.starts_at || item.registration_deadline) }}</strong></div>
            <div class="competition-list-row__body">
              <div class="resource-card-meta"><span class="resource-status">{{ competitionStatus(item) }}</span><span>{{ competitionAudience(item) }}</span></div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.description || '赛事说明暂未发布。' }}</p>
            </div>
            <div class="competition-list-row__meta"><span>报名截止</span><strong>{{ formatResourceDate(item.registration_deadline) }}</strong></div>
          </article>
        </div>
      </div>
      <EmptyState v-else title="暂无赛事" description="平台发布赛事后，会在这里显示报名时间和参赛范围。" />
    </section>
    <section v-else class="resource-content-page resource-content-page--announcements">
      <div class="resource-section-heading">
        <div><p class="eyebrow">学校与平台</p><h2>最近通知</h2><p class="muted">按发布时间查看研究、活动和项目安排，个人审核与邀请事项请到消息中心处理。</p></div>
        <span class="resource-count">{{ filteredNotices.length }} 条通知</span>
      </div>
      <div v-if="filteredNotices.length" class="announcement-feed paper-card" aria-label="通知列表">
        <article v-for="item in filteredNotices" :key="item.id" class="announcement-feed__item" :class="{ 'announcement-feed__item--unread': item.is_read === false }">
          <div class="announcement-feed__marker"><span class="timeline-dot" aria-hidden="true"></span><time :datetime="item.published_at">{{ formatResourceDate(item.published_at) }}</time></div>
          <div class="announcement-feed__body">
            <div class="resource-card-meta"><span class="resource-source">{{ announcementSource(item) }}</span><span v-if="item.is_read === false" class="resource-unread">未读</span></div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.body }}</p>
          </div>
        </article>
      </div>
      <EmptyState v-else :title="keyword.trim() ? '没有匹配的通知' : (isTeacher ? '暂无学生公告' : '暂无校内通知')" description="新的学校或平台通知发布后，会在这里按时间显示。" />
    </section>

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
.case-library-header-link { display: inline-flex; align-items: center; gap: 8px; text-decoration: none; white-space: nowrap; }
.case-library-header-count { min-width: 20px; height: 20px; display: inline-grid; place-items: center; padding: 0 5px; border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); font-size: 11px; }
.case-application-view { display: grid; gap: 16px; }
.case-application-workspace { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(360px, .75fr); align-items: start; gap: 16px; }
.case-application-list, .case-application-panel { min-width: 0; padding: 24px; }
.case-application-list .list-row:first-child { border-top: 0; }
.section-heading-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 8px; }
.section-heading-row h2 { margin: 4px 0 0; font-size: 21px; }
.case-application-count { flex: 0 0 auto; color: var(--muted); font-size: 12px; }
.case-application-hint { margin: 0 0 5px; color: var(--muted); font-size: 12px; line-height: 1.6; }
.case-application-records { display: grid; }
.case-application-records .empty-state { margin-top: 14px; }
.case-application-panel { display: grid; gap: 18px; align-content: start; }
.case-application-panel__header { display: grid; gap: 3px; }
.case-application-panel h2 { margin: 5px 0 7px; font-size: 20px; }
.case-application-panel label { display: grid; gap: 7px; color: var(--muted); font-size: 12px; }
.case-application-panel select { min-height: 38px; padding: 0 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); color: var(--ink); }
.case-application-selection { display: grid; gap: 14px; }
.case-application-project-meta { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 13px 14px; border: 1px solid var(--sage-line-soft); border-radius: var(--radius-sm); background: var(--sage-soft); color: var(--muted); font-size: 11px; }
.case-application-project-meta strong { min-width: 0; overflow: hidden; color: var(--ink); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.case-application-action { display: grid; gap: 14px; padding-top: 16px; border-top: 1px solid var(--line); }
.case-application-action__reason { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.65; }
.case-application-action :deep(.secondary-button) { justify-self: start; }
.case-application-empty { padding: 20px; }
.case-showcase { display: grid; gap: 18px; }
.case-showcase__heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; padding-top: 4px; }
.case-showcase__heading h2 { margin: 4px 0 5px; font: 700 21px/1.3 var(--sans); }
.case-showcase__heading .muted { margin: 0; color: var(--muted); font-size: 12px; }
.case-showcase__count { padding-bottom: 3px; color: var(--muted); font-size: 12px; white-space: nowrap; }
.case-showcase__main { min-width: 0; display: grid; gap: 16px; }
.case-showcase__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.case-showcase-card { min-width: 0; display: flex; flex-direction: column; gap: 18px; padding: 24px; color: inherit; background: var(--paper); text-decoration: none; transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease; }
.case-showcase-card:hover { border-color: var(--sage-line); box-shadow: 0 12px 26px rgba(38,64,49,.08); transform: translateY(-2px); }
.case-showcase-card:focus-visible { outline: 2px solid var(--moss); outline-offset: 2px; border-color: var(--moss); box-shadow: 0 0 0 3px rgba(76,114,69,.12); }
.case-showcase-card__top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; min-width: 0; }
.case-showcase-card__identity { display: flex; align-items: center; gap: 12px; min-width: 0; }
.case-showcase-card__identity > div { min-width: 0; }
.case-showcase-card__mark { width: 44px; height: 44px; flex: 0 0 44px; display: grid; place-items: center; border-radius: 12px; background: var(--moss); color: #fff; font: 700 19px/1 var(--sans); }
.case-showcase-card__type { overflow: hidden; margin: 0 0 5px; color: var(--moss); font-size: 11px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.case-showcase-card h3 { overflow-wrap: anywhere; margin: 0; color: var(--ink); font: 700 20px/1.35 var(--sans); }
.case-showcase-card__scope { flex: 0 0 auto; padding: 6px 10px; border: 1px solid var(--sage-line); border-radius: 999px; color: var(--moss-dark); background: rgba(255,255,255,.64); font-size: 11px; white-space: nowrap; }
.case-showcase-card__copy { display: grid; gap: 7px; min-width: 0; }
.case-showcase-card__label { margin: 0; color: var(--moss); font-size: 11px; font-weight: 700; }
.case-showcase-card__copy h4 { overflow-wrap: anywhere; margin: 0 0 7px; color: var(--ink); font: 600 17px/1.5 var(--sans); }
.case-showcase-card__method, .case-showcase-card__summary { overflow-wrap: anywhere; margin: 0; color: var(--muted); font-size: 13px; line-height: 1.7; }
.case-showcase-card__summary { margin-top: 3px; padding-top: 12px; border-top: 1px solid var(--line); }
.case-showcase-card__facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; padding: 14px 0 0; border-top: 1px solid var(--line); }
.case-showcase-card__facts span { min-width: 0; display: grid; gap: 4px; }
.case-showcase-card__facts small { color: var(--muted-light); font-size: 10px; }
.case-showcase-card__facts strong { overflow: hidden; color: var(--ink); font-size: 12px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
.case-showcase-card__footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: auto; padding-top: 14px; border-top: 1px solid var(--line); }
.case-showcase-card__footer > span { color: var(--muted); font-size: 11px; }
.case-showcase-card__open { display: inline-flex; align-items: center; gap: 7px; color: var(--moss-dark); font: 700 12px/1.4 var(--sans); }
.case-showcase-card__open:hover { color: var(--moss); }
.case-detail-view { display: grid; gap: 18px; }
.case-detail-view__sheet { display: grid; gap: 22px; min-width: 0; padding: 30px 32px; }
.case-detail-view__identity { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding-bottom: 22px; border-bottom: 1px solid var(--line); }
.case-detail-view__identity .case-showcase-card__identity { align-items: flex-start; }
.case-detail-view__identity h2 { overflow-wrap: anywhere; margin: 0; color: var(--ink); font: 700 clamp(22px, 2.8vw, 32px)/1.25 var(--sans); letter-spacing: -.03em; }
.case-detail-view__identity .case-showcase-card__scope { margin-top: 2px; }
.case-detail__grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.case-detail__section { display: grid; gap: 7px; min-width: 0; padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-muted); }
.case-detail__section--plain { padding: 0 0 20px; border: 0; border-bottom: 1px solid var(--line); border-radius: 0; background: transparent; }
.case-detail__section > * { min-width: 0; }
.case-detail__section > p:not(.case-detail__label) { overflow-wrap: anywhere; margin: 0; color: var(--muted); font-size: 13px; line-height: 1.75; }
.case-detail__label { margin: 0; color: var(--moss); font-size: 11px; font-weight: 700; }
.case-detail__section h3 { overflow-wrap: anywhere; margin: 0; color: var(--ink); font: 650 17px/1.5 var(--sans); }
.case-detail__section-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.case-detail__section-heading > span { color: var(--muted); font-size: 11px; }
.case-detail__materials { display: grid; gap: 9px; }
.case-detail__material { display: grid; gap: 4px; padding: 12px; border: 1px solid var(--sage-line-soft); border-radius: 8px; background: var(--paper); }
.case-detail__material strong { overflow-wrap: anywhere; color: var(--ink); font-size: 13px; }
.case-detail__material > span { color: var(--muted-light); font-size: 11px; }
.case-detail__material p { overflow-wrap: anywhere; margin: 3px 0 0; color: var(--muted); font-size: 12px; line-height: 1.7; white-space: pre-wrap; }
.case-detail-view__facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 0; padding-top: 2px; }
.case-detail-view__facts div { display: grid; gap: 5px; min-width: 0; }
.case-detail-view__facts dt { color: var(--muted-light); font-size: 11px; }
.case-detail-view__facts dd { overflow-wrap: anywhere; margin: 0; color: var(--ink); font-size: 13px; font-weight: 650; }
.case-detail__tags { display: flex; flex-wrap: wrap; gap: 6px; }
.case-detail__tags span { padding: 5px 8px; border: 1px solid var(--sage-line-soft); border-radius: 999px; color: var(--moss-dark); background: var(--sage-soft); font-size: 11px; }
.demo-content-filter { position: relative; margin-bottom: 20px; }
.demo-content-filter > .el-icon { position: absolute; z-index: 1; left: 13px; top: 50%; transform: translateY(-50%); color: var(--muted); }
.demo-content-filter .input { padding-left: 36px; }
.demo-content-filter--resource .input { width: min(100%, 560px); min-width: 360px; }
.resource-content-page { display: grid; gap: 18px; min-width: 0; }
.resource-section-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; padding-top: 3px; }
.resource-section-heading h2 { margin: 4px 0 5px; color: var(--ink); font: 700 22px/1.3 var(--sans); }
.resource-section-heading .muted { max-width: 740px; margin: 0; color: var(--muted); font-size: 12px; line-height: 1.7; }
.resource-count { flex: 0 0 auto; padding-bottom: 4px; color: var(--muted); font-size: 12px; white-space: nowrap; }
.competition-stream { display: grid; gap: 14px; min-width: 0; }
.competition-feature { display: grid; grid-template-columns: 118px minmax(0, 1fr); gap: 24px; min-width: 0; padding: 24px; border-color: var(--sage-line); background: linear-gradient(135deg, var(--sage-soft) 0%, var(--paper) 72%); }
.competition-feature__date, .competition-list-row__date { display: grid; align-content: center; justify-items: center; gap: 2px; min-height: 104px; padding: 14px 10px; border: 1px solid var(--sage-line); border-radius: 14px; color: var(--moss-dark); background: rgba(255,255,255,.68); text-align: center; }
.competition-feature__date span, .competition-list-row__date span { font-size: 11px; }
.competition-feature__date strong, .competition-list-row__date strong { font: 700 34px/1 var(--sans); letter-spacing: -.04em; }
.competition-feature__body, .competition-list-row__body { min-width: 0; }
.resource-card-meta { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 14px; color: var(--muted); font-size: 11px; }
.resource-status, .resource-source, .resource-unread { display: inline-flex; align-items: center; min-height: 24px; padding: 3px 9px; border: 1px solid var(--sage-line); border-radius: 999px; color: var(--moss-dark); background: rgba(255,255,255,.72); font-size: 11px; font-weight: 650; }
.resource-status::before { width: 6px; height: 6px; margin-right: 6px; border-radius: 50%; background: var(--moss); content: ''; }
.competition-feature h2 { overflow-wrap: anywhere; margin: 12px 0 8px; color: var(--ink); font: 700 25px/1.35 var(--sans); }
.competition-feature p, .competition-list-row p { overflow-wrap: anywhere; margin: 0; color: var(--muted); font-size: 13px; line-height: 1.75; }
.competition-facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 20px 0 0; padding-top: 16px; border-top: 1px solid var(--sage-line-soft); }
.competition-facts div, .competition-list-row__meta { display: grid; gap: 5px; min-width: 0; }
.competition-facts dt, .competition-list-row__meta span { color: var(--muted-light); font-size: 10px; }
.competition-facts dd, .competition-list-row__meta strong { overflow-wrap: anywhere; margin: 0; color: var(--ink); font-size: 12px; font-weight: 650; }
.competition-list { display: grid; gap: 10px; }
.competition-list-row { display: grid; grid-template-columns: 72px minmax(0, 1fr) 150px; gap: 18px; align-items: center; min-width: 0; padding: 15px 18px; }
.competition-list-row__date { min-height: 64px; padding: 8px; border-radius: 10px; }
.competition-list-row__date strong { font-size: 23px; }
.competition-list-row h3 { overflow-wrap: anywhere; margin: 7px 0 4px; color: var(--ink); font: 700 17px/1.4 var(--sans); }
.competition-list-row__meta { justify-items: end; text-align: right; }
.announcement-feed { display: grid; gap: 0; padding: 5px 24px; }
.announcement-feed__item { display: grid; grid-template-columns: 116px minmax(0, 1fr); gap: 20px; min-width: 0; padding: 22px 0; border-bottom: 1px solid var(--line); }
.announcement-feed__item:last-child { border-bottom: 0; }
.announcement-feed__marker { position: relative; min-height: 72px; padding: 2px 18px 0 0; border-right: 1px solid var(--sage-line); color: var(--muted); font-size: 11px; text-align: right; }
.announcement-feed__marker .timeline-dot { right: -6px; left: auto; top: 5px; width: 10px; height: 10px; }
.announcement-feed__item--unread .announcement-feed__marker { color: var(--moss-dark); font-weight: 650; }
.announcement-feed__body { min-width: 0; }
.announcement-feed__body h3 { overflow-wrap: anywhere; margin: 10px 0 6px; color: var(--ink); font: 700 18px/1.4 var(--sans); }
.announcement-feed__body p { overflow-wrap: anywhere; margin: 0; color: var(--muted); font-size: 13px; line-height: 1.8; white-space: pre-wrap; }
.resource-unread { color: var(--moss-dark); background: var(--sage-soft); }
.demo-content-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.demo-content-card { display: flex; min-height: 210px; flex-direction: column; align-items: flex-start; padding: 26px; }
.demo-content-card h3 { margin: 7px 0 10px; font-size: 18px; line-height: 1.4; }
.demo-content-card .muted { flex: 1; margin: 0 0 18px; line-height: 1.7; }
.demo-content-card .secondary-button, .demo-content-card .case-review-actions { margin-top: auto; }
.demo-content-meta { color: var(--muted); font-size: 12px; }
.case-review-actions { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
