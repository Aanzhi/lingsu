# AI 工作台顶部与输入操作区布局优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变 AI 工作台功能和主布局的前提下，稳定顶部上下文操作区与底部输入操作栏的层级、间距和对齐。

**Architecture:** 保留 `AICenter.vue` 对工作台级别结构和顶部操作的控制，将 Composer 的底部操作拆为“工具组—快捷键提示—发送操作”三个明确的 flex 区域。历史会话、Skill 选择、发送和停止事件继续通过现有 emit/handler 链路传递，不新增数据流。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, scoped CSS, Vitest, Vue/Vite production build, in-app browser verification.

**Spec:** `docs/superpowers/specs/2026-08-28-ai-workbench-action-layout-design.md`

## Global Constraints

- `不增加新的 AI 能力、Skill 或会话数据字段。`
- `不改变三个主 Agent 的模式切换逻辑。`
- `不改动对话历史筛选、标题生成和结果卡片逻辑。`
- `不进行移动端布局设计或适配扩展。`
- `采用定向验证，不执行全量测试。`
- 不新增后端接口或持久化逻辑。
- 保护当前工作区已有未提交改动；提交或验证时只处理本计划涉及的文件和新增代码。

## File Map

- Modify: `frontend/src/pages/shared/AICenter.vue` — 顶部当前上下文/历史入口的结构标识、对齐规则，以及新对话页对 Composer 提示文字的覆盖样式。
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue` — 底部工具组、快捷键提示和发送操作的结构与稳定横向排列；保留通用材料引用能力。
- Modify: `frontend/src/aiWorkbenchLayout.test.ts` — 顶部和底部布局契约测试，确保三个模式共用稳定的操作区规则。

### Task 1: Write failing layout contract tests

**Files:**
- Modify: `frontend/src/aiWorkbenchLayout.test.ts`

**Interfaces:**
- `AICenter.vue` must expose `ai-workbench-header__actions`, `ai-workbench-context-pill` and an explicit `ai-workbench-history-button` class without changing the existing `历史会话` button behavior.
- `AIWorkbenchComposer.vue` must expose `ai-workbench-composer__tools` and `ai-workbench-composer__action` wrappers around the existing buttons.
- The Composer footer must declare a flex layout where `.composer-hint` can shrink and ellipsize without pushing `.send-button`.

- [ ] **Step 1: Add the header hierarchy assertions**

Add this test after the existing test that checks the shared context pill:

```ts
  it('keeps the current context primary and history as a secondary header action', () => {
    expect(page).toContain('class="ai-workbench-header__actions"')
    expect(page).toContain('class="ai-workbench-context-pill"')
    expect(page).toContain('class="text-button ai-workbench-history-button"')
    expect(page).toContain('.ai-workbench-header__actions { align-items: center;')
    expect(page).toContain('gap: 14px;')
    expect(page).toContain('.ai-workbench-context-pill { flex: 0 1 360px;')
  })
```

- [ ] **Step 2: Add the Composer three-part toolbar assertions**

Add this test after the existing Composer/material citation test:

```ts
  it('keeps Composer actions in a stable tools-hint-send row', () => {
    expect(composer).toContain('class="ai-workbench-composer__tools"')
    expect(composer).toContain('class="ai-workbench-composer__action"')
    expect(composer).toContain('.ai-workbench-composer__footer { display: flex;')
    expect(composer).toContain('.ai-workbench-composer__tools { display: flex;')
    expect(composer).toContain('.composer-hint { flex: 1 1 auto;')
    expect(composer).toContain('text-overflow: ellipsis;')
    expect(composer).toContain('white-space: nowrap;')
    expect(composer).toContain('.send-button { width: 70px;')
  })
```

- [ ] **Step 3: Update the existing new-page hint assertion**

Change the existing reference assertion in `keeps the reference treatment coherent and scoped to the new main area` from:

```ts
expect(page).toContain('.ai-workbench-page--new :deep(.composer-hint) { margin-left: 0; margin-right: auto;')
```

to:

```ts
expect(page).toContain('.ai-workbench-page--new :deep(.composer-hint) { margin: 0;')
```

- [ ] **Step 4: Run the focused test to confirm the tests fail for the missing structure**

Run from `frontend/`:

```bash
npm test -- --run src/aiWorkbenchLayout.test.ts
```

Expected: FAIL because the new wrapper classes and shared spacing declarations do not exist yet; existing tests unrelated to the new contract remain green.

### Task 2: Implement the A-variant header action hierarchy

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue:890-893` — new-conversation header actions.
- Modify: `frontend/src/pages/shared/AICenter.vue:1067-1074` — header action styles.

**Interfaces:**
- Consumes the existing `workspaceContextLabel`, `historyConversations`, `historyOpen`, `sending` and `loading` state.
- Produces the same `历史会话` button with the same `openHistory` handler, `aria-controls`, `aria-expanded`, disabled state and conditional rendering.

- [ ] **Step 1: Add an explicit secondary-action class without changing behavior**

Change only the class attribute on the existing history button:

```vue
<button v-if="historyConversations.length" class="text-button ai-workbench-history-button" type="button" :disabled="sending || loading" aria-controls="conversation-history" :aria-expanded="historyOpen" @click="openHistory">历史会话</button>
```

Keep the context pill immediately before it:

```vue
<span class="ai-workbench-context-pill">{{ workspaceContextLabel }}</span>
```

- [ ] **Step 2: Apply the stable header spacing rules**

Replace the current header action rule with:

```css
.ai-workbench-header__actions { display: flex; align-items: center; justify-content: flex-end; gap: 14px; min-width: 0; max-width: 100%; padding-top: 2px; }
.ai-workbench-context-pill { display: inline-flex; align-items: center; flex: 0 1 360px; min-width: 0; max-width: 360px; min-height: 32px; overflow: hidden; padding: 8px 11px; border: 1px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--paper); color: var(--moss-dark); font-size: 12px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.ai-workbench-history-button { flex: 0 0 auto; }
```

Do not add another project selector or duplicate project text in the Composer.

- [ ] **Step 3: Run the header-focused test**

Run:

```bash
npm test -- --run src/aiWorkbenchLayout.test.ts
```

Expected: the header contract passes; the Composer contract remains red until Task 3.

### Task 3: Implement the stable Composer tools-hint-send row

**Files:**
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue:61-70` — footer markup wrappers.
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue:75-95` — shared Composer styles.
- Modify: `frontend/src/pages/shared/AICenter.vue:1128-1129` — new-page Composer overrides.

**Interfaces:**
- Consumes the existing `showSkillPicker`, `skillName`, `showMaterialCitation`, `selectedMaterialIds`, `sending`, `disabled`, `canSend`, `showSendIcon` props and existing emits.
- Produces unchanged `add-skill`, `cite-material`, `send` and `stop` emits, with the same accessible labels and button text.

- [ ] **Step 1: Wrap optional tools together**

Inside `.ai-workbench-composer__footer`, wrap the existing Skill and material buttons in one tools group, keep the hint as the middle item, and wrap the send/stop conditional buttons in one action group:

```vue
<div class="ai-workbench-composer__tools">
  <button v-if="props.showSkillPicker" class="composer-tool-button composer-skill-button" :class="{ 'composer-skill-button--selected': props.skillName }" type="button" :disabled="props.disabled" :aria-label="props.skillName ? `切换技能：${props.skillName}` : '添加技能'" @click="emit('add-skill')">
    <span v-if="props.skillName">＋ 技能 · {{ props.skillName }}</span>
    <span v-else>＋ 添加技能</span>
  </button>
  <button v-if="props.showMaterialCitation" class="composer-tool-button selected-material" type="button" :disabled="props.disabled || !canCiteMaterials" @click="emit('cite-material')">＋ 引用材料<span v-if="props.selectedMaterialIds?.length"> · 已选 {{ props.selectedMaterialIds.length }}</span></button>
</div>
<span class="composer-hint">Enter 发送 · Shift+Enter 换行</span>
<div class="ai-workbench-composer__action">
  <button v-if="props.sending" class="send-button send-button--stop" type="button" @click="emit('stop')">停止</button>
  <button v-else class="send-button" type="button" :disabled="props.disabled || !props.canSend" @click="emit('send')">发送<el-icon v-if="props.showSendIcon" class="send-button__icon" aria-hidden="true"><ArrowRight /></el-icon></button>
</div>
```

Do not change the surrounding textarea or any event expression.

- [ ] **Step 2: Use flex groups and protect the fixed send action**

Replace the current footer/hint styles with these shared rules while retaining the existing colors and focus states:

```css
.ai-workbench-composer__footer { display: flex; align-items: center; gap: 12px; min-width: 0; color: var(--muted); font-size: 10px; }
.ai-workbench-composer__tools { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 0 1 auto; }
.ai-workbench-composer__action { display: flex; align-items: center; justify-content: flex-end; flex: 0 0 auto; }
.composer-hint { min-width: 0; overflow: hidden; flex: 1 1 auto; margin: 0; color: var(--muted-light); text-overflow: ellipsis; white-space: nowrap; }
.composer-skill-button--selected, .selected-material { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.send-button { width: 70px; min-width: 70px; }
```

Retain the existing `@media (max-width: 680px)` block unless the base layout makes one of its declarations invalid; do not add a new mobile layout or new breakpoint.

- [ ] **Step 3: Remove the new-page auto-margin override**

Change the AICenter new-page rule to keep the hint neutral inside the flex row:

```css
.ai-workbench-page--new :deep(.composer-hint) { margin: 0; color: var(--muted-light); }
```

Keep the existing new-page send sizing and colors, but add `width: 80px;` beside its existing `min-width: 80px;` so the student workbench button does not move when the hint or Skill label changes.

- [ ] **Step 4: Run the focused tests to verify the Composer contract**

Run:

```bash
npm test -- --run src/aiWorkbenchLayout.test.ts src/aiCenterUI.test.ts
```

Expected: all tests in both files pass.

### Task 4: Run targeted regression and browser verification

**Files:**
- Test only; no additional source files.

**Interfaces:**
- Verifies the final shared layout against the existing presentation and workbench contracts.

- [ ] **Step 1: Run the related frontend test set**

Run from `frontend/`:

```bash
npm test -- --run src/stores/presentationModel.test.ts src/aiConversationHistoryUI.test.ts src/aiCenterUI.test.ts src/aiWorkbenchLayout.test.ts src/aiResultCard.test.ts src/studentAICenterEntry.test.ts src/stores/aiWorkbenchModel.test.ts
```

Expected: all selected test files pass; do not run the full test suite.

- [ ] **Step 2: Type-check and build the frontend**

Run:

```bash
npm run build
```

Expected: `vue-tsc --noEmit` and `vite build` complete successfully. Existing dependency annotation and chunk-size warnings may remain; no new TypeScript error is acceptable.

- [ ] **Step 3: Verify the three desktop modes in the browser**

Use the existing in-app browser tab at viewport `1203x998` and inspect these URLs:

```text
http://127.0.0.1:5173/student/ai?mode=opening
http://127.0.0.1:5173/student/ai?mode=research&projectId=91
http://127.0.0.1:5173/student/ai?mode=defense&projectId=91
```

For each empty state, confirm:

- `.ai-workbench-header__actions` keeps the context pill as the primary item and `历史会话` aligned as the secondary item.
- `.ai-workbench-composer__tools`, `.composer-hint`, and `.ai-workbench-composer__action` remain on one baseline.
- `.send-button` has the same width and right edge after switching modes.
- No mode-specific vertical drift returns; the shared workbench content grid remains unchanged.

Then inspect the Skill picker and send-disabled state once on the opening page. Confirm Skill selection and button behavior still work without running a message.

- [ ] **Step 4: Check the diff and preserve unrelated work**

Run from the repository root:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; existing unrelated modifications remain untouched and no generated visual-companion files are staged as product code.
