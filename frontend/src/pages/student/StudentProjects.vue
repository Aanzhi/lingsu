<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { errorMessage, type Project } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import ProjectLifecycleMenu from '../../components/ProjectLifecycleMenu.vue'
import StatusTag from '../../components/StatusTag.vue'
import { auth } from '../../stores/auth'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { studentProjectRoute, studentProjectsPath } from '../../stores/pageContracts'
import { projectTypeLabel } from '../../stores/presentationModel'
import { student } from '../../stores/student'

const open = ref(false)
const route = useRoute()
const router = useRouter()
const saving = ref(false)
const error = ref('')
const feedback = ref<FeedbackState | null>(null)
const createdProjectId = ref<number | null>(null)
const search = ref('')
const page = ref(1)
const PROJECTS_PAGE_SIZE = 6
const creationMode = ref<'direct' | 'ai'>('direct')
const form = reactive({ title: '', problem: '', plan: '', project_type: 'research' as Project['project_type'] })

const activeProjects = computed(() => student.state.projects.filter((p) => !p.is_archived && !p.deleted_at))
const currentProjects = computed(() => {
  if (route.query.tab === 'archived') return student.state.archivedProjects
  if (route.query.tab === 'trashed') return student.state.trashedProjects
  return activeProjects.value
})
const filteredProjects = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  if (!query) return currentProjects.value
  return currentProjects.value.filter((project) => [
    project.title,
    project.problem,
    projectTypeLabel(project.project_type),
    project.status,
  ].some((value) => String(value ?? '').toLocaleLowerCase().includes(query)))
})
const activeTab = computed(() => !route.query.tab || route.query.tab === 'active')
const hasSearch = computed(() => Boolean(search.value.trim()))
const featuredProject = computed(() => {
  if (!activeTab.value || hasSearch.value) return null
  return activeProjects.value.find((project) => project.is_primary) ?? activeProjects.value[0] ?? null
})
const shelfProjects = computed(() => {
  if (!featuredProject.value) return filteredProjects.value
  return filteredProjects.value.filter((project) => project.id !== featuredProject.value?.id)
})
const totalPages = computed(() => Math.max(1, Math.ceil(shelfProjects.value.length / PROJECTS_PAGE_SIZE)))
const visibleProjects = computed(() => {
  const start = (page.value - 1) * PROJECTS_PAGE_SIZE
  return shelfProjects.value.slice(start, start + PROJECTS_PAGE_SIZE)
})
const pageStart = computed(() => shelfProjects.value.length ? (page.value - 1) * PROJECTS_PAGE_SIZE + 1 : 0)
const pageEnd = computed(() => Math.min(page.value * PROJECTS_PAGE_SIZE, shelfProjects.value.length))
const tabCounts = computed(() => ({
  active: activeProjects.value.length,
  archived: student.state.archivedProjects.length,
  trashed: student.state.trashedProjects.length,
}))
const focus = computed(() => {
  const value = String(route.query.focus ?? '')
  return (['journey', 'materials', 'apply'] as const).includes(value as 'journey' | 'materials' | 'apply')
    ? value as 'journey' | 'materials' | 'apply'
    : null
})
const focusMessage = computed(() => {
  const messages = {
    journey: '创建或选择一个项目后，这里会打开对应的研究章节。',
    materials: '完成项目中的任务后，提交的材料会按章节归档到这里。',
    apply: '项目完成并有通过审核的材料后，才能提交成果展示申请。',
  }
  return focus.value ? messages[focus.value] : ''
})
const listLoading = computed(() => route.query.tab === 'archived' ? student.resourceLoading.archived : route.query.tab === 'trashed' ? student.resourceLoading.trashed : student.resourceLoading.projects)
function lifecycleLabel() {
  if (route.query.tab === 'archived') return '已归档'
  if (route.query.tab === 'trashed') return '回收站'
  return '进行中'
}
function lifecycleDateLabel() {
  if (route.query.tab === 'archived') return '归档时间'
  if (route.query.tab === 'trashed') return '移入时间'
  return '创建时间'
}
function lifecycleDate(project: Project) {
  if (route.query.tab === 'archived') return project.archived_at?.slice(0, 10) ?? '--'
  if (route.query.tab === 'trashed') return project.trashed_at?.slice(0, 10) ?? '--'
  return project.created_at.slice(0, 10)
}

async function load() {
  error.value = ''
  try {
    if (!student.loaded.value) await student.load()
    await Promise.all([student.loadArchived(), student.loadTrashed()])
    if (route.query.create === '1' && auth.user.value?.authorized) { creationMode.value = 'direct'; open.value = true }
  } catch (reason) {
    error.value = errorMessage(reason)
    feedback.value = makeFeedback('error', error.value, '项目书架没有加载完成，可以重试。', '重试')
    throw reason
  }
}

onMounted(() => {
  void load().catch(() => undefined)
})

watch(() => route.query.create, (value) => {
  if (value === '1' && auth.user.value?.authorized) { creationMode.value = 'direct'; open.value = true }
})
watch([search, () => route.query.tab], () => { page.value = 1 })
watch(shelfProjects, () => { if (page.value > totalPages.value) page.value = totalPages.value }, { immediate: true })
async function create() {
  error.value = ''
  if (!form.title.trim() || !form.problem.trim()) {
    error.value = '已有课题路径需要填写项目题目和研究问题；还没有课题可以使用下方 AI 引导。'
    return
  }
  saving.value = true
  try {
    const project = await student.createProject({ ...form })
    open.value = false
    Object.assign(form, { title: '', problem: '', plan: '', project_type: 'research' })
    createdProjectId.value = project.id
    feedback.value = makeFeedback('success', '项目已创建。', `“${project.title}”已进入本校项目池，教师认领后会生成研究任务。`, '查看项目')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '项目没有创建成功，已保留当前填写内容，可以重试。', '重试')
  } finally { saving.value = false }
}

async function openBrainstorm() {
  open.value = false
  error.value = ''
  await router.push({ path: '/student/ai', query: { mode: 'opening', agent: 'proposal-topic' } })
}
function setPage(nextPage: number) {
  page.value = Math.min(Math.max(nextPage, 1), totalPages.value)
}

function openCreatedProject() {
  if (createdProjectId.value) void router.push(studentProjectRoute(createdProjectId.value))
}
function handleFeedbackAction() {
  if (feedback.value?.actionLabel === '查看项目') openCreatedProject()
  else void load().catch(() => undefined)
}

async function handlePrimary(project: Project) { try { await student.setPrimary(project.id) } catch (reason) { error.value = errorMessage(reason) } }
async function handleArchive(project: Project) {
  if (!confirm(`确定将项目《${project.title}》归档？仅已完成的项目可以归档。`)) return
  try { await student.archive(project.id) } catch (reason) { error.value = errorMessage(reason) }
}
async function handleUnarchive(project: Project) { try { await student.unarchive(project.id) } catch (reason) { error.value = errorMessage(reason) } }
async function handleTrash(project: Project) {
  if (!confirm(`确定将项目《${project.title}》移入回收站？30 天后自动删除。`)) return
  try { await student.trash(project.id) } catch (reason) { error.value = errorMessage(reason) }
}
async function handleRestore(project: Project) { try { await student.restore(project.id) } catch (reason) { error.value = errorMessage(reason) } }
</script>

<template>
  <div class="page student-projects-page">
    <PageHeader eyebrow="项目" title="我的项目" description="查看项目进度，进入研究进程，管理已归档和回收站项目。">
      <template #actions>
        <button class="primary-button" type="button" :disabled="!auth.user.value?.authorized || saving" @click="open = true">
          <el-icon><Plus /></el-icon> 新建项目
        </button>
      </template>
    </PageHeader>

    <FeedbackBanner v-model="feedback" @action="handleFeedbackAction" />

    <div v-if="!auth.user.value?.authorized" class="read-only-banner">
      学校授权当前为只读：可以浏览历史项目，但不能新建或提交材料。
    </div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-if="listLoading" class="loading-state" role="status">正在读取项目书架…</p>
    <p v-if="focus" class="project-focus-note">{{ focusMessage }}</p>

    <nav class="project-lifecycle-tabs" role="tablist" aria-label="项目生命周期">
      <RouterLink :to="studentProjectsPath()" :class="{ 'is-active': !$route.query.tab || $route.query.tab === 'active' }" :aria-selected="!$route.query.tab || $route.query.tab === 'active'" aria-controls="student-project-list" role="tab">进行中 <span>{{ tabCounts.active }}</span></RouterLink>
      <RouterLink to="/student/projects?tab=archived" :class="{ 'is-active': $route.query.tab === 'archived' }" :aria-selected="$route.query.tab === 'archived'" aria-controls="student-project-list" role="tab">已归档 <span>{{ tabCounts.archived }}</span></RouterLink>
      <RouterLink to="/student/projects?tab=trashed" :class="{ 'is-active': $route.query.tab === 'trashed' }" :aria-selected="$route.query.tab === 'trashed'" aria-controls="student-project-list" role="tab">回收站 <span>{{ tabCounts.trashed }}</span></RouterLink>
    </nav>

    <div v-if="currentProjects.length || search" class="project-toolbar">
      <label class="project-search">
        <span class="sr-only">搜索项目</span>
        <input v-model="search" type="search" placeholder="搜索项目名称、研究问题或项目类型" />
      </label>
      <span class="project-result-count" aria-live="polite">
        <template v-if="featuredProject">其他项目 {{ pageStart }}–{{ pageEnd }} / 共 {{ shelfProjects.length }} 个</template>
        <template v-else>显示 {{ pageStart }}–{{ pageEnd }} / 共 {{ filteredProjects.length }} 个项目</template>
      </span>
    </div>

    <section id="student-project-list" class="student-projects-body" :class="{ 'student-projects-body--archive': $route.query.tab === 'archived', 'student-projects-body--trash': $route.query.tab === 'trashed' }">
      <EmptyState v-if="!currentProjects.length && !listLoading" :title="$route.query.tab === 'archived' ? '没有已归档的项目' : $route.query.tab === 'trashed' ? '回收站是空的' : '还没有进行中的项目'" :description="focus ? focusMessage : $route.query.tab === 'trashed' ? '删除的项目会在这里保留 30 天，逾期后会被自动清除。' : $route.query.tab === 'archived' ? '完成的项目可以归档保存，保持项目书架整洁。' : '已有课题可以直接创建；还没有课题可以在新建项目中选择 AI 开题引导。'" />
      <EmptyState v-else-if="!filteredProjects.length" title="没有匹配的项目" description="换一个关键词，或清空搜索后查看全部项目。"><button class="secondary-button" type="button" @click="search = ''">清空搜索</button></EmptyState>
      <template v-else>
        <article v-if="featuredProject" class="current-project-panel paper-card" aria-labelledby="current-project-title">
          <div class="current-project-panel__identity">
            <span class="current-project-panel__mark">{{ featuredProject.title.slice(0, 1) }}</span>
            <div>
              <p class="current-project-panel__eyebrow">当前项目 · {{ projectTypeLabel(featuredProject.project_type) }}</p>
              <h2 id="current-project-title">{{ featuredProject.title }}</h2>
              <StatusTag :status="featuredProject.status" />
            </div>
          </div>
          <div class="current-project-panel__content">
            <div class="current-project-panel__field">
              <span>研究问题</span>
              <p>{{ featuredProject.problem || '尚未填写研究问题，进入项目后可以继续完善。' }}</p>
            </div>
            <div class="current-project-panel__field">
              <span>初步方案</span>
              <p>{{ featuredProject.plan || '尚未补充初步方案，确认研究问题后再继续。' }}</p>
            </div>
          </div>
          <div class="current-project-panel__aside">
            <div class="current-project-panel__facts">
              <span><small>项目状态</small><strong>{{ lifecycleLabel() }}</strong></span>
              <span><small>成员</small><strong>{{ featuredProject.members.length }} 人</strong></span>
              <span><small>指导教师</small><strong>{{ featuredProject.primary_teacher_name || '待认领' }}</strong></span>
              <span><small>创建时间</small><strong>{{ lifecycleDate(featuredProject) }}</strong></span>
            </div>
            <footer class="current-project-panel__actions">
              <RouterLink class="primary-button" :to="studentProjectRoute(featuredProject.id)">{{ featuredProject.status === 'unclaimed' ? '继续编辑' : '继续研究' }} →</RouterLink>
              <ProjectLifecycleMenu :project="featuredProject" :authorized="auth.user.value?.authorized" student-mode @primary="handlePrimary(featuredProject)" @trash="handleTrash(featuredProject)" @archive="handleArchive(featuredProject)" />
            </footer>
          </div>
        </article>

        <section class="student-project-shelf" aria-labelledby="student-project-shelf-title">
          <header class="student-project-shelf__header">
            <div>
              <p class="eyebrow">项目管理</p>
              <h2 id="student-project-shelf-title">{{ featuredProject ? '其他项目' : '项目列表' }}</h2>
              <p>{{ featuredProject ? '管理其他研究方向，选择项目后继续推进。' : '按生命周期查看项目，进入项目后继续推进。' }}</p>
            </div>
            <span v-if="featuredProject" class="student-project-shelf__current-note">当前项目已置顶展示</span>
          </header>

          <div v-if="shelfProjects.length" class="student-project-grid">
            <article v-for="project in visibleProjects" :key="project.id" class="student-project-card" :class="{ 'student-project-card--unclaimed': project.status === 'unclaimed', 'student-project-card--archived': $route.query.tab === 'archived', 'student-project-card--trashed': $route.query.tab === 'trashed' }">
              <header class="student-project-card__header">
                <div class="student-project-card__identity">
                  <span class="student-project-card__mark">{{ project.title.slice(0, 1) }}</span>
                  <div>
                    <p class="student-project-card__eyebrow">{{ projectTypeLabel(project.project_type) }} · {{ lifecycleLabel() }}</p>
                    <h3>{{ project.title }}</h3>
                  </div>
                </div>
                <StatusTag :status="project.status" />
              </header>

              <div class="student-project-card__summary">
                <div>
                  <span>研究问题</span>
                  <p>{{ project.problem || '尚未填写研究问题' }}</p>
                </div>
                <div>
                  <span>初步方案</span>
                  <p>{{ project.plan || '尚未补充，进入项目后可以继续完善。' }}</p>
                </div>
              </div>

              <dl class="student-project-card__facts">
                <div><dt>成员</dt><dd>{{ project.members.length }} 人</dd></div>
                <div><dt>{{ lifecycleDateLabel() }}</dt><dd>{{ lifecycleDate(project) }}</dd></div>
                <div v-if="$route.query.tab === 'trashed'"><dt>自动删除</dt><dd>{{ project.days_until_purge ?? 30 }} 天</dd></div>
                <div v-else><dt>指导教师</dt><dd>{{ project.primary_teacher_name || '待认领' }}</dd></div>
              </dl>

              <footer class="student-project-card__actions">
                <RouterLink :class="$route.query.tab ? 'secondary-button' : 'primary-button'" :to="studentProjectRoute(project.id)">{{ $route.query.tab === 'archived' ? '查看存档' : $route.query.tab === 'trashed' ? '查看项目' : project.status === 'unclaimed' ? '继续编辑' : '进入项目' }} →</RouterLink>
                <ProjectLifecycleMenu v-if="!$route.query.tab" :project="project" :authorized="auth.user.value?.authorized" student-mode @primary="handlePrimary(project)" @trash="handleTrash(project)" @archive="handleArchive(project)" />
                <ProjectLifecycleMenu v-else-if="$route.query.tab === 'archived'" :project="project" :authorized="auth.user.value?.authorized" student-mode @unarchive="handleUnarchive(project)" @trash="handleTrash(project)" />
                <ProjectLifecycleMenu v-else :project="project" :authorized="auth.user.value?.authorized" student-mode @restore="handleRestore(project)" />
              </footer>
            </article>
          </div>
          <div v-else-if="featuredProject" class="student-project-shelf-empty">
            <strong>还没有其他项目</strong>
            <p>当前项目已置顶。你可以继续研究，或新建另一个项目。</p>
          </div>
        </section>
      </template>
    </section>

    <nav v-if="shelfProjects.length > PROJECTS_PAGE_SIZE" class="project-pagination" aria-label="项目列表分页">
      <button class="secondary-button" type="button" :disabled="page === 1" @click="setPage(page - 1)">上一页</button>
      <span aria-live="polite">第 {{ page }} / {{ totalPages }} 页</span>
      <button class="secondary-button" type="button" :disabled="page === totalPages" @click="setPage(page + 1)">下一页</button>
    </nav>

    <el-dialog v-model="open" title="新建项目" width="680px" class="paper-dialog">
      <form class="dialog-form" @submit.prevent="void create()">
        <div class="creation-dialog-intro">
          <p class="eyebrow">选择创建方式</p>
          <h3>你现在有研究方向了吗？</h3>
          <p>已有课题可以直接建项目；还在探索方向，可以让灵思 AI 先帮你整理问题。</p>
        </div>
        <div class="creation-choice-grid" role="tablist" aria-label="项目创建方式">
          <button class="creation-choice" :class="{ 'is-active': creationMode === 'direct' }" type="button" role="tab" :aria-selected="creationMode === 'direct'" @click="creationMode = 'direct'">
            <span class="creation-choice__number">01</span>
            <span><strong>已有课题</strong><small>填写题目和研究问题，立即进入研究进程。</small></span>
            <em>{{ creationMode === 'direct' ? '当前选择' : '直接创建' }}</em>
          </button>
          <button class="creation-choice creation-choice--ai" type="button" role="tab" aria-selected="false" @click="void openBrainstorm()">
            <span class="creation-choice__number">02</span>
            <span><strong>AI 开题</strong><small>从观察和兴趣开始，逐步形成可研究的问题。</small></span>
            <em>进入引导 →</em>
          </button>
        </div>
        <section v-if="creationMode === 'direct'" class="creation-form-panel">
          <div class="creation-form-panel__heading"><div><p class="eyebrow">直接创建</p><h4>把已知课题写进项目</h4></div><span>必填：题目、研究问题</span></div>
            <label>项目题目 <input v-model="form.title" placeholder="用清晰的对象与目标描述项目"></label>
            <label>项目类型
              <select v-model="form.project_type">
                <option value="research">研究型</option>
                <option value="invention">发明型</option>
                <option value="engineering">工程型</option>
              </select>
            </label>
            <label>研究问题 <textarea v-model="form.problem" rows="3" placeholder="例如：不同坡度会如何影响校园积水的持续时间？" /></label>
            <label>初步方案（可选） <textarea v-model="form.plan" rows="3" placeholder="准备如何观察、研究、制作或验证？" /></label>
        </section>
        <p v-if="error" class="form-error">{{ error }}</p>
        <div class="dialog-actions">
          <button class="secondary-button" type="button" @click="open = false">取消</button>
          <button class="primary-button" :disabled="saving" type="submit">{{ saving ? '正在创建…' : '创建项目' }}</button>
        </div>
      </form>
    </el-dialog>
  </div>
</template>

<style scoped>
.project-focus-note { margin: 0 0 16px; padding: 10px 14px; border: 1px solid var(--sage-line); border-radius: var(--radius-md); background: var(--sage-soft); color: var(--moss-dark); font-size: 12px; }
.read-only-banner {
  margin-bottom: 18px;
  padding: 10px 14px;
  border: 1px solid var(--amber-line);
  background: var(--amber-soft);
  border-radius: var(--radius-md);
  color: var(--clay-deep);
  font-size: 12.5px;
}
.form-error {
  color: var(--clay);
  font-size: 12.5px;
  margin: 0 0 12px;
}
.dialog-hint { margin: -4px 0 0; padding: 9px 11px; border-radius: 8px; background: var(--sage-soft); color: var(--moss-dark); font-size: 12px; line-height: 1.5; }
.project-lifecycle-tabs {
  display: flex;
  gap: 6px;
  margin: 4px 0 24px;
  border-bottom: 1px solid var(--line);
}
.project-lifecycle-tabs a {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
  position: relative;
}
.project-lifecycle-tabs a span {
  display: inline-grid;
  place-items: center;
  min-width: 22px;
  height: 20px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  background: var(--paper-soft);
  border: 1px solid var(--line);
  border-radius: 999px;
}
.project-lifecycle-tabs a.is-active {
  color: var(--moss-dark);
  font-weight: 700;
}
.project-lifecycle-tabs a.is-active::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: -1px;
  height: 2px;
  background: var(--moss);
}
.project-lifecycle-tabs a.is-active span {
  color: var(--moss-dark);
  background: var(--sage-soft);
  border-color: var(--sage-line);
}
.project-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin: -8px 0 16px;
}
.project-search {
  flex: 1 1 360px;
  max-width: 520px;
}
.project-search input {
  width: 100%;
  min-height: var(--control-height);
  padding: 9px 12px;
  border: 1px solid var(--line-dark);
  border-radius: var(--radius-sm);
  background: var(--paper);
  color: var(--ink);
  outline: none;
}
.project-search input:focus { border-color: var(--moss); box-shadow: 0 0 0 3px var(--color-focus-ring); }
.project-result-count { flex: 0 0 auto; color: var(--muted); font-size: 12px; }
.student-projects-body { min-width: 0; }
.current-project-panel {
  display: grid;
  grid-template-columns: minmax(295px, 1.15fr) minmax(285px, 1.1fr) minmax(205px, .85fr);
  gap: 20px;
  align-items: center;
  min-width: 0;
  margin: 2px 0 28px;
  padding: 28px;
  border-color: var(--sage-line);
  background: linear-gradient(112deg, var(--sage-soft) 0%, var(--paper) 74%);
  box-shadow: var(--shadow-soft);
}
.current-project-panel:hover { border-color: #aac9af; box-shadow: var(--shadow-hover); }
.current-project-panel__identity { display: flex; align-items: flex-start; gap: 15px; min-width: 0; }
.current-project-panel__mark { display: grid; width: 58px; height: 58px; flex: 0 0 58px; place-items: center; border-radius: 17px; color: #fff; background: var(--moss-dark); font: 700 24px/1 var(--sans); }
.current-project-panel__identity > div { display: grid; min-width: 0; gap: 9px; }
.current-project-panel__eyebrow { margin: 0; color: var(--moss); font-size: 11px; font-weight: 700; letter-spacing: .06em; }
.current-project-panel h2 { margin: 0; overflow-wrap: anywhere; color: var(--ink); font: 700 25px/1.3 var(--sans); text-wrap: balance; }
.current-project-panel__content { display: grid; gap: 15px; min-width: 0; }
.current-project-panel__field { min-width: 0; }
.current-project-panel__field + .current-project-panel__field { padding-top: 14px; border-top: 1px solid var(--line); }
.current-project-panel__field > span, .student-project-card__summary span { display: block; margin-bottom: 5px; color: var(--moss); font-size: 10px; font-weight: 700; letter-spacing: .06em; }
.current-project-panel__field p { display: -webkit-box; overflow: hidden; margin: 0; color: var(--ink-soft); font-size: 13px; line-height: 1.6; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
.current-project-panel__aside { display: grid; gap: 18px; min-width: 0; padding-left: 22px; border-left: 1px solid var(--sage-line); }
.current-project-panel__facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px 18px; min-width: 0; }
.current-project-panel__facts span { display: grid; gap: 5px; min-width: 0; }
.current-project-panel__facts small { color: var(--muted); font-size: 10px; }
.current-project-panel__facts strong { overflow: hidden; color: var(--ink); font-size: 12px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.current-project-panel__actions { display: grid; gap: 10px; min-width: 0; }
.current-project-panel__actions > * { justify-content: center; }
.student-project-shelf { min-width: 0; }
.student-project-shelf__header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 14px; }
.student-project-shelf__header h2 { margin: 3px 0 5px; font: 700 21px/1.35 var(--sans); }
.student-project-shelf__header p:not(.eyebrow) { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.student-project-shelf__current-note { flex: 0 0 auto; padding: 7px 10px; border: 1px solid var(--sage-line); border-radius: 999px; color: var(--moss-dark); background: var(--sage-soft); font-size: 11px; }
.student-project-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; min-width: 0; }
.student-project-card { display: grid; grid-template-rows: auto 1fr auto auto; min-width: 0; min-height: 300px; padding: 21px 22px 18px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-soft); transition: border-color var(--transition-fast), box-shadow var(--transition-fast), transform var(--transition-fast); }
.student-project-card:hover { border-color: var(--sage-line); box-shadow: var(--shadow-hover); transform: translateY(-1px); }
.student-project-card--unclaimed { border-color: var(--sage-line); background: linear-gradient(122deg, var(--paper) 0%, var(--sage-soft) 100%); }
.student-project-card--archived { background: var(--sage-soft); }
.student-project-card--trashed { border-color: var(--amber-line); background: var(--amber-soft); }
.student-project-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; min-width: 0; }
.student-project-card__identity { display: flex; align-items: flex-start; gap: 12px; min-width: 0; }
.student-project-card__mark { display: grid; width: 42px; height: 42px; flex: 0 0 42px; place-items: center; border-radius: 12px; color: #fff; background: var(--moss); font: 700 18px/1 var(--sans); }
.student-project-card--archived .student-project-card__mark { background: var(--sage); color: var(--moss-dark); }
.student-project-card--trashed .student-project-card__mark { background: var(--clay); }
.student-project-card__identity > div { display: grid; min-width: 0; gap: 7px; }
.student-project-card__eyebrow { margin: 0; color: var(--moss); font-size: 10px; font-weight: 700; letter-spacing: .04em; }
.student-project-card h3 { margin: 0; overflow-wrap: anywhere; color: var(--ink); font: 700 18px/1.35 var(--sans); }
.student-project-card__header .status-tag { flex: 0 0 auto; margin-top: 2px; }
.student-project-card__summary { display: grid; gap: 12px; min-width: 0; margin: 20px 0 16px; }
.student-project-card__summary > div { min-width: 0; }
.student-project-card__summary > div + div { padding-top: 12px; border-top: 1px solid var(--line); }
.student-project-card__summary p { display: -webkit-box; overflow: hidden; margin: 0; color: var(--muted); font-size: 12px; line-height: 1.55; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.student-project-card__facts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; min-width: 0; margin: 0; padding: 13px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.student-project-card__facts div { display: grid; gap: 4px; min-width: 0; }
.student-project-card__facts dt { color: var(--muted-light); font-size: 10px; }
.student-project-card__facts dd { overflow: hidden; margin: 0; color: var(--ink); font-size: 11.5px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.student-project-card__actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; min-width: 0; padding-top: 15px; }
.student-project-card__actions > * { min-width: 0; }
.student-project-card__actions > .primary-button, .student-project-card__actions > .secondary-button { flex: 0 1 auto; }
.student-project-shelf-empty { padding: 28px; border: 1px dashed var(--sage-line); border-radius: var(--radius-md); background: var(--paper-soft); color: var(--ink); }
.student-project-shelf-empty strong { display: block; font: 700 15px var(--sans); }
.student-project-shelf-empty p { margin: 6px 0 0; color: var(--muted); font-size: 12px; }
.project-pagination { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 20px 0 4px; }
.project-pagination > span { min-width: 92px; color: var(--muted); font-size: 12px; text-align: center; }
.dialog-form { display: grid; gap: 14px; }
.creation-dialog-intro { display: grid; gap: 4px; padding-bottom: 2px; }
.creation-dialog-intro h3 { margin: 0; color: var(--ink); font: 700 19px/1.3 var(--sans); }
.creation-dialog-intro p:last-child { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.creation-choice-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.creation-choice { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 10px; align-items: start; min-width: 0; padding: 14px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper-soft); color: var(--ink); text-align: left; cursor: pointer; }
.creation-choice:hover, .creation-choice:focus-visible { border-color: var(--moss); }
.creation-choice.is-active { border-color: var(--moss); background: var(--sage-soft); box-shadow: 0 0 0 2px rgba(76,114,69,.08); }
.creation-choice--ai { border-color: var(--sage-line); }
.creation-choice__number { color: var(--moss); font: 700 11px var(--sans); }
.creation-choice > span:nth-child(2) { display: grid; gap: 4px; min-width: 0; }
.creation-choice strong { font-size: 13px; }
.creation-choice small { color: var(--muted); font-size: 11px; line-height: 1.45; }
.creation-choice em { color: var(--moss-dark); font-size: 10px; font-style: normal; white-space: nowrap; }
.creation-form-panel { display: grid; gap: 12px; padding: 16px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); }
.creation-form-panel__heading { display: flex; align-items: end; justify-content: space-between; gap: 12px; padding-bottom: 4px; border-bottom: 1px solid var(--line); }
.creation-form-panel__heading h4 { margin: 3px 0 0; font: 700 15px/1.3 var(--sans); }
.creation-form-panel__heading > span { color: var(--muted-light); font-size: 10px; }
.dialog-form label { display: grid; gap: 6px; color: var(--ink); font-size: 12.5px; font-weight: 600; }
.dialog-form input, .dialog-form select, .dialog-form textarea {
  padding: 9px 11px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  color: var(--ink);
  font-size: 13px;
}
.dialog-form input:focus, .dialog-form select:focus, .dialog-form textarea:focus {
  border-color: var(--moss);
  outline: none;
}
.dialog-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }
@media (max-width: 720px) {
  .current-project-panel { grid-template-columns: 1fr; gap: 18px; }
  .current-project-panel__aside { padding: 15px 0 0; border-top: 1px solid var(--sage-line); border-left: 0; }
  .current-project-panel__actions { display: flex; justify-content: flex-start; flex-wrap: wrap; }
  .student-project-grid { grid-template-columns: 1fr; }
  .student-project-card__actions { flex-wrap: wrap; justify-content: flex-start; }
  .project-toolbar { align-items: stretch; flex-direction: column; }
  .project-search { max-width: none; }
  .project-result-count { align-self: flex-start; }
  .creation-choice-grid { grid-template-columns: 1fr; }
  .creation-form-panel__heading { align-items: flex-start; flex-direction: column; }
}
</style>
