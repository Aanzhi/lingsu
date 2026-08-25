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
const pageSize = 2
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
const totalPages = computed(() => Math.max(1, Math.ceil(filteredProjects.value.length / pageSize)))
const visibleProjects = computed(() => filteredProjects.value.slice((page.value - 1) * pageSize, page.value * pageSize))
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

async function load() {
  error.value = ''
  try {
    if (!student.loaded.value) await student.load()
    await Promise.all([student.loadArchived(), student.loadTrashed()])
    if (route.query.create === '1' && auth.user.value?.authorized) open.value = true
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
  if (value === '1' && auth.user.value?.authorized) open.value = true
})
watch([() => route.query.tab, search], () => { page.value = 1 })
watch(totalPages, (value) => { if (page.value > value) page.value = value })

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
  await router.push({ path: '/student/ai', query: { mode: 'brainstorm', agent: 'proposal-topic' } })
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
    <PageHeader eyebrow="项目" title="我的项目" description="查看项目进度，进入研究旅程，管理已归档和回收站项目。">
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
    <p v-if="student.loading.value" class="loading-state" role="status">正在读取项目书架…</p>
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
      <span class="project-result-count" aria-live="polite">显示 {{ visibleProjects.length }} / {{ filteredProjects.length }} 个项目</span>
    </div>

    <section id="student-project-list" v-if="!$route.query.tab || $route.query.tab === 'active'" class="paper-card demo-project-list">
      <article v-for="(project, index) in visibleProjects" :key="project.id" class="pilot-list-row">
        <div class="pilot-person">
          <span class="pilot-avatar" :class="{ 'demo-project-avatar--orange': index % 2 === 1 }">{{ project.title.slice(0, 1) }}</span>
          <div class="pilot-list-row__main">
            <div class="pilot-list-row__title">{{ project.title }}</div>
            <div class="pilot-list-row__meta">{{ projectTypeLabel(project.project_type) }} · {{ project.created_at.slice(0, 10) }} 创建</div>
          </div>
        </div>
        <div class="pilot-list-row__actions">
          <StatusTag :status="project.status" />
          <RouterLink class="text-link" :to="studentProjectRoute(project.id)">{{ project.status === 'unclaimed' ? '继续编辑 →' : '进入项目 →' }}</RouterLink>
        </div>
      </article>
      <EmptyState v-if="!activeProjects.length && !student.loading.value" title="还没有进行中的项目" :description="focus ? focusMessage : '已有课题可以直接创建；还没有课题可以在新建项目中选择 AI 开题引导。'" />
      <EmptyState v-else-if="!filteredProjects.length" title="没有匹配的项目" description="换一个关键词，或清空搜索后查看全部项目。">
        <button class="secondary-button" type="button" @click="search = ''">清空搜索</button>
      </EmptyState>
    </section>

    <section v-else-if="$route.query.tab === 'archived'" class="project-compact-list">
      <article
        v-for="project in visibleProjects"
        :key="project.id"
        class="project-book paper-card project-book--archived"
      >
        <div class="project-book__cover project-book__cover--muted">
          <span>{{ projectTypeLabel(project.project_type) }}</span>
          <b>{{ project.title.slice(0, 1) }}</b>
        </div>
        <div class="project-book__body">
          <div class="project-book__meta">
            <StatusTag :status="project.status" />
            <span class="status-tag success">已归档</span>
            <small>归档于 {{ project.archived_at?.slice(0, 10) ?? '--' }}</small>
          </div>
          <h2>{{ project.title }}</h2>
          <p>{{ project.problem || '尚未填写研究问题' }}</p>
          <footer>
            <span>{{ project.members.length }} 位成员</span>
            <RouterLink class="archive-link" :to="studentProjectRoute(project.id)">查看存档 →</RouterLink>
          </footer>
        </div>
        <div class="project-book__actions" @click.stop>
          <ProjectLifecycleMenu
            :project="project"
            :authorized="auth.user.value?.authorized"
            student-mode
            @unarchive="handleUnarchive(project)"
            @trash="handleTrash(project)"
          />
        </div>
      </article>
      <EmptyState v-if="!student.state.archivedProjects.length && !student.loading.value" title="没有已归档的项目" description="完成的项目可以归档保存，保持项目书架整洁。" />
      <EmptyState v-else-if="!filteredProjects.length" title="没有匹配的项目" description="换一个关键词，或清空搜索后查看全部项目。"><button class="secondary-button" type="button" @click="search = ''">清空搜索</button></EmptyState>
    </section>

    <section v-else-if="$route.query.tab === 'trashed'" class="project-compact-list">
      <article
        v-for="project in visibleProjects"
        :key="project.id"
        class="project-book paper-card project-book--trashed"
      >
        <div class="project-book__cover project-book__cover--muted">
          <span>{{ projectTypeLabel(project.project_type) }}</span>
          <b>{{ project.title.slice(0, 1) }}</b>
        </div>
        <div class="project-book__body">
          <div class="project-book__meta">
            <StatusTag :status="project.status" />
            <span class="status-tag danger">回收站</span>
            <small>剩余 {{ project.days_until_purge ?? 30 }} 天自动删除</small>
          </div>
          <h2>{{ project.title }}</h2>
          <p>{{ project.problem || '尚未填写研究问题' }}</p>
          <div class="project-book__progress project-book__progress--warning">
            <i :style="{ width: `${Math.min(100, ((project.days_until_purge ?? 30) / 30) * 100)}%` }" />
          </div>
          <footer>
            <span>移入回收站于 {{ project.trashed_at?.slice(0, 10) ?? '--' }}</span>
          </footer>
        </div>
        <div class="project-book__actions" @click.stop>
          <ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" student-mode @restore="handleRestore(project)" />
        </div>
      </article>
      <EmptyState v-if="!student.state.trashedProjects.length && !student.loading.value" title="回收站是空的" description="删除的项目会在这里保留 30 天，逾期后会被自动清除。" />
      <EmptyState v-else-if="!filteredProjects.length" title="没有匹配的项目" description="换一个关键词，或清空搜索后查看全部项目。"><button class="secondary-button" type="button" @click="search = ''">清空搜索</button></EmptyState>
    </section>

    <nav v-if="filteredProjects.length > pageSize" class="project-pagination" aria-label="项目分页">
      <button class="secondary-button" type="button" :disabled="page === 1" @click="page -= 1">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button class="secondary-button" type="button" :disabled="page === totalPages" @click="page += 1">下一页</button>
    </nav>

    <el-dialog v-model="open" title="新建项目" width="680px" class="paper-dialog">
      <form class="dialog-form" @submit.prevent="void create()">
        <div class="creation-paths">
          <section class="creation-path creation-path--direct">
            <div class="path-heading"><span class="path-kicker">路径一 · 已有课题</span><span class="path-badge">直接创建</span></div>
            <h3>已经知道要研究什么？</h3>
            <p>填写项目题目和研究问题，确认后立即进入项目概览。初步方案可以稍后补充。</p>
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
          <section class="creation-path creation-path--ai">
            <div class="path-heading"><span class="path-kicker">路径二 · 还没有课题</span><span class="path-badge path-badge--ai">AI 引导</span></div>
            <h3>从一个观察或兴趣开始</h3>
            <p>AI 会通过“现象 → 边界 → 候选问题”三步引导你头脑风暴。你确认项目草稿后，才会真正创建项目。</p>
            <ul><li>不需要先想好正式题目</li><li>一次生成 3 个可验证候选</li><li>标题、类型、问题和方案都能手动修改</li></ul>
            <button class="secondary-button creation-ai-button" type="button" :disabled="saving" @click="void openBrainstorm()">用 AI 一步步梳理研究课题 →</button>
          </section>
        </div>
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
.project-pagination { display: flex; align-items: center; justify-content: center; gap: 14px; margin: 20px 0 4px; color: var(--muted); font-size: 12px; }
.demo-project-list { padding: var(--space-6); }
.demo-project-avatar--orange { color: var(--clay); background: var(--clay-soft); }
.demo-project-section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--space-4); margin: var(--space-7) 0 var(--space-4); }
.demo-project-section-head h2 { margin: 0; color: var(--ink); font: 700 20px/1.25 var(--sans); letter-spacing: -.015em; }
.demo-project-section-head p { margin: 4px 0 0; color: var(--muted-light); font-size: 12px; }
.demo-project-create-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-4); }
.demo-project-create-card { min-height: 174px; padding: var(--space-6); }
.demo-project-create-card h3 { margin: 0 0 5px; color: var(--ink); font: 700 15px/1.25 var(--sans); }
.demo-project-create-card > p:not(.eyebrow) { min-height: 42px; margin: 0 0 18px; color: var(--muted); font-size: 13px; line-height: 1.6; }

.project-compact-list {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}

.project-book {
  position: relative;
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr) auto;
  min-height: 112px;
  overflow: hidden;
  transition: transform .18s ease, box-shadow .18s ease;
}
.project-book:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}
.project-book--archived { opacity: .88; }
.project-book--trashed { opacity: .82; }
.project-book--trashed .project-book__cover { background: var(--sage); }

.project-book__cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 14px 7px;
  background: var(--moss);
  color: #fff;
  text-align: center;
}
.project-book__cover--muted {
  background: var(--sage);
}
.project-book__cover span { display: block; font-size: 9px; letter-spacing: 0; opacity: .86; white-space: nowrap; }
.project-book__cover b { font: 700 22px/1 var(--sans); }

.project-book__body {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
  padding: 14px 16px;
}
.project-book__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.project-book__meta small { color: var(--muted); font-size: 11px; margin-left: auto; }
.project-book__body h2 {
  margin: 0;
  font: 700 17px/1.35 var(--sans);
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}
.project-book__body p {
  margin: 0;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.55;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}
.project-book__body footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
  color: var(--muted);
  margin-top: auto;
}
.archive-link {
  color: var(--moss-dark);
  font-weight: 600;
  font-size: 12px;
}
.archive-link:hover { color: var(--moss); }

.project-book__progress {
  height: 4px;
  background: rgba(76, 114, 69, .12);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 4px;
}
.project-book__progress i {
  display: block;
  height: 100%;
  background: var(--moss);
  border-radius: 999px;
  transition: width .3s ease;
}
.project-book__progress--warning i {
  background: var(--amber);
}

.project-book__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 42px;
  padding: 14px 14px 14px 0;
  opacity: 1;
  transition: opacity .15s ease;
}
.project-book--trashed .project-book__actions,
.project-book--archived .project-book__actions {
  opacity: 1;
}

.dialog-form { display: grid; gap: 14px; }
.creation-paths { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.creation-path { display: grid; align-content: start; gap: 9px; padding: 14px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper-soft); }
.creation-path--direct { border-color: var(--line-dark); background: var(--paper); }
.creation-path--ai { background: var(--sage-soft); border-color: var(--sage-line); }
.path-heading { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.path-kicker { color: var(--moss-dark); font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.path-badge { padding: 3px 7px; border-radius: 999px; background: var(--paper-soft); color: var(--muted); font-size: 10px; white-space: nowrap; }
.path-badge--ai { background: var(--paper); color: var(--moss-dark); }
.creation-path h3 { margin: 0; color: var(--ink); font: 700 16px/1.3 var(--sans); }
.creation-path p { margin: 0; color: var(--muted); font-size: 11.5px; line-height: 1.55; }
.creation-path label { display: grid; gap: 5px; color: var(--ink); font-size: 12px; font-weight: 600; }
.creation-path input, .creation-path select, .creation-path textarea { width: 100%; box-sizing: border-box; padding: 9px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--paper); color: var(--ink); font-size: 12.5px; }
.creation-path input:focus, .creation-path select:focus, .creation-path textarea:focus { border-color: var(--moss); outline: 2px solid var(--color-focus-ring); }
.creation-path ul { display: grid; gap: 5px; margin: 0; padding-left: 18px; color: var(--moss-dark); font-size: 11.5px; line-height: 1.45; }
.creation-ai-button { justify-self: start; margin-top: 2px; }
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
  .project-toolbar { align-items: stretch; flex-direction: column; }
  .project-search { max-width: none; }
  .project-result-count { align-self: flex-start; }
  .project-book { grid-template-columns: 52px minmax(0, 1fr) 38px; }
  .project-book__body { padding: 13px 12px; }
  .project-book__body footer { align-items: flex-start; flex-direction: column; gap: 3px; }
  .project-book__meta small { width: 100%; margin-left: 0; }
  .project-book__actions { padding-right: 10px; }
  .creation-paths { grid-template-columns: 1fr; }
  .creation-ai-button { width: 100%; justify-content: center; }
}
</style>
