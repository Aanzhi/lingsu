<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, CircleCheck, Collection, MagicStick, User } from '@element-plus/icons-vue'
import { errorMessage } from '../../api'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import ProjectLifecycleMenu from '../../components/ProjectLifecycleMenu.vue'
import StatusTag from '../../components/StatusTag.vue'
import { auth } from '../../stores/auth'
import { teacherStore } from '../../stores/teacher'
import { reviewValidation, type ReviewDecision } from '../../stores/teacherApiModel'
import { attachmentSecurity } from '../../stores/attachmentModel'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { operationSuccess, reviewCompletionAction } from '../../stores/interactionModel'
import { selectReviewById } from '../../stores/reviewSelectionModel'
import { reviewPageState } from '../../stores/reviewPageState'

const route = useRoute(); const router = useRouter(); const surface = computed(() => String(route.meta.surface ?? 'home'))
const error = ref(''); const comment = ref(''); const busy = ref(false); const feedback = ref<FeedbackState | null>(null)
const attachmentState = attachmentSecurity
const selectedProject = computed(() => teacherStore.state.guided.find((item) => item.id === Number(route.params.id)) ?? teacherStore.state.guided[0])
const selectedRevision = computed(() => selectReviewById(teacherStore.state.reviews, Number(route.params.submissionId)))
const reviewState = computed(() => reviewPageState(selectedRevision.value))
const titles = computed<Record<string, [string, string, string]>>(() => ({ home: ['今日指导工作台', '把注意力放在需要判断的地方', '待审核、待认领与成员确认在同一张桌面上汇总。'], pool: ['本校项目池', '认领值得一起探索的问题', '学生创建的项目会在这里等待本校教师认领。'], projects: ['指导项目', '项目进度与风险', '查看团队、阶段和材料进度。'], project: ['指导项目', selectedProject.value?.title ?? '项目详情', '项目团队与真实成长数据。'], reviews: ['审核收件箱', '学生材料审核', '查看正文、附件和版本，给出清晰可执行的反馈。'], review: ['材料审核', selectedRevision.value?.material_title ?? '审核详情', '审核决定将同步到学生任务地图。'], members: ['团队管理', '成员邀请确认', '学生接受邀请后，经主指导教师确认才正式加入。'] }))
const heading = computed(() => titles.value[surface.value] ?? titles.value.home)
const activeTab = computed(() => {
  const tab = String(route.query.tab ?? 'guided')
  return (['guided', 'archived', 'trashed'] as const).includes(tab as any) ? (tab as 'guided' | 'archived' | 'trashed') : 'guided'
})
function navigateTab(tab: 'guided' | 'archived' | 'trashed') { router.push({ path: '/teacher/projects', query: tab === 'guided' ? {} : { tab } }) }
onMounted(async () => {
  try {
    await teacherStore.load()
    await Promise.all([teacherStore.loadArchived(), teacherStore.loadTrashed()])
  } catch (reason) { error.value = errorMessage(reason) }
})
async function claim(id: number) { busy.value = true; feedback.value = null; try { await teacherStore.claim(id); feedback.value = makeFeedback('success', operationSuccess('claim'), '学生会看到第一项可开始任务。') } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '项目没有被改变，可以稍后重试。', '重试') } finally { busy.value = false } }
async function review(decision: ReviewDecision) { if (!selectedRevision.value) return; error.value = reviewValidation(decision, comment.value) ?? ''; if (error.value) { feedback.value = makeFeedback('error', error.value, '请补充可执行意见后再提交。'); return } busy.value = true; feedback.value = null; try { await teacherStore.review(selectedRevision.value.id, decision, comment.value); comment.value = ''; feedback.value = makeFeedback('success', operationSuccess(decision === 'approved' ? 'review_approved' : 'review_returned'), '审核结果已同步给学生，队列也已更新。', reviewCompletionAction()) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '审核决定没有保存，可以重试。', '重试') } finally { busy.value = false } }
async function decide(id: number, approved: boolean) { busy.value = true; feedback.value = null; try { await teacherStore.decide(id, approved); feedback.value = makeFeedback('success', operationSuccess(approved ? 'member_approved' : 'member_rejected')) } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '成员状态没有改变，可以重试。', '重试') } finally { busy.value = false } }
async function handleFeedbackAction() { if (feedback.value?.actionLabel === reviewCompletionAction()) { feedback.value = null; await router.push('/teacher/reviews'); return } await teacherStore.load().catch((reason) => { feedback.value = makeFeedback('error', errorMessage(reason), '数据没有刷新成功，请重试。', '重试') }) }
async function handleArchive(id: number) { if (!confirm('确定归档该项目？仅已完成的项目可以归档。')) return; try { await teacherStore.archive(id) } catch (reason) { error.value = errorMessage(reason) } }
async function handleUnarchive(id: number) { try { await teacherStore.unarchive(id) } catch (reason) { error.value = errorMessage(reason) } }
async function handleTrash(id: number) { if (!confirm('确定将项目移入回收站？30 天后自动删除。')) return; try { await teacherStore.trash(id) } catch (reason) { error.value = errorMessage(reason) } }
async function handleRestore(id: number) { try { await teacherStore.restore(id) } catch (reason) { error.value = errorMessage(reason) } }
</script>
<template><div class="page teacher-page"><PageHeader :eyebrow="heading[0]" :title="heading[1]" :description="heading[2]"><template #actions><button v-if="surface === 'reviews' || surface === 'review'" class="secondary-button" type="button" @click="router.push('/teacher/ai')"><el-icon><MagicStick /></el-icon> 打开真实审核 AI</button></template></PageHeader><FeedbackBanner v-model="feedback" @action="handleFeedbackAction" /><p v-if="!auth.user.value?.authorized" class="read-only-banner">学校授权已停用或到期，当前只能浏览历史数据。</p><p v-if="error" class="form-error" role="alert">{{ error }}</p><template v-if="surface === 'home'"><div class="metric-grid teacher-metrics"><RouterLink to="/teacher/reviews" class="metric-card risk"><small>待审核材料</small><strong>{{ teacherStore.state.reviews.length }}</strong><span>需要处理</span><el-icon><ArrowRight /></el-icon></RouterLink><RouterLink to="/teacher/pool" class="metric-card"><small>待认领项目</small><strong>{{ teacherStore.state.pool.length }}</strong><span>来自本校学生</span><el-icon><ArrowRight /></el-icon></RouterLink><RouterLink to="/teacher/members" class="metric-card"><small>成员待确认</small><strong>{{ teacherStore.state.invitations.length }}</strong><span>确认后进入团队</span><el-icon><ArrowRight /></el-icon></RouterLink><RouterLink to="/teacher/projects" class="metric-card"><small>指导项目</small><strong>{{ teacherStore.state.guided.length }}</strong><span>{{ teacherStore.state.guided.filter((item) => item.status === 'active').length }} 个进行中</span><el-icon><ArrowRight /></el-icon></RouterLink><button class="metric-card metric-card--archived" type="button" @click="navigateTab('archived')"><small>已归档</small><strong>{{ teacherStore.state.archived.length }}</strong><span>已完成项目</span><el-icon><ArrowRight /></el-icon></button><button class="metric-card metric-card--trashed" type="button" @click="navigateTab('trashed')"><small>回收站</small><strong>{{ teacherStore.state.trashed.length }}</strong><span>30 天自动清除</span><el-icon><ArrowRight /></el-icon></button></div><section class="desk-panel"><div class="section-heading"><div><p class="eyebrow">优先处理</p><h2>审核收件箱</h2></div><RouterLink to="/teacher/reviews">查看全部 →</RouterLink></div><RouterLink v-for="revision in teacherStore.state.reviews.slice(0, 4)" :key="revision.id" :to="`/teacher/reviews/${revision.id}`" class="review-row"><span class="file-glyph">V</span><div><strong>{{ revision.material_title }}</strong><small>{{ revision.project_title }} · {{ revision.author_name }}</small></div><StatusTag :status="revision.status" /><span>开始审核 →</span></RouterLink><EmptyState v-if="!teacherStore.state.reviews.length" title="收件箱已清空" description="当前没有需要判断的提交；新的材料提交后会自动进入这里。"><RouterLink class="secondary-button" to="/teacher/projects">查看指导项目</RouterLink></EmptyState></section></template><template v-else-if="surface === 'pool'"><div class="pool-grid"><article v-for="project in teacherStore.state.pool" :key="project.id" class="pool-card paper-card"><header><StatusTag :status="project.status" /><span>{{ project.project_type }}</span></header><h2>{{ project.title }}</h2><p>{{ project.problem }}</p><div class="pool-plan"><small>初步方案</small><p>{{ project.plan }}</p></div><footer><span><el-icon><User /></el-icon>{{ project.members[0]?.username }}</span><button class="primary-button" type="button" :disabled="busy || !auth.user.value?.authorized" @click="claim(project.id)">认领并启动</button></footer></article><EmptyState v-if="!teacherStore.state.pool.length" title="当前没有待认领项目" description="学生新建项目后会自动出现在本校项目池。"><RouterLink class="secondary-button" to="/teacher/projects">查看指导项目</RouterLink></EmptyState></div></template><template v-else-if="surface === 'projects' || surface === 'project'">
  <nav v-if="surface === 'projects'" class="project-lifecycle-tabs" role="tablist">
    <a href="#" :class="{ 'is-active': activeTab === 'guided' }" role="tab" @click.prevent="navigateTab('guided')">指导中 <span>{{ teacherStore.state.guided.length }}</span></a>
    <a href="#" :class="{ 'is-active': activeTab === 'archived' }" role="tab" @click.prevent="navigateTab('archived')">已归档 <span>{{ teacherStore.state.archived.length }}</span></a>
    <a href="#" :class="{ 'is-active': activeTab === 'trashed' }" role="tab" @click.prevent="navigateTab('trashed')">回收站 <span>{{ teacherStore.state.trashed.length }}</span></a>
  </nav>

  <div v-if="surface === 'project' && selectedProject" class="guided-grid">
    <RouterLink :to="`/teacher/projects/${selectedProject.id}`" class="guided-card guided-card--detail">
      <div class="section-heading"><StatusTag :status="selectedProject.status" /><span>{{ selectedProject.project_type }}</span></div>
      <h2>{{ selectedProject.title }}</h2>
      <p>{{ selectedProject.problem }}</p>
      <div class="project-health"><div><small>成员</small><strong>{{ selectedProject.members.length }}</strong></div><div><small>成长值</small><strong>{{ selectedProject.growth.experience }} XP</strong></div><div><small>等级</small><strong>Lv.{{ selectedProject.growth.level }}</strong></div></div>
      <footer><span>{{ selectedProject.members.map((item) => item.username).join('、') }}</span><b>查看项目 →</b></footer>
    </RouterLink>
  </div>

  <div v-else-if="activeTab === 'guided'" class="guided-grid">
    <article v-for="project in teacherStore.state.guided" :key="project.id" class="guided-card">
      <RouterLink :to="`/teacher/projects/${project.id}`" class="guided-card-link">
        <div class="section-heading"><StatusTag :status="project.status" /><span>{{ project.project_type }}</span></div>
        <h2>{{ project.title }}</h2>
        <p>{{ project.problem }}</p>
        <div class="project-health"><div><small>成员</small><strong>{{ project.members.length }}</strong></div><div><small>成长值</small><strong>{{ project.growth.experience }} XP</strong></div><div><small>等级</small><strong>Lv.{{ project.growth.level }}</strong></div></div>
        <footer><span>{{ project.members.map((item) => item.username).join('、') }}</span><b>查看项目 →</b></footer>
      </RouterLink>
      <div class="guided-card__actions" @click.stop>
        <ProjectLifecycleMenu
          :project="project"
          :authorized="auth.user.value?.authorized"
          @archive="handleArchive(project.id)"
          @unarchive="handleUnarchive(project.id)"
          @trash="handleTrash(project.id)"
          @restore="handleRestore(project.id)"
        />
      </div>
    </article>
    <EmptyState v-if="!teacherStore.state.guided.length" title="还没有指导项目" description="认领学生项目后，可在这里跟进团队、任务和材料进度。"><RouterLink class="secondary-button" to="/teacher/pool">前往项目池</RouterLink></EmptyState>
  </div>

  <div v-else-if="activeTab === 'archived'" class="guided-grid">
    <article v-for="project in teacherStore.state.archived" :key="project.id" class="guided-card guided-card--archived">
      <RouterLink :to="`/teacher/projects/${project.id}`" class="guided-card-link">
        <div class="section-heading"><StatusTag :status="project.status" /><span class="status-tag success">已归档</span></div>
        <h2>{{ project.title }}</h2>
        <p>{{ project.problem }}</p>
        <div class="project-health"><div><small>成员</small><strong>{{ project.members.length }}</strong></div><div><small>归档于</small><strong>{{ project.archived_at?.slice(0, 10) ?? '--' }}</strong></div></div>
        <footer><span>{{ project.members.map((item) => item.username).join('、') }}</span></footer>
      </RouterLink>
      <div class="guided-card__actions" @click.stop>
        <ProjectLifecycleMenu
          :project="project"
          :authorized="auth.user.value?.authorized"
          @unarchive="handleUnarchive(project.id)"
          @trash="handleTrash(project.id)"
        />
      </div>
    </article>
    <EmptyState v-if="!teacherStore.state.archived.length" title="没有已归档的项目" description="完成的项目可以归档保存，保持项目书架整洁。" />
  </div>

  <div v-else-if="activeTab === 'trashed'" class="guided-grid">
    <article v-for="project in teacherStore.state.trashed" :key="project.id" class="guided-card guided-card--trashed">
      <div class="guided-card-link">
        <div class="section-heading"><StatusTag :status="project.status" /><span class="status-tag danger">回收站</span></div>
        <h2>{{ project.title }}</h2>
        <p>{{ project.problem }}</p>
        <div class="project-health"><div><small>成员</small><strong>{{ project.members.length }}</strong></div><div><small>剩余</small><strong>{{ project.days_until_purge ?? 30 }} 天</strong></div></div>
        <footer><span>移入回收站于 {{ project.trashed_at?.slice(0, 10) ?? '--' }}</span></footer>
      </div>
      <div class="guided-card__actions" @click.stop>
        <ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" @restore="handleRestore(project.id)" />
      </div>
    </article>
    <EmptyState v-if="!teacherStore.state.trashed.length" title="回收站是空的" description="删除的项目会在这里保留 30 天，逾期后会被自动清除。" />
  </div>
</template><template v-else-if="surface === 'reviews'"><section class="review-inbox"><div class="inbox-list"><RouterLink v-for="revision in teacherStore.state.reviews" :key="revision.id" :to="`/teacher/reviews/${revision.id}`" class="inbox-item"><span class="file-glyph">V</span><div><strong>{{ revision.material_title }}</strong><small>{{ revision.project_title }} · {{ revision.author_name }}</small></div><StatusTag :status="revision.status" /></RouterLink><EmptyState v-if="!teacherStore.state.reviews.length" title="没有待审核材料" description="学生提交后将保留版本、真实性确认与附件检查状态。" /></div><aside class="review-guide"><el-icon><Collection /></el-icon><h3>审核原则</h3><p>核对事实与证据。打回意见必须明确下一步动作。</p></aside></section></template><template v-else-if="surface === 'review' && reviewState === 'completed'"><section class="review-complete paper-card"><el-icon><CircleCheck /></el-icon><div><p class="eyebrow">审核已完成</p><h2>这份材料的审核结果已同步给学生</h2><p>待审核队列已更新。你可以返回队列继续处理，或查看指导项目的整体进度。</p></div><div><RouterLink class="primary-button" to="/teacher/reviews">返回审核队列</RouterLink><RouterLink class="secondary-button" to="/teacher/projects">查看指导项目</RouterLink></div></section></template><template v-else-if="surface === 'review' && selectedRevision"><div class="review-desk"><aside class="version-rail"><RouterLink to="/teacher/reviews">← 返回审核队列</RouterLink><p class="eyebrow">提交信息</p><strong>{{ selectedRevision.author_name }}</strong><small>{{ selectedRevision.created_at.slice(0, 16).replace('T', ' ') }}</small></aside><section class="submission-paper paper-card"><header><div><p class="eyebrow">学生提交</p><h2>{{ selectedRevision.material_title }}</h2></div><StatusTag :status="selectedRevision.status" /></header><article>{{ selectedRevision.content }}</article><div class="attachment-review"><strong>附件</strong><span v-for="file in selectedRevision.attachments" :key="file.id" class="attachment-security-row"><a v-if="attachmentState(file.scan_status).downloadable" :href="file.download_url">{{ file.original_name }}</a><span v-else>{{ file.original_name }}</span><b :class="attachmentState(file.scan_status).tone">{{ attachmentState(file.scan_status).label }}</b></span><small v-if="!selectedRevision.attachments.length">本版本没有附件</small></div><div class="truth-proof"><el-icon><CircleCheck /></el-icon><span><strong>学生已确认材料真实性</strong><small>{{ selectedRevision.truth_confirmed ? '已确认' : '未确认' }}</small></span></div></section><aside class="review-actions"><p class="eyebrow">审核决定</p><h2>给出下一步方向</h2><button class="secondary-button full" type="button" @click="router.push('/teacher/ai')"><el-icon><MagicStick /></el-icon> 前往真实 AI 风险检查</button><label>审核意见<textarea v-model="comment" rows="8" /></label><button class="approve-button full" :disabled="busy" type="button" @click="review('approved')">通过并解锁下一任务</button><button class="return-button full" :disabled="busy" type="button" @click="review('revision_required')">打回修订</button></aside></div></template><template v-else-if="surface === 'members'"><section class="member-queue paper-card"><div v-for="invite in teacherStore.state.invitations" :key="invite.id" class="member-approval"><span class="avatar soft">{{ invite.invitee_name.slice(0, 1) }}</span><div><strong>{{ invite.invitee_name }}</strong><small>申请加入：{{ invite.project_title }}</small></div><StatusTag status="waiting_teacher" /><button class="secondary-button" type="button" @click="decide(invite.id, false)">拒绝</button><button class="primary-button" type="button" @click="decide(invite.id, true)">确认加入</button></div><EmptyState v-if="!teacherStore.state.invitations.length" title="没有待确认成员" description="成员接受邀请后，会在此等待主指导教师确认。" /></section></template></div></template>

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
  cursor: pointer;
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

.guided-card {
  position: relative;
}
.guided-card-link {
  text-decoration: none;
  color: inherit;
  display: block;
}
.guided-card--archived { opacity: .9; }
.guided-card--trashed { opacity: .82; }
.guided-card--detail { grid-column: 1 / -1; }

.guided-card__actions {
  position: absolute;
  top: 14px;
  right: 14px;
  opacity: 0;
  transition: opacity .15s ease;
}
.guided-card:hover .guided-card__actions,
.guided-card:focus-within .guided-card__actions {
  opacity: 1;
}
.guided-card--trashed .guided-card__actions,
.guided-card--archived .guided-card__actions {
  opacity: 1;
}

.metric-card--archived {
  background: var(--sage-soft);
  border: 1px solid #c8d8c0;
}
.metric-card--archived small { color: var(--moss-dark); }
.metric-card--archived strong { color: var(--moss-dark); }

.metric-card--trashed {
  background: #f6eddc;
  border: 1px solid #ebddc1;
}
.metric-card--trashed small { color: #775f34; }
.metric-card--trashed strong { color: #5d4d2a; }
</style>
