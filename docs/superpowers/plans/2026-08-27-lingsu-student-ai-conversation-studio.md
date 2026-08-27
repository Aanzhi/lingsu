# 灵思 AI Conversation Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将学生端 `/student/ai` 改造成第 3 个视觉方向 Conversation Studio，并让学生工作台导航默认收起为可展开的图标栏。

**Architecture:** 在共享 `WorkspaceShell`/`WorkspaceFrame` 中增加仅学生启用的导航收起状态，使用本地偏好保持默认收起和用户选择。AI 页面继续由 `AICenter.vue` 编排现有会话数据流，只重组页面骨架为标题、模式、Agent 身份、欢迎/消息画布和 Composer 五层；示例问题通过纯函数提供并复用现有 `sendMessage`，不触碰后端接口。

**Tech Stack:** Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Vitest、Vite、Codex in-app Browser。

---

## 文件结构与职责

- Create: `frontend/src/stores/sidebarPreference.ts` — 纯函数封装收起偏好读取、解析和写入，提供默认收起策略。
- Test: `frontend/src/stores/sidebarPreference.test.ts` — 验证缺省值、合法值、非法值和存储写入。
- Modify: `frontend/src/layouts/StudentLayout.vue` — 只为学生工作台打开可折叠导航能力。
- Modify: `frontend/src/components/WorkspaceShell.vue` — 管理学生导航状态、链接无障碍名称和切换动作。
- Modify: `frontend/src/components/WorkspaceFrame.vue` — 将收起状态映射到 shell/aside class，并渲染切换按钮。
- Modify: `frontend/src/styles/foundations.css` — 增加桌面图标栏、展开态和焦点样式。
- Modify: `frontend/src/styles/responsive.css` — 在 860px 以下恢复文字导航，不让收起状态破坏移动端发现性。
- Modify: `frontend/src/stores/aiWorkbenchModel.ts` — 提供按模式返回三条示例问题的纯函数。
- Modify: `frontend/src/stores/aiWorkbenchModel.test.ts` — 验证三种模式的示例问题稳定且不共享可变数组。
- Modify: `frontend/src/pages/shared/AICenter.vue` — 统一 AI 页面骨架、欢迎态、Agent 身份条和对话画布。
- Modify: `frontend/src/components/ai/AIModeTabs.vue` — 调整三段模式控件的密度、描述和 active/focus 状态。
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue` — 保持输入/发送契约，调整为画布底部的主操作区域。
- Modify: `frontend/src/aiCenterUI.test.ts` — 更新页面结构契约，锁定 Agent 身份和示例问题。
- Modify: `frontend/src/aiWorkbenchLayout.test.ts` — 更新布局契约，锁定统一画布和唯一 Composer。
- Modify: `frontend/src/studentNavigationLayout.test.ts` — 锁定学生默认收起、切换语义和教师/平台不受影响。

## 执行约束

- 每个行为改动先写一个能证明需求缺失的测试，运行并看到失败，再写最小实现。
- 不修改 Django、API、数据库模型、权限或会话状态机。
- 不删除现有导航链接和 `AIResultCard` 的人工确认边界。
- 不使用 `git reset --hard`、`git checkout --` 或批量格式化；保留工作区中与本任务无关的修改。

### Task 1: Add and test the sidebar preference contract

**Files:**
- Create: `frontend/src/stores/sidebarPreference.ts`
- Test: `frontend/src/stores/sidebarPreference.test.ts`

- [ ] **Step 1: Write the failing tests**

Add this test file:

```ts
import { describe, expect, it } from 'vitest'
import { readSidebarPreference, writeSidebarPreference } from './sidebarPreference'

describe('sidebar preference', () => {
  it('defaults to collapsed when no preference exists', () => {
    expect(readSidebarPreference({ getItem: () => null })).toBe(true)
  })

  it('restores explicit expanded and collapsed values', () => {
    expect(readSidebarPreference({ getItem: () => '0' })).toBe(false)
    expect(readSidebarPreference({ getItem: () => '1' })).toBe(true)
  })

  it('falls back to collapsed for an invalid value', () => {
    expect(readSidebarPreference({ getItem: () => 'unknown' })).toBe(true)
  })

  it('writes a stable string value for the browser storage adapter', () => {
    let savedKey = ''
    let savedValue = ''
    writeSidebarPreference({ setItem: (key, value) => { savedKey = key; savedValue = value } }, false)
    expect(savedKey).toBe('lingsu:student-sidebar-collapsed')
    expect(savedValue).toBe('0')
  })
})
```

- [ ] **Step 2: Run the focused test and verify the expected failure**

Run from `frontend/`:

```bash
npm test -- sidebarPreference.test.ts
```

Expected: Vitest fails because `./sidebarPreference` does not exist yet. Do not continue until the failure is caused by the missing contract rather than a test syntax error.

- [ ] **Step 3: Implement the smallest pure helper**

Create `frontend/src/stores/sidebarPreference.ts`:

```ts
export const STUDENT_SIDEBAR_STORAGE_KEY = 'lingsu:student-sidebar-collapsed'

type StorageReader = Pick<Storage, 'getItem'>
type StorageWriter = Pick<Storage, 'setItem'>

export function readSidebarPreference(storage: StorageReader, fallback = true): boolean {
  const value = storage.getItem(STUDENT_SIDEBAR_STORAGE_KEY)
  if (value === '0') return false
  if (value === '1') return true
  return fallback
}

export function writeSidebarPreference(storage: StorageWriter, collapsed: boolean): void {
  storage.setItem(STUDENT_SIDEBAR_STORAGE_KEY, collapsed ? '1' : '0')
}
```

- [ ] **Step 4: Run the focused test and the model test**

```bash
npm test -- sidebarPreference.test.ts stores/aiWorkbenchModel.test.ts
```

Expected: all tests pass.

- [ ] **Step 5: Commit the preference contract**

```bash
git add frontend/src/stores/sidebarPreference.ts frontend/src/stores/sidebarPreference.test.ts
git commit -m "feat: add student sidebar preference contract"
```

### Task 2: Make only the student workspace sidebar collapsible

**Files:**
- Modify: `frontend/src/layouts/StudentLayout.vue`
- Modify: `frontend/src/components/WorkspaceShell.vue`
- Modify: `frontend/src/components/WorkspaceFrame.vue`
- Modify: `frontend/src/styles/foundations.css`
- Modify: `frontend/src/styles/responsive.css`
- Test: `frontend/src/studentNavigationLayout.test.ts`

- [ ] **Step 1: Extend the navigation layout test with failing expectations**

Add assertions to the shared navigation contract:

```ts
it('enables a default-collapsed icon sidebar for students only', () => {
  expect(studentLayout).toContain('collapsible-sidebar')
  expect(workspaceShell).toContain('readSidebarPreference')
  expect(workspaceShell).toContain('writeSidebarPreference')
  expect(workspaceShell).toContain('aria-expanded')
  expect(foundations).toContain('.workspace-shell--sidebar-collapsed')
  expect(foundations).toContain('.workspace-sidebar--collapsed')
  expect(responsive).toContain('.workspace-shell--sidebar-collapsed .workspace-sidebar')
  expect(teacherLayout).not.toContain('collapsible-sidebar')
  expect(platformLayout).not.toContain('collapsible-sidebar')
})
```

- [ ] **Step 2: Run the focused test and verify it fails**

```bash
npm test -- studentNavigationLayout.test.ts
```

Expected: the new test fails because the student layout and shared shell do not yet expose the collapse contract.

- [ ] **Step 3: Add the student-only prop and state wiring**

In `frontend/src/layouts/StudentLayout.vue`, change the workspace branch to:

```vue
<WorkspaceShell v-else role="student" role-tone="student" section-label="学生工作台" collapsible-sidebar />
```

In `frontend/src/components/WorkspaceShell.vue`, import `onMounted`, `ref`, and `watch`, import the two preference helpers, and replace the props declaration with:

```ts
const props = withDefaults(defineProps<{
  role: NavigationRole
  roleTone: 'student' | 'teacher' | 'platform'
  sectionLabel: string
  collapsibleSidebar?: boolean
}>(), {
  collapsibleSidebar: false,
})

const sidebarCollapsed = ref(true)

onMounted(() => {
  if (!props.collapsibleSidebar) return
  try {
    sidebarCollapsed.value = readSidebarPreference(window.localStorage)
  } catch {
    sidebarCollapsed.value = true
  }
})

watch(sidebarCollapsed, (collapsed) => {
  if (!props.collapsibleSidebar) return
  try {
    writeSidebarPreference(window.localStorage, collapsed)
  } catch {
    // Private browsing or blocked storage should not break navigation.
  }
})
```

Pass the state to `WorkspaceFrame`:

```vue
<WorkspaceFrame
  :theme="role === 'platform_admin' ? 'management' : 'user'"
  :navigation-label="`${sectionLabel}导航`"
  :sidebar-collapsible="props.collapsibleSidebar"
  :sidebar-collapsed="props.collapsibleSidebar && sidebarCollapsed"
>
```

Add `:aria-label="props.collapsibleSidebar && sidebarCollapsed ? item.label : undefined"` and `:title="props.collapsibleSidebar && sidebarCollapsed ? item.label : undefined"` to every primary and utility `RouterLink`. Keep each existing text `<span>` in the DOM so the expanded state remains unchanged.

- [ ] **Step 4: Add the frame prop and accessible toggle**

In `frontend/src/components/WorkspaceFrame.vue`, extend the props defaults:

```ts
sidebarCollapsible?: boolean
sidebarCollapsed?: boolean
```

with defaults of `false`, and apply these classes:

```vue
<div
  class="workspace-shell"
  :class="{
    'workspace-shell--full': !showSidebar,
    'workspace-shell--hero': layout === 'hero',
    'workspace-shell--sidebar-collapsed': sidebarCollapsible && sidebarCollapsed,
  }"
>
  <aside
    v-if="showSidebar"
    class="workspace-sidebar"
    :class="{ 'workspace-sidebar--collapsed': sidebarCollapsible && sidebarCollapsed }"
    :aria-label="navigationLabel"
  >
    <slot name="sidebar" />
    <button
      v-if="sidebarCollapsible"
      class="workspace-sidebar__toggle"
      type="button"
      :aria-expanded="!sidebarCollapsed"
      :aria-label="sidebarCollapsed ? '展开学生工作台导航' : '收起学生工作台导航'"
      :title="sidebarCollapsed ? '展开导航' : '收起导航'"
      @click="$emit('toggle-sidebar')"
    >
      <span aria-hidden="true">{{ sidebarCollapsed ? '›' : '‹' }}</span>
      <span class="workspace-sidebar__toggle-label">{{ sidebarCollapsed ? '展开' : '收起' }}</span>
    </button>
  </aside>
```

Because `WorkspaceFrame` needs to emit the click, add `toggle-sidebar` to its emits and in `WorkspaceShell` listen with `@toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"`.

- [ ] **Step 5: Add desktop collapsed styles and mobile reset**

Append the following focused rules to `frontend/src/styles/foundations.css` near the existing workspace shell rules:

```css
.workspace-shell--sidebar-collapsed { grid-template-columns: 72px minmax(0, 1fr); }
.workspace-sidebar--collapsed { align-items: center; padding: 24px 10px; }
.workspace-sidebar--collapsed .workspace-sidebar__label,
.workspace-sidebar--collapsed .workspace-sidebar__subnav,
.workspace-sidebar--collapsed > a > span { display: none; }
.workspace-sidebar--collapsed > a { width: 44px; justify-content: center; padding-inline: 0; }
.workspace-sidebar--collapsed > a .el-icon { width: 20px; height: 20px; font-size: 17px; }
.workspace-sidebar__toggle { width: 100%; min-height: 36px; margin-top: auto; padding: 0 9px; display: flex; align-items: center; justify-content: center; gap: 8px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--muted); font: inherit; font-size: 12px; cursor: pointer; }
.workspace-sidebar__toggle:hover, .workspace-sidebar__toggle:focus-visible { border-color: var(--moss); color: var(--moss-dark); background: var(--sage-soft); outline: none; }
.workspace-sidebar--collapsed .workspace-sidebar__toggle { width: 44px; padding-inline: 0; font-size: 20px; }
.workspace-sidebar--collapsed .workspace-sidebar__toggle-label { display: none; }
```

Add the mobile behavior in `responsive.css` within the `max-width: 860px` block:

```css
.workspace-shell--sidebar-collapsed { grid-template-columns: 1fr; }
.workspace-shell--sidebar-collapsed .workspace-sidebar { align-items: center; padding: 9px 42px 9px 14px; }
.workspace-shell--sidebar-collapsed .workspace-sidebar__label,
.workspace-shell--sidebar-collapsed .workspace-sidebar > a > span { display: inline; }
.workspace-shell--sidebar-collapsed .workspace-sidebar__subnav { display: flex; }
.workspace-shell--sidebar-collapsed .workspace-sidebar__toggle { display: none; }
```

- [ ] **Step 6: Run navigation and preference tests**

```bash
npm test -- studentNavigationLayout.test.ts sidebarPreference.test.ts
```

Expected: all focused tests pass and teacher/platform layout tests remain green.

- [ ] **Step 7: Commit the sidebar behavior**

```bash
git add frontend/src/layouts/StudentLayout.vue frontend/src/components/WorkspaceShell.vue frontend/src/components/WorkspaceFrame.vue frontend/src/styles/foundations.css frontend/src/styles/responsive.css frontend/src/studentNavigationLayout.test.ts
git commit -m "feat: collapse student workspace navigation by default"
```

### Task 3: Add deterministic starter prompts by workbench mode

**Files:**
- Modify: `frontend/src/stores/aiWorkbenchModel.ts`
- Test: `frontend/src/stores/aiWorkbenchModel.test.ts`

- [ ] **Step 1: Write the failing model test**

Extend the import and add:

```ts
import { AI_WORKBENCH_MODES, draftActions, materialSelectionScope, resolveAIContext, resolveStudentAgent, starterPrompts, visibleAgents, type AIWorkspaceMode } from './aiWorkbenchModel'

it('returns three starter prompts for each workbench mode', () => {
  const modes: AIWorkspaceMode[] = ['opening', 'research', 'defense']
  for (const mode of modes) {
    const prompts = starterPrompts(mode)
    expect(prompts).toHaveLength(3)
    expect(prompts.every((prompt) => prompt.length > 6)).toBe(true)
    expect(starterPrompts(mode)).not.toBe(prompts)
  }
  expect(starterPrompts('research')).toEqual([
    '帮我拆解今天的研究任务',
    '如何设计下一步实验？',
    '怎样整理现有证据？',
  ])
})
```

- [ ] **Step 2: Run the focused test and verify it fails**

```bash
npm test -- stores/aiWorkbenchModel.test.ts
```

Expected: Vitest reports that `starterPrompts` is not exported.

- [ ] **Step 3: Implement the pure prompt map**

Add to `aiWorkbenchModel.ts`:

```ts
const AI_STARTER_PROMPTS: Record<AIWorkspaceMode, readonly string[]> = {
  opening: ['把我的观察整理成研究问题', '哪些变量值得先记录？', '给我一个可执行的开题思路'],
  research: ['帮我拆解今天的研究任务', '如何设计下一步实验？', '怎样整理现有证据？'],
  defense: ['帮我提炼项目亮点', '给我一个展示提纲', '模拟一次答辩提问'],
}

export function starterPrompts(mode: AIWorkspaceMode): string[] {
  return [...AI_STARTER_PROMPTS[mode]]
}
```

- [ ] **Step 4: Run the model tests and commit**

```bash
npm test -- stores/aiWorkbenchModel.test.ts
git add frontend/src/stores/aiWorkbenchModel.ts frontend/src/stores/aiWorkbenchModel.test.ts
git commit -m "feat: add AI workbench starter prompts"
```

Expected: the model test passes before the commit is created.

### Task 4: Make AICenter use the Conversation Studio skeleton

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/aiCenterUI.test.ts`
- Modify: `frontend/src/aiWorkbenchLayout.test.ts`

- [ ] **Step 1: Write failing structure tests**

Add these assertions to `aiCenterUI.test.ts`:

```ts
it('shows the active assistant and starter prompts inside one conversation studio', () => {
  expect(source).toContain('ai-assistant-bar')
  expect(source).toContain('currentAgent?.name')
  expect(source).toContain('starterPrompts(workbenchMode)')
  expect(source).toContain('ai-welcome')
  expect(source).toContain('ai-starter-prompt')
  expect(source).toContain('@click="void sendMessage(prompt)"')
})

it('keeps the existing conversation result and recovery contracts in the studio canvas', () => {
  expect(source).toContain('ai-conversation-stage')
  expect(source).toContain('AIResultCard')
  expect(source).toContain('resumePendingMessage')
  expect(source).toContain('message.status === \'failed\'')
})
```

Update the existing simple-layout expectations to require `ai-conversation-stage` and `ai-assistant-bar`; remove assertions that specifically require the old `:show-mode-descriptions="false"` and the old large empty-state spacing.

- [ ] **Step 2: Run the focused tests and verify they fail**

```bash
npm test -- aiCenterUI.test.ts aiWorkbenchLayout.test.ts
```

Expected: the new assertions fail because the current template has no welcome block, assistant identity bar, or conversation stage wrapper.

- [ ] **Step 3: Add the computed starter prompts and assistant copy**

In the import from `aiWorkbenchModel`, include `starterPrompts`. Add these computed values beside `modeAgents` and `currentAgent`:

```ts
const modeStarterPrompts = computed(() => starterPrompts(workbenchMode.value))
const assistantName = computed(() => currentAgent.value?.name || (agentsLoading.value ? '正在准备助手…' : '灵思 AI'))
const assistantDescription = computed(() => currentAgent.value?.description || '围绕当前研究阶段，帮助你梳理问题、证据和下一步行动。')
```

Use `modeStarterPrompts` in the template; do not add another API request or another source of Agent data.

- [ ] **Step 4: Replace the split new/active header with one page skeleton**

Keep the root class and `isNewConversation`/`isConversationStarted` bindings, then replace the two top-level `template v-if` branches with this structure. Move the existing message loop and `AIResultCard` into the `v-else` branch without changing their handlers:

```vue
<header class="ai-workbench-header" aria-labelledby="ai-workbench-title">
  <div class="ai-workbench-heading">
    <span class="eyebrow">研究工作台</span>
    <h1 id="ai-workbench-title">灵思 AI</h1>
    <p>把问题说出来，和研究助手一起推进下一步。</p>
  </div>
  <div class="ai-workbench-header__actions">
    <span class="ai-workbench-context-pill">{{ workspaceContextLabel }}</span>
    <button v-if="isNewConversation" class="text-button" type="button" :disabled="sending || loading || !conversations.length" @click="openHistory">历史会话</button>
    <button v-else class="text-button" type="button" :disabled="sending" @click="startNewConversation">新建对话</button>
  </div>
</header>

<section class="ai-workbench-mode-region" aria-label="灵思 AI 模式">
  <AIModeTabs :model-value="workbenchMode" :disabled="sending" :show-agent-rail="false" :show-mode-descriptions="true" @update:model-value="selectWorkbenchMode" />
</section>

<section v-if="loading || projectsLoading" class="ai-workbench-skeleton" role="status" aria-label="正在准备灵思 AI"><i /><i /><i /></section>
<section v-else-if="(projectRequired && !currentProject) || (!agentsLoading && !currentAgent)" class="ai-workbench-context-note" role="status">
  <span v-if="projectRequired && !currentProject">研究和成果表达默认绑定你的主项目，请先在“我的项目”创建或设置主项目。</span>
  <span v-else>当前模式暂未配置 AI 助手，请联系平台管理员。</span>
  <button v-if="projectRequired && !currentProject" class="secondary-button" type="button" @click="chooseProject">去我的项目</button>
</section>

<section v-else class="ai-conversation-stage" aria-label="灵思 AI 对话工作区">
  <header class="ai-assistant-bar">
    <span class="ai-assistant-avatar" aria-hidden="true">灵思</span>
    <div class="ai-assistant-copy">
      <div><strong>{{ assistantName }}</strong><span class="ai-assistant-status">在线</span></div>
      <p>{{ assistantDescription }}</p>
    </div>
    <span class="ai-assistant-stage">{{ workbenchMode === 'defense' ? '成果表达' : workbenchMode === 'opening' ? '开题' : '研究' }}</span>
  </header>

  <section ref="chatStreamRef" class="ai-conversation-stream" aria-live="polite" :aria-busy="sending" @scroll="updateScrollAffordance">
    <div v-if="conversationLoading" class="ai-stream-loading"><span class="ai-loading-dot" />正在恢复对话…</div>
    <div v-if="isNewConversation" class="ai-welcome">
      <span class="ai-welcome__eyebrow">{{ workbenchMode === 'opening' ? '从一个观察开始' : workbenchMode === 'defense' ? '把成果讲清楚' : '继续推进你的研究' }}</span>
      <h2>你好，{{ auth.user.value?.display_name || auth.user.value?.username || '同学' }}</h2>
      <p>告诉我你正在思考的问题、遇到的困难或想完成的下一步。</p>
      <div class="ai-starter-prompts" aria-label="开始对话示例">
        <button v-for="prompt in modeStarterPrompts" :key="prompt" class="ai-starter-prompt" type="button" :disabled="composerDisabled" @click="void sendMessage(prompt)">
          <span aria-hidden="true">→</span><span>{{ prompt }}</span>
        </button>
      </div>
    </div>
    <template v-else>
      <article v-for="message in messages" :key="message.id" class="ai-message" :class="message.role">
        <div class="ai-message__label">{{ message.role === 'user' ? '你' : '灵思 AI' }}</div>
        <div class="ai-message__body">
          <p v-for="(block, blockIndex) in messageBlocks(message.content)" :key="`${message.id}-${blockIndex}`">{{ block }}</p>
          <p v-if="!message.content && (message.status === 'queued' || message.status === 'streaming')" class="ai-message__pending">{{ message.status === 'queued' ? '正在排队…' : '正在生成…' }}</p>
          <div v-if="message.status === 'failed'" class="ai-message__error"><span>{{ message.error_message || '生成失败' }}</span><button type="button" :disabled="sending" @click="retryMessage(message)">{{ sending ? '重试中…' : '重试' }}</button></div>
          <AIResultCard
            v-if="hasResult(message)"
            data-result-actions="确认创建项目 / 保存为材料"
            :mode="workbenchMode"
            :message="message"
            :draft="artifactDraftFor(message)"
            :opening-draft="openingDraft"
            :saving="savingMessage === message.id"
            :creating-project="creatingProject"
            :can-save-material="Boolean(currentProject && message.generation_log)"
            :can-create-project="workbenchMode === 'opening' && Boolean(selectedId)"
            @update:draft="artifactDrafts[message.id] = $event"
            @update:opening-draft="openingDraft = $event"
            @save-material="void openMaterialSave(message)"
            @create-project="void createProjectFromArtifact(message)"
            @retry="regenerateMessage(message)"
            @copy="copyMessage(message)"
          />
        </div>
      </article>
    </template>
  </section>
  <button v-if="showJumpLatest" type="button" class="jump-latest" @click="scrollToLatest()">↓ 跳到最新消息</button>
</section>
```

When transferring the current message loop, keep the existing `messageBlocks`, pending state, failed-state retry button, `AIResultCard` props, and all emitted handlers byte-for-byte unless a class name must be nested under the new stage.

- [ ] **Step 5: Keep one Composer and history/modal behavior**

Keep one `AIWorkbenchComposer` instance after the stage and keep:

```vue
:show-meta="false"
:show-material-citation="false"
@update:draft="draft = $event"
@send="void sendMessage()"
@stop="abortActiveStream()"
```

Leave `AIConversationHistory`, the material confirmation dialog, notice regions, and all existing script functions in place. Only move their surrounding layout; do not change API payloads.

- [ ] **Step 6: Run the focused structure tests and commit the template behavior**

```bash
npm test -- aiCenterUI.test.ts aiWorkbenchLayout.test.ts
git add frontend/src/pages/shared/AICenter.vue frontend/src/aiCenterUI.test.ts frontend/src/aiWorkbenchLayout.test.ts
git commit -m "feat: introduce conversation studio AI layout"
```

Expected: both focused suites pass.

### Task 5: Apply the Conversation Studio visual system

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/components/ai/AIModeTabs.vue`
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue`
- Modify: `frontend/src/styles/responsive.css`

- [ ] **Step 1: Add failing style-contract assertions**

Extend `aiWorkbenchLayout.test.ts` and `aiCenterUI.test.ts`:

```ts
it('uses a balanced stage and anchored composer instead of a floating empty form', () => {
  expect(page).toContain('.ai-conversation-stage')
  expect(page).toContain('grid-template-rows: auto auto minmax(0, 1fr) auto')
  expect(page).toContain('.ai-workbench-page--new .ai-conversation-stream')
  expect(composer).toContain('box-shadow')
  expect(tabs).toContain('showModeDescriptions')
})
```

- [ ] **Step 2: Run the focused style tests and verify the new assertions fail**

```bash
npm test -- aiCenterUI.test.ts aiWorkbenchLayout.test.ts
```

Expected: the new CSS contract is absent or still reflects the old 900px centered form.

- [ ] **Step 3: Replace AICenter page-level styles with the approved hierarchy**

Use the existing tokens and add these rules to the scoped style in `AICenter.vue`:

```css
.ai-center-page { display: grid; grid-template-rows: auto auto minmax(0, 1fr) auto auto; width: 100%; max-width: var(--content-max); min-width: 0; height: calc(100vh - var(--topbar-height) - 64px); min-height: 620px; box-sizing: border-box; margin: 0 auto; padding: 28px 0 24px; overflow: hidden; }
.ai-workbench-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding-bottom: 18px; border-bottom: 1px solid var(--line); }
.ai-workbench-heading h1 { margin: 4px 0 7px; font: 750 clamp(32px, 4vw, 48px)/1.02 var(--sans); letter-spacing: -.055em; }
.ai-workbench-heading p { margin: 0; color: var(--muted); font-size: 14px; line-height: 1.6; }
.ai-workbench-mode-region { width: 100%; margin: 18px 0 14px; }
.ai-conversation-stage { display: grid; grid-template-rows: auto minmax(0, 1fr) auto; min-width: 0; min-height: 0; overflow: hidden; border: 1px solid var(--line-dark); border-radius: var(--radius-lg); background: var(--paper); box-shadow: var(--shadow-soft); }
.ai-assistant-bar { display: flex; align-items: center; gap: 13px; min-width: 0; padding: 16px 20px; border-bottom: 1px solid var(--line); background: linear-gradient(90deg, var(--paper-soft), var(--paper)); }
.ai-assistant-avatar { display: grid; width: 42px; height: 42px; flex: 0 0 42px; place-items: center; border-radius: 13px; background: var(--moss-dark); color: #fff; font-size: 11px; font-weight: 800; letter-spacing: .04em; }
.ai-assistant-copy { min-width: 0; flex: 1; }
.ai-assistant-copy > div { display: flex; align-items: center; gap: 8px; }
.ai-assistant-copy strong { color: var(--ink); font-size: 14px; }
.ai-assistant-copy p { overflow: hidden; margin: 4px 0 0; color: var(--muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.ai-assistant-status { color: var(--success); font-size: 10px; font-weight: 700; }
.ai-assistant-status::before { content: ''; display: inline-block; width: 6px; height: 6px; margin-right: 4px; border-radius: 50%; background: currentColor; vertical-align: 1px; }
.ai-assistant-stage { flex: 0 0 auto; padding: 5px 9px; border: 1px solid var(--sage-line); border-radius: 999px; color: var(--moss-dark); background: var(--sage-soft); font-size: 11px; font-weight: 700; }
.ai-conversation-stream { display: grid; align-content: start; gap: 22px; min-width: 0; min-height: 0; overflow-y: auto; padding: 24px clamp(20px, 5vw, 72px) 28px; scrollbar-width: thin; }
.ai-welcome { align-self: center; justify-self: center; width: min(100%, 680px); padding: clamp(22px, 5vh, 46px) 0 26px; text-align: center; }
.ai-welcome__eyebrow { color: var(--moss); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
.ai-welcome h2 { margin: 11px 0 7px; color: var(--ink); font: 750 clamp(25px, 3vw, 34px)/1.15 var(--sans); letter-spacing: -.035em; }
.ai-welcome > p { max-width: 520px; margin: 0 auto; color: var(--muted); font-size: 14px; line-height: 1.7; }
.ai-starter-prompts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 28px; text-align: left; }
.ai-starter-prompt { min-height: 76px; padding: 13px 14px; display: flex; align-items: flex-start; gap: 8px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper-soft); color: var(--ink); font: inherit; font-size: 12px; line-height: 1.55; text-align: left; cursor: pointer; transition: transform var(--transition-fast), border-color var(--transition-fast), background-color var(--transition-fast); }
.ai-starter-prompt > span:first-child { color: var(--moss); font-size: 16px; font-weight: 800; }
.ai-starter-prompt:hover:not(:disabled), .ai-starter-prompt:focus-visible { border-color: var(--moss); background: var(--sage-soft); outline: none; transform: translateY(-1px); }
.ai-starter-prompt:disabled { cursor: wait; opacity: .52; }
.ai-workbench-composer-host { width: 100%; min-width: 0; margin: 14px auto 0; }
.ai-workbench-page--active .ai-workbench-composer-host { position: static; padding-top: 0; background: transparent; }
.ai-center-page :deep(.ai-workbench-composer) { padding: 16px 18px 13px; border-color: var(--line-dark); border-radius: var(--radius-lg); background: var(--paper); box-shadow: 0 8px 24px rgba(42, 70, 47, .08); }
```

Retain the existing message and dialog rules, adjusting widths to the new stream padding so user bubbles remain readable. Keep `AIResultCard` and error surfaces visually compact.

- [ ] **Step 4: Tune shared mode tabs and Composer without changing their events**

In `AIModeTabs.vue`, keep the same props/emits and use the existing `showModeDescriptions` prop. Set the active tab to a clear bottom rule and subtle sage surface; keep descriptions single-line and hide them only at mobile widths.

In `AIWorkbenchComposer.vue`, keep the existing `textarea`, Enter handler, send/stop branches, and material citation branch. Increase the textarea usable height to `92px`, make the footer `min-height: 34px`, and use the project primary button tokens. Do not add upload or automatic-save behavior.

- [ ] **Step 5: Add narrow-screen rules**

Add to `responsive.css`:

```css
@media (max-width: 1040px) {
  .ai-center-page { height: auto; min-height: calc(100vh - var(--topbar-height) - 32px); overflow: visible; }
  .ai-conversation-stage { min-height: 560px; }
  .ai-conversation-stream { padding-inline: 20px; }
}

@media (max-width: 720px) {
  .ai-center-page { min-height: 0; grid-template-rows: auto auto auto auto auto; padding-inline: 0; }
  .ai-workbench-header { align-items: flex-start; flex-direction: column; }
  .ai-workbench-header__actions { width: 100%; align-items: flex-start; justify-content: flex-start; flex-wrap: wrap; }
  .ai-workbench-context-pill { max-width: 100%; }
  .ai-conversation-stage { min-height: 520px; border-radius: var(--radius-md); }
  .ai-assistant-bar { align-items: flex-start; padding: 14px; }
  .ai-assistant-stage { margin-left: auto; }
  .ai-assistant-copy p { white-space: normal; }
  .ai-starter-prompts { grid-template-columns: 1fr; }
  .ai-starter-prompt { min-height: 0; }
  .ai-center-page :deep(.ai-workbench-composer) { border-radius: var(--radius-md); }
}
```

- [ ] **Step 6: Run the focused tests, TypeScript check, and commit visual styling**

```bash
npm test -- aiCenterUI.test.ts aiWorkbenchLayout.test.ts
npm run build
git add frontend/src/pages/shared/AICenter.vue frontend/src/components/ai/AIModeTabs.vue frontend/src/components/ai/AIWorkbenchComposer.vue frontend/src/styles/responsive.css frontend/src/aiCenterUI.test.ts frontend/src/aiWorkbenchLayout.test.ts
git commit -m "style: polish conversation studio hierarchy"
```

Expected: focused tests and `vue-tsc`/Vite build pass. Existing Vite dependency and chunk-size warnings may remain, but no new TypeScript or build errors are allowed.

### Task 6: Full regression and browser visual acceptance

**Files:**
- No new source files; inspect the committed changes and browser output.

- [ ] **Step 1: Run the complete frontend suite**

From `frontend/`:

```bash
npm test
npm run build
```

Expected: all existing tests pass, including the new sidebar and starter-prompt tests; production build succeeds.

- [ ] **Step 2: Verify the local service state**

From the repository root:

```bash
docker compose ps
curl -fsS http://127.0.0.1:18001/api/health/
curl -fsS http://127.0.0.1:5173/ >/dev/null
```

Expected: backend health responds successfully and the Vite page is reachable.

- [ ] **Step 3: Inspect the current student AI route in the in-app Browser**

Reuse the existing claimed tab at:

```text
http://127.0.0.1:5173/student/ai?mode=research&projectId=91&taskId=500&agent=proposal-topic&researchQuestion=1
```

After reload, verify the visible DOM contains:

```text
展开学生工作台导航
灵思 AI
研究
当前 Agent / assistant identity
开始对话示例
描述你要继续完成的研究任务…
```

Capture a 1280px-class screenshot and inspect that the content fills the viewport without the old empty lower half.

- [ ] **Step 4: Verify the collapsed/expanded navigation contract**

Use the accessible button name `展开学生工作台导航` and confirm its `aria-expanded` is `false`. Click it and verify:

1. `aria-expanded` becomes `true`;
2. labels such as `首页`, `我的项目`, and `灵思 AI` become visible;
3. the main AI content width contracts without horizontal overflow;
4. clicking `收起学生工作台导航` returns to the 72px icon rail;
5. reloading keeps the last chosen state.

- [ ] **Step 5: Verify preserved AI behavior without creating external data**

Do not send a real message during visual QA unless the user explicitly requests it. Verify from the DOM that:

- `Enter 发送 · Shift+Enter 换行` remains visible;
- the send button remains disabled for an empty draft;
- the history button exists only in the new-conversation state;
- `AIResultCard` and retry labels remain in the source;
- mode links preserve `projectId`/`taskId` through existing router behavior.

- [ ] **Step 6: Check final repository state and commit any QA-only test adjustments**

```bash
git diff --check
git status --short --branch
```

Expected: no whitespace errors, only intended committed changes, and no generated build output tracked by Git.

## Plan self-review

- Design coverage: sidebar default collapse, desktop expand/collapse, mobile text fallback, Conversation Studio hierarchy, current Agent identity, starter prompts, existing message/error/result flows, responsive layout, accessibility, and browser acceptance are each assigned above.
- All implementation steps are concrete and include exact paths, snippets, commands, and expected outcomes.
- Type consistency: the helper names are `readSidebarPreference`/`writeSidebarPreference`; the model export is `starterPrompts`; the frame props are `sidebarCollapsible`/`sidebarCollapsed`; all later tasks use those exact names.
- Scope check: only frontend shared-shell and student-AI presentation files are touched; backend and persistence contracts remain unchanged.
