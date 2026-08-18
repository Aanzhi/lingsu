<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { errorMessage, type Project } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import ProjectLifecycleMenu from '../../components/ProjectLifecycleMenu.vue'
import StatusTag from '../../components/StatusTag.vue'
import { auth } from '../../stores/auth'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { student } from '../../stores/student'

const open = ref(false)
const saving = ref(false)
const error = ref('')
const feedback = ref<FeedbackState | null>(null)
const createdProjectId = ref<number | null>(null)
const form = reactive({ title: '', problem: '', plan: '', project_type: 'research' as Project['project_type'] })
const typeLabel: Record<Project['project_type'], string> = { research: '研究型', invention: '发明型', engineering: '工程型' }

const activeProjects = computed(() => student.state.projects.filter((p) => !p.is_archived && !p.deleted_at))
const tabCounts = computed(() => ({
  active: activeProjects.value.length,
  archived: student.state.archivedProjects.length,
  trashed: student.state.trashedProjects.length,
}))

onMounted(async () => {
  try {
    if (!student.loaded.value) await student.load()
    await Promise.all([student.loadArchived(), student.loadTrashed()])
  } catch (reason) { error.value = errorMessage(reason) }
})

async function create() {
  error.value = ''
  if (!form.title.trim() || !form.problem.trim() || !form.plan.trim()) {
    error.value = '请完整填写项目题目、问题与初步方案'
    return
  }
  saving.value = true
  try {
    const project = await student.createProject({ ...form })
    open.value = false
    Object.assign(form, { title: '', problem: '', plan: '', project_type: 'research' })
    createdProjectId.value = project.id
    feedback.value = makeFeedback('success', '项目草稿已创建。', `“${project.title}”已进入本校项目池，等待教师认领后生成任务地图。`, '查看项目')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '项目没有创建成功，已保留当前填写内容，可以重试。', '重试')
  } finally { saving.value = false }
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
    <PageHeader eyebrow="我的研究" title="项目书架" description="创建项目后会进入本校项目池，由教师认领并启动真实任务链。">
      <template #actions>
        <button class="primary-button" type="button" :disabled="!auth.user.value?.authorized || saving" @click="open = true">
          <el-icon><Plus /></el-icon> 新建项目
        </button>
      </template>
    </PageHeader>

    <FeedbackBanner v-model="feedback" />

    <div v-if="!auth.user.value?.authorized" class="read-only-banner">
      学校授权当前为只读：可以浏览历史项目，但不能新建或提交材料。
    </div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>

    <nav class="project-lifecycle-tabs" role="tablist">
      <RouterLink to="/student/projects" :class="{ 'is-active': !$route.query.tab || $route.query.tab === 'active' }" role="tab">进行中 <span>{{ tabCounts.active }}</span></RouterLink>
      <RouterLink to="/student/projects?tab=archived" :class="{ 'is-active': $route.query.tab === 'archived' }" role="tab">已归档 <span>{{ tabCounts.archived }}</span></RouterLink>
      <RouterLink to="/student/projects?tab=trashed" :class="{ 'is-active': $route.query.tab === 'trashed' }" role="tab">回收站 <span>{{ tabCounts.trashed }}</span></RouterLink>
    </nav>

    <section v-if="!$route.query.tab || $route.query.tab === 'active'" class="project-grid">
      <RouterLink
        v-for="project in activeProjects"
        :key="project.id"
        class="project-book paper-card"
        :to="`/student/projects/${project.id}`"
      >
        <div class="project-book__cover">
          <span>{{ typeLabel[project.project_type] }}</span>
          <b>{{ project.title.slice(0, 1) }}</b>
        </div>
        <div class="project-book__body">
          <div class="project-book__meta">
            <StatusTag :status="project.status" />
            <span v-if="project.is_primary" class="status-tag current">主项目</span>
            <small>创建于 {{ project.created_at.slice(0, 10) }}</small>
          </div>
          <h2>{{ project.title }}</h2>
          <p>{{ project.problem }}</p>
          <div class="project-book__progress"><i :style="{ width: `${Math.min(100, project.growth.experience / 7)}%` }" /></div>
          <footer>
            <span>Lv.{{ project.growth.level }} · {{ project.growth.title }}</span>
            <b>{{ project.members.length }} 位成员</b>
          </footer>
        </div>
        <div class="project-book__actions" @click.stop>
          <ProjectLifecycleMenu
            :project="project"
            :authorized="auth.user.value?.authorized"
            student-mode
            @primary="handlePrimary(project)"
            @archive="handleArchive(project)"
            @unarchive="handleUnarchive(project)"
            @trash="handleTrash(project)"
            @restore="handleRestore(project)"
          />
        </div>
      </RouterLink>
      <EmptyState v-if="!activeProjects.length && !student.loading.value" title="还没有进行中的项目" description="从一个真实、具体、值得研究的问题开始。">
        <button class="primary-button" type="button" :disabled="!auth.user.value?.authorized" @click="open = true">新建第一个项目</button>
      </EmptyState>
    </section>

    <section v-else-if="$route.query.tab === 'archived'" class="project-grid">
      <article
        v-for="project in student.state.archivedProjects"
        :key="project.id"
        class="project-book paper-card project-book--archived"
      >
        <div class="project-book__cover project-book__cover--muted">
          <span>{{ typeLabel[project.project_type] }}</span>
          <b>{{ project.title.slice(0, 1) }}</b>
        </div>
        <div class="project-book__body">
          <div class="project-book__meta">
            <StatusTag :status="project.status" />
            <span class="status-tag success">已归档</span>
            <small>归档于 {{ project.archived_at?.slice(0, 10) ?? '--' }}</small>
          </div>
          <h2>{{ project.title }}</h2>
          <p>{{ project.problem }}</p>
          <footer>
            <span>{{ project.members.length }} 位成员</span>
            <RouterLink class="archive-link" :to="`/student/projects/${project.id}`">查看存档 →</RouterLink>
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
    </section>

    <section v-else-if="$route.query.tab === 'trashed'" class="project-grid">
      <article
        v-for="project in student.state.trashedProjects"
        :key="project.id"
        class="project-book paper-card project-book--trashed"
      >
        <div class="project-book__cover project-book__cover--muted">
          <span>{{ typeLabel[project.project_type] }}</span>
          <b>{{ project.title.slice(0, 1) }}</b>
        </div>
        <div class="project-book__body">
          <div class="project-book__meta">
            <StatusTag :status="project.status" />
            <span class="status-tag danger">回收站</span>
            <small>剩余 {{ project.days_until_purge ?? 30 }} 天自动删除</small>
          </div>
          <h2>{{ project.title }}</h2>
          <p>{{ project.problem }}</p>
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
    </section>

    <el-dialog v-model="open" title="新建项目" width="620px" class="paper-dialog">
      <form class="dialog-form" @submit.prevent="create">
        <label>项目题目 <input v-model="form.title" placeholder="用清晰的对象与目标描述项目"></label>
        <label>项目类型
          <select v-model="form.project_type">
            <option value="research">研究型</option>
            <option value="invention">发明型</option>
            <option value="engineering">工程型</option>
          </select>
        </label>
        <label>想解决的问题 <textarea v-model="form.problem" rows="3" placeholder="真实场景中发生了什么？为什么值得解决？" /></label>
        <label>初步方案 <textarea v-model="form.plan" rows="3" placeholder="准备如何观察、研究、制作或验证？" /></label>
        <p v-if="error" class="form-error">{{ error }}</p>
        <div class="dialog-actions">
          <button class="secondary-button" type="button" @click="open = false">取消</button>
          <button class="primary-button" :disabled="saving" type="submit">{{ saving ? '正在创建…' : '创建并等待认领' }}</button>
        </div>
      </form>
    </el-dialog>
  </div>
</template>

<style scoped>
.read-only-banner {
  margin-bottom: 18px;
  padding: 10px 14px;
  border: 1px solid #ebddc1;
  background: #f6eddc;
  border-radius: var(--radius-md);
  color: #775f34;
  font-size: 12.5px;
}
.form-error {
  color: var(--clay);
  font-size: 12.5px;
  margin: 0 0 12px;
}
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
  border-color: #c8d8c0;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 18px;
}

.project-book {
  position: relative;
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  overflow: hidden;
  transition: transform .18s ease, box-shadow .18s ease;
}
.project-book:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}
.project-book--archived { opacity: .88; }
.project-book--trashed { opacity: .82; }
.project-book--trashed .project-book__cover { background: linear-gradient(160deg, #a8b6a0, #6e8270); }

.project-book__cover {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 22px 10px;
  background: linear-gradient(160deg, var(--moss), #6b9368);
  color: #fff;
  text-align: center;
}
.project-book__cover--muted {
  background: linear-gradient(160deg, var(--sage), var(--moss));
}
.project-book__cover span { font-size: 11px; letter-spacing: .08em; opacity: .9; }
.project-book__cover b { font: 700 30px/1 var(--serif); }

.project-book__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px 18px 16px;
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
  font: 700 17px/1.35 var(--serif);
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
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.project-book__body footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
  color: var(--muted);
  margin-top: 4px;
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
  background: linear-gradient(90deg, var(--moss), #6b9368);
  border-radius: 999px;
  transition: width .3s ease;
}
.project-book__progress--warning i {
  background: linear-gradient(90deg, var(--amber), #c08a4a);
}

.project-book__actions {
  position: absolute;
  top: 14px;
  right: 14px;
  opacity: 0;
  transition: opacity .15s ease;
}
.project-book:hover .project-book__actions,
.project-book:focus-within .project-book__actions {
  opacity: 1;
}
.project-book--trashed .project-book__actions,
.project-book--archived .project-book__actions {
  opacity: 1;
}

.dialog-form { display: grid; gap: 14px; }
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
</style>
