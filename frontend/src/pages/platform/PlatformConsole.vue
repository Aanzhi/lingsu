<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Bell, Medal, Plus } from '@element-plus/icons-vue'
import { errorMessage, getServiceStatus, type ServiceStatus } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import EmptyState from '../../components/EmptyState.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { platformStore } from '../../stores/platform'
import { licenseStatus, type ApiSchool } from '../../stores/platformApiModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { operationSuccess, type OperationKind } from '../../stores/interactionModel'
import { platformSchoolRoute } from '../../stores/pageContracts'

const route = useRoute()
const surface = computed(() => String(route.meta.surface ?? 'home'))
const error = ref('')
const busy = ref(false)
const dataReady = ref(false)
const feedback = ref<FeedbackState | null>(null)
const serviceStatus = ref<ServiceStatus | null>(null)
const confirmState = ref<{ title: string; description: string; confirmText: string; danger: boolean; work: () => Promise<unknown>; success: OperationKind } | null>(null)
const schoolOpen = ref(false)
const competitionOpen = ref(false)
const announcementOpen = ref(false)
const schoolSearch = ref('')
const schoolStatus = ref<'all' | 'active' | 'inactive'>('all')
const contentSearch = ref('')
const schoolForm = reactive({ name: '', license_expires_at: '2027-07-31', is_active: true })
const competitionForm = reactive({ title: '', registration_deadline: '2026-12-31', description: '' })
const announcementForm = reactive({ title: '', body: '' })
const headings = computed<Record<string, [string, string, string]>>(() => ({
  home: ['概览', '平台概览', '查看学校授权、项目活跃度和服务状态，具体管理操作进入对应工作页。'],
  schools: ['学校空间', '学校空间', '管理学校空间和授权状态；进入详情查看数据，开关只控制授权。'],
  competitions: ['运营内容', '赛事管理', '创建、发布或撤回面向师生的赛事信息。'],
  announcements: ['运营内容', '系统公告', '发布平台公告，并让学校端在通知中心查看。'],
}))
const heading = computed(() => headings.value[surface.value] ?? headings.value.home)
const valid = computed(() => platformStore.state.schools.filter((item) => item.is_authorized).length)
const expiring = computed(() => platformStore.state.schools.filter((item) => licenseStatus(item) === 'expiring').length)
const activeProjects = computed(() => platformStore.state.schools.reduce((sum, item) => sum + item.project_count, 0))
const activityBars = computed(() => {
  const schools = platformStore.state.schools.slice(0, 10)
  const max = Math.max(...schools.map((item) => item.project_count), 1)
  return schools.map((item) => ({ label: item.name, count: item.project_count, height: Math.max(8, Math.round((item.project_count / max) * 100)) }))
})
const serviceItems = computed(() => serviceStatus.value ? (['database', 'task_queue', 'ai'] as const).map((key) => ({ key, label: ({ database: '核心 API / 数据库', task_queue: '任务队列', ai: 'AI 服务' } as Record<string, string>)[key], value: serviceStatus.value?.[key] || 'unknown' })) : [])
const filteredSchools = computed(() => {
  const keyword = schoolSearch.value.trim().toLowerCase()
  return platformStore.state.schools.filter((school) => {
    if (schoolStatus.value === 'active' && !school.is_active) return false
    if (schoolStatus.value === 'inactive' && school.is_active) return false
    return !keyword || school.name.toLowerCase().includes(keyword)
  })
})
const filteredCompetitions = computed(() => {
  const keyword = contentSearch.value.trim().toLowerCase()
  return platformStore.state.competitions.filter((item) => !keyword || `${item.title} ${item.description}`.toLowerCase().includes(keyword))
})
const filteredAnnouncements = computed(() => {
  const keyword = contentSearch.value.trim().toLowerCase()
  return platformStore.state.announcements.filter((item) => !keyword || `${item.title} ${item.body}`.toLowerCase().includes(keyword))
})
function serviceTone(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? 'active' : 'disabled' }
function serviceLabel(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? '正常' : value === 'not_configured' ? '未配置' : '不可用' }

async function load() {
  error.value = ''
  dataReady.value = false
  try {
    const [, serviceResponse] = await Promise.all([platformStore.load(), getServiceStatus().catch(() => null)])
    serviceStatus.value = serviceResponse?.data ?? null
    dataReady.value = true
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '平台数据没有加载完成，可以重试。', '重试')
    throw reason
  }
}
onMounted(() => { void load().catch(() => undefined) })
watch(surface, () => {
  schoolOpen.value = false
  competitionOpen.value = false
  announcementOpen.value = false
  confirmState.value = null
  error.value = ''
  feedback.value = null
  schoolSearch.value = ''
  schoolStatus.value = 'all'
  contentSearch.value = ''
})

async function action(work: () => Promise<unknown>, success?: OperationKind) {
  error.value = ''
  busy.value = true
  dataReady.value = false
  feedback.value = null
  try {
    await work()
    dataReady.value = true
    if (success) feedback.value = makeFeedback('success', operationSuccess(success))
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '状态没有改变，可以重试。', '重试')
  } finally { busy.value = false }
}

function askConfirm(config: NonNullable<typeof confirmState.value>) { confirmState.value = config }
async function confirmAction() {
  if (!confirmState.value) return
  const current = confirmState.value
  confirmState.value = null
  await action(current.work, current.success)
}
async function addSchool() {
  if (!schoolForm.name.trim()) { feedback.value = makeFeedback('error', '请输入学校名称', '学校名称不能为空。'); return }
  await action(() => platformStore.createSchool({ ...schoolForm }))
  if (!feedback.value?.tone || feedback.value.tone === 'success') { schoolOpen.value = false; schoolForm.name = '' }
}
async function addCompetition() {
  if (!competitionForm.title.trim()) { feedback.value = makeFeedback('error', '请输入赛事名称', '赛事名称不能为空。'); return }
  await action(() => platformStore.createCompetition({ ...competitionForm, status: 'draft', audience: 'all' }))
  if (!feedback.value?.tone || feedback.value.tone === 'success') { competitionOpen.value = false; competitionForm.title = ''; competitionForm.description = '' }
}
async function addAnnouncement() {
  if (!announcementForm.title.trim() || !announcementForm.body.trim()) { feedback.value = makeFeedback('error', '请填写公告标题和正文', '标题和正文都不能为空。'); return }
  await action(() => platformStore.announce(announcementForm.title, announcementForm.body))
  if (!feedback.value?.tone || feedback.value.tone === 'success') { announcementOpen.value = false; Object.assign(announcementForm, { title: '', body: '' }) }
}
function toggleSchool(item: ApiSchool) {
  askConfirm({
    title: item.is_active ? '停用学校授权？' : '恢复学校授权？',
    description: item.is_active ? '停用后师生只能读取历史数据，不能创建、提交或审核。' : '恢复后师生可以继续进行项目操作。',
    confirmText: item.is_active ? '停用并只读' : '恢复授权',
    danger: item.is_active,
    work: () => platformStore.updateSchool(item.id, { is_active: !item.is_active }),
    success: item.is_active ? 'school_disabled' : 'school_enabled',
  })
}
</script>

<template>
  <div class="page platform-page">
    <PageHeader :eyebrow="heading[0]" :title="heading[1]" :description="heading[2]">
      <template #actions>
        <RouterLink v-if="surface === 'home'" class="primary-button" to="/platform/schools">查看学校空间</RouterLink>
        <button v-if="surface === 'schools'" class="primary-button" :disabled="platformStore.loading.value || busy" type="button" @click="schoolOpen = true"><el-icon><Plus /></el-icon> 添加学校</button>
        <button v-if="surface === 'competitions'" class="primary-button" :disabled="platformStore.loading.value || busy" type="button" @click="competitionOpen = true"><el-icon><Plus /></el-icon> 发布赛事</button>
        <button v-if="surface === 'announcements'" class="primary-button" :disabled="platformStore.loading.value || busy" type="button" @click="announcementOpen = true"><el-icon><Plus /></el-icon> 发布公告</button>
      </template>
    </PageHeader>
    <FeedbackBanner v-model="feedback" @action="() => void load().catch(() => undefined)" />
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-if="platformStore.loading.value" class="loading-state" role="status">正在读取平台数据…</p>

    <template v-if="surface === 'home' && dataReady && !platformStore.loading.value">
      <div class="pilot-metric-grid">
        <RouterLink to="/platform/schools" class="pilot-card pilot-metric"><div class="pilot-metric__label">已授权学校</div><div class="pilot-metric__value">{{ valid }}</div><div class="pilot-metric__foot good">{{ expiring ? `${expiring} 所即将到期` : '全部服务正常' }}</div></RouterLink>
        <RouterLink to="/platform/schools" class="pilot-card pilot-metric"><div class="pilot-metric__label">活跃项目</div><div class="pilot-metric__value">{{ activeProjects }}</div><div class="pilot-metric__foot">当前学校空间累计</div></RouterLink>
        <RouterLink to="/platform/ai-agents" class="pilot-card pilot-metric"><div class="pilot-metric__label">AI 助手模板</div><div class="pilot-metric__value">—</div><div class="pilot-metric__foot">进入模板页查看启用状态</div></RouterLink>
        <RouterLink to="/platform/schools" class="pilot-card pilot-metric"><div class="pilot-metric__label">待处理事项</div><div class="pilot-metric__value">{{ expiring }}</div><div class="pilot-metric__foot warn">需要管理员关注</div></RouterLink>
      </div>
      <div class="pilot-two-col pilot-platform-detail">
        <section class="pilot-card pilot-content-card">
          <h2>学校空间项目规模</h2><p class="section-note">按当前学校空间的项目数量展示</p>
          <div v-if="activityBars.length" class="pilot-chart" aria-label="学校空间项目规模"><i v-for="item in activityBars" :key="item.label" :title="`${item.label} · ${item.count} 个项目`" :style="{ height: `${item.height}%` }" /></div><div v-else class="platform-chart-empty">暂无学校数据</div><div v-if="activityBars.length" class="pilot-chart-axis"><span>{{ activityBars[0].label }}</span><span>{{ activityBars.at(-1)?.label }}</span></div>
        </section>
        <section class="pilot-card pilot-content-card">
          <h2>系统状态</h2>
          <div v-for="item in serviceItems" :key="item.key" class="pilot-list-row"><div class="pilot-list-row__main"><div class="pilot-list-row__title">{{ item.label }}</div><div class="pilot-list-row__meta">服务端当前状态：{{ serviceLabel(item.value) }}</div></div><StatusTag :status="serviceTone(item.value)" /></div>
          <div v-if="!serviceItems.length" class="platform-service-empty">服务状态暂不可用，请稍后重试。</div>
        </section>
      </div>
    </template>

    <template v-else-if="surface === 'schools' && dataReady && !platformStore.loading.value">
      <section class="platform-school-list paper-card"><div class="filter-bar"><input v-model="schoolSearch" class="input" placeholder="搜索学校名称" aria-label="搜索学校名称"><select v-model="schoolStatus" class="select" aria-label="筛选授权状态"><option value="all">全部状态</option><option value="active">已启用</option><option value="inactive">已停用</option></select></div><div class="table-wrap"><table><thead><tr><th>学校</th><th>联系人</th><th>活跃项目</th><th>授权到期</th><th>授权</th><th>操作</th></tr></thead><tbody><tr v-for="item in filteredSchools" :key="item.id"><td><div class="row-title">{{ item.name }}</div><div class="row-meta">学校空间 ID：SCH-{{ String(item.id).padStart(4, '0') }}</div></td><td>{{ item.teacher_count }} 位教师</td><td>{{ item.project_count }}</td><td>{{ item.license_expires_at ?? '长期' }}</td><td><el-switch :model-value="item.is_active" :disabled="busy" size="small" :aria-label="`${item.name}授权开关`" @change="toggleSchool(item)" /></td><td><RouterLink class="secondary-button" :to="platformSchoolRoute(item.id)">查看详情 →</RouterLink></td></tr></tbody></table><EmptyState v-if="!filteredSchools.length" :title="platformStore.state.schools.length ? '没有匹配学校' : '暂无学校空间'" description="调整搜索或授权状态后继续查找。" /></div></section>
    </template>

    <template v-else-if="surface === 'competitions' && dataReady && !platformStore.loading.value">
      <div class="filter-bar platform-content-filter"><input v-model="contentSearch" class="input" placeholder="搜索赛事标题或说明" aria-label="搜索赛事"><span class="filter-hint">输入后即时筛选</span></div><section class="platform-content-grid"><article v-for="item in filteredCompetitions" :key="item.id" class="paper-card"><p class="eyebrow">赛事</p><h3>{{ item.title }}</h3><p class="muted">报名截止：{{ item.registration_deadline?.slice(0, 10) ?? '未设置' }}</p><StatusTag :status="item.status === 'published' ? 'published' : 'draft'" /><button class="secondary-button" :disabled="busy" type="button" @click="askConfirm({ title: item.status === 'published' ? '撤回这项赛事？' : '发布这项赛事？', description: item.status === 'published' ? '撤回后学生和教师将不再看到该赛事。' : '发布后赛事会立即显示在师生端。', confirmText: item.status === 'published' ? '确认撤回' : '确认发布', danger: item.status === 'published', work: () => platformStore.toggleCompetition(item), success: item.status === 'published' ? 'competition_withdrawn' : 'competition_published' })">{{ item.status === 'published' ? '撤回' : '发布' }}</button></article><EmptyState v-if="!filteredCompetitions.length" :title="platformStore.state.competitions.length ? '没有匹配赛事' : '暂无赛事'" description="调整关键词后继续查找。" /></section>
    </template>

    <template v-else-if="surface === 'announcements' && dataReady && !platformStore.loading.value">
      <div class="filter-bar platform-content-filter"><input v-model="contentSearch" class="input" placeholder="搜索公告标题或正文" aria-label="搜索系统公告"><span class="filter-hint">输入后即时筛选</span></div><div class="platform-content-grid"><article v-for="item in filteredAnnouncements" :key="item.id" class="paper-card"><p class="eyebrow">公告</p><h3>{{ item.title }}</h3><p class="muted">{{ item.body }}</p><StatusTag status="published" /></article><EmptyState v-if="!filteredAnnouncements.length" :title="platformStore.state.announcements.length ? '没有匹配公告' : '暂无系统公告'" description="调整关键词后继续查找。" /></div>
    </template>
    <EmptyState v-else-if="!platformStore.loading.value && !dataReady" title="平台数据暂不可用" description="平台数据没有加载完成，请使用上方“重试”恢复页面。" />

    <el-dialog v-model="schoolOpen" title="创建学校空间" width="540px"><form class="dialog-form" @submit.prevent="addSchool"><label>学校名称<input v-model="schoolForm.name"></label><label>授权到期日<input v-model="schoolForm.license_expires_at" type="date"></label><div class="dialog-actions"><button class="secondary-button" type="button" @click="schoolOpen = false">取消</button><button class="primary-button" :disabled="busy" type="submit">创建学校</button></div></form></el-dialog>
    <el-dialog v-model="competitionOpen" title="创建赛事" width="620px"><form class="dialog-form" @submit.prevent="addCompetition"><label>赛事名称<input v-model="competitionForm.title"></label><label>截止日期<input v-model="competitionForm.registration_deadline" type="date"></label><label>赛事说明<textarea v-model="competitionForm.description" rows="4" /></label><div class="dialog-actions"><button class="secondary-button" type="button" @click="competitionOpen = false">取消</button><button class="primary-button" :disabled="busy" type="submit">保存草稿</button></div></form></el-dialog>
    <el-dialog v-model="announcementOpen" title="发布系统公告" width="580px"><form class="dialog-form" @submit.prevent="addAnnouncement"><label>公告标题<input v-model="announcementForm.title"></label><label>公告正文<textarea v-model="announcementForm.body" rows="6" /></label><div class="dialog-actions"><button class="secondary-button" type="button" @click="announcementOpen = false">取消</button><button class="primary-button" :disabled="busy" type="submit">发布公告</button></div></form></el-dialog>
    <ConfirmDialog v-if="confirmState" :model-value="true" :title="confirmState.title" :description="confirmState.description" :confirm-text="confirmState.confirmText" :danger="confirmState.danger" @update:model-value="confirmState = null" @confirm="confirmAction" />
  </div>
</template>

<style scoped>
.platform-school-list { padding: 26px; }
.platform-school-list .table-wrap { margin-top: 6px; }
.platform-school-list table { min-width: 820px; }
.platform-content-filter { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.platform-content-filter .input { flex: 1; min-width: 280px; }
.filter-hint { color: var(--muted-light); font-size: 11px; white-space: nowrap; }
.platform-content-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.platform-content-grid > article { display: flex; min-height: 190px; flex-direction: column; align-items: flex-start; padding: 26px; }
.platform-content-grid h3 { margin: 7px 0 10px; font-size: 18px; }
.platform-content-grid .muted { flex: 1; margin-bottom: 18px; line-height: 1.65; }
.platform-content-grid .secondary-button { margin-top: 14px; }
</style>
