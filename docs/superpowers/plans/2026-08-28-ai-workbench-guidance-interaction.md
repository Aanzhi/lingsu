# AI Workbench Guidance Interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将新建对话态的三张静态步骤卡变成可选择、可编辑、可聚焦 Composer 的任务入口。

**Architecture:** AICenter.vue 继续拥有模式化工作流数据和 draft 状态；每个步骤增加完整 starter 模板，点击时只更新当前新建对话的 draft 和选中状态。AIWorkbenchComposer.vue 暴露最小的 `focus()` 接口，让页面通过组件边界聚焦 textarea，不改变发送和会话接口。

**Tech Stack:** Vue 3、TypeScript、Vitest、Vite。

---

### Task 1: 固化步骤卡交互契约

**Files:**
- Modify: `frontend/src/aiWorkbenchLayout.test.ts`
- Modify: `frontend/src/aiCenterUI.test.ts`

- [ ] **Step 1: Write the failing contract assertions**

在现有 AI workbench UI 契约测试中增加以下断言：

```ts
expect(pageTemplate).toContain('ai-workbench-empty__step-button')
expect(pageTemplate).toContain('@click="startGuideStep(step)"')
expect(pageTemplate).toContain(':aria-pressed="activeGuideStep === step.label"')
expect(page).toContain('const activeGuideStep = ref<string | null>(null)')
expect(page).toContain('composerRef.value?.focus()')
expect(composer).toContain('defineExpose({ focus: focusTextarea })')
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm --prefix frontend test -- --run src/aiWorkbenchLayout.test.ts src/aiCenterUI.test.ts`

Expected: FAIL because the step buttons, selection handler and Composer focus API do not exist yet.

### Task 2: Add the Composer focus boundary

**Files:**
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue:1-60`

- [ ] **Step 1: Add a textarea ref and exposed focus method**

Change the Vue import and script setup to:

```ts
import { computed, ref } from 'vue'
const textareaRef = ref<HTMLTextAreaElement | null>(null)
function focusTextarea() {
  textareaRef.value?.focus()
}
defineExpose({ focus: focusTextarea })
```

Add `ref="textareaRef"` to the existing textarea without changing its props or events.

- [ ] **Step 2: Keep the Composer contract unchanged**

Confirm that `update:draft`, `send`, `stop`, `cite-material` and `add-skill` remain the only emitted events and that the focus method does not send or mutate draft content.

### Task 3: Make the three steps actionable

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue:1-175,906-927,989-1007`

- [ ] **Step 1: Add step starter templates and selection state**

Extend each `emptyWorkflow` item with a `starter` string and add:

```ts
const activeGuideStep = ref<string | null>(null)
const composerRef = ref<InstanceType<typeof AIWorkbenchComposer> | null>(null)

async function startGuideStep(step: { label: string; starter: string }) {
  activeGuideStep.value = step.label
  draft.value = step.starter
  await nextTick()
  composerRef.value?.focus()
}
```

Use mode-specific, multi-line starters with fields for context and desired output. Do not call `sendMessage()` from this handler.

- [ ] **Step 2: Replace static list items with accessible buttons**

Render each step as a full-width button inside its list item:

```vue
<button
  class="ai-workbench-empty__step-button"
  :class="{ 'ai-workbench-empty__step-button--active': activeGuideStep === step.label }"
  type="button"
  :aria-label="`开始：${step.title}`"
  :aria-pressed="activeGuideStep === step.label"
  @click="startGuideStep(step)"
>
  <span class="ai-workbench-empty__step-index">{{ step.label }}</span>
  <span class="ai-workbench-empty__step-copy"><strong>{{ step.title }}</strong><small>{{ step.description }}</small></span>
  <span class="ai-workbench-empty__step-action">{{ activeGuideStep === step.label ? '已载入' : '开始' }} →</span>
</button>
```

Attach `ref="composerRef"` to the one existing `AIWorkbenchComposer` instance.

### Task 4: Style the actionable state without changing the layout

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue:1093-1098`

- [ ] **Step 1: Move card surface styling to the button**

Keep the existing three-column grid and dimensions. Remove visual card properties from the `li`, then style `.ai-workbench-empty__step-button` with the same border, radius, padding and background. Add hover, `:focus-visible`, and active rules using existing `--line`, `--moss`, `--sage-soft`, `--paper-soft` and `--shadow-soft` tokens.

- [ ] **Step 2: Make the action affordance visible only when useful**

Keep `.ai-workbench-empty__step-action` subtle by default, then reveal it on hover, focus-visible and active states. The selected state must remain visible without hover so the user knows which template is loaded.

### Task 5: Verify the focused behavior

**Files:**
- No new files.

- [ ] **Step 1: Run the focused tests**

Run: `npm --prefix frontend test -- --run src/aiWorkbenchLayout.test.ts src/aiCenterUI.test.ts`

Expected: PASS for the updated contracts.

- [ ] **Step 2: Build the frontend**

Run: `npm --prefix frontend run build`

Expected: exit code 0; existing non-blocking bundler warnings are acceptable.

- [ ] **Step 3: Verify one interaction in the PC browser**

At `http://127.0.0.1:5174/student/ai?mode=research`, click the first workflow step and verify the card has `aria-pressed="true"`, the textarea contains the multi-line starter, and `document.activeElement` is the Composer textarea. Repeat the same check for opening and defense mode without sending a message.

- [ ] **Step 4: Check the diff**

Run: `git diff --check`

Expected: no whitespace errors. Do not run the full test suite.
