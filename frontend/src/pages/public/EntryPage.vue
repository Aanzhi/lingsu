<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import WorkspaceFrame from '../../components/WorkspaceFrame.vue'
import { auth } from '../../stores/auth'
import { routeForAuthRole } from '../../stores/authModel'

const restoring = ref(true)
onMounted(async () => {
  await auth.restore()
  restoring.value = false
})
const workspacePath = computed(() => auth.user.value ? routeForAuthRole(auth.user.value.role) : '/login')
const workspaceLabel = computed(() => auth.user.value ? '进入我的工作台' : '登录工作台')
</script>

<template>
  <div v-if="restoring" class="entry-loader" aria-label="正在进入灵溯">
    <span class="brand-mark">溯</span><p>正在进入灵溯…</p>
  </div>
  <WorkspaceFrame v-else :show-sidebar="false" edge-to-edge>
    <template #topbar>
      <header class="app-topbar">
        <RouterLink class="auth-brand" to="/" aria-label="返回灵溯首页"><span class="brand-mark">溯</span><strong>灵溯</strong><span class="brand-divider" /><span class="brand-subtitle">青少年科学创新项目工作台</span></RouterLink>
        <div class="public-entry__actions">
          <RouterLink class="primary-button" :to="workspacePath">{{ workspaceLabel }}</RouterLink>
        </div>
      </header>
    </template>
    <div class="public-entry">
      <div class="public-entry__content">
        <section class="public-page-header">
          <div>
            <h1>把科创项目推进到结果。</h1>
            <p class="public-page-description">从项目创建、材料提交到教师审核，灵溯把科创协作放在同一条工作流中。</p>
          </div>
          <a class="public-button public-button--primary" href="#roles">选择开始方式 →</a>
        </section>

        <section class="public-hero-grid">
          <article class="public-card public-hero-card">
            <p class="public-eyebrow public-eyebrow--inverse">灵溯 · 研究工作台</p>
            <h2>把想法变成可以验证的发现。</h2>
            <p>从提出问题、查找资料，到实践验证和成果表达，每一步都有清晰的下一行动。</p>
            <div class="public-hero-meta"><span>学生 · 教师 · 学校</span><span>一套研究路径</span></div>
          </article>
          <article class="public-card public-next-card">
            <div class="public-task-kicker"><span>第一次使用？</span><span class="public-status">3 分钟了解</span></div>
            <h2>先看看研究旅程</h2>
            <p>了解平台如何把一个模糊的兴趣，变成可以完成的项目。</p>
          </article>
        </section>

        <section id="roles" class="public-start-section" aria-label="你可以从这里开始">
          <header class="public-section-head"><div><h2>你可以从这里开始</h2><p>不需要一次准备好所有答案</p></div></header>
          <div class="public-three-col">
            <article class="public-role-card public-role-card--student public-card public-card--pad" data-role="student">
              <span class="role-badge role-badge--student">学生端 · 注册</span>
              <h3>我想做一个项目</h3>
              <p class="public-muted">创建项目、完成研究任务，并在需要时接受同学或教师邀请。</p>
              <RouterLink class="public-button public-button--subtle public-role-card__action" to="/register?role=student">注册学生账号</RouterLink>
            </article>
            <article class="public-role-card public-role-card--teacher public-card public-card--pad" data-role="teacher">
              <span class="role-badge role-badge--teacher">教师端 · 登录</span>
              <h3>我想指导学生</h3>
              <p class="public-muted">从项目池认领项目、审核材料，并指导学生推进研究任务。</p>
              <RouterLink class="public-button public-button--subtle public-role-card__action" to="/login">登录教师工作台</RouterLink>
            </article>
            <article class="public-card public-card--pad">
              <p class="public-eyebrow">学校</p><h3>我想了解平台</h3>
              <p class="public-muted">查看研究旅程、AI 助手和学校空间的整体协作方式。</p>
              <a class="public-button public-button--subtle" href="#platform">了解平台如何协作</a>
            </article>
          </div>
        </section>

        <section id="platform" class="public-platform-section" aria-label="平台如何协作">
          <header class="public-section-head"><div><h2>平台如何协作</h2><p>每个角色只处理自己负责的下一步</p></div></header>
          <div class="public-three-col">
            <article class="public-card public-card--pad"><p class="public-eyebrow">学校空间</p><h3>统一管理项目进度</h3><p class="public-muted">学校可以查看项目活跃度、教师指导和服务状态，管理授权范围。</p></article>
            <article class="public-card public-card--pad"><p class="public-eyebrow">AI 助手</p><h3>把问题拆成可执行步骤</h3><p class="public-muted">灵思 AI 根据开题、研究推进和成果表达提供辅助，最终决定由用户确认。</p></article>
            <article class="public-card public-card--pad"><p class="public-eyebrow">成果治理</p><h3>分级审核后再公开</h3><p class="public-muted">学生、指导教师和平台分别确认公开范围，案例通过审核后进入公域。</p></article>
          </div>
        </section>
      </div>
    </div>
  </WorkspaceFrame>
</template>

<style scoped>
.public-entry { width: 100%; min-height: calc(100vh - var(--topbar-height)); padding: var(--space-8) clamp(20px, 4vw, 64px) 72px; background: var(--ivory); }
.public-entry__content { width: min(var(--content-max), 100%); margin: 0 auto; }
.auth-brand { display: inline-flex; align-items: center; gap: 12px; }
.auth-brand strong { font: 700 24px/1 var(--sans); letter-spacing: .08em; }
.public-entry__actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.public-page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--space-5); margin-bottom: var(--space-7); }
.public-page-header h1, .public-page-header p, .public-card h2, .public-card h3, .public-card p, .public-section-head h2, .public-section-head p { margin-top: 0; }
.public-page-header h1, .public-card h2, .public-card h3, .public-section-head h2 { color: var(--ink); font-family: var(--sans); line-height: 1.25; }
.public-page-header h1 { margin-bottom: 8px; font-size: clamp(26px, 3vw, 36px); letter-spacing: -.025em; }
.public-page-description { max-width: 650px; margin-bottom: 0; color: var(--muted); font-size: 14px; }
.public-eyebrow { margin: 0 0 6px; color: var(--moss); font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.public-eyebrow--inverse { color: rgba(255,255,255,.65); }
.public-button { display: inline-flex; min-height: 36px; align-items: center; justify-content: center; gap: 7px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); padding: 8px 13px; background: var(--paper); color: var(--muted); font-size: 13px; font-weight: 600; text-decoration: none; transition: .16s ease; }
.public-button:hover { border-color: var(--moss); background: var(--paper-soft); color: var(--moss-dark); transform: translateY(-1px); }
.public-button--primary { border-color: var(--moss); background: var(--moss); color: #fff; }
.public-button--primary:hover { border-color: var(--moss-dark); background: var(--moss-dark); color: #fff; }
.public-button--subtle { border-color: transparent; background: transparent; color: var(--moss); }
.public-button--subtle:hover { background: var(--sage-soft); }
.public-card { border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-soft); }
.public-card--pad { padding: var(--space-6); }
.public-role-card { display: flex; min-height: 228px; flex-direction: column; align-items: flex-start; border-inline-start: 4px solid var(--role-accent); transition: border-color .16s ease, background-color .16s ease, box-shadow .16s ease; }
.public-role-card--student { --role-accent: var(--moss); --role-dark: var(--moss-dark); --role-surface: var(--sage-soft); --role-line: var(--sage-line); }
.public-role-card--teacher { --role-accent: var(--management-brand); --role-dark: var(--management-brand-deep); --role-surface: #e6efee; --role-line: #bfd2d0; }
.public-role-card:hover { border-color: var(--role-accent); background: var(--role-surface); box-shadow: var(--shadow-hover); }
.public-role-card .role-badge { margin-bottom: 12px; }
.public-role-card h3 { margin-bottom: 8px; }
.public-role-card .public-muted { flex: 1; }
.public-role-card__action { border-color: var(--role-line); background: var(--role-surface); color: var(--role-dark); }
.public-role-card__action:hover { border-color: var(--role-accent); background: var(--role-surface); color: var(--role-dark); }
.public-hero-grid, .public-three-col { display: grid; gap: var(--space-4); }
.public-hero-grid { grid-template-columns: minmax(0, 1.35fr) minmax(280px, .65fr); }
.public-three-col { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.public-hero-card { position: relative; overflow: hidden; min-height: 250px; padding: clamp(22px, 4vw, 42px); background: var(--moss-dark); color: #fff; }
.public-hero-card::after { position: absolute; right: -42px; bottom: -70px; width: 220px; height: 220px; border: 1px solid rgba(255,255,255,.2); border-radius: 50%; box-shadow: 0 0 0 22px rgba(255,255,255,.04), 0 0 0 44px rgba(255,255,255,.025); content: ''; }
.public-hero-card h2 { max-width: 510px; margin-bottom: 12px; color: #fff; font-size: clamp(24px, 3vw, 34px); }
.public-hero-card > p:not(.public-eyebrow) { max-width: 540px; margin-bottom: 24px; color: rgba(255,255,255,.76); }
.public-hero-meta { display: flex; flex-wrap: wrap; gap: 18px; color: rgba(255,255,255,.7); font-size: 12px; }
.public-next-card { padding: var(--space-6); }
.public-task-kicker { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 18px; color: var(--muted-light); font-size: 12px; }
.public-status { display: inline-flex; min-height: 22px; align-items: center; padding: 2px 7px; border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); font-size: 11px; }
.public-next-card h2 { margin-bottom: 7px; font-size: 20px; }
.public-next-card > p { margin-bottom: 20px; color: var(--muted); font-size: 13px; }
.public-section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--space-4); margin: var(--space-7) 0 var(--space-4); }
.public-section-head h2 { margin-bottom: 0; font-size: 20px; letter-spacing: -.015em; }
.public-section-head p { margin: 4px 0 0; color: var(--muted-light); font-size: 12px; }
.public-card h3 { margin-bottom: 5px; font-size: 15px; }
.public-muted { min-height: 65px; margin-bottom: 10px; color: var(--muted-light); font-size: 14px; }
.public-platform-section { margin-top: var(--space-7); }
</style>
