# 灵思 AI Workbench「研究动作优先」Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将学生端 `/student/ai` 改造成保留工作台侧栏、以研究动作和当前 Agent 为核心的浅色 AI Workbench，同时保留现有真实会话、流式响应、材料引用和确认写入业务。

**Architecture:** 保留 `AICenter.vue` 中的业务状态和 API 调用，把页面编排收敛为“工作台头部 → 同构模式栏 → Agent 动作轨道 → 会话流/空状态 → 统一 Composer”。历史、上下文和更多 Agent 使用独立覆盖层，不再放进会被 `overflow` 裁切的对话容器。初始化改为先渲染稳定壳层，再分别填充项目、Agent、会话和消息。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Vue Router, Vitest, Vite, 现有 AI API 与方案 B CSS 令牌。

---

## 文件与职责地图

- Modify: `frontend/src/pages/shared/AICenter.vue` — 保留 AI 业务状态，重排工作台模板、异步加载和抽屉挂载。
- Modify: `frontend/src/components/ai/AIModeTabs.vue` — 保留三模式和动态 Agent 数据，统一动作优先视觉、箭头轨道和无滚动条交互。
- Modify: `frontend/src/components/ai/AIToolPicker.vue` — 将更多 Agent 改为脱离父容器的固定抽屉/浮层，避免裁切并提供明确关闭行为。
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue` — 三模式共用输入结构，始终显示当前 Agent 和真实上下文权限。
- Modify: `frontend/src/components/ai/AIConversationHistory.vue` — 与新工作台浮层层级一致，保留搜索、新建、归档和恢复入口。
- Modify: `frontend/src/components/ai/AIContextDrawer.vue` — 保留材料 ID 选择和权限说明，统一为工作台抽屉样式。
- Modify: `frontend/src/aiCenterUI.test.ts` — 更新静态契约，覆盖同构模式、动作优先和确认规则。
- Modify: `frontend/src/studentAICenterEntry.test.ts` — 保留路由/权限回归，删除与旧追问文案绑定的断言。
- Modify: `frontend/src/progressiveLoadingUI.test.ts` — 明确 AI 静态壳层先于请求完成渲染。
- Create: `frontend/src/aiWorkbenchLayout.test.ts` — 针对页面结构、浮层定位和无失效旧结构的最小回归测试。
- Create: `docs/superpowers/specs/2026-08-26-ai-workbench-action-first-design.md` — 已确认的设计规格，作为实现验收依据。

## Task 1: 写入 RED 契约测试

**Files:**
- Modify: `frontend/src/aiCenterUI.test.ts`
- Modify: `frontend/src/studentAICenterEntry.test.ts`
- Modify: `frontend/src/progressiveLoadingUI.test.ts`
- Create: `frontend/src/aiWorkbenchLayout.test.ts`

- [ ] **Step 1: 替换与新规格冲突的旧断言。**

在 `frontend/src/aiCenterUI.test.ts` 中，将旧的“缺少信息时追问”断言替换为：

```ts
it('uses one direct composer for all three modes and shows the selected agent', () => {
  expect(source.match(/<AIWorkbenchComposer/g) ?? []).toHaveLength(1)
  expect(source).toContain('agent-name="currentAgent?.name"')
  expect(source).toContain('selected-material-ids="selectedMaterialIds"')
  expect(source).not.toContain('缺少信息时灵思会在对话中追问')
  expect(source).not.toContain('补充信息（可选）')
})
```

将 AI 页面结构断言扩展为：

```ts
it('keeps the action-first workbench layers in a stable order', () => {
  expect(source).toContain('ai-workbench-header')
  expect(source).toContain('ai-workbench-mode-region')
  expect(source).toContain('ai-workbench-conversation')
  expect(source).toContain('ai-workbench-composer-host')
  expect(source).toContain('ai-workbench-skeleton')
  expect(source).not.toContain('class="ai-simple-layout"')
  expect(source).not.toContain('v-if="false"')
})
```

- [ ] **Step 2: 增加浮层和 Agent 动作轨道契约。**

创建 `frontend/src/aiWorkbenchLayout.test.ts`：

```ts
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')
const page = read('./pages/shared/AICenter.vue')
const tabs = read('./components/ai/AIModeTabs.vue')
const picker = read('./components/ai/AIToolPicker.vue')

describe('action-first AI workbench layout', () => {
  it('uses a shared mode and action rail for opening, research and defense', () => {
    expect(tabs).toContain('data-agent-rail')
    expect(tabs).toContain('查看前面的 Agent')
    expect(tabs).toContain('查看后面的 Agent')
    expect(tabs).toContain('更多能力')
    expect(page).toContain('mode="opening"')
    expect(page).toContain('mode="research"')
    expect(page).toContain('mode="defense"')
  })

  it('mounts the agent picker as an overlay rather than an absolute child menu', () => {
    expect(picker).toContain('teleport')
    expect(picker).toContain('agent-picker-overlay')
    expect(picker).not.toContain('position: absolute')
    expect(picker).not.toContain('overflow-y: auto')
  })

  it('keeps direct-input language and explicit context permissions', () => {
    expect(page).toContain('直接输入你的研究目标')
    expect(page).not.toContain('填写后可让 AI 工具更准确')
    expect(read('./components/ai/AIWorkbenchComposer.vue')).toContain('不读取项目材料')
  })
})
```

- [ ] **Step 3: 明确渐进加载不以全部请求作为首屏条件。**

在 `frontend/src/progressiveLoadingUI.test.ts` 追加：

```ts
it('renders the AI frame before project, agent, and conversation requests finish', () => {
  const ai = read('./pages/shared/AICenter.vue')
  expect(ai).toContain('class="ai-workbench-frame"')
  expect(ai).toContain('class="ai-workbench-skeleton"')
  expect(ai).toContain('aria-label="正在准备灵思 AI"')
  expect(ai).not.toContain('v-if="!loading && !hasConversationMessages"')
})
```

- [ ] **Step 4: 运行 RED 测试并确认失败原因是新契约尚未实现。**

Run:

```bash
npm --prefix frontend exec vitest run src/aiCenterUI.test.ts src/aiWorkbenchLayout.test.ts src/progressiveLoadingUI.test.ts src/studentAICenterEntry.test.ts
```

Expected: FAIL，失败集中在缺少新的工作台结构、Teleported Agent picker 和直接输入文案；不得因为 TypeScript 语法错误失败。

## Task 2: 重排页面壳层并保留真实业务状态

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue`

- [ ] **Step 1: 用稳定壳层替换旧模板容器。**

将模板根部收敛为以下层级，业务事件继续调用现有函数：

```vue
<div class="page ai-center-page ai-workbench-frame">
  <header class="ai-workbench-header">
    <div class="ai-workbench-heading">
      <span class="eyebrow">研究工作台</span>
      <h1>灵思 AI</h1>
      <p>{{ aiPageDescription }}</p>
    </div>
    <div class="ai-workbench-header__actions">
      <span class="ai-workbench-context-pill">{{ workspaceContextLabel }}</span>
      <button type="button" :aria-expanded="historyOpen" aria-controls="conversation-history" @click="historyOpen = !historyOpen">历史会话</button>
      <button type="button" :aria-expanded="contextOpen" aria-controls="ai-context-drawer" @click="contextOpen = !contextOpen">项目上下文</button>
    </div>
  </header>
  <section class="ai-workbench-mode-region" aria-label="选择灵思 AI 工作模式">
    <AIModeTabs ... />
  </section>
  <section v-if="loading && !modeAgents.length" class="ai-workbench-skeleton" role="status" aria-label="正在准备灵思 AI"><i /><i /><i /></section>
  <section class="ai-workbench-conversation" :class="{ 'has-messages': hasConversationMessages }">
    <header v-if="hasConversationMessages" class="ai-session-bar">...</header>
    <section ref="chatStreamRef" class="chat-stream ai-conversation-stream">...</section>
    <div class="ai-workbench-composer-host"><AIWorkbenchComposer ... /></div>
  </section>
  <AIConversationHistory v-if="historyOpen" ... />
  <AIToolPicker v-if="agentOpen" ... />
  <AIContextDrawer ... />
</div>
```

- [ ] **Step 2: 移除旧的隐藏结构和重复入口。**

删除 `AIContextChooser`、`AIProjectAssistant` 在本页的已隐藏 `v-if="false"` 结构、旧 `ai-simple-layout`、旧 scope 卡片和“补充信息”相关展示；保留 `AIResearchWizard` 仅在结构化开题结果实际存在时显示。

- [ ] **Step 3: 改造初始化为可见壳层优先。**

将 `onMounted` 拆成以下确定性流程：

```ts
onMounted(() => {
  window.addEventListener('keydown', onGlobalKeydown)
  void bootstrapWorkbench()
})

async function bootstrapWorkbench() {
  loading.value = true
  void loadProjectsResource()
  void loadAgentsResource()
  try {
    await loadConversationsResource()
  } catch (reason) {
    error.value = errorMessage(reason, '历史会话暂时无法加载，请重试。')
  } finally {
    loading.value = false
    await nextTick()
    scrollToLatest('auto')
  }
}
```

`loadProjectsResource` 和 `loadAgentsResource` 只更新各自的 refs；会话创建仍使用既有 `createAIConversation`，开题、研究、成果表达的项目边界保持不变。请求失败时只标记对应区域错误，不清空已经渲染的壳层。

- [ ] **Step 4: 保持真实发送/重试/确认写入链路。**

发送 payload 继续通过 `materialSelectionScope(selectedMaterialIds.value)` 传入 `context_scope.selected_materials`；保留 `streamAIConversationMessage`、`retryAIConversationMessage`、`saveAIGenerationAsMaterial` 和 `createProjectFromOpening`，不添加自动提交逻辑。

- [ ] **Step 5: 运行页面结构测试。**

Run:

```bash
npm --prefix frontend exec vitest run src/aiCenterUI.test.ts src/aiWorkbenchLayout.test.ts src/progressiveLoadingUI.test.ts src/studentAICenterEntry.test.ts
```

Expected: Task 1 新增契约与页面壳层相关断言通过；旧业务断言若失败，只修复模板事件/属性，不改变 API 行为。

## Task 3: 统一模式栏、Agent 动作轨道和更多能力浮层

**Files:**
- Modify: `frontend/src/components/ai/AIModeTabs.vue`
- Modify: `frontend/src/components/ai/AIToolPicker.vue`
- Modify: `frontend/src/pages/shared/AICenter.vue`

- [ ] **Step 1: 让三个模式保持同构。**

在 `AIModeTabs.vue` 中继续以 `AI_WORKBENCH_MODES` 渲染所有模式，只把模式差异放在 `modelValue`；模式按钮均使用同一 `ai-mode-card` 结构。Agent 轨道保留 `visibleAgentCount = 4` 和左右箭头，根元素增加 `data-agent-rail`，轨道容器使用 `overflow: hidden` 但不出现滚动条。

- [ ] **Step 2: 保证选中 Agent 在工作台可见。**

Agent 胶囊的 `active` 状态继续由 `selectedAgent === agent.key` 决定；`AICenter.vue` 给 Composer 传入 `agent-name="currentAgent?.name"`，模式切换和选择 Agent 时不清空 `draft`。

- [ ] **Step 3: 将 Agent picker 改成固定覆盖层。**

在 `AIToolPicker.vue` 使用：

```vue
<Teleport to="body">
  <div class="agent-picker-overlay" role="presentation" @click.self="emit('close')">
    <section id="agent-menu" class="agent-picker-drawer" role="dialog" aria-modal="true" aria-label="选择 AI 工具（平台模板）">
      ...现有搜索、分类和分组按钮...
      <button type="button" aria-label="关闭 AI 工具选择" @click="emit('close')">×</button>
    </section>
  </div>
</Teleport>
```

新增 `close` emit；选择 Agent 后由父级关闭。覆盖层使用 `position: fixed`，抽屉不使用 `position: absolute`，内容区域不设置 `overflow-y: auto`，通过两列分组和 `max-height` 内部视觉压缩保证 1280px 完整展示。

- [ ] **Step 4: 执行模式和 Agent 交互测试。**

Run:

```bash
npm --prefix frontend exec vitest run src/aiWorkbenchLayout.test.ts src/aiCenterUI.test.ts
```

Expected: 三模式、箭头、动态 Agent、更多能力浮层和选中 Agent 契约全部通过。

## Task 4: Composer、历史和上下文抽屉统一视觉及状态

**Files:**
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue`
- Modify: `frontend/src/components/ai/AIConversationHistory.vue`
- Modify: `frontend/src/components/ai/AIContextDrawer.vue`

- [ ] **Step 1: 统一 Composer 的直接输入文案。**

保持一个 Composer 组件，按模式只切换 placeholder：

```ts
const placeholder = props.mode === 'opening'
  ? '写下你的观察或研究想法…'
  : props.mode === 'defense'
    ? '告诉我你想如何准备成果表达…'
    : '描述你要继续完成的研究任务…'
```

Composer 顶部显示 `当前 Agent · {{ agentName }}` 和项目权限；开题隐藏材料引用按钮，研究/成果表达继续显示材料 ID 选择入口。

- [ ] **Step 2: 统一抽屉层级和关闭行为。**

历史、上下文抽屉使用统一 `z-index: 100`、顶栏下方定位、遮罩点击关闭和 `aria-label`；保留既有搜索、新建、归档、恢复、材料选择、论文类型和引用来源功能。

- [ ] **Step 3: 补齐异步状态文案。**

加载时显示局部 skeleton；空 Agent 显示“当前模式暂无可用能力”；无会话显示直接输入 Composer；错误 banner 提供真实重试触发入口或保留现有 API 重试按钮。归档会话 Composer 继续禁用，生成时只禁用必要控件。

- [ ] **Step 4: 运行组件静态回归。**

Run:

```bash
npm --prefix frontend exec vitest run src/aiCenterUI.test.ts src/studentAICenterEntry.test.ts src/progressiveLoadingUI.test.ts
```

Expected: Composer、材料 ID、历史和确认写入相关断言通过。

## Task 5: 工作台样式收敛与浏览器验收

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/components/ai/AIModeTabs.vue`
- Modify: `frontend/src/components/ai/AIToolPicker.vue`
- Modify: `frontend/src/components/ai/AIWorkbenchComposer.vue`
- Modify: `frontend/src/components/ai/AIConversationHistory.vue`
- Modify: `frontend/src/components/ai/AIContextDrawer.vue`

- [ ] **Step 1: 替换页面级旧 CSS。**

保留方案 B 令牌，将工作区 CSS 收敛为：

```css
.ai-center-page { width: 100%; max-width: 1120px; min-width: 0; margin: 0 auto; padding: 28px 0 24px; }
.ai-workbench-frame { display: flex; flex-direction: column; min-height: calc(100vh - 66px); }
.ai-workbench-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; }
.ai-workbench-mode-region { display: grid; gap: 12px; margin-top: 24px; }
.ai-workbench-conversation { display: flex; min-height: 0; flex: 1 1 auto; flex-direction: column; }
.ai-workbench-composer-host { width: min(100%, 960px); margin: auto auto 8px; }
```

消息态 Composer 使用 sticky 底部；空态 Composer 位于工作台下半区但不制造大块顶部空白。页面不设置横向滚动，Agent 轨道隐藏滚动条但保留箭头操作。

- [ ] **Step 2: 完成 1280px/1440px 浏览器检查。**

使用现有 Node REPL 浏览器会话打开：

```text
http://127.0.0.1:5173/student/ai
http://127.0.0.1:5173/student/ai?mode=opening
http://127.0.0.1:5173/student/ai?mode=research&projectId=91
http://127.0.0.1:5173/student/ai?mode=defense&projectId=91
```

分别设置 1280px 和 1440px，核对：首屏壳层先出现、模式结构一致、Agent 选中名称可见、更多能力不裁切、无横向滚动、开题不出现材料引用、研究/表达显示项目上下文。

- [ ] **Step 3: 检查控制台错误和旧文案。**

浏览器 Console 不应出现 Vue unresolved component、重复 key 或未处理请求错误；页面不应出现“补充信息（可选）”“缺少信息时灵思会在对话中追问”、旧隐藏 `v-if="false"` 或 Agent picker 内部滚动条。

- [ ] **Step 4: 运行本轮定向验证。**

```bash
npm --prefix frontend exec vitest run src/aiCenterUI.test.ts src/aiWorkbenchLayout.test.ts src/studentAICenterEntry.test.ts src/progressiveLoadingUI.test.ts
npm --prefix frontend run build
git diff --check
```

Expected: 相关 Vitest 全部通过，Vite build 退出码为 0，`git diff --check` 无输出。根据用户要求，本轮不执行全量 E2E 和后端全量测试。

## Spec coverage review

- 页面保留学生侧栏：Task 2。
- A「研究动作优先」层级和三模式同构：Task 2、Task 3。
- 动态平台 Agent、箭头、更多能力浮层：Task 3。
- 选中 Agent 始终显示、直接输入不追问：Task 2、Task 4。
- 项目/任务/材料权限和材料 ID：Task 2、Task 4。
- 历史与上下文抽屉：Task 4。
- 先壳层后资源的渐进加载：Task 2。
- 流式发送、停止、重试、草稿、开题确认：Task 2、Task 4。
- 1280px/1440px、无横向滚动和无裁切：Task 5。
- 不改后端模型、权限和自动写入规则：所有任务的边界。
