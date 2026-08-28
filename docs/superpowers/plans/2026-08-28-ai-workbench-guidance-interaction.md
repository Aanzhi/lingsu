# AI Workbench Guidance Interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将新建对话态的三张静态步骤卡变成可选择、可编辑、可确认生成的任务入口。

**Architecture:** AICenter.vue 继续拥有模式化工作流数据；每个步骤由字段配置驱动，点击时打开独立的填空工作框，字段值与底部 Composer draft 分离。确认生成后将已填写字段组合为结构化文本，通过现有 `sendMessage(contentOverride)` 链路进入正式对话，不自动新增 API 或 Agent。

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
expect(page).toContain('guideDialogOpen && guideDialogStep')
expect(page).toContain('guideDialogFieldRefs.value[0]?.focus()')
expect(page).toContain('guideDialogValues[field.key]')
expect(page).toContain('guideDialogComplete')
expect(page).toContain('@click="generateGuideStep"')
expect(composer).not.toContain('defineExpose({ focus: focusTextarea })')
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `npm --prefix frontend test -- --run src/aiWorkbenchLayout.test.ts src/aiCenterUI.test.ts`

Expected: FAIL because the field configuration, fill-in form and required-field validation do not exist yet.

### Task 2: Add the step work dialog state and generation flow

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue:1-250,312,654,958-1070`

- [ ] **Step 1: Add isolated dialog state**

Add `EmptyWorkflowField` with `key`, `label`, `placeholder`, and `required` properties. Extend each `EmptyWorkflowStep` with a `fields` array. Add `guideDialogOpen`, `guideDialogStep`, `guideDialogValues` and a field-ref array. `startGuideStep(step)` must set the selected card, initialize every field value to an empty string, open the dialog, and focus the first field after `nextTick()`; it must not mutate the Composer `draft`.

- [ ] **Step 2: Reuse the current send chain only after confirmation**

Add `guideDialogComplete` to require every `required` field to contain non-whitespace text. Add `generateGuideStep()` that builds `任务目标 + 字段标题 + 字段值`, closes the dialog, and calls `sendMessage(generatedContent, { includeUserMessage: true })` only when required fields are complete and the normal composer is not disabled. Add `closeGuideDialog()` that only closes/reset state.

### Task 3: Render an independent step work dialog

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue:958-1070`

- [ ] **Step 1: Replace static list items with accessible buttons**

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
  <span class="ai-workbench-empty__step-action">{{ activeGuideStep === step.label ? '已打开' : '打开' }} →</span>
</button>
```

Add a dialog after the existing overlays:

```vue
<div v-if="guideDialogOpen && guideDialogStep" class="ai-confirm-backdrop ai-guide-dialog-backdrop" role="presentation" @click.self="closeGuideDialog">
  <section class="ai-guide-dialog" role="dialog" aria-modal="true" aria-labelledby="guide-dialog-title">
    <header>...步骤标题和关闭按钮...</header>
    <label v-for="field in guideDialogStep.fields" :key="field.key">
      <span>{{ field.label }}<em v-if="field.required">必填</em></span>
      <textarea ref="guideDialogFieldRefs" :placeholder="field.placeholder" v-model="guideDialogValues[field.key]" />
    </label>
    <footer><button @click="closeGuideDialog">取消</button><button :disabled="!guideDialogComplete" @click="generateGuideStep">开始生成</button></footer>
  </section>
</div>
```

### Task 4: Style the actionable state and dialog without changing the layout

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue:1093-1098`

- [ ] **Step 1: Keep the card surface styling on the button**

Keep the existing three-column grid and dimensions. Remove visual card properties from the `li`, then style `.ai-workbench-empty__step-button` with the same border, radius, padding and background. Add hover, `:focus-visible`, and active rules using existing `--line`, `--moss`, `--sage-soft`, `--paper-soft` and `--shadow-soft` tokens.

- [ ] **Step 2: Make the action affordance visible only when useful**

Keep `.ai-workbench-empty__step-action` subtle by default, then reveal it on hover, focus-visible and active states. The selected state must remain visible without hover so the user knows which template is loaded.

- [ ] **Step 3: Style the dialog as a focused working surface**

Use the existing `ai-confirm-backdrop`, `--paper`, `--line-dark`, `--moss` and `--shadow-hover` tokens. The dialog must have a readable title, multiple compact labeled fill-in fields, required-state hints, a visible cancel action and a primary “开始生成” action. Clicking the backdrop closes it; it must not add mobile-only layout rules.

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

At `http://127.0.0.1:5174/student/ai?mode=research`, click the first workflow step and verify the card has `aria-pressed="true"`, an independent `role="dialog"` is visible, multiple labeled fill-in fields are rendered, the first field receives focus, the primary button is disabled until required fields are filled, and the bottom Composer draft is unchanged. Repeat the same check for opening and defense mode without sending a message.

- [ ] **Step 4: Check the diff**

Run: `git diff --check`

Expected: no whitespace errors. Do not run the full test suite.
