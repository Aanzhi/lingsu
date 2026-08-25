<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowRight,
  CircleCheck,
  Collection,
  User,
} from "@element-plus/icons-vue";
import { errorMessage } from "../../api";
import EmptyState from "../../components/EmptyState.vue";
import FeedbackBanner from "../../components/FeedbackBanner.vue";
import MemberAssignDialog from "../../components/MemberAssignDialog.vue";
import PageHeader from "../../components/PageHeader.vue";
import ProjectLifecycleMenu from "../../components/ProjectLifecycleMenu.vue";
import StatusTag from "../../components/StatusTag.vue";
import TeacherAIPreReview from "../../components/TeacherAIPreReview.vue";
import { auth } from "../../stores/auth";
import { teacherStore } from "../../stores/teacher";
import {
  reviewAIProvenance,
  reviewValidation,
  type ReviewDecision,
} from "../../stores/teacherApiModel";
import { teacherProjectListMeta } from "../../stores/teacherProjectModel";
import { reviewActions } from "../../stores/managementPortalModel";
import { projectTypeLabel } from "../../stores/presentationModel";
import { attachmentSecurity } from "../../stores/attachmentModel";
import { makeFeedback, type FeedbackState } from "../../stores/feedbackModel";
import {
  operationSuccess,
  reviewCompletionAction,
} from "../../stores/interactionModel";
import { selectReviewById } from "../../stores/reviewSelectionModel";
import { reviewPageState } from "../../stores/reviewPageState";
import { teacherReviewRoute } from "../../stores/pageContracts";

const route = useRoute();
const router = useRouter();
const surface = computed(() => String(route.meta.surface ?? "home"));
const error = ref("");
const comment = ref("");
const busy = ref(false);
const completedReview = ref(false);
const feedback = ref<FeedbackState | null>(null);
const poolPage = ref(1);
const poolPageSize = 3;
const poolSearch = ref("");
const poolType = ref<"all" | "research" | "invention" | "engineering">("all");
const poolSort = ref<"recent" | "attention">("recent");
const filteredPool = computed(() => {
  const keyword = poolSearch.value.trim().toLowerCase();
  return [...teacherStore.state.pool]
    .filter((project) => {
      if (poolType.value !== "all" && project.project_type !== poolType.value) return false;
      if (!keyword) return true;
      return `${project.title} ${project.problem}`.toLowerCase().includes(keyword);
    })
    .sort((left, right) => {
      if (poolSort.value === "attention") return left.members.length - right.members.length || right.created_at.localeCompare(left.created_at);
      return right.created_at.localeCompare(left.created_at);
    });
});
const poolTotalPages = computed(() => Math.max(1, Math.ceil(filteredPool.value.length / poolPageSize)));
const visiblePool = computed(() => filteredPool.value.slice((poolPage.value - 1) * poolPageSize, poolPage.value * poolPageSize));
const teacherProjectPage = ref(1);
const teacherProjectPageSize = 3;
const teacherProjectSearch = ref("");
const memberProjectId = ref<number | null>(null);
const memberAssignOpen = ref(false);
const attachmentState = attachmentSecurity;
const selectedRevision = computed(() =>
  selectReviewById(
    teacherStore.state.reviews,
    Number(route.params.submissionId),
  ),
);
const reviewState = computed(() => reviewPageState(selectedRevision.value, completedReview.value));
const canReviewSelectedRevision = computed(() => {
  if (!selectedRevision.value || !auth.user.value?.id) return false;
  const primaryTeacherId = selectedRevision.value.primary_teacher_id === undefined ? auth.user.value.id : selectedRevision.value.primary_teacher_id;
  return reviewActions({ primaryTeacherId, currentTeacherId: auth.user.value.id }).length > 0;
});
const aiProvenance = computed(() =>
  selectedRevision.value ? reviewAIProvenance(selectedRevision.value) : null,
);
const titles = computed<Record<string, [string, string, string]>>(() => ({
  home: [
    "工作台",
    "指导工作台",
    "查看本校项目、待审核材料和成员事项，优先处理需要你决定的记录。",
  ],
  pool: [
    "项目池",
    "项目池",
    "浏览本校尚未认领的项目，确认研究方向后认领为指导项目。",
  ],
  projects: ["指导项目", "指导项目", "查看已认领、已归档和回收站项目，进入详情继续指导。"],
  reviews: [
    "材料审核",
    "学生材料审核",
    "按提交顺序处理负责项目的材料，给出通过或明确的修改建议。",
  ],
  review: [
    "材料审核",
    selectedRevision.value?.material_title ?? "审核详情",
    "核对正文、附件和真实性确认后，提交审核决定。",
  ],
  members: [
    "成员",
    "成员与邀请",
    "确认成员加入申请，并从具体指导项目发出成员邀请。",
  ],
}));
const heading = computed(
  () => titles.value[surface.value] ?? titles.value.home,
);
const activeTab = computed(() => {
  const tab = String(route.query.tab ?? "guided");
  return (["guided", "archived", "trashed"] as const).includes(tab as any)
    ? (tab as "guided" | "archived" | "trashed")
    : "guided";
});
const currentTeacherProjects = computed(() => activeTab.value === "archived"
  ? teacherStore.state.archived
  : activeTab.value === "trashed"
    ? teacherStore.state.trashed
    : teacherStore.state.guided);
const filteredTeacherProjects = computed(() => {
  const keyword = teacherProjectSearch.value.trim().toLowerCase();
  if (!keyword) return currentTeacherProjects.value;
  return currentTeacherProjects.value.filter((project) => `${project.title} ${project.problem}`.toLowerCase().includes(keyword));
});
const teacherProjectTotalPages = computed(() => Math.max(1, Math.ceil(filteredTeacherProjects.value.length / teacherProjectPageSize)));
const visibleTeacherProjects = computed(() => filteredTeacherProjects.value.slice((teacherProjectPage.value - 1) * teacherProjectPageSize, teacherProjectPage.value * teacherProjectPageSize));
const memberProject = computed(() => teacherStore.state.guided.find((project) => project.id === memberProjectId.value) ?? null);
const reviewContextProject = computed(() => {
  const projectId = Number(route.query.projectId);
  if (!Number.isFinite(projectId) || projectId <= 0) return null;
  return [...teacherStore.state.guided, ...teacherStore.state.archived, ...teacherStore.state.trashed].find((project) => project.id === projectId) ?? null;
});
const visibleReviews = computed(() => reviewContextProject.value
  ? teacherStore.state.reviews.filter((reviewItem) => reviewItem.project_title === reviewContextProject.value?.title)
  : teacherStore.state.reviews);
watch([surface, () => route.params.submissionId], () => {
  comment.value = "";
  error.value = "";
  feedback.value = null;
  completedReview.value = false;
  poolPage.value = 1;
  teacherProjectPage.value = 1;
  poolSearch.value = "";
  poolType.value = "all";
  poolSort.value = "recent";
  teacherProjectSearch.value = "";
});
watch(activeTab, () => { teacherProjectPage.value = 1; });
watch(poolTotalPages, (value) => { if (poolPage.value > value) poolPage.value = value; });
watch(teacherProjectTotalPages, (value) => { if (teacherProjectPage.value > value) teacherProjectPage.value = value; });
watch(() => route.query.projectId, () => {
  const requested = Number(route.query.projectId);
  if (Number.isFinite(requested) && requested > 0) memberProjectId.value = requested;
});
function navigateTab(tab: "guided" | "archived" | "trashed") {
  router.push({
    path: "/teacher/projects",
    query: tab === "guided" ? {} : { tab },
  });
}
async function handleMemberAssigned() {
  memberAssignOpen.value = false;
  await load();
  feedback.value = makeFeedback("success", "已将该同学加入项目。", "对方无需再次确认，立即成为正式成员。");
}
async function load() {
  error.value = "";
  try {
    await teacherStore.load();
    await Promise.all([
      teacherStore.loadArchived(),
      teacherStore.loadTrashed(),
    ]);
    const requestedProjectId = Number(route.query.projectId);
    memberProjectId.value = teacherStore.state.guided.some((project) => project.id === requestedProjectId)
      ? requestedProjectId
      : memberProjectId.value && teacherStore.state.guided.some((project) => project.id === memberProjectId.value)
        ? memberProjectId.value
        : teacherStore.state.guided[0]?.id ?? null;
  } catch (reason) {
    error.value = errorMessage(reason);
    feedback.value = makeFeedback("error", error.value, "指导工作台没有加载完成，可以重试。", "重试");
    throw reason;
  }
}
onMounted(() => { void load().catch(() => undefined); });
async function claim(id: number) {
  busy.value = true;
  feedback.value = null;
  try {
    await teacherStore.claim(id);
    feedback.value = makeFeedback(
      "success",
      operationSuccess("claim"),
      "学生会看到第一项可开始任务。",
    );
  } catch (reason) {
    feedback.value = makeFeedback(
      "error",
      errorMessage(reason),
      "项目没有被改变，可以稍后重试。",
      "重试",
    );
  } finally {
    busy.value = false;
  }
}
async function review(decision: ReviewDecision) {
  if (!selectedRevision.value) return;
  if (!canReviewSelectedRevision.value) {
    feedback.value = makeFeedback("error", "这份材料不属于你负责的项目。", "只有项目指导教师可以提交审核决定。", "返回审核队列");
    return;
  }
  error.value = reviewValidation(decision, comment.value) ?? "";
  if (error.value) {
    feedback.value = makeFeedback(
      "error",
      error.value,
      "请补充可执行意见后再提交。",
    );
    return;
  }
  busy.value = true;
  feedback.value = null;
  try {
    await teacherStore.review(
      selectedRevision.value.id,
      decision,
      comment.value,
    );
    comment.value = "";
    completedReview.value = true;
    feedback.value = makeFeedback(
      "success",
      operationSuccess(
        decision === "approved" ? "review_approved" : "review_returned",
      ),
      "审核结果已同步给学生，队列也已更新。",
      reviewCompletionAction(),
    );
  } catch (reason) {
    feedback.value = makeFeedback(
      "error",
      errorMessage(reason),
      "审核决定没有保存，可以重试。",
      "重试",
    );
  } finally {
    busy.value = false;
  }
}
async function decide(id: number, approved: boolean) {
  busy.value = true;
  feedback.value = null;
  try {
    await teacherStore.decide(id, approved);
    feedback.value = makeFeedback(
      "success",
      operationSuccess(approved ? "member_approved" : "member_rejected"),
    );
  } catch (reason) {
    feedback.value = makeFeedback(
      "error",
      errorMessage(reason),
      "成员状态没有改变，可以重试。",
      "重试",
    );
  } finally {
    busy.value = false;
  }
}
async function handleFeedbackAction() {
  if (feedback.value?.actionLabel === reviewCompletionAction()) {
    feedback.value = null;
    await router.push("/teacher/reviews");
    return;
  }
  await load().catch(() => undefined);
}
async function handleArchive(id: number) {
  if (!confirm("确定归档该项目？仅已完成的项目可以归档。")) return;
  try {
    await teacherStore.archive(id);
  } catch (reason) {
    error.value = errorMessage(reason);
  }
}
async function handleUnarchive(id: number) {
  try {
    await teacherStore.unarchive(id);
  } catch (reason) {
    error.value = errorMessage(reason);
  }
}
async function handleTrash(id: number) {
  if (!confirm("确定将项目移入回收站？30 天后自动删除。")) return;
  try {
    await teacherStore.trash(id);
  } catch (reason) {
    error.value = errorMessage(reason);
  }
}
async function handleRestore(id: number) {
  try {
    await teacherStore.restore(id);
  } catch (reason) {
    error.value = errorMessage(reason);
  }
}
</script>
<template>
  <div class="page teacher-page">
    <PageHeader
      :eyebrow="heading[0]"
      :title="heading[1]"
      :description="heading[2]"
    ><template #actions><RouterLink v-if="surface === 'home'" class="primary-button" to="/teacher/reviews">查看待审核材料</RouterLink><button v-else-if="surface === 'members' && memberProject" class="primary-button" type="button" @click="memberAssignOpen = true">邀请成员</button></template></PageHeader><FeedbackBanner v-model="feedback" @action="handleFeedbackAction" /><MemberAssignDialog v-if="surface === 'members' && memberAssignOpen && memberProject" :project-id="memberProject.id" :existing-member-ids="memberProject.members.map((member) => member.account)" @assigned="void handleMemberAssigned()" @close="memberAssignOpen = false" />
    <p v-if="!auth.user.value?.authorized" class="read-only-banner">
      学校授权已停用或到期，当前只能浏览历史数据。
    </p>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>
    <p v-if="teacherStore.loading.value" class="loading-state" role="status">正在读取指导数据…</p>
    <template v-if="surface === 'home'"
      ><div class="pilot-metric-grid">
        <RouterLink to="/teacher/pool" class="pilot-card pilot-metric"><div class="pilot-metric__label">待指导项目</div><div class="pilot-metric__value">{{ teacherStore.state.pool.length }}</div><div class="pilot-metric__foot">{{ Math.min(teacherStore.state.pool.length, 2) }} 个今天更新</div></RouterLink>
        <RouterLink to="/teacher/reviews" class="pilot-card pilot-metric"><div class="pilot-metric__label">待审核材料</div><div class="pilot-metric__value">{{ teacherStore.state.reviews.length }}</div><div class="pilot-metric__foot warn">{{ teacherStore.state.reviews.length ? '按提交时间排序' : '当前已清空' }}</div></RouterLink>
        <RouterLink to="/teacher/projects" class="pilot-card pilot-metric"><div class="pilot-metric__label">进行中项目</div><div class="pilot-metric__value">{{ teacherStore.state.guided.filter((item) => item.status === 'active').length }}</div><div class="pilot-metric__foot good">持续跟进研究进度</div></RouterLink>
        <RouterLink to="/teacher/members" class="pilot-card pilot-metric"><div class="pilot-metric__label">需要关注学生</div><div class="pilot-metric__value">{{ teacherStore.state.invitations.length }}</div><div class="pilot-metric__foot">成员确认与长期未更新</div></RouterLink>
      </div>
      <div class="pilot-section-head"><div><h2>最近需要处理</h2><p>按紧急程度排序</p></div></div>
      <section class="pilot-card pilot-list-card">
        <RouterLink
          v-for="revision in teacherStore.state.reviews.slice(0, 3)"
          :key="revision.id"
          :to="teacherReviewRoute(revision.id)"
          class="pilot-list-row"
          ><div class="pilot-person"><span class="pilot-avatar">{{ revision.project_title.slice(0, 1) }}</span><div class="pilot-list-row__main"><div class="pilot-list-row__title">{{ revision.project_title }}</div><div class="pilot-list-row__meta">{{ revision.author_name }} · {{ revision.material_title }}</div></div></div><div class="pilot-list-row__actions"><StatusTag :status="revision.status" /><span class="text-link">进入审核 →</span></div></RouterLink
        ><EmptyState v-if="!teacherStore.state.reviews.length" title="暂无待处理事项" description="新的材料提交、项目认领和成员邀请会在这里出现。"><RouterLink class="secondary-button" to="/teacher/pool">查看项目池</RouterLink></EmptyState>
      </section></template
    ><template v-else-if="surface === 'pool'"
      ><section class="pool-list-shell paper-card"><div class="pool-filter-bar filter-bar"><input v-model="poolSearch" class="input" placeholder="搜索项目名称或研究问题"><select v-model="poolType" class="select"><option value="all">全部类型</option><option value="research">研究型</option><option value="invention">发明型</option><option value="engineering">工程型</option></select><select v-model="poolSort" class="select"><option value="recent">最新创建</option><option value="attention">成员较少，优先关注</option></select></div><div class="pool-compact-list">
        <article
          v-for="project in visiblePool"
          :key="project.id"
          class="pool-card"
        >
          <div class="row-main"><div class="row-title">{{ project.title }}</div><div class="row-meta">{{ projectTypeLabel(project.project_type) }} · {{ project.members[0]?.username || '负责人待定' }} · {{ project.members.length || 1 }} 名成员</div></div>
          <div class="row-actions"><StatusTag :status="project.status" /><button
              class="primary-button"
              type="button"
              :disabled="busy || !auth.user.value?.authorized"
              @click="claim(project.id)"
            >
              查看并认领
            </button></div>
        </article>
        <EmptyState
          v-if="!filteredPool.length"
          :title="teacherStore.state.pool.length ? '没有匹配项目' : '当前没有待认领项目'"
          :description="teacherStore.state.pool.length ? '调整关键词或类型后继续查找。' : '学生新建项目后会自动出现在本校项目池。'"
          ><RouterLink class="secondary-button" to="/teacher/projects"
            >查看指导项目</RouterLink
          ></EmptyState
        >
      </div></section>
      <nav v-if="filteredPool.length > poolPageSize" class="pool-pagination" aria-label="项目池分页">
        <button class="secondary-button" type="button" :disabled="poolPage === 1" @click="poolPage -= 1">上一页</button>
        <span>第 {{ poolPage }} / {{ poolTotalPages }} 页</span>
        <button class="secondary-button" type="button" :disabled="poolPage === poolTotalPages" @click="poolPage += 1">下一页</button>
      </nav></template
    ><template v-else-if="surface === 'projects'">
      <nav class="project-lifecycle-tabs" role="tablist" aria-label="项目生命周期">
        <a href="#" :class="{ 'is-active': activeTab === 'guided' }" :aria-selected="activeTab === 'guided'" aria-controls="teacher-project-list" role="tab" @click.prevent="navigateTab('guided')">指导中 <span>{{ teacherStore.state.guided.length }}</span></a>
        <a href="#" :class="{ 'is-active': activeTab === 'archived' }" :aria-selected="activeTab === 'archived'" aria-controls="teacher-project-list" role="tab" @click.prevent="navigateTab('archived')">已归档 <span>{{ teacherStore.state.archived.length }}</span></a>
        <a href="#" :class="{ 'is-active': activeTab === 'trashed' }" :aria-selected="activeTab === 'trashed'" aria-controls="teacher-project-list" role="tab" @click.prevent="navigateTab('trashed')">回收站 <span>{{ teacherStore.state.trashed.length }}</span></a>
      </nav>

      <section v-if="activeTab === 'guided'" id="teacher-project-list" class="pilot-card card-pad"><div class="filter-bar"><input v-model="teacherProjectSearch" class="input" placeholder="搜索指导项目或研究问题"></div><div class="teacher-project-table table-wrap"><table><thead><tr><th>项目</th><th>负责人</th><th>成员</th><th>创建时间</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="project in visibleTeacherProjects" :key="project.id"><td><div class="row-title">{{ project.title }}</div><div class="row-meta">{{ teacherProjectListMeta(project).typeLabel }} · {{ teacherProjectListMeta(project).memberCount }} 名成员</div></td><td>{{ teacherProjectListMeta(project).leaderName }}</td><td>{{ teacherProjectListMeta(project).memberCount }} 人</td><td>{{ teacherProjectListMeta(project).createdDate }}</td><td><StatusTag :status="project.status" /></td><td><div class="teacher-project-actions"><ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" @archive="handleArchive(project.id)" @unarchive="handleUnarchive(project.id)" @trash="handleTrash(project.id)" @restore="handleRestore(project.id)" /><RouterLink class="secondary-button" :to="`/teacher/projects/${project.id}`">指导详情 →</RouterLink></div></td></tr></tbody></table></div>
        <EmptyState v-if="!filteredTeacherProjects.length" :title="teacherStore.state.guided.length ? '没有匹配的指导项目' : '还没有指导项目'" :description="teacherStore.state.guided.length ? '调整关键词后继续查找。' : '认领学生项目后，可在详情页跟进团队、任务和材料进度。'"><RouterLink v-if="!teacherStore.state.guided.length" class="secondary-button" to="/teacher/pool">前往项目池</RouterLink></EmptyState>
      </section>

      <div v-else-if="activeTab === 'archived'" id="teacher-project-list" class="guided-list">
        <article v-for="project in visibleTeacherProjects" :key="project.id" class="project-row project-row--archived">
          <div class="project-row__main"><div class="project-row__title"><h2>{{ project.title }}</h2><StatusTag :status="project.status" /><span class="status-tag success">已归档</span><span class="project-row__type">{{ teacherProjectListMeta(project).typeLabel }}</span></div><div class="project-row__meta"><span><small>负责人</small><strong>{{ teacherProjectListMeta(project).leaderName }}</strong></span><span><small>成员</small><strong>{{ teacherProjectListMeta(project).memberCount }} 人</strong></span><span><small>归档于</small><strong>{{ project.archived_at?.slice(0, 10) ?? teacherProjectListMeta(project).createdDate }}</strong></span></div></div>
          <div class="project-row__actions" @click.stop><ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" @unarchive="handleUnarchive(project.id)" @trash="handleTrash(project.id)" /></div>
          <RouterLink class="project-row__detail" :to="`/teacher/projects/${project.id}`">查看指导详情 <ArrowRight /></RouterLink>
        </article>
        <EmptyState v-if="!teacherStore.state.archived.length" title="没有已归档的项目" description="完成的项目可以归档保存，保持列表整洁。" />
      </div>

      <div v-else-if="activeTab === 'trashed'" id="teacher-project-list" class="guided-list">
        <article v-for="project in visibleTeacherProjects" :key="project.id" class="project-row project-row--trashed">
          <div class="project-row__main"><div class="project-row__title"><h2>{{ project.title }}</h2><StatusTag :status="project.status" /><span class="status-tag danger">回收站</span><span class="project-row__type">{{ teacherProjectListMeta(project).typeLabel }}</span></div><div class="project-row__meta"><span><small>负责人</small><strong>{{ teacherProjectListMeta(project).leaderName }}</strong></span><span><small>成员</small><strong>{{ teacherProjectListMeta(project).memberCount }} 人</strong></span><span><small>移入于</small><strong>{{ project.trashed_at?.slice(0, 10) ?? teacherProjectListMeta(project).createdDate }}</strong></span><span><small>自动清除</small><strong>{{ project.days_until_purge ?? 30 }} 天</strong></span></div></div>
          <div class="project-row__actions" @click.stop><ProjectLifecycleMenu :project="project" :authorized="auth.user.value?.authorized" @restore="handleRestore(project.id)" /></div>
          <RouterLink class="project-row__detail" :to="`/teacher/projects/${project.id}`">查看指导详情 <ArrowRight /></RouterLink>
        </article>
        <EmptyState v-if="!teacherStore.state.trashed.length" title="回收站是空的" description="删除的项目会在这里保留 30 天，逾期后会被自动清除。" />
      </div>
      <nav v-if="currentTeacherProjects.length > teacherProjectPageSize" class="teacher-project-pagination" aria-label="指导项目分页">
        <button class="secondary-button" type="button" :disabled="teacherProjectPage === 1" @click="teacherProjectPage -= 1">上一页</button>
        <span>第 {{ teacherProjectPage }} / {{ teacherProjectTotalPages }} 页</span>
        <button class="secondary-button" type="button" :disabled="teacherProjectPage === teacherProjectTotalPages" @click="teacherProjectPage += 1">下一页</button>
      </nav> </template
    ><template v-else-if="surface === 'reviews'"
      ><section class="review-inbox">
        <div class="inbox-list">
        <p v-if="reviewContextProject" class="review-context-note">当前项目：{{ reviewContextProject.title }} · 只显示该项目匹配的待审核材料</p>
        <RouterLink
          v-for="revision in visibleReviews"
            :key="revision.id"
            :to="teacherReviewRoute(revision.id)"
            class="inbox-item"
            ><span class="file-glyph">V</span>
            <div>
              <strong>{{ revision.material_title }}</strong
              ><small
                >{{ revision.project_title }} ·
                {{ revision.author_name }}</small
              >
            </div>
            <StatusTag :status="revision.status" /></RouterLink
          ><EmptyState
            v-if="!visibleReviews.length"
            :title="reviewContextProject ? '当前项目没有待审核材料' : '没有待审核材料'"
            :description="reviewContextProject ? '返回审核队列查看其他负责项目的提交。' : '学生提交后将保留版本、真实性确认与附件检查状态。'"
          />
        </div>
        <aside class="review-guide">
          <el-icon><Collection /></el-icon>
          <h3>审核原则</h3>
          <p>核对事实与证据。打回意见必须明确下一步动作。</p>
        </aside>
      </section></template
    ><template v-else-if="surface === 'review' && reviewState === 'completed'"
      ><section class="review-complete paper-card">
        <el-icon><CircleCheck /></el-icon>
        <div>
          <p class="eyebrow">审核已完成</p>
          <h2>这份材料的审核结果已同步给学生</h2>
          <p>
            待审核队列已更新。你可以返回队列继续处理，或查看指导项目的整体进度。
          </p>
        </div>
        <div>
          <RouterLink class="primary-button" to="/teacher/reviews"
            >返回审核队列</RouterLink
          ><RouterLink class="secondary-button" to="/teacher/projects"
            >查看指导项目</RouterLink
          >
        </div>
      </section></template
    ><template v-else-if="surface === 'review' && selectedRevision"
      ><div class="review-desk">
        <aside class="version-rail">
          <RouterLink to="/teacher/reviews">← 返回审核队列</RouterLink>
          <p class="eyebrow">提交信息</p>
          <strong>{{ selectedRevision.author_name }}</strong
          ><small>{{
            selectedRevision.created_at.slice(0, 16).replace("T", " ")
          }}</small>
        </aside>
        <section class="submission-paper paper-card">
          <header>
            <div>
              <p class="eyebrow">学生提交</p>
              <h2>{{ selectedRevision.material_title }}</h2>
            </div>
            <StatusTag :status="selectedRevision.status" />
          </header>
          <article>{{ selectedRevision.content }}</article>
          <section v-if="aiProvenance" class="ai-provenance">
            <strong>AI 草稿来源（仍需人工核验）</strong>
            <p>{{ aiProvenance.source }}</p>
            <small>智能体：{{ selectedRevision.source_summary?.agent_key || '通用助手' }} · {{ selectedRevision.source_summary?.paper_type || '课题申报' }} · {{ selectedRevision.source_summary?.created_at.slice(0, 16).replace('T', ' ') }}</small>
            <ul v-if="aiProvenance.items.length">
              <li v-for="check in aiProvenance.items" :key="check.item"><span>{{ check.item }}</span><small v-if="check.guidance">{{ check.guidance }}</small></li>
            </ul>
            <p v-else class="form-hint">生成记录未提供核验项，仍请核对事实、数据和引用来源。</p>
          </section>
          <div class="attachment-review">
            <strong>附件</strong
            ><span
              v-for="file in selectedRevision.attachments"
              :key="file.id"
              class="attachment-security-row"
              ><a
                v-if="attachmentState(file.scan_status).downloadable"
                :href="file.download_url"
                >{{ file.original_name }}</a
              ><span v-else>{{ file.original_name }}</span
              ><b :class="attachmentState(file.scan_status).tone">{{
                attachmentState(file.scan_status).label
              }}</b></span
            ><small v-if="!selectedRevision.attachments.length"
              >本版本没有附件</small
            >
          </div>
          <div class="truth-proof">
            <el-icon><CircleCheck /></el-icon
            ><span
              ><strong>学生已确认材料真实性</strong
              ><small>{{
                selectedRevision.truth_confirmed ? "已确认" : "未确认"
              }}</small></span
            >
          </div>
          <TeacherAIPreReview
            :material-id="selectedRevision.material"
            :material-title="selectedRevision.material_title"
            :material-content="selectedRevision.content"
            @use-draft="comment = $event"
          />
        </section>
        <aside class="review-actions">
          <p class="eyebrow">审核决定</p>
          <h2>给出下一步方向</h2>
          <template v-if="canReviewSelectedRevision">
          <label>审核意见<textarea v-model="comment" rows="8" /></label
          ><button
            class="approve-button full"
            :disabled="busy"
            type="button"
            @click="review('approved')"
          >
            通过并解锁下一任务</button
          ><button
            class="return-button full"
            :disabled="busy"
            type="button"
            @click="review('revision_required')"
          >
            打回修订
          </button>
          </template>
          <div v-else class="review-read-only"><strong>当前为只读审核视图</strong><p>这份材料属于其他指导教师负责的项目，不能提交通过或打回决定。</p><RouterLink class="secondary-button" to="/teacher/reviews">返回我的审核队列</RouterLink></div>
        </aside>
      </div></template
    ><template v-else-if="surface === 'review'"
      ><EmptyState title="找不到待审核材料" description="这份提交可能已完成审核、已被撤回，或链接已经失效。"><RouterLink class="secondary-button" to="/teacher/reviews">返回审核队列</RouterLink></EmptyState></template
    ><template v-else-if="surface === 'members'"
      ><section class="demo-member-list paper-card">
        <div v-if="teacherStore.state.guided.length" class="member-context-bar"><label>邀请到项目<select v-model.number="memberProjectId"><option v-for="project in teacherStore.state.guided" :key="project.id" :value="project.id">{{ project.title }}</option></select></label></div>
        <div
          v-for="invite in teacherStore.state.invitations"
          :key="invite.id"
          class="pilot-list-row"
        >
          <div class="pilot-person"><span class="pilot-avatar">{{ invite.invitee_name.slice(0, 1) }}</span><div class="pilot-list-row__main"><div class="pilot-list-row__title">{{ invite.invitee_name }}</div><div class="pilot-list-row__meta">申请加入 · {{ invite.project_title }}</div></div></div>
          <div class="pilot-list-row__actions"><StatusTag status="waiting_teacher" /><button
            class="secondary-button"
            type="button"
            @click="decide(invite.id, false)"
          >
            拒绝</button
          ><button
            class="primary-button"
            type="button"
            @click="decide(invite.id, true)"
          >
            确认加入
          </button></div>
        </div>
        <div v-for="entry in teacherStore.state.guided.flatMap((project) => project.members.map((member) => ({ project, member }))).slice(0, 3)" :key="`${entry.project.id}-${entry.member.id}`" class="pilot-list-row"><div class="pilot-person"><span class="pilot-avatar">{{ entry.member.username.slice(0, 1) }}</span><div class="pilot-list-row__main"><div class="pilot-list-row__title">{{ entry.member.username }}</div><div class="pilot-list-row__meta">{{ entry.member.role === 'leader' ? '项目负责人' : '项目成员' }} · {{ entry.project.title }}</div></div></div><div class="pilot-list-row__actions"><StatusTag :status="entry.member.role === 'leader' ? 'active' : 'draft'" /></div></div>
        <EmptyState
          v-if="!teacherStore.state.invitations.length && !teacherStore.state.guided.some((project) => project.members.length)"
          title="没有待确认成员"
          description="成员接受邀请后，会在此等待主指导教师确认。"
        /></section
    ></template>
  </div>
</template>

<style scoped>
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
  content: "";
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
.pool-list-shell { padding: 26px; }
.pool-filter-bar { margin-bottom: 6px; }
.pool-compact-list { display: grid; }
.pool-compact-list .pool-card { display: flex; width: 100%; min-height: 68px; box-sizing: border-box; flex-direction: row; align-items: center; justify-content: space-between; gap: 18px; padding: 15px 0; border: 0; border-top: 1px solid var(--line); border-radius: 0; background: transparent; box-shadow: none; }
.pool-compact-list .pool-card:hover { border-color: var(--line); box-shadow: none; transform: none; }
.pool-compact-list .pool-card:first-child { border-top: 0; }
.pool-compact-list .row-actions { display: flex; align-items: center; gap: 10px; }
.pool-pagination { display: flex; align-items: center; justify-content: center; gap: 14px; margin-top: 18px; color: var(--muted); font-size: 12px; }
.teacher-project-pagination { display: flex; align-items: center; justify-content: center; gap: 14px; margin-top: 18px; color: var(--muted); font-size: 12px; }
.teacher-project-table table { min-width: 800px; }
.teacher-project-actions { display: flex; align-items: center; gap: 8px; }
.teacher-project-actions .secondary-button { white-space: nowrap; }
.demo-member-list { padding: 26px; }
.member-context-bar { display: flex; justify-content: flex-end; margin-bottom: 14px; }
.member-context-bar label { display: grid; gap: 6px; color: var(--muted); font-size: 12px; }
.member-context-bar select { min-width: 260px; min-height: 36px; padding: 0 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); color: var(--ink); }
.demo-member-list .pilot-list-row:first-child { border-top: 0; }
.review-read-only { display: grid; gap: 8px; padding: 14px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper-soft); }
.review-context-note { margin: 0 0 12px; padding: 9px 12px; border: 1px solid var(--sage-line); border-radius: var(--radius-sm); background: var(--sage-soft); color: var(--moss-dark); font-size: 12px; }
.review-read-only strong { color: var(--ink); font-size: 13px; }
.review-read-only p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.6; }

.guided-list { display: grid; gap: 8px; }
.project-row { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: 18px; min-width: 0; padding: 15px 17px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); transition: border-color .15s ease, box-shadow .15s ease; }
.project-row:hover { border-color: var(--sage-line); box-shadow: var(--shadow-soft); }
.project-row--archived { background: var(--sage-soft); }
.project-row--trashed { background: var(--amber-soft); border-color: var(--amber-line); }
.project-row__main { min-width: 0; display: grid; gap: 10px; }
.project-row__title { display: flex; align-items: center; gap: 8px; min-width: 0; flex-wrap: wrap; }
.project-row__title h2 { min-width: 0; max-width: min(48vw, 520px); margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font: 700 17px/1.35 var(--sans); color: var(--ink); }
.project-row__type { color: var(--muted); font-size: 11px; }
.project-row__meta { display: flex; align-items: center; gap: 26px; color: var(--muted); }
.project-row__meta span { display: grid; gap: 2px; min-width: 74px; }
.project-row__meta small { font-size: 10px; }
.project-row__meta strong { color: var(--ink); font-size: 12px; font-weight: 600; }
.project-row__actions { position: relative; z-index: 2; }
.project-row__detail { display: inline-flex; align-items: center; gap: 5px; color: var(--moss-dark); font-size: 12px; font-weight: 700; text-decoration: none; white-space: nowrap; }
.project-row__detail:hover { color: var(--moss); }
.project-row__detail .el-icon, .project-row__detail > svg { width: 14px; height: 14px; font-size: 14px; flex: 0 0 auto; }
@media (max-width: 820px) {
  .project-row { grid-template-columns: minmax(0, 1fr) auto; gap: 12px; }
  .project-row__main { grid-column: 1 / -1; }
  .project-row__detail { grid-column: 1; grid-row: 2; }
  .project-row__actions { grid-column: 2; grid-row: 2; }
  .project-row__title h2 { max-width: 56vw; }
}
@media (max-width: 520px) {
  .project-row { padding: 13px; }
  .project-row__meta { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 16px; }
  .project-row__title h2 { max-width: 100%; font-size: 16px; }
  .project-row__detail { font-size: 11.5px; }
}

.metric-card--archived {
  background: var(--sage-soft);
  border: 1px solid var(--sage-line);
}
.metric-card--archived small {
  color: var(--moss-dark);
}
.metric-card--archived strong {
  color: var(--moss-dark);
}

.metric-card--trashed {
  background: var(--amber-soft);
  border: 1px solid var(--amber-line);
}
.metric-card--trashed small {
  color: var(--clay-deep);
}
.metric-card--trashed strong {
  color: var(--clay-deep);
}
</style>
