# 灵思 AI 中心布局重构（方案 D + D2 · v2）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AICenter.vue 从「阶段 Tab + Agent Pills 纵向堆叠 + 5 层 Composer + 双写上下文」重构为「意图 4 Tab + 阶段二级过滤 Chips + D2 三段式紧凑 Composer + 左权威右只读的三栏布局」，同屏密度提升 30%，分类理解从 3 步降到 1 步，彻底消除左右栏操作冲突。

**Architecture:** 采用「Pinia 单一状态源」+「子组件拆分」的分层架构。将 interactionModel 从纯函数模块升级为 Pinia store，统一承载 currentStepId、referenceStepIds、referenceMaterialIds；aiModel 新增意图分类常量；将 1500 行级的 AICenter.vue 拆分为 6 个独立子组件（AICIntentTabs、AICTreeLegend + AICJourneyTree、AICContextPanel、AICD2Composer、CheckResultSummary），每个组件的 props/events 严格遵循「一个文件解决一个问题」。**左栏 JourneyTree 是参考上下文的唯一写入权威**，右栏 ContextPanel 和 Composer 底栏 chips 均为只读派生视图。

**Tech Stack:** Vue 3.5 + TypeScript 5.7 + Pinia 2.2 + Element Plus 2.8 + Vitest 2.1

---

## 文件结构总览

| 操作 | 路径 | 职责 |
| --- | --- | --- |
| **升级** | `frontend/src/stores/interactionModel.ts` | 从纯操作消息模块 → Pinia defineStore：承载 currentStepId / referenceStepIds / referenceMaterialIds 及 actions |
| **新增** | `frontend/src/stores/interactionModel.test.ts` | 新 store 的单元测试（setCurrentStep / toggleReferenceStep / toggleReferenceMaterial） |
| **修改** | `frontend/src/stores/aiModel.ts` | 新增 INTENTS 常量、agentIntent() 映射函数、STAGE_FILTER_CHIPS 常量、filterAgentsByIntentAndStage() |
| **新增** | `frontend/src/stores/aiModel.test.ts` | agentIntent() 分类映射、意图 × 阶段交集过滤逻辑的单元测试 |
| **新增** | `frontend/src/components/shared/CheckResultSummary.vue` | 通用「检查类摘要卡」：分数胶囊 + 缺失/冲突 + 问题清单（含优先级）+ details 折叠原始 JSON |
| **新增** | `frontend/src/components/shared/CheckResultSummary.test.ts` | CheckResultSummary 结构快照 + coverage score class 等测试 |
| **重写** | `frontend/src/components/ConsistencyCheckCard.vue` | 复用 CheckResultSummary，自身仅做调用 AI + 解析 + 传 props |
| **新增** | `frontend/src/pages/shared/components/AICIntentTabs.vue` | 中栏顶部：意图 4 Tab（带数量胶囊）→ 旅程过滤 Chips 行 → Agent 卡片网格 |
| **新增** | `frontend/src/pages/shared/components/AICTreeLegend.vue` | 左栏顶部：3 色图例（当前步骤 / 已选为参考 / 有材料） |
| **新增** | `frontend/src/pages/shared/components/AICJourneyTree.vue` | 左栏主体：阶段折叠 + 步骤行 3px 色条 + hover「+参考」按钮（唯一写入入口） |
| **新增** | `frontend/src/pages/shared/components/AICContextPanel.vue` | 右栏「上下文」Tab：只读派生视图，按权重排序，提供「从左侧操作」引导文案；无增删按钮 |
| **新增** | `frontend/src/pages/shared/components/AICD2Composer.vue` | 中栏底部 D2 三段式 Composer：顶工具栏（快捷宏/变量/上下文/助手胶囊）→ Textarea（含只读上下文注入块） → 底栏（chips 摘要/配额/发送按钮） |
| **重写** | `frontend/src/pages/shared/AICenter.vue` | 精简为 ~300 行「装配器」：加载数据 → 实例化上述 6 组件 → 三栏 CSS Grid → 提供发送 generate() 方法 |
| **新增** | `frontend/src/pages/shared/AICenter.test.ts` | 集成级计算属性测试：空态判定、意图切换后 selectedAgent 自动归一化、三栏同步更新逻辑 |

---

### Task 1: 升级 interactionModel 为 Pinia store（底层状态权威）

**Files:**
- **Modify:** `frontend/src/stores/interactionModel.ts` (保留原 operationSuccess / reviewCompletionAction 导出，下方追加 defineStore)
- **Create:** `frontend/src/stores/interactionModel.test.ts`

#### 背景
当前 `interactionModel.ts` 仅存 3 条纯消息映射函数。本任务把它升级为 AICenter 的**唯一上下文状态源**，所有后续组件（左 Tree / 右 Panel / Composer）全部依赖此 store，不允许各自维护 ref。

- [ ] **Step 1: 写 failing 单元测试**

创建 `frontend/src/stores/interactionModel.test.ts`：

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useInteractionStore } from '../interactionModel'

describe('useInteractionStore', () => {
  beforeEach(() => { setActivePinia(createPinia()) })

  it('currentStepId 默认为 null，setCurrentStep 后唯一化（同ID再点=取消）', () => {
    const s = useInteractionStore()
    expect(s.currentStepId).toBeNull()
    s.setCurrentStep(17)
    expect(s.currentStepId).toBe(17)
    s.setCurrentStep(22)
    expect(s.currentStepId).toBe(22)
    s.setCurrentStep(22)
    expect(s.currentStepId).toBeNull()
  })

  it('toggleReferenceStep 做集合 toggle，不重复；不允许把 currentStep 加入 reference', () => {
    const s = useInteractionStore()
    expect(s.referenceStepIds).toEqual([])
    s.toggleReferenceStep(5)
    s.toggleReferenceStep(8)
    expect(s.referenceStepIds).toEqual([5, 8])
    s.toggleReferenceStep(5)
    expect(s.referenceStepIds).toEqual([8])
    s.setCurrentStep(5)
    s.toggleReferenceStep(5)
    expect(s.referenceStepIds).not.toContain(5)
  })

  it('toggleReferenceMaterial 做集合 toggle', () => {
    const s = useInteractionStore()
    s.toggleReferenceMaterial(101)
    s.toggleReferenceMaterial(102)
    expect(s.referenceMaterialIds).toEqual([101, 102])
    s.toggleReferenceMaterial(101)
    expect(s.referenceMaterialIds).toEqual([102])
  })

  it('getters：isCurrentStep / isReferenceStep / isReferenceMaterial / referenceCount', () => {
    const s = useInteractionStore()
    s.setCurrentStep(3)
    s.toggleReferenceStep(5)
    s.toggleReferenceMaterial(77)
    expect(s.isCurrentStep(3)).toBe(true)
    expect(s.isCurrentStep(4)).toBe(false)
    expect(s.isReferenceStep(5)).toBe(true)
    expect(s.isReferenceStep(3)).toBe(false)   // current 不占 reference 槽
    expect(s.isReferenceMaterial(77)).toBe(true)
    expect(s.isReferenceMaterial(88)).toBe(false)
    expect(s.referenceCount).toBe(2)
  })

  it('clearAll 重置所有引用', () => {
    const s = useInteractionStore()
    s.setCurrentStep(3)
    s.toggleReferenceStep(5)
    s.toggleReferenceMaterial(77)
    s.clearAll()
    expect(s.currentStepId).toBeNull()
    expect(s.referenceStepIds).toEqual([])
    expect(s.referenceMaterialIds).toEqual([])
  })
})
```

- [ ] **Step 2: 运行测试，确认全部 FAIL（`useInteractionStore` 未定义）**

```bash
cd frontend && npx vitest run src/stores/interactionModel.test.ts
```

Expected: FAIL with `Cannot find module '../interactionModel'` 或 `useInteractionStore is not a function`

- [ ] **Step 3: 写最小实现（升级 interactionModel.ts）**

用下面内容**完全替换** `frontend/src/stores/interactionModel.ts`（保留原消息函数 + 新增 store）：

```ts
import { defineStore } from 'pinia'

// —— 原有消息映射函数（teacher/platform 端仍用，保持不变）——
export type OperationKind = 'claim' | 'review_approved' | 'review_returned' | 'member_approved' | 'member_rejected' | 'school_enabled' | 'school_disabled' | 'invite_reset' | 'competition_published' | 'competition_withdrawn' | 'search'
const messages: Record<OperationKind, string> = {
  claim: '项目已认领，研究任务地图已生成。',
  review_approved: '材料已通过，下一任务已解锁。',
  review_returned: '修订意见已发送，学生会在任务台看到优先修复任务。',
  member_approved: '成员已加入项目团队。',
  member_rejected: '成员邀请已拒绝。',
  school_enabled: '学校授权已恢复，可以继续写入。',
  school_disabled: '学校已停用，师生保留历史只读访问。',
  invite_reset: '邀请码已重置，请将新邀请码安全交给学校。',
  competition_published: '赛事已发布到全平台。',
  competition_withdrawn: '赛事已撤回，不再对师生展示。',
  search: '筛选结果已更新。',
}
export function operationSuccess(kind: OperationKind) { return messages[kind] }
export function reviewCompletionAction() { return '返回审核队列' }

// —— 新增：AI 中心交互 store（左右栏 / Composer 的单一状态权威）——
export const useInteractionStore = defineStore('aic-interaction', {
  state: () => ({
    currentStepId: null as number | null,
    referenceStepIds: [] as number[],
    referenceMaterialIds: [] as number[],
  }),
  getters: {
    isCurrentStep: (state) => (id: number) => state.currentStepId === id,
    isReferenceStep: (state) => (id: number) =>
      state.currentStepId !== id && state.referenceStepIds.includes(id),
    isReferenceMaterial: (state) => (id: number) => state.referenceMaterialIds.includes(id),
    /** 参考项总数（不含当前步骤），用于 Composer 底栏 chip 统计 */
    referenceCount: (state) => state.referenceStepIds.length + state.referenceMaterialIds.length,
  },
  actions: {
    setCurrentStep(stepId: number | null) {
      if (stepId === null) { this.currentStepId = null; return }
      // 同 ID 再点 = 取消；新 ID 直接切换
      this.currentStepId = this.currentStepId === stepId ? null : stepId
      // 语义约束：current step 永远不进入 reference 集合
      this.referenceStepIds = this.referenceStepIds.filter((x) => x !== this.currentStepId)
    },
    toggleReferenceStep(stepId: number) {
      if (this.currentStepId === stepId) return  // 不允许把 currentStep 加入 reference
      const idx = this.referenceStepIds.indexOf(stepId)
      if (idx >= 0) this.referenceStepIds.splice(idx, 1)
      else this.referenceStepIds.push(stepId)
    },
    toggleReferenceMaterial(materialId: number) {
      const idx = this.referenceMaterialIds.indexOf(materialId)
      if (idx >= 0) this.referenceMaterialIds.splice(idx, 1)
      else this.referenceMaterialIds.push(materialId)
    },
    clearAll() {
      this.currentStepId = null
      this.referenceStepIds = []
      this.referenceMaterialIds = []
    },
  },
})
```

- [ ] **Step 4: 跑测试，确认全部 PASS**

```bash
cd frontend && npx vitest run src/stores/interactionModel.test.ts
```

Expected: 5 passing。若 `setCurrentStep(22) 再点 22 → null` 的取消语义不符合真实产品需求，请改成无条件赋值：`this.currentStepId = stepId`，同步调整对应测试断言即可。

- [ ] **Step 5: Commit**

```bash
cd /Users/anzhi/Desktop/雷灵/星辰/lingsu
git add frontend/src/stores/interactionModel.ts frontend/src/stores/interactionModel.test.ts
git commit -m "feat(aic): upgrade interactionModel to Pinia store with current/ref state"
```

---

### Task 2: 扩展 aiModel.ts 添加意图分类常量

**Files:**
- **Modify:** `frontend/src/stores/aiModel.ts` (append after existing functions)
- **Create:** `frontend/src/stores/aiModel.test.ts`

#### 背景
原 `aiModel.ts` 仅有状态辅助函数与 prompt 组合器。本任务新增「用户意图 × 研究旅程」二级分类体系，供 Task 5 AICIntentTabs 直接消费。

- [ ] **Step 1: 写 failing 单元测试**

创建 `frontend/src/stores/aiModel.test.ts`：

```ts
import { describe, expect, it } from 'vitest'
import type { AIAgent } from '../api'
import {
  INTENTS, STAGE_FILTERS, agentIntent, agentStage,
  filterAgentsByIntentAndStage, type IntentKey,
} from '../aiModel'

function mkAgent(partial: Partial<AIAgent> & { key: string; name: string; category: string }): AIAgent {
  return {
    id: -1, role: 'student', description: '', system_instruction: '', prompt_template: '',
    input_schema: [], context_scope_default: { project_basics: true },
    is_active: true, school: null, order: 0, ...partial,
  }
}
const sample: AIAgent[] = [
  mkAgent({ key: 'topic',     name: '选题建议',           category: '开题' }),   // idea
  mkAgent({ key: 'outline',   name: '结构大纲',           category: '写作' }),   // idea
  mkAgent({ key: 'draft',     name: '报告起草',           category: '写作' }),   // write
  mkAgent({ key: 'chart',     name: '图表说明',           category: '写作' }),   // write
  mkAgent({ key: 'polish',    name: '文本润色',           category: '写作' }),   // edit
  mkAgent({ key: 'ref-fmt',   name: '参考文献规范化',     category: '写作' }),   // edit
  mkAgent({ key: 'consist',   name: '一致性检查',         category: '答辩' }),   // check
  mkAgent({ key: 'evidence',  name: '证据完整性',         category: '答辩' }),   // check
]

describe('意图 / 阶段 二级分类', () => {
  it('INTENTS 有且仅有 4 个，顺序固定 idea → write → edit → check', () => {
    expect(INTENTS.map((i) => i.key)).toEqual<IntentKey[]>(['idea', 'write', 'edit', 'check'])
  })
  it('STAGE_FILTERS 包含 不限 + 5 阶段 共 6 项', () => {
    expect(STAGE_FILTERS.map((s) => s.key)).toEqual(['_all_', 'kaoti', 'sheji', 'zhizuo', 'chengguo', 'dabian'])
  })
  it('agentIntent 把 sample 8 条 2/2/2/2 分桶', () => {
    const counts = { idea: 0, write: 0, edit: 0, check: 0 }
    sample.forEach((a) => { counts[agentIntent(a)]++ })
    expect(counts).toEqual({ idea: 2, write: 2, edit: 2, check: 2 })
  })
  it('agentStage 将 category 映射到阶段 key', () => {
    expect(agentStage(sample[0])).toBe('kaoti')
    expect(agentStage(sample[6])).toBe('dabian')
    expect(agentStage(mkAgent({ key: 'x', name: 'X', category: '实验' }))).toBe('zhizuo')
    expect(agentStage(mkAgent({ key: 'y', name: 'Y', category: '写作' }))).toBe('chengguo')
    expect(agentStage(mkAgent({ key: 'z', name: 'Z', category: '未知' }))).toBe('sheji') // 兜底
  })
  it('filterAgentsByIntentAndStage: idea × _all_ = 2 条', () => {
    const r = filterAgentsByIntentAndStage(sample, 'idea', '_all_')
    expect(r.map((a) => a.key)).toEqual(['topic', 'outline'])
  })
  it('filterAgentsByIntentAndStage: check × dabian = 2 条', () => {
    const r = filterAgentsByIntentAndStage(sample, 'check', 'dabian')
    expect(r.map((a) => a.key)).toEqual(['consist', 'evidence'])
  })
  it('filterAgentsByIntentAndStage: idea × chengguo = 空', () => {
    expect(filterAgentsByIntentAndStage(sample, 'idea', 'chengguo')).toEqual([])
  })
})
```

- [ ] **Step 2: 运行测试 → FAIL**

```bash
cd frontend && npx vitest run src/stores/aiModel.test.ts
```

Expected: FAIL with `INTENTS is not exported`

- [ ] **Step 3: 写最小实现（扩展 aiModel.ts）**

**在原文件末尾追加**以下内容。注意 `import type { AIAgent }` 若文件开头已有则删掉这行（保持 TS strict 无重复 import）：

```ts
import type { AIAgent } from '../api'

// —— 研究旅程阶段（供 AICenter 与过滤器复用）——
export const STAGES: Array<{ key: string; label: string }> = [
  { key: 'kaoti',    label: '立项与开题' },
  { key: 'sheji',    label: '方案与设计' },
  { key: 'zhizuo',   label: '制作与测试' },
  { key: 'chengguo', label: '成果整理' },
  { key: 'dabian',   label: '答辩与展示' },
]
const CATEGORY_TO_STAGE: Record<string, string> = {
  '开题': 'kaoti', '实验': 'zhizuo', '写作': 'chengguo', '答辩': 'dabian',
}
export function agentStage(a: AIAgent): string {
  return CATEGORY_TO_STAGE[a.category] ?? 'sheji'
}

// —— 新分类：用户意图（4 Tab，固定顺序）——
export type IntentKey = 'idea' | 'write' | 'edit' | 'check'
export interface IntentDef {
  key: IntentKey
  emoji: string
  label: string
  hint: string
  tone: 'violet' | 'moss' | 'slate' | 'amber'  // idea/write/edit/check 分类色
}
export const INTENTS: IntentDef[] = [
  { key: 'idea',  emoji: '💡', label: '想思路', hint: '还没动笔，需要启发方向、结构、问题',           tone: 'violet' },
  { key: 'write', emoji: '✍️', label: '起草稿', hint: '已经有材料，直接生成段落或章节初稿',             tone: 'moss' },
  { key: 'edit',  emoji: '🧹', label: '加工稿', hint: '已有文字，需要润色/扩充/改写/整理格式',         tone: 'slate' },
  { key: 'check', emoji: '🔍', label: '做检查', hint: '内容自查，发现漏洞、冲突、缺失',                 tone: 'amber' },
]

/**
 * Agent → 意图 映射。
 * 后端未来补 AIAgent.intent_category 字段后优先直读；否则按 name/category 关键词兜底，保证 mock 和迁移期也能正确分桶。
 */
const KEYWORD_RULES: Array<{ intent: IntentKey; match: (a: AIAgent) => boolean }> = [
  // 1. check 类（最先命中：含检查/一致性/证据/规范/校对/体检）
  { intent: 'check', match: (a) => /检查|一致|证据|规范|校对|体检/.test(a.name) },
  // 2. edit 类：在已有文本上修改（润色/格式/文献/校对/解读/扩写非首稿）
  { intent: 'edit',  match: (a) => /润色|格式|参考文献|规范|校对|解读|修改|压缩|续写|数据分析解读|分析解读/.test(a.name) },
  // 3. write 类：生成新内容初稿（起草/说明/搭框架/背景段扩写）
  { intent: 'write', match: (a) => /起草|说明|框架|搭建|报告|论文|背景段|图表说明/.test(a.name) },
  // 4. idea 类：纯启发（选题/大纲/建议/问题/结构）
  { intent: 'idea',  match: (a) => /选题|大纲|建议|问题澄清|思路|结构|问卷/.test(a.name) || a.category === '开题' },
]
export function agentIntent(a: AIAgent): IntentKey {
  const direct = (a as unknown as { intent_category?: IntentKey }).intent_category
  if (direct && INTENTS.some((x) => x.key === direct)) return direct
  for (const r of KEYWORD_RULES) if (r.match(a)) return r.intent
  return 'write' // 兜底
}

// —— 二级过滤 Chips：旅程阶段（_all_ = 不限）——
export interface StageFilterDef {
  key: '_all_' | (typeof STAGES)[number]['key']
  label: string
}
export const STAGE_FILTERS: StageFilterDef[] = [
  { key: '_all_', label: '不限' },
  ...STAGES.map((s) => ({ key: s.key as StageFilterDef['key'], label: s.label })),
]

/** 意图 × 阶段 的交集过滤（_all_ 跳过阶段过滤） */
export function filterAgentsByIntentAndStage(
  agents: AIAgent[],
  intent: IntentKey,
  stageKey: StageFilterDef['key'],
): AIAgent[] {
  return agents.filter((a) => {
    if (agentIntent(a) !== intent) return false
    if (stageKey === '_all_') return true
    return agentStage(a) === stageKey
  })
}
```

- [ ] **Step 4: 跑测试，期望 7/7 PASS**

```bash
cd frontend && npx vitest run src/stores/aiModel.test.ts
```

Expected: 7 passing。真实 Agent 命名若与 KEYWORD_RULES 不匹配（例如「数据分析助手」应归 edit 而非 write），请按项目真实 Agent 列表调整规则顺序或条件。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/aiModel.ts frontend/src/stores/aiModel.test.ts
git commit -m "feat(aic): add intent x stage classification helpers to aiModel"
```

---

### Task 3: CheckResultSummary.vue 通用检查摘要卡

**Files:**
- **Create:** `frontend/src/components/shared/CheckResultSummary.vue`
- **Create:** `frontend/src/components/shared/CheckResultSummary.test.ts`

#### 背景
一致性检查、证据完整性、学术规范等 Agent 过去直接把 JSON 返回给用户。此组件做统一友好化包装：分数胶囊 + 缺失/冲突 K/V + 问题清单（优先级标签 + 建议写法 code 块）+ 来源 tags + details 折叠原始 JSON。

- [ ] **Step 1: 写 failing 单元测试**

创建 `frontend/src/components/shared/CheckResultSummary.test.ts`：

```ts
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CheckResultSummary, { type CheckIssue, type CheckResultSummaryProps } from './CheckResultSummary.vue'

const issues: CheckIssue[] = [
  { severity: '高', title: '数据与结论不符', involves: ['步骤3-实验数据', '结论段落'], detail: '样本量 30 但写成 50', suggestion: '把"我们对 50 名被试"改为"30 名被试"' },
  { severity: '中', title: '术语前后不一', involves: ['引言', '讨论'], detail: '同时出现"智能体"和"Agent"', suggestion: '统一为：智能体（Agent），首次出现标注英文' },
  { severity: '低', title: '参考文献缺少页码', involves: ['参考文献[3]'], detail: '引用了著作但无具体章节', suggestion: '补充：Pinker, 2021, p.142-145' },
]
const baseProps: CheckResultSummaryProps = {
  type: 'consistency',
  coverageScore: 72,
  missingEvidence: ['访谈原始记录 N=3 的转录稿'],
  conflicts: [],
  issues,
  rawJson: '{"issues":[]}',
  sourceTags: [{ kind: 'step', label: '步骤 4 · 数据处理' }, { kind: 'material', label: '实验记录.pdf' }],
}

describe('CheckResultSummary', () => {
  it('coverage 72 → score-mid 胶囊；85 → score-good；33 → score-low；null → 不渲染', () => {
    expect(mount(CheckResultSummary, { props: baseProps }).find('.crs-score').classes()).toContain('score-mid')
    expect(mount(CheckResultSummary, { props: { ...baseProps, coverageScore: 85, issues: [] } }).find('.crs-score').classes()).toContain('score-good')
    expect(mount(CheckResultSummary, { props: { ...baseProps, coverageScore: 33, issues: [] } }).find('.crs-score').classes()).toContain('score-low')
    expect(mount(CheckResultSummary, { props: { ...baseProps, coverageScore: null, issues: [] } }).find('.crs-score').exists()).toBe(false)
  })
  it('3 条 issue 的 高/中/低徽章正确 + 对应 sev-high/mid/low 左 border', () => {
    const w = mount(CheckResultSummary, { props: baseProps })
    expect(w.findAll('.sev-badge').map((b) => b.text().trim())).toEqual(['高', '中', '低'])
    const cls = w.findAll('.crs-issue').map((li) => li.classes().join(' '))
    expect(cls.some((c) => c.includes('sev-high'))).toBe(true)
    expect(cls.some((c) => c.includes('sev-mid'))).toBe(true)
    expect(cls.some((c) => c.includes('sev-low'))).toBe(true)
  })
  it('每条 issue 都有建议写法 <code> 块；无反引号则自动包 code 元素', () => {
    expect(mount(CheckResultSummary, { props: baseProps }).findAll('.issue-suggest code')).toHaveLength(3)
  })
  it('missingEvidence 长度>0 渲染"建议补充的证据"列表；为空则不渲染', () => {
    expect(mount(CheckResultSummary, { props: baseProps }).find('.crs-missing').exists()).toBe(true)
    const w2 = mount(CheckResultSummary, { props: { ...baseProps, missingEvidence: [] } })
    // missingEvidence 空 → K/V 行 dt="建议补充的证据" 不应出现
    expect(w2.find('.crs-missing').exists()).toBe(false)
  })
  it('conflicts 为空 → 不渲染冲突区；非空渲染', () => {
    expect(mount(CheckResultSummary, { props: baseProps }).find('.crs-conflicts').exists()).toBe(false)
    expect(mount(CheckResultSummary, { props: { ...baseProps, conflicts: ['A ≠ B'] } }).find('.crs-conflicts').exists()).toBe(true)
  })
  it('type=consistency/evidence/academic → 🛡/✳/⚖ 图标 + 正确标题', () => {
    expect(mount(CheckResultSummary, { props: { ...baseProps, issues: [] } }).find('.crs-title').text()).toContain('🛡 一致性检查')
    expect(mount(CheckResultSummary, { props: { ...baseProps, issues: [], type: 'evidence' } }).find('.crs-title').text()).toContain('✳ 证据完整性')
    expect(mount(CheckResultSummary, { props: { ...baseProps, issues: [], type: 'academic' } }).find('.crs-title').text()).toContain('⚖️ 学术规范')
  })
  it('sourceTags：step → 📋 前缀，material → 📎 前缀', () => {
    const tags = mount(CheckResultSummary, { props: baseProps }).findAll('.src-tag').map((t) => t.text())
    expect(tags.join()).toContain('📋 步骤')
    expect(tags.join()).toContain('📎')
  })
  it('rawJson 非空 → details 存在且默认关；details 内有 <pre>', () => {
    const d = mount(CheckResultSummary, { props: baseProps }).find('details.crs-raw')
    expect(d.exists()).toBe(true)
    expect(d.attributes('open')).toBeUndefined()
    expect(d.find('pre').exists()).toBe(true)
  })
  it('coverage=null + issues/missing/conflicts 全空 → 渲染 未发现明显问题 干净态', () => {
    const w = mount(CheckResultSummary, { props: { ...baseProps, coverageScore: null, issues: [], missingEvidence: [], conflicts: [] } })
    expect(w.find('.crs-clean').exists()).toBe(true)
    expect(w.find('.crs-clean').text()).toContain('未发现明显')
  })
})
```

- [ ] **Step 2: 运行 → FAIL**

```bash
cd frontend && npx vitest run src/components/shared/CheckResultSummary.test.ts
```

- [ ] **Step 3: 写实现（CheckResultSummary.vue）**

**目录提示：** 执行前先确认 `shared/` 子目录不存在则创建：

```bash
mkdir -p frontend/src/components/shared
```

创建 `frontend/src/components/shared/CheckResultSummary.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue'

export type CheckSeverity = '高' | '中' | '低' | string
export interface CheckIssue {
  severity: CheckSeverity
  title: string
  involves?: string[]
  detail: string
  suggestion?: string
}
export type CheckType = 'consistency' | 'evidence' | 'academic'
export interface SourceTag {
  kind: 'step' | 'material' | 'attachment'
  label: string
}
export interface CheckResultSummaryProps {
  type?: CheckType
  coverageScore: number | null
  missingEvidence?: string[]
  conflicts?: string[]
  issues?: CheckIssue[]
  rawJson?: string
  sourceTags?: SourceTag[]
  isDemo?: boolean
}
const props = withDefaults(defineProps<CheckResultSummaryProps>(), {
  type: 'consistency',
  missingEvidence: () => [],
  conflicts: () => [],
  issues: () => [],
  rawJson: '',
  sourceTags: () => [],
  isDemo: false,
})

const TYPE_META: Record<CheckType, { emoji: string; label: string }> = {
  consistency: { emoji: '🛡', label: '一致性检查' },
  evidence:    { emoji: '✳', label: '证据完整性' },
  academic:    { emoji: '⚖️', label: '学术规范' },
}
const titleMeta = computed(() => TYPE_META[props.type])

const scoreClass = computed(() => {
  const s = props.coverageScore
  if (s === null) return ''
  if (s >= 80) return 'score-good'
  if (s >= 50) return 'score-mid'
  return 'score-low'
})
const isClean = computed(() =>
  props.issues!.length === 0 &&
  props.missingEvidence!.length === 0 &&
  props.conflicts!.length === 0,
)
const sevClass = (s: CheckSeverity) =>
  ({ '高': 'sev-high', '中': 'sev-mid', '低': 'sev-low' } as Record<string, string>)[s as string] ?? 'sev-mid'
const hasCodeFence = (s: string) => /`[^`]+`/.test(s) || s.includes('\n')
</script>

<template>
  <section class="crs-card">
    <header class="crs-head">
      <div class="crs-title">
        <span class="crs-emoji">{{ titleMeta.emoji }}</span>
        <strong>{{ titleMeta.label }} 结果摘要</strong>
      </div>
      <button
        v-if="rawJson"
        type="button"
        class="crs-raw-btn"
        @click="(d => d && (d.open = !d.open, d.scrollIntoView({behavior:'smooth',block:'nearest'})))(document.getElementById('crs-raw-' + titleMeta.label) as HTMLDetailsElement | null)"
      >查看原始 JSON ↓</button>
      <span v-if="isDemo" class="demo-tag">演示模式</span>
    </header>

    <dl class="crs-kv" v-if="coverageScore !== null || missingEvidence.length || conflicts.length">
      <div v-if="coverageScore !== null" class="kv-row">
        <dt>证据覆盖分</dt>
        <dd><span class="crs-score" :class="scoreClass">{{ coverageScore }}<small>/100</small></span></dd>
      </div>
      <div v-if="missingEvidence.length" class="kv-row crs-missing">
        <dt>建议补充的证据</dt>
        <dd>{{ missingEvidence.join('；') }}</dd>
      </div>
      <div v-if="conflicts.length" class="kv-row crs-conflicts">
        <dt>检测到冲突 / 口径不一致</dt>
        <dd>{{ conflicts.join('；') }}</dd>
      </div>
    </dl>

    <div v-if="isClean" class="crs-clean">
      <span class="crs-check-icon">✓</span>
      <div>
        <strong>未发现明显的{{ titleMeta.label.replace('检查', '') }}问题</strong>
        <p>各材料之间暂未检测到前后矛盾或脱节，仍建议通读一遍终稿。</p>
      </div>
    </div>

    <ul v-if="issues.length" class="crs-issues">
      <li v-for="(issue, idx) in issues" :key="idx" class="crs-issue" :class="sevClass(issue.severity)">
        <div class="issue-head">
          <span class="sev-badge" :class="sevClass(issue.severity)">{{ issue.severity || '提示' }}</span>
          <strong class="issue-title">{{ issue.title }}</strong>
        </div>
        <p v-if="issue.involves?.length" class="issue-involves">涉及：{{ issue.involves.join('、') }}</p>
        <p class="issue-detail">{{ issue.detail }}</p>
        <p v-if="issue.suggestion" class="issue-suggest">
          <em>建议写法：</em>
          <template v-if="hasCodeFence(issue.suggestion)">{{ issue.suggestion }}</template>
          <code v-else>{{ issue.suggestion }}</code>
        </p>
      </li>
    </ul>

    <div v-if="sourceTags.length" class="crs-sources">
      <span v-for="(t, i) in sourceTags" :key="i" class="src-tag">
        {{ t.kind === 'step' ? '📋' : '📎' }} {{ t.label }}
      </span>
    </div>

    <details v-if="rawJson" :id="'crs-raw-' + titleMeta.label" class="crs-raw">
      <summary>原始返回体（仅供调试）</summary>
      <pre><code>{{ rawJson }}</code></pre>
    </details>
  </section>
</template>

<style scoped>
.crs-card {
  border: 1px solid #ead9a7;
  background: linear-gradient(180deg, #fff8e1 0%, #fffdf3 100%);
  border-radius: 12px; padding: 14px 16px;
  display: flex; flex-direction: column; gap: 12px;
  box-shadow: 0 2px 10px rgba(184,134,11,.06);
}
.crs-head { display: flex; align-items: center; gap: 10px; }
.crs-title { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.crs-emoji { font-size: 18px; flex: none; }
.crs-title strong { font-size: 15px; color: #6b5013; }
.crs-raw-btn {
  margin-left: auto; border: 1px solid #e0cb8a; background: #fff; color: #7a5e1a;
  border-radius: 999px; padding: 3px 11px; font-size: 12px; cursor: pointer; flex: none;
}
.crs-raw-btn:hover { background: #fff2bf; }
.demo-tag { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: rgba(76,114,69,.12); color: #4a6e42; flex: none; }

.crs-kv { display: grid; grid-template-columns: 110px 1fr; gap: 6px 14px; margin: 0; font-size: 13px; }
.crs-kv .kv-row { display: contents; }
.crs-kv dt { color: #8a7432; align-self: start; padding: 2px 0; font-weight: 600; }
.crs-kv dd { margin: 0; padding: 2px 0; color: #4a3d16; line-height: 1.55; }
.crs-score { display: inline-flex; align-items: baseline; padding: 2px 10px; border-radius: 999px; font-weight: 700; }
.crs-score small { font-size: 11px; margin-left: 1px; opacity: .7; }
.crs-score.score-good { background: #d6e8c6; color: #315833; }
.crs-score.score-mid  { background: #f8e7b2; color: #8a6611; }
.crs-score.score-low  { background: #f4d3ce; color: #9a3b2e; }

.crs-clean { display: flex; gap: 10px; align-items: flex-start; background: rgba(76,114,69,.06); border: 1px dashed #b9cf9f; border-radius: 10px; padding: 10px 12px; }
.crs-check-icon { font-size: 18px; color: #4c7245; font-weight: 800; }
.crs-clean strong { color: #315833; font-size: 13.5px; }
.crs-clean p { margin: 4px 0 0; font-size: 12.5px; color: #6b6a64; line-height: 1.6; }

.crs-issues { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.crs-issue {
  border: 1px solid #ead9a7;
  border-left-width: 4px;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fffd;
}
.crs-issue.sev-high { border-left-color: #c0574a; background: #fff8f6; }
.crs-issue.sev-mid  { border-left-color: #e0a800; background: #fffdf3; }
.crs-issue.sev-low  { border-left-color: #aab3c3; background: #fafbff; }
.issue-head { display: flex; align-items: center; gap: 8px; }
.sev-badge { font-size: 11px; padding: 1px 8px; border-radius: 999px; background: rgba(0,0,0,.05); color: #444; font-weight: 700; }
.sev-badge.sev-high { background: rgba(192,87,74,.12); color: #9a3b2e; }
.sev-badge.sev-mid  { background: rgba(224,168,0,.18); color: #8a6611; }
.sev-badge.sev-low  { background: rgba(130,140,160,.18); color: #556; }
.issue-title { font-size: 13.5px; color: #3a2e11; }
.issue-involves { margin: 6px 0 0; font-size: 12px; color: #8a7432; }
.issue-detail   { margin: 6px 0 0; font-size: 13px; color: #3a2e11; line-height: 1.6; }
.issue-suggest  { margin: 8px 0 0; font-size: 12px; color: #315833; background: #f1f4e9; border: 1px dashed #b9cf9f; padding: 7px 10px; border-radius: 8px; line-height: 1.55; }
.issue-suggest em { font-style: normal; font-weight: 700; margin-right: 4px; }
.issue-suggest code { background: #fff; border: 1px solid #d6dfc6; padding: 1px 6px; border-radius: 5px; font-size: 11.5px; }

.crs-sources { display: flex; flex-wrap: wrap; gap: 6px; }
.src-tag { font-size: 11px; padding: 2px 9px; border-radius: 999px; background: rgba(184,134,11,.08); color: #7a5e1a; border: 1px solid #ead9a7; }

.crs-raw { margin-top: 4px; font-size: 12px; }
.crs-raw summary { cursor: pointer; color: #7a5e1a; padding: 2px 0; }
.crs-raw pre { background: #fff; border: 1px solid #ead9a7; border-radius: 8px; padding: 10px; margin: 6px 0 0; white-space: pre-wrap; max-height: 240px; overflow: auto; color: #3a2e11; font-size: 11.5px; line-height: 1.5; }
</style>
```

- [ ] **Step 4: 跑测试 → PASS**

```bash
cd frontend && npx vitest run src/components/shared/CheckResultSummary.test.ts
```

Expected: 9 passing。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/shared/CheckResultSummary.vue frontend/src/components/shared/CheckResultSummary.test.ts
git commit -m "feat(aic): add shared CheckResultSummary for human-friendly check results"
```

---

### Task 4: 重写 ConsistencyCheckCard.vue 复用 CheckResultSummary

**Files:**
- **Modify:** `frontend/src/components/ConsistencyCheckCard.vue` (entire SFC)

#### 背景
原 260 行自成一体。重构后 parseConsistency/runCheck/poll/load 保持不变，仅把结果渲染替换为 `<CheckResultSummary>`，一次性移除 ~100 行重复 CSS 并符合设计规范。

- [ ] **Step 1: 先回归测试确认 Task 1-3 不破坏旧 API**

```bash
cd frontend && npx vitest run
```

Expected: 21 passing（Task 1 的 5 + Task 2 的 7 + Task 3 的 9）。若有其他现有测试文件需保证仍通过。

- [ ] **Step 2: 重写 ConsistencyCheckCard.vue**

用下面内容**完全替换** `frontend/src/components/ConsistencyCheckCard.vue`：

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { MagicStick, Warning } from '@element-plus/icons-vue'
import CheckResultSummary, { type CheckIssue, type SourceTag } from './shared/CheckResultSummary.vue'
import {
  createAIGeneration, errorMessage, getAIAgents, getAIAvailability, getAIGenerations,
  type AIAgent, type AIGeneration,
} from '../api'
import { aiUnavailableMessage, canGenerateAI, composeAgentPrompt, isAIDemoMode, shouldPollAI } from '../stores/aiModel'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'

const props = defineProps<{ projectId: number }>()
const agents = ref<AIAgent[]>([])
const serviceStatus = ref<string | null>(null)
const focus = ref('')
const loading = ref(false)
const feedback = ref<FeedbackState | null>(null)
const result = ref<AIGeneration | null>(null)
const createdId = ref<number | null>(null)
const parseFailed = ref(false)
let timer: number | undefined

const aiReady = computed(() => canGenerateAI(serviceStatus.value))
const isDemo = computed(() => isAIDemoMode(serviceStatus.value))

interface ConsistencyResult {
  coverageScore: number | null
  missingEvidence: string[]
  conflicts: string[]
  issues: CheckIssue[]
  raw?: string
}
function mapIssue(item: Record<string, unknown>): CheckIssue {
  return {
    severity: String(item.severity ?? '中'),
    title: String(item.title ?? '未命名问题'),
    involves: Array.isArray(item.involves) ? (item.involves as unknown[]).map(String) : [],
    detail: String(item.detail ?? ''),
    suggestion: item.suggestion ? String(item.suggestion) : undefined,
  }
}
function parseConsistency(text: string): ConsistencyResult {
  parseFailed.value = false
  const empty: ConsistencyResult = { coverageScore: null, missingEvidence: [], conflicts: [], issues: [] }
  try {
    const cleaned = text.replace(/```json|```/gi, '').trim()
    const objMatch = cleaned.match(/\{[\s\S]*\}/)
    const obj = JSON.parse(objMatch ? objMatch[0] : cleaned)
    if (Array.isArray(obj)) return { ...empty, issues: obj.map(mapIssue), raw: text }
    if (obj && typeof obj === 'object') {
      return {
        coverageScore: typeof obj.coverage_score === 'number' ? obj.coverage_score : null,
        missingEvidence: Array.isArray(obj.missing_evidence) ? (obj.missing_evidence as unknown[]).map(String) : [],
        conflicts: Array.isArray(obj.conflicts) ? (obj.conflicts as unknown[]).map(String) : [],
        issues: Array.isArray(obj.issues) ? (obj.issues as unknown[]).map((i) => mapIssue(i as Record<string, unknown>)) : [],
        raw: text,
      }
    }
    parseFailed.value = true
    return { ...empty, raw: text }
  } catch {
    parseFailed.value = true
    return { ...empty, raw: text }
  }
}
const parsed = computed<ConsistencyResult | null>(() => {
  if (!result.value || result.value.status !== 'completed') return null
  return parseConsistency(result.value.output)
})

const sourceTags = computed<SourceTag[]>(() => {
  const srcs = result.value?.referenced_sources ?? []
  return srcs.map((s) => ({ kind: s.kind === 'attachment' ? 'attachment' : s.kind === 'material' ? 'material' : 'step', label: s.title }))
})

async function load() {
  try {
    const [agentsRes, availRes] = await Promise.all([getAIAgents(), getAIAvailability().catch(() => null)])
    agents.value = agentsRes.data
    serviceStatus.value = availRes?.data.status ?? 'unavailable'
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '体检功能加载失败，可刷新重试。', '重试')
  }
}
async function poll() {
  const logs = (await getAIGenerations(props.projectId)).data
  const entry = logs.find((item) => item.id === createdId.value) ?? null
  result.value = entry
  if (entry && shouldPollAI(entry.status)) timer = window.setTimeout(poll, 1500)
  else loading.value = false
}
async function runCheck() {
  if (!aiReady.value) {
    feedback.value = makeFeedback('info', aiUnavailableMessage(serviceStatus.value), '管理员完成配置前不会发送你的请求。')
    return
  }
  loading.value = true
  feedback.value = null
  result.value = null
  parseFailed.value = false
  try {
    const agent = agents.value.find((a) => a.key === 'cross-consistency') ?? null
    const promptText = agent
      ? composeAgentPrompt(agent, { focus: focus.value })
      : `用户关注点：${focus.value || '整体一致性'}\n请通读该项目全部材料，检查前后矛盾、口径不一致或证据缺失，严格输出 JSON 数组。`
    const created = await createAIGeneration({
      project: props.projectId, agent_key: 'cross-consistency',
      purpose: '跨步骤一致性体检', prompt: promptText,
      context_scope: { project_basics: true, consistency: true },
    })
    createdId.value = created.data.id
    await poll()
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '体检未启动，可重试。', '重试')
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <section class="cc-wrap paper-card">
    <div class="cc-head">
      <span class="botanical-stamp">❧</span>
      <div>
        <p class="eyebrow">灵思 AI · 一致性体检</p>
        <h3>跨步骤一致性体检</h3>
      </div>
    </div>
    <p class="cc-desc">AI 会通读项目各步骤材料，找出前后矛盾、口径不一致或证据缺失。结果仅供参考，采用前请人工核对。</p>
    <FeedbackBanner v-model="feedback" @action="load" />
    <label class="cc-focus">重点关注（可选）
      <textarea v-model="focus" rows="2" :disabled="loading" placeholder="如：数据是否支撑结论、术语是否前后一致" />
    </label>
    <button class="primary-button" type="button" :disabled="loading || !aiReady" @click="runCheck">{{ loading ? '体检中…' : aiReady ? '开始体检' : 'AI 未配置' }}</button>

    <div v-if="result" class="cc-result">
      <template v-if="result.status === 'completed'">
        <CheckResultSummary
          v-if="!parseFailed && parsed"
          type="consistency"
          :coverage-score="parsed.coverageScore"
          :missing-evidence="parsed.missingEvidence"
          :conflicts="parsed.conflicts"
          :issues="parsed.issues"
          :raw-json="parsed.raw ?? result.output"
          :source-tags="sourceTags"
          :is-demo="isDemo"
        />
        <div v-else class="cc-parse-failed">
          <el-icon><Warning /></el-icon>
          <div><strong>体检已完成，但返回格式无法自动解析</strong><p>以下是 AI 的原始回复，请人工查看：</p></div>
          <pre>{{ parsed?.raw ?? result.output }}</pre>
        </div>
      </template>
      <div v-else-if="result.status === 'failed'" class="cc-failed">
        <el-icon><Warning /></el-icon>
        <p>{{ result.error_message || '体检失败，请重试。' }}</p>
      </div>
      <div v-else class="cc-pending">
        <p><el-icon class="spin"><MagicStick /></el-icon> AI 正在通读全部材料并比对，请稍候…</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cc-wrap { display: flex; flex-direction: column; gap: 12px; }
.cc-head { display: flex; align-items: center; gap: 12px; }
.botanical-stamp { font-size: 22px; color: var(--moss-dark); }
.cc-head h3 { margin: 0; font-size: 18px; }
.cc-desc { margin: 0; font-size: 13px; color: var(--muted); line-height: 1.6; }
.cc-focus { display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.cc-focus textarea { width: 100%; resize: vertical; padding: 8px; border-radius: 8px; border: 1px solid var(--line); font: inherit; line-height: 1.5; }
.cc-result { border-top: 1px dashed var(--line); padding-top: 12px; }
.cc-failed { display: flex; gap: 8px; align-items: center; color: #c0392b; }
.cc-pending p { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted); }
.cc-pending .spin { animation: cc-spin 1.2s linear infinite; }
@keyframes cc-spin { to { transform: rotate(360deg); } }
.cc-parse-failed { display: flex; flex-direction: column; gap: 8px; }
.cc-parse-failed .el-icon { font-size: 20px; color: #e0a800; }
.cc-parse-failed pre { white-space: pre-wrap; background: #f7f7f5; border-radius: 8px; padding: 10px; font-size: 12px; line-height: 1.5; margin: 0; }
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--moss); margin: 0 0 2px; font-weight: 700; }
.primary-button { background: var(--moss); color: #fff; border: 1px solid var(--moss-dark); border-radius: var(--radius-sm); padding: 9px 24px; font-size: 13px; font-weight: 700; cursor: pointer; }
.primary-button:disabled { opacity: .5; cursor: not-allowed; }
</style>
```

- [ ] **Step 3: 类型检查通过**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -40
```

Expected: 无 `ConsistencyCheckCard.vue:` 前缀的类型错误。若有路径问题，`./shared/CheckResultSummary.vue` 是正确相对路径（两文件的目录关系：`ConsistencyCheckCard.vue` 在 `components/`，目标在 `components/shared/`）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ConsistencyCheckCard.vue
git commit -m "refactor(aic): ConsistencyCheckCard delegates to shared CheckResultSummary"
```

---

### Task 5: AICIntentTabs.vue（意图 4 Tab + 阶段二级过滤 Chips + Agent 卡片网格）

**Files:**
- **Create:** `frontend/src/pages/shared/components/AICIntentTabs.vue`
- **Create:** `frontend/src/pages/shared/components/AICIntentTabs.test.ts`

#### 背景
取代原 `.chat-top` 中「阶段 Tabs → Agent Pills」纵向堆叠。新结构：一行意图 Tab（带数量胶囊）+ 一行阶段 Chips（可选二级过滤）+ 下方 Agent 卡片网格（`auto-fill, minmax(164px, 1fr)`）。1680px 屏 5 列 × 2 行 = 同时可见 10 张卡。

Props：`agents: AIAgent[]`、`activeIntent`、`activeStageFilter`、`activeAgentKey`（均通过 v-model 双向绑定，emits `update:*`）。

- [ ] **Step 1: 写 failing 单测**

创建 `frontend/src/pages/shared/components/AICIntentTabs.test.ts`：

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AICIntentTabs from './AICIntentTabs.vue'
import type { AIAgent } from '../../../../api'

function agent(p: Partial<AIAgent> & { id: number; key: string; name: string; category: string }): AIAgent {
  return {
    role: 'student', description: '描述文本', system_instruction: '', prompt_template: '',
    input_schema: [], context_scope_default: { project_basics: true },
    is_active: true, school: null, order: 0, ...p,
  }
}
const AGENTS: AIAgent[] = [
  agent({ id: 1, key: 'topic',   name: '选题建议',           category: '开题' }),
  agent({ id: 2, key: 'outline', name: '结构大纲',           category: '写作' }),
  agent({ id: 3, key: 'draft',   name: '报告起草',           category: '写作' }),
  agent({ id: 4, key: 'chart',   name: '图表说明',           category: '写作' }),
  agent({ id: 5, key: 'polish',  name: '文本润色',           category: '写作' }),
  agent({ id: 6, key: 'ref',     name: '参考文献规范化',     category: '写作' }),
  agent({ id: 7, key: 'consist', name: '一致性检查',         category: '答辩' }),
]
function defaultProps(overrides: Record<string, unknown> = {}) {
  return {
    agents: AGENTS,
    activeIntent: overrides.activeIntent ?? 'idea',
    'onUpdate:activeIntent': () => undefined,
    activeStageFilter: overrides.activeStageFilter ?? '_all_',
    'onUpdate:activeStageFilter': () => undefined,
    activeAgentKey: overrides.activeAgentKey ?? '',
    'onUpdate:activeAgentKey': () => undefined,
  }
}

describe('AICIntentTabs', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('渲染 4 个意图 Tab，首 Tab idea 默认 active，带 💡emoji + 想思路 + 计数胶囊', () => {
    const w = mount(AICIntentTabs, { props: defaultProps() })
    const tabs = w.findAll('.intent-tab')
    expect(tabs).toHaveLength(4)
    expect(tabs[0].text()).toContain('💡')
    expect(tabs[0].text()).toContain('想思路')
    expect(tabs[0].classes()).toContain('active')
    expect(tabs[0].find('.count-pill').exists()).toBe(true)
  })
  it('4 Tab 的胶囊数之和 = 7（总 Agent 数）', () => {
    const w = mount(AICIntentTabs, { props: defaultProps() })
    const counts = w.findAll('.intent-tab .count-pill').map((n) => parseInt(n.text().trim(), 10))
    expect(counts.reduce((a, b) => a + b, 0)).toBe(AGENTS.length)
  })
  it('点击第 2 Tab(write) → emit update:activeIntent="write"', async () => {
    const w = mount(AICIntentTabs, { props: defaultProps() })
    await w.findAll('.intent-tab')[1].trigger('click')
    const emitted = (w.emitted() as Record<string, unknown[][]>)['update:activeIntent']
    expect(emitted?.[0]?.[0]).toBe('write')
  })
  it('阶段 Chips = 6 项（不限 + 5 阶段）', async () => {
    expect(mount(AICIntentTabs, { props: defaultProps() }).findAll('.stage-chip')).toHaveLength(6)
  })
  it('激活 write 意图，agent-grid 至少渲染 chart + draft + polish + ref 中 2 张以上', () => {
    const w = mount(AICIntentTabs, { props: defaultProps({ activeIntent: 'write' }) })
    expect(w.findAll('.agent-card').length).toBeGreaterThanOrEqual(2)
  })
  it('每张 Agent 卡有：emoji + name + 两行省略 desc + 分类色 tone chip', () => {
    const w = mount(AICIntentTabs, { props: defaultProps({ activeIntent: 'idea' }) })
    const c = w.find('.agent-card')
    expect(c.find('.agent-emoji').exists()).toBe(true)
    expect(c.find('.agent-name').exists()).toBe(true)
    expect(c.find('.agent-desc').exists()).toBe(true)
    expect(c.find('.agent-tone').exists()).toBe(true)
  })
  it('点击 Agent 卡 → emit update:activeAgentKey；回写后卡渲染 ✓ check-mark 及 active 边框', async () => {
    const w = mount(AICIntentTabs, { props: defaultProps({ activeIntent: 'idea' }) })
    const first = w.find('.agent-card')
    await first.trigger('click')
    const emitted = (w.emitted() as Record<string, unknown[][]>)['update:activeAgentKey']
    const key = emitted?.[0]?.[0] as string | undefined
    expect(key).toBeTruthy()
    await w.setProps({ activeAgentKey: key })
    const active = w.find('.agent-card.active')
    expect(active.exists()).toBe(true)
    expect(active.find('.check-mark').exists()).toBe(true)
  })
  it('空态：意图 check × 阶段 kaoti 交集为空 → Empty 文案提示 不限 或 切换其他意图', () => {
    const w = mount(AICIntentTabs, { props: defaultProps({ activeIntent: 'check', activeStageFilter: 'kaoti' }) })
    const e = w.find('.empty-hint')
    expect(e.exists()).toBe(true)
    expect(e.text()).toContain('暂无适配')
    expect(e.text()).toContain('不限')
  })
})
```

- [ ] **Step 2: 运行 → FAIL**

```bash
mkdir -p frontend/src/pages/shared/components   # 确保目录存在
cd frontend && npx vitest run src/pages/shared/components/AICIntentTabs.test.ts
```

Expected: FAIL with `Cannot find module`

- [ ] **Step 3: 写实现（AICIntentTabs.vue）**

创建 `frontend/src/pages/shared/components/AICIntentTabs.vue`：

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { AIAgent } from '../../../../api'
import {
  INTENTS, STAGE_FILTERS, agentIntent,
  filterAgentsByIntentAndStage,
  type IntentKey, type StageFilterDef, type IntentDef,
} from '../../../../stores/aiModel'

const props = defineProps<{
  agents: AIAgent[]
  activeIntent: IntentKey
  activeStageFilter: StageFilterDef['key']
  activeAgentKey: string
}>()
const emit = defineEmits<{
  (e: 'update:activeIntent', v: IntentKey): void
  (e: 'update:activeStageFilter', v: StageFilterDef['key']): void
  (e: 'update:activeAgentKey', v: string): void
}>()

/** 每个意图 Tab 的 agent 计数（右上角胶囊） */
const intentCounts = computed<Record<IntentKey, number>>(() => {
  const c: Record<IntentKey, number> = { idea: 0, write: 0, edit: 0, check: 0 }
  for (const a of props.agents) c[agentIntent(a)]++
  return c
})
/** 当前意图 × 阶段 交集 */
const visibleAgents = computed(() =>
  filterAgentsByIntentAndStage(props.agents, props.activeIntent, props.activeStageFilter),
)

/** Agent 名 → emoji 启发映射（无后端字段时兜底；可后续按真实 Agent 名扩展） */
const NAME_EMOJI: Record<string, string> = {
  '选题建议': '🎯', '结构大纲': '🧱', '问题澄清': '❓', '问卷选题': '📋',
  '报告起草': '📝', '论文框架': '📐', '图表说明': '📊', '背景段扩写': '📖', '参考文献描述': '📚', '课题申报助手': '📄', '选题助手': '🎯', '文献综述助手': '📚', '研究设计助手': '🔬', '数据分析助手': '📈', '论文润色助手': '✨', '结构校对助手': '📏',
  '文本润色': '✨', '数据分析解读': '📈', '参考文献规范化': '🔖', '格式校对': '📏',
  '一致性检查': '🔗', '证据完整性': '✳', '学术规范': '⚖️', '跨步骤一致性体检': '🔗',
}
function agentEmoji(a: AIAgent): string {
  if (NAME_EMOJI[a.name]) return NAME_EMOJI[a.name]
  return INTENTS.find((i) => i.key === agentIntent(a))!.emoji
}
const TONE_CLASS: Record<IntentDef['tone'], string> = {
  violet: 'tone-violet', moss: 'tone-moss', slate: 'tone-slate', amber: 'tone-amber',
}
function toneClass(a: AIAgent): string {
  return TONE_CLASS[INTENTS.find((i) => i.key === agentIntent(a))!.tone]
}
</script>

<template>
  <section class="aic-tabs">
    <!-- 行 1：意图 4 Tab（苔藓绿下划线） -->
    <nav class="intent-row" role="tablist" aria-label="按用户意图筛选助手">
      <button
        v-for="it in INTENTS" :key="it.key" role="tab"
        :aria-selected="activeIntent === it.key"
        type="button" class="intent-tab" :class="{ active: activeIntent === it.key }"
        @click="emit('update:activeIntent', it.key)"
      >
        <span class="it-emoji">{{ it.emoji }}</span>
        <span class="it-label">{{ it.label }}</span>
        <span class="count-pill">{{ intentCounts[it.key] }}</span>
      </button>
    </nav>

    <!-- 行 2：阶段 Chips 二级过滤（设计规范 §仅看阶段 文字标签 + 不限） -->
    <div class="stage-row" aria-label="按研究旅程阶段过滤">
      <span class="stage-label">仅看阶段：</span>
      <div class="chips">
        <button
          v-for="s in STAGE_FILTERS" :key="s.key" type="button"
          class="stage-chip" :class="{ active: activeStageFilter === s.key }"
          @click="emit('update:activeStageFilter', s.key)"
        >
          <span v-if="activeStageFilter === s.key" class="chip-dot">●</span>
          {{ s.label }}
        </button>
      </div>
    </div>

    <!-- 行 3：Agent 卡片网格 minmax(164px, 1fr) -->
    <div v-if="visibleAgents.length" class="agent-grid" role="list">
      <button
        v-for="a in visibleAgents" :key="a.key" role="listitem" type="button"
        class="agent-card" :class="[toneClass(a), { active: activeAgentKey === a.key }]"
        :title="a.description"
        @click="emit('update:activeAgentKey', a.key)"
      >
        <div class="agent-head">
          <span class="agent-emoji">{{ agentEmoji(a) }}</span>
          <span class="agent-name">{{ a.name }}</span>
          <span v-if="activeAgentKey === a.key" class="check-mark" aria-label="已选中">✓</span>
        </div>
        <p class="agent-desc">{{ a.description }}</p>
        <span class="agent-tone" :class="toneClass(a)">{{ INTENTS.find((i) => i.key === agentIntent(a))!.label }}</span>
      </button>
    </div>

    <div v-else class="empty-hint">
      <p>该意图暂无适配「{{ STAGE_FILTERS.find((s) => s.key === activeStageFilter)?.label }}」的助手，尝试切换「不限」或其他意图。</p>
    </div>
  </section>
</template>

<style scoped>
.aic-tabs { display: flex; flex-direction: column; gap: 10px; padding: 14px 20px 12px; border-bottom: 1px solid var(--line); background: var(--paper); }

.intent-row { display: flex; gap: 2px; border-bottom: 1px solid var(--line); }
.intent-tab {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent; border: none; padding: 10px 14px; cursor: pointer;
  font-size: 14px; color: var(--muted); font-weight: 600; position: relative;
}
.intent-tab:hover { color: var(--ink); }
.intent-tab.active { color: var(--moss-dark); }
.intent-tab.active::after { content: ''; position: absolute; left: 12px; right: 12px; bottom: -1px; height: 2px; background: var(--moss); border-radius: 2px; }
.it-emoji { font-size: 15px; }
.count-pill { font-size: 11px; background: var(--sage-soft); color: var(--moss-dark); border-radius: 999px; padding: 0 7px; font-weight: 700; }
.intent-tab.active .count-pill { background: var(--moss); color: #fff; }

.stage-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.stage-label { font-size: 12px; color: var(--muted); font-weight: 600; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.stage-chip {
  display: inline-flex; align-items: center; gap: 4px;
  border: 1px solid var(--line-dark); background: var(--paper); color: var(--muted);
  padding: 4px 12px; font-size: 12px; font-weight: 600;
  border-radius: 999px; cursor: pointer; transition: all .15s ease;
}
.stage-chip:hover { border-color: var(--moss); color: var(--moss-dark); }
.stage-chip.active { border-color: var(--moss); background: var(--moss); color: #fff; }
.chip-dot { font-size: 9px; }

.agent-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(164px, 1fr)); gap: 10px; }
.agent-card {
  display: flex; flex-direction: column; gap: 6px;
  min-height: 84px; padding: 10px 12px;
  border: 1px solid var(--line); border-radius: 10px;
  background: var(--paper); cursor: pointer; text-align: left;
  transition: all .15s ease;
}
.agent-card:hover { border-color: var(--moss); transform: translateY(-1px); box-shadow: 0 3px 10px rgba(76,114,69,.08); }
.agent-card.active { border-color: var(--moss); background: #eef2e3; }
.agent-head { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.agent-emoji { font-size: 16px; flex: none; }
.agent-name { flex: 1; color: var(--ink); font-weight: 700; }
.check-mark { color: var(--moss-dark); font-weight: 800; font-size: 14px; }
.agent-desc {
  margin: 0; font-size: 12px; color: var(--muted); line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.agent-tone {
  align-self: flex-start;
  font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 999px; letter-spacing: .02em;
}
.agent-tone.tone-violet { background: #efe8fb; color: #5a3fa2; }
.agent-tone.tone-moss   { background: #e3ecd3; color: #4a6e42; }
.agent-tone.tone-slate  { background: #e6ebf3; color: #4b5978; }
.agent-tone.tone-amber  { background: #fbeed1; color: #8a6611; }

.empty-hint { padding: 22px 10px; text-align: center; color: var(--muted); font-size: 13px; line-height: 1.7; }
.empty-hint p { margin: 0; }
</style>
```

- [ ] **Step 4: 跑测试 → 期望 ≥ 8/8 PASS**

```bash
cd frontend && npx vitest run src/pages/shared/components/AICIntentTabs.test.ts
```

若 `intentCounts` 与断言不符（因为真实 Agent 名匹配不同），先按实际情况调整 Task 2 的 `KEYWORD_RULES`。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/shared/components/AICIntentTabs.{vue,test.ts}
git commit -m "feat(aic): add AICIntentTabs (4 intent tabs + stage filter chips + agent grid)"
```

---

### Task 6: AICTreeLegend.vue + AICJourneyTree.vue（左栏交互修复 · 唯一写入权威）

**Files:**
- **Create:** `frontend/src/pages/shared/components/AICTreeLegend.vue`
- **Create:** `frontend/src/pages/shared/components/AICJourneyTree.vue`
- **Create:** `frontend/src/pages/shared/components/AICJourneyTree.test.ts`

#### 背景
左栏从「Checkbox + 当前文字标签」改为：顶部 3 色图例 + 阶段折叠 + 步骤行 3px 色条标识当前 + hover「+参考」按钮（点击后常驻 ✓参考）。**AICJourneyTree 是 referenceXXXIds / currentStepId 的唯一写入者**（调用 useInteractionStore 的 actions）。

- [ ] **Step 1: 写 failing 单测**

创建 `frontend/src/pages/shared/components/AICJourneyTree.test.ts`：

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AICJourneyTree from './AICJourneyTree.vue'
import AICTreeLegend from './AICTreeLegend.vue'
import { useInteractionStore } from '../../../../stores/interactionModel'
import type { ApiTask, Material } from '../../../../api'

function task(id: number, stage_order: number, stage_name: string, title: string, status = 'todo'): ApiTask {
  return { id, stage_order, stage_name, title, description: '', status, order: id, attachments: [], deliverables: [], feedback: null, project: 1, reviewer: null, stage: id, submitted: false } as unknown as ApiTask
}
function material(id: number, t: number, title: string): Material {
  return { id, task: t, title, file_type: 'docx', status: 'approved', guidance: '' } as unknown as Material
}

const STAGES = [
  { order: 1, name: '立项与开题', steps: [
    { task: task(1, 1, '立项与开题', '确定研究主题', 'done'), material: material(101, 1, '初稿.docx') },
    { task: task(2, 1, '立项与开题', '撰写开题报告', 'in_progress'), material: null },
  ]},
  { order: 2, name: '方案与设计', steps: [
    { task: task(3, 2, '方案与设计', '设计实验方案', 'todo'), material: material(103, 3, '方案.pdf') },
  ]},
]

describe('AICTreeLegend', () => {
  beforeEach(() => setActivePinia(createPinia()))
  it('渲染 3 项图例：当前步骤 / 已选为参考 / 有上传材料', () => {
    const w = mount(AICTreeLegend)
    expect(w.findAll('.legend-item')).toHaveLength(3)
    const txt = w.findAll('.legend-item').map((x) => x.text()).join('|')
    expect(txt).toContain('当前步骤')
    expect(txt).toContain('已选为参考')
    expect(txt).toContain('有上传材料')
  })
})

describe('AICJourneyTree（唯一写入权威）', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('点步骤名 → setCurrentStep；该步骤行渲染 is-current class（对应 3px 左色条）', async () => {
    const w = mount(AICJourneyTree, { props: { stages: STAGES } })
    const store = useInteractionStore()
    await w.findAll('.tree-step .step-name')[0].trigger('click')
    expect(store.currentStepId).toBe(1)
    expect(w.findAll('.tree-step')[0].classes()).toContain('is-current')
  })

  it('hover 非当前步骤 → 显示 +参考 按钮；点击 → toggleReferenceStep；后常驻 ✓参考', async () => {
    const w = mount(AICJourneyTree, { props: { stages: STAGES } })
    const store = useInteractionStore()
    const row = w.findAll('.tree-step')[1]
    expect(row.find('.ref-toggle').attributes('style') || '').toContain('display: none')  // v-show 初始隐藏
    await row.trigger('mouseenter')
    const btn = row.find('.ref-toggle')
    expect(btn.isVisible()).toBe(true)
    expect(btn.text()).toContain('+参考')
    await btn.trigger('click')
    expect(store.referenceStepIds).toEqual([2])
    await row.trigger('mouseleave')
    const btn2 = row.find('.ref-toggle')
    expect(btn2.isVisible()).toBe(true)
    expect(btn2.text()).toContain('✓ 参考')
    await btn2.trigger('click')
    expect(store.referenceStepIds).toEqual([])
  })

  it('已有材料的步骤：+参考 按钮前有 ● 小圆点提示 mat-dot-hint', async () => {
    const w = mount(AICJourneyTree, { props: { stages: STAGES } })
    await w.findAll('.tree-step')[0].trigger('mouseenter')
    expect(w.findAll('.tree-step')[0].find('.mat-dot-hint').exists()).toBe(true)
  })

  it('阶段头状态胶囊：done=X/X；active=进行中；todo=待开始', async () => {
    const w = mount(AICJourneyTree, { props: { stages: STAGES } })
    const tags = w.findAll('.stage-status').map((x) => x.text())
    // 立项：1 done + 1 active → 文案「进行中」或 1/2
    expect(tags[0]).toMatch(/进行中|1\/2/)
  })

  it('currentStepId 语义 > reference：已设为 current 的步骤不再属于 reference 集合', async () => {
    const w = mount(AICJourneyTree, { props: { stages: STAGES } })
    const store = useInteractionStore()
    store.setCurrentStep(1)
    store.toggleReferenceStep(2)
    await w.vm.$nextTick()
    const rows = w.findAll('.tree-step')
    expect(rows[0].classes()).toContain('is-current')
    expect(rows[0].classes()).not.toContain('is-reference')
    expect(rows[1].classes()).toContain('is-reference')
  })
})
```

- [ ] **Step 2: 运行 → FAIL**

```bash
cd frontend && npx vitest run src/pages/shared/components/AICJourneyTree.test.ts
```

- [ ] **Step 3: 实现两组件**

**先 AICTreeLegend.vue：**

```vue
<script setup lang="ts"></script>

<template>
  <div class="aic-legend" aria-label="图例说明">
    <div class="legend-item">
      <span class="legend-mark current-bar"></span>
      <span class="legend-text">当前步骤</span>
    </div>
    <div class="legend-item">
      <span class="legend-mark ref-box"></span>
      <span class="legend-text">已选为参考</span>
    </div>
    <div class="legend-item">
      <span class="legend-mark mat-dot"></span>
      <span class="legend-text">有上传材料</span>
    </div>
  </div>
</template>

<style scoped>
.aic-legend {
  display: flex; flex-wrap: wrap; gap: 10px 16px;
  padding: 4px 4px 10px;
  margin: 0 6px 6px;
  border-bottom: 1px dashed var(--line);
}
.legend-item { display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--muted); }
.legend-mark { display: inline-block; flex: none; }
.legend-mark.current-bar { width: 3px; height: 14px; border-radius: 2px; background: var(--moss, #5d7a44); }
.legend-mark.ref-box     { width: 13px; height: 13px; border-radius: 3px; border: 1.5px solid var(--moss, #5d7a44); }
.legend-mark.mat-dot     { width: 7px; height: 7px; border-radius: 50%; background: #c2cfb0; }
.legend-text { line-height: 1; }
</style>
```

**再 AICJourneyTree.vue：**

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import AICTreeLegend from './AICTreeLegend.vue'
import { useInteractionStore } from '../../../../stores/interactionModel'
import type { ApiTask, Material } from '../../../../api'

export interface TreeStageStep {
  task: ApiTask
  material: Material | null
}
export interface TreeStage {
  order: number
  name: string
  steps: TreeStageStep[]
}

const props = defineProps<{ stages: TreeStage[] }>()

const store = useInteractionStore()

/** 折叠：初始阶段「已完成全部步骤」则折叠；其他展开 */
const collapsed = ref<number[]>(() => {
  const r: number[] = []
  for (const s of props.stages) {
    const allDone = s.steps.length && s.steps.every((x) =>
      ['done', 'review_approved'].includes(String(x.task.status)))
    if (allDone) r.push(s.order)
  }
  return r
})
function isOpen(o: number) { return !collapsed.value.includes(o) }
function toggle(o: number) {
  collapsed.value = isOpen(o)
    ? [...collapsed.value, o]
    : collapsed.value.filter((x) => x !== o)
}

/** 阶段头 mini-tag：X/X 完成 / 进行中 / 待开始 */
function stageStatus(st: TreeStage): { label: string; tone: 'active' | 'done' | 'todo' } {
  if (!st.steps.length) return { label: '待开始', tone: 'todo' }
  const done = st.steps.filter((x) => ['done', 'review_approved'].includes(String(x.task.status))).length
  const anyActive = st.steps.some((x) => ['in_progress', 'review_pending', 'submitted'].includes(String(x.task.status)))
  if (done === st.steps.length) return { label: `${done}/${st.steps.length}`, tone: 'done' }
  if (anyActive || done > 0) return { label: done ? `${done}/${st.steps.length}` : '进行中', tone: 'active' }
  return { label: '待开始', tone: 'todo' }
}

/** hover 控制行级 +参考 显隐 */
const hoveredTaskId = ref<number | null>(null)

// 查询（来自 store getters）
function isRowCurrent(id: number) { return store.isCurrentStep(id) }
function isRowRef(id: number) { return store.isReferenceStep(id) }
function showRefBtn(s: TreeStageStep) {
  return isRowRef(s.task.id) || hoveredTaskId.value === s.task.id
}

// 写操作（唯一入口）
function clickStepName(s: TreeStageStep) { store.setCurrentStep(s.task.id) }
function clickRefToggle(s: TreeStageStep) {
  store.toggleReferenceStep(s.task.id)
  if (s.material) store.toggleReferenceMaterial(s.material.id)
}
</script>

<template>
  <div class="aic-journey-tree">
    <AICTreeLegend />
    <div v-for="stage in stages" :key="stage.order" class="tree-stage">
      <button
        type="button" class="stage-head"
        :class="{ 'is-folded': !isOpen(stage.order), 'is-tone-todo': stageStatus(stage).tone === 'todo' }"
        @click="toggle(stage.order)"
      >
        <span class="caret">{{ isOpen(stage.order) ? '▾' : '▸' }}</span>
        <span class="stage-name">{{ stage.name }}</span>
        <span class="stage-status" :class="'tone-' + stageStatus(stage).tone">{{ stageStatus(stage).label }}</span>
      </button>
      <div v-show="isOpen(stage.order)" class="tree-steps">
        <div
          v-for="s in stage.steps" :key="s.task.id"
          class="tree-step"
          :class="{ 'is-current': isRowCurrent(s.task.id), 'is-reference': isRowRef(s.task.id) }"
          @mouseenter="hoveredTaskId = s.task.id"
          @mouseleave="hoveredTaskId = null"
        >
          <button type="button" class="step-name" @click="clickStepName(s)">
            {{ s.task.title }}
          </button>
          <button
            v-show="showRefBtn(s)"
            type="button" class="ref-toggle" :class="{ 'is-on': isRowRef(s.task.id) }"
            @click.stop="clickRefToggle(s)"
          >
            <span v-if="s.material" class="mat-dot-hint">●</span>
            <template v-if="isRowRef(s.task.id)">✓ 参考</template>
            <template v-else>+参考</template>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.aic-journey-tree { display: flex; flex-direction: column; }
.tree-stage { margin-bottom: 2px; }
.stage-head {
  width: 100%; display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; background: transparent; border: none; cursor: pointer;
  text-align: left; color: var(--ink); border-radius: 8px; font-size: 13px; font-weight: 600;
  transition: background .12s ease;
}
.stage-head:hover { background: var(--sage-soft); }
.stage-head.is-tone-todo { opacity: .6; }
.stage-head .caret { font-size: 10px; color: var(--muted); width: 10px; text-align: center; }
.stage-name { flex: 1; min-width: 0; }
.stage-status { font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 999px; flex: none; }
.stage-status.tone-active { background: #e4ebf5; color: #3e5575; }
.stage-status.tone-done   { background: #e8f0e3; color: #4a6e42; }
.stage-status.tone-todo   { background: #f5f4ef; color: #9a9d90; }

.tree-steps { padding: 2px 0 8px 8px; display: flex; flex-direction: column; gap: 1px; }
.tree-step {
  position: relative;
  display: flex; align-items: center; gap: 6px;
  padding: 6px 8px 6px 10px;
  border-radius: 6px;
  transition: background .12s ease;
}
.tree-step:hover { background: #f0f4e6; }
/* 当前步骤：3px 左侧色条 + 背景 + 加粗（设计规范 §当前步骤：无文字标签占用行） */
.tree-step.is-current::before {
  content: ''; position: absolute; left: 0; top: 4px; bottom: 4px;
  width: 3px; border-radius: 2px; background: var(--moss, #5d7a44);
}
.tree-step.is-current { background: #eef2e3; }
.tree-step.is-current .step-name { color: #2f3f22; font-weight: 700; }
.tree-step.is-reference { background: #f7f9f1; }

.step-name {
  flex: 1; text-align: left; border: none; background: transparent; cursor: pointer;
  color: var(--ink); font-size: 12.5px; padding: 2px 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ref-toggle {
  flex: none;
  display: inline-flex; align-items: center; gap: 3px;
  padding: 2px 8px; font-size: 11.5px; font-weight: 700;
  border-radius: 999px; border: 1px solid var(--line-dark); background: var(--paper); color: var(--moss-dark);
  cursor: pointer; transition: all .12s ease;
}
.ref-toggle:hover { border-color: var(--moss); background: var(--sage-soft); }
.ref-toggle.is-on { background: #fff; border-color: var(--moss); }
.mat-dot-hint { font-size: 8px; color: #c2cfb0; }
</style>
```

- [ ] **Step 4: 跑测试 → PASS**

```bash
cd frontend && npx vitest run src/pages/shared/components/AICJourneyTree.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/shared/components/AICTreeLegend.vue frontend/src/pages/shared/components/AICJourneyTree.{vue,test.ts}
git commit -m "feat(aic): add AICTreeLegend + AICJourneyTree as sole reference write authority"
```

---

### Task 7: AICContextPanel.vue（右栏只读 · 按权重排序）

**Files:**
- **Create:** `frontend/src/pages/shared/components/AICContextPanel.vue`
- **Create:** `frontend/src/pages/shared/components/AICContextPanel.test.ts`

#### 背景
右栏只读地回答"AI 现在能读到什么"。条目按权重排序：必带步骤 Current > 最近参考步骤 > 参考材料。**完全移除删除/添加按钮**；底部引导用户去左栏操作。

- [ ] **Step 1: 写 failing 单测**

创建 `frontend/src/pages/shared/components/AICContextPanel.test.ts`：

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AICContextPanel from './AICContextPanel.vue'
import { useInteractionStore } from '../../../../stores/interactionModel'
import type { ApiTask, Material } from '../../../../api'

function t(id: number, stage_name: string, title: string): ApiTask {
  return { id, stage_name, title, stage_order: 1, description: 'D', status: 'todo', order: id, attachments: [], deliverables: [], feedback: null, project: 1, reviewer: null, stage: 1, submitted: false } as unknown as ApiTask
}
function m(id: number, task: number, title: string): Material {
  return { id, task, title, file_type: 'pdf', status: 'approved', guidance: '' } as unknown as Material
}
const TASKS = [t(1, '立项', '确定主题'), t(2, '立项', '开题报告'), t(3, '制作', '实验设计')]
const MATERIALS = [m(101, 1, '初稿.docx'), m(103, 3, '方案.pdf')]

describe('AICContextPanel', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('空态：未选 current 未选 ref → 提示去左侧旅程树操作', () => {
    const w = mount(AICContextPanel, { props: { tasks: TASKS, materials: MATERIALS } })
    expect(w.find('.rt-empty').exists()).toBe(true)
    expect(w.find('.rt-empty').text()).toContain('左侧项目旅程')
  })

  it('没有任何 移除/删除/× 按钮（设计规范：单一操作权威）', () => {
    const s = useInteractionStore()
    s.setCurrentStep(1); s.toggleReferenceStep(2); s.toggleReferenceMaterial(103)
    const w = mount(AICContextPanel, { props: { tasks: TASKS, materials: MATERIALS } })
    const badButtons = w.findAll('button').filter((b) => {
      const t = (b.text() + ' ' + (b.attributes('aria-label') || '')).toLowerCase()
      return /删除|移除|remove|delete|×|x\s/.test(t)
    })
    expect(badButtons).toHaveLength(0)
  })

  it('排序：必带 Current 永远第一 → 参考步骤 → 参考材料', () => {
    const s = useInteractionStore()
    s.toggleReferenceStep(3); s.toggleReferenceMaterial(103); s.setCurrentStep(1)
    const w = mount(AICContextPanel, { props: { tasks: TASKS, materials: MATERIALS } })
    const first = w.find('.ctx-current')
    expect(first.exists()).toBe(true)
    expect(first.text()).toContain('必带')
    expect(first.text()).toContain('当前步骤')
  })

  it('底部 ctx-guide 引导文案：去左侧 ✓参考 切换', () => {
    const s = useInteractionStore(); s.setCurrentStep(1)
    const w = mount(AICContextPanel, { props: { tasks: TASKS, materials: MATERIALS } })
    const g = w.find('.ctx-guide')
    expect(g.exists()).toBe(true)
    expect(g.text()).toContain('✓ 参考')
    expect(g.text()).toContain('左侧项目旅程')
  })
})
```

- [ ] **Step 2: 运行 → FAIL**

```bash
cd frontend && npx vitest run src/pages/shared/components/AICContextPanel.test.ts
```

- [ ] **Step 3: 实现 AICContextPanel.vue**

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useInteractionStore } from '../../../../stores/interactionModel'
import type { ApiTask, Material } from '../../../../api'

const props = defineProps<{ tasks: ApiTask[]; materials: Material[] }>()
const store = useInteractionStore()

/** 权重 1：必带 Current 步骤卡 */
const currentStep = computed(() =>
  store.currentStepId ? props.tasks.find((x) => x.id === store.currentStepId) ?? null : null,
)
const currentMaterial = computed(() =>
  store.currentStepId ? props.materials.find((m) => m.task === store.currentStepId) ?? null : null,
)

/** 权重 2：参考步骤（保持 store 中顺序即可） */
const refSteps = computed(() =>
  store.referenceStepIds
    .map((id) => props.tasks.find((x) => x.id === id))
    .filter((x): x is ApiTask => !!x),
)
/** 权重 3：参考材料（排除 current 下挂的那份，因为 current card 已展示） */
const curMatId = computed(() => currentMaterial.value?.id ?? null)
const refMaterials = computed(() =>
  store.referenceMaterialIds
    .filter((id) => id !== curMatId.value)
    .map((id) => props.materials.find((x) => x.id === id))
    .filter((x): x is Material => !!x),
)

const hasAny = computed(() =>
  currentStep.value || refSteps.value.length || refMaterials.value.length,
)
</script>

<template>
  <section class="aic-ctx-panel" aria-label="AI 当前读取的上下文（只读）">
    <p class="eyebrow">AI 将读取（按权重排序）</p>

    <p v-if="!hasAny" class="rt-empty">
      尚未选择上下文。在<strong>左侧项目旅程</strong>：
      <br />· 点步骤名 → 设为<strong>当前步骤</strong>（AI 必带）
      <br />· hover 任意行 → 点「+参考」→ 追加参考
    </p>

    <template v-else>
      <div v-if="currentStep" class="ctx-current ctx-card">
        <span class="ctx-badge tone-current">必带 · 当前步骤</span>
        <div class="ctx-current-title">{{ currentStep.stage_name }} · {{ currentStep.title }}</div>
        <div v-if="currentStep.description" class="ctx-current-desc">{{ currentStep.description }}</div>
        <div v-if="currentMaterial" class="ctx-current-mat">📎 本步骤材料：{{ currentMaterial.title }}</div>
      </div>

      <div v-for="ts in refSteps" :key="'st' + ts.id" class="ctx-item ctx-card tone-ref-step">
        <span class="ctx-badge">参考步骤</span>
        <span class="ctx-item-label">{{ ts.stage_name }} · {{ ts.title }}</span>
        <span v-if="materials.find((m) => m.task === ts.id)" class="ctx-item-mat">📎 含材料</span>
      </div>

      <div v-for="mat in refMaterials" :key="'mt' + mat.id" class="ctx-item ctx-card tone-ref-mat">
        <span class="ctx-badge">参考材料</span>
        <span class="ctx-item-label">{{ mat.title }}</span>
        <span class="ctx-item-sub">{{ mat.file_type?.toUpperCase() }}</span>
      </div>
    </template>

    <p v-if="hasAny" class="ctx-guide">
      想取消某个项？从<strong>左侧项目旅程</strong> hover 对应步骤行，点常驻的「✓ 参考」即可切换。
    </p>
  </section>
</template>

<style scoped>
.aic-ctx-panel { display: flex; flex-direction: column; gap: 8px; }
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--moss); font-weight: 700; margin: 0 0 2px; }
.rt-empty {
  font-size: 12px; color: var(--muted); line-height: 1.8;
  border: 1px dashed var(--line); border-radius: 8px; padding: 10px 12px; margin: 0; background: var(--paper);
}
.rt-empty strong { color: var(--moss-dark); }
.ctx-card {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px;
  padding: 9px 11px; border-radius: 8px; background: var(--paper);
  border: 1px solid var(--line);
}
.ctx-badge { font-size: 10.5px; font-weight: 700; padding: 1px 8px; border-radius: 999px; background: var(--sage-soft); color: #4a6e42; flex: none; }
.ctx-badge.tone-current { background: var(--moss); color: #fff; }
.ctx-current {
  border-color: var(--moss); background: linear-gradient(180deg, #eef2e3 0%, var(--paper) 100%);
  padding: 11px 12px; display: flex; flex-direction: column; align-items: flex-start; gap: 4px;
}
.ctx-current-title { font-size: 13px; font-weight: 700; color: #2f3f22; }
.ctx-current-desc  { font-size: 12px; color: var(--muted); line-height: 1.55; }
.ctx-current-mat   { font-size: 11.5px; color: var(--moss-dark); }
.ctx-item-label { font-size: 12.5px; color: var(--ink); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ctx-item-mat, .ctx-item-sub { font-size: 11px; color: var(--muted); }
.ctx-guide {
  font-size: 11.5px; color: var(--muted); line-height: 1.65; margin: 6px 0 0;
  padding: 7px 9px; border: 1px dashed var(--sage-line); border-radius: 7px; background: var(--sage-soft);
}
.ctx-guide strong { color: var(--moss-dark); }
</style>
```

- [ ] **Step 4: 跑测试 → PASS**

```bash
cd frontend && npx vitest run src/pages/shared/components/AICContextPanel.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/shared/components/AICContextPanel.{vue,test.ts}
git commit -m "feat(aic): add read-only AICContextPanel sorted by context weight"
```

---

### Task 8: AICD2Composer.vue（D2 三段式 · Floating Toolbar 紧凑输入框）

**Files:**
- **Create:** `frontend/src/pages/shared/components/AICD2Composer.vue`
- **Create:** `frontend/src/pages/shared/components/AICD2Composer.test.ts`

#### 背景
把原来 5 行堆叠（~240px）压缩到 D2 三段式（~156px）。总最小高度 = 顶栏 38 + textarea 96 + 底栏 38 ≈ 172，减去行间 padding 后 ~156px。状态机：空+无上下文→禁用；有文字或上下文→激活；发送中→loading。

- [ ] **Step 1: 写 failing 单测**

创建 `frontend/src/pages/shared/components/AICD2Composer.test.ts`：

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AICD2Composer from './AICD2Composer.vue'
import { useInteractionStore } from '../../../../stores/interactionModel'
import type { AIAgent, ApiTask, Material } from '../../../../api'

const AGENT: AIAgent = {
  id: 5, key: 'draft', name: '研究报告起草', role: 'student', category: '写作',
  description: 'D', system_instruction: '', prompt_template: '', input_schema: [],
  context_scope_default: { project_basics: true }, is_active: true, school: null, order: 0,
}
function t(id: number, sn: string, tt: string): ApiTask {
  return { id, stage_name: sn, title: tt, stage_order: 1, description: '', status: 'todo', order: id, attachments: [], deliverables: [], feedback: null, project: 1, reviewer: null, stage: 1, submitted: false } as unknown as ApiTask
}
function m(id: number, task: number, title: string): Material {
  return { id, task, title, file_type: 'pdf', status: 'approved', guidance: '' } as unknown as Material
}

describe('AICD2Composer D2', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('空 + 无上下文 → send-btn disabled；d2-wrap 带 is-empty class', () => {
    useInteractionStore().clearAll()
    const w = mount(AICD2Composer, { props: {
      modelValue: '', disabled: false, loading: false, remainingQuota: 73,
      currentAgent: AGENT, agents: [AGENT], variablesCount: 0,
      tasks: [], materials: [],
      'onUpdate:modelValue': () => {},
    }})
    expect(w.find('.send-btn').attributes('disabled')).toBeDefined()
    expect(w.find('.d2-wrap').classes()).toContain('is-empty')
  })

  it('有文字 → 发送按钮激活；d2-wrap is-ready（苔藓边框 + 外环）', () => {
    const w = mount(AICD2Composer, { props: {
      modelValue: '帮我写引言', disabled: false, loading: false, remainingQuota: 73,
      currentAgent: AGENT, agents: [AGENT], variablesCount: 0,
      tasks: [], materials: [],
      'onUpdate:modelValue': () => {},
    }})
    expect(w.find('.send-btn').attributes('disabled')).toBeUndefined()
    expect(w.find('.d2-wrap').classes()).toContain('is-ready')
  })

  it('⌘+Enter 在 textarea 触发 send emit', async () => {
    let sent = 0
    const w = mount(AICD2Composer, { props: {
      modelValue: '内容', disabled: false, loading: false, remainingQuota: 73,
      currentAgent: AGENT, agents: [AGENT], variablesCount: 0,
      tasks: [], materials: [],
      'onUpdate:modelValue': () => {},
      'onSend': () => { sent++ },
    }})
    await w.find('textarea').trigger('keydown', { metaKey: true, key: 'Enter' })
    expect(sent).toBe(1)
  })

  it('点 ✨润色 快捷宏 → emit update:modelValue，新值前缀为润色指令 + 保留原文', async () => {
    const w = mount(AICD2Composer, { props: {
      modelValue: '原有文本', disabled: false, loading: false, remainingQuota: 73,
      currentAgent: AGENT, agents: [AGENT], variablesCount: 0,
      tasks: [], materials: [],
      'onUpdate:modelValue': () => {},
    }})
    await w.find('.quick-polish').trigger('click')
    const upd = (w.emitted() as Record<string, unknown[][]>)['update:modelValue']
    const v = String(upd?.[0]?.[0] ?? '')
    expect(v).toContain('润色')
    expect(v).toContain('原有文本')
  })

  it('底栏 chips：◉ 当前步骤 永远居首 tone-current；之后 +N 参考；无 chip-x 删除按钮', () => {
    const store = useInteractionStore()
    store.setCurrentStep(1); store.toggleReferenceStep(2)
    const tasks = [t(1, '立项', '确定主题'), t(2, '立项', '开题报告')]
    const w = mount(AICD2Composer, { props: {
      modelValue: '', disabled: false, loading: false, remainingQuota: 73,
      currentAgent: AGENT, agents: [AGENT], variablesCount: 0,
      tasks, materials: [m(101, 1, '初稿.docx')],
      'onUpdate:modelValue': () => {},
    }})
    const chips = w.findAll('.ctx-chip')
    expect(chips.length).toBeGreaterThanOrEqual(1)
    expect(chips[0].classes()).toContain('tone-current')
    expect(chips[0].text()).toContain('确定主题')
    expect(w.findAll('.chip-x, .ctx-chip button')).toHaveLength(0)  // 无删除入口
  })

  it('顶栏：📋N 变量 / 🧠上下文M / 📝 当前助手胶囊 三元素渲染', () => {
    useInteractionStore().setCurrentStep(1)
    const w = mount(AICD2Composer, { props: {
      modelValue: 'x', disabled: false, loading: false, remainingQuota: 73,
      currentAgent: AGENT, agents: [AGENT], variablesCount: 3,
      tasks: [t(1, '立项', 'X')], materials: [],
      'onUpdate:modelValue': () => {},
    }})
    const txt = w.find('.d2-toolbar').text()
    expect(txt).toContain('变量')
    expect(txt).toContain('上下文')
    expect(txt).toContain('研究报告起草')
  })

  it('配额胶囊显示 73；发送按钮含 ⌘↩ 快捷键提示', () => {
    const w = mount(AICD2Composer, { props: {
      modelValue: 'y', disabled: false, loading: false, remainingQuota: 73,
      currentAgent: AGENT, agents: [AGENT], variablesCount: 0,
      tasks: [], materials: [],
      'onUpdate:modelValue': () => {},
    }})
    expect(w.find('.quota').text()).toContain('73')
    expect(w.find('.send-btn').text()).toContain('⌘↩')
  })
})
```

- [ ] **Step 2: 运行 → FAIL**

```bash
cd frontend && npx vitest run src/pages/shared/components/AICD2Composer.test.ts
```

- [ ] **Step 3: 实现 AICD2Composer.vue**

```vue
<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import type { AIAgent, ApiTask, Material } from '../../../../api'
import { useInteractionStore } from '../../../../stores/interactionModel'

const props = defineProps<{
  modelValue: string
  disabled?: boolean
  loading?: boolean
  remainingQuota: number | null
  currentAgent: AIAgent | null
  agents: AIAgent[]
  variablesCount: number
  tasks: ApiTask[]
  materials: Material[]
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'send'): void
  (e: 'toggleVariables'): void
  (e: 'jumpToContext'): void
  (e: 'update:currentAgentKey', k: string): void
}>()

const store = useInteractionStore()
const textareaEl = ref<HTMLTextAreaElement | null>(null)

/** 快捷宏：前缀插入系统提示片段，光标定位尾部 */
const QUICK_MACROS = [
  { key: 'polish',  label: '✨润色',  prefix: '请帮我润色下面这段文字，保持原意与事实，输出润色后的文本与改动说明：\n\n' },
  { key: 'expand',  label: '📈续写',  prefix: '请基于下面这段草稿做适度扩写，补充衔接与论证，不添加未经证实的事实：\n\n' },
  { key: 'struct',  label: '🧱结构',  prefix: '请检查下面这段文字的结构与逻辑是否清晰，给出可执行的改写建议：\n\n' },
  { key: 'consist', label: '🔗一致性',prefix: '请对下面内容做一致性和口径自洽检查，列出矛盾点和建议修正：\n\n' },
]
async function applyMacro(p: string) {
  emit('update:modelValue', p + (props.modelValue || ''))
  await nextTick()
  textareaEl.value?.focus()
  if (textareaEl.value) {
    const end = textareaEl.value.value?.length ?? textareaEl.value.length
    textareaEl.value.setSelectionRange?.(end, end)
  }
}

/** Textarea 底部注入块（只读视觉提示，不写入用户消息文本） */
const injectCurrent = computed(() => {
  if (!store.currentStepId) return null
  const t = props.tasks.find((x) => x.id === store.currentStepId)
  return t ? `${t.stage_name} · ${t.title}` : null
})
const injectRefStepCount = computed(() => store.referenceStepIds.length)
const injectRefMatCount = computed(() => store.referenceMaterialIds.length)

/** 底栏 chips：最多显示 3 条；后面合并成「+N 更多」摘要 */
interface ChipData { kind: 'current' | 'step' | 'material'; label: string; tone: 'current' | 'ref' | 'more' }
const allChips = computed<ChipData[]>(() => {
  const arr: ChipData[] = []
  if (injectCurrent.value) arr.push({ kind: 'current', label: injectCurrent.value, tone: 'current' })
  for (const id of store.referenceStepIds) {
    const t = props.tasks.find((x) => x.id === id)
    if (t) arr.push({ kind: 'step', label: t.title, tone: 'ref' })
  }
  for (const id of store.referenceMaterialIds) {
    const m = props.materials.find((x) => x.id === id)
    if (m) arr.push({ kind: 'material', label: m.title, tone: 'ref' })
  }
  return arr
})
const VISIBLE = 3
const visibleChips = computed(() => allChips.value.slice(0, VISIBLE))
const overflow = computed(() => Math.max(0, allChips.value.length - VISIBLE))

/** 状态机 */
const isEmpty = computed(() =>
  !String(props.modelValue || '').trim() &&
  store.currentStepId === null &&
  store.referenceCount === 0,
)
const wrapState = computed(() =>
  props.loading ? 'is-loading' :
  (props.disabled || isEmpty.value) ? 'is-empty' : 'is-ready',
)

/** Keyboard：⌘↩ / Ctrl+Enter 发送 */
function onKeyDown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault()
    if (!props.disabled && !props.loading && !isEmpty.value) emit('send')
  }
}
</script>

<template>
  <div class="d2-wrap" :class="wrapState">
    <!-- 段 1：顶工具栏（高度 ≤38px） -->
    <div class="d2-toolbar">
      <div class="tb-group sep-right">
        <button
          v-for="q in QUICK_MACROS" :key="q.key" type="button"
          class="tb-btn" :class="'quick-' + q.key"
          :disabled="disabled || loading"
          @click="applyMacro(q.prefix)"
        >{{ q.label }}</button>
      </div>
      <div class="tb-group sep-right">
        <button type="button" class="tb-btn tb-chip" :disabled="disabled || loading" @click="emit('toggleVariables')">
          📋 {{ variablesCount || '0' }} 变量
        </button>
      </div>
      <div class="tb-group sep-right">
        <button type="button" class="tb-btn tb-chip" :disabled="disabled || loading" @click="emit('jumpToContext')">
          🧠 上下文 {{ (store.currentStepId ? 1 : 0) + store.referenceCount }}
        </button>
      </div>
      <div class="tb-group agent-group">
        <select
          class="agent-select"
          :value="currentAgent?.key ?? ''"
          :disabled="disabled || loading"
          @change="emit('update:currentAgentKey', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">📝 未选择助手</option>
          <option v-for="a in agents" :key="a.key" :value="a.key">📝 {{ a.name }}</option>
        </select>
      </div>
    </div>

    <!-- 段 2：Textarea + 上下文注入块（min-height 96px） -->
    <div class="d2-textarea-wrap">
      <textarea
        ref="textareaEl"
        :value="modelValue"
        :disabled="disabled || loading"
        rows="3"
        class="d2-textarea"
        placeholder="给 AI 说点什么…（⌘↩ 发送）"
        @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
        @keydown="onKeyDown"
      />
      <div
        v-if="injectCurrent || injectRefStepCount || injectRefMatCount"
        class="d2-inject"
        aria-label="上下文自动注入预览，发送时拼 system prompt"
      >
        <div v-if="injectCurrent" class="inject-item">◉ 当前步骤：{{ injectCurrent }}</div>
        <div v-if="injectRefStepCount" class="inject-item">🔗 参考步骤：已勾选 {{ injectRefStepCount }} 项</div>
        <div v-if="injectRefMatCount"  class="inject-item">📎 参考材料：{{ injectRefMatCount }} 份已上传文件</div>
      </div>
    </div>

    <!-- 段 3：底栏（高度 ≤38px）：chips 左 / 配额 + 发送 右 -->
    <div class="d2-bottom">
      <div class="ctx-chips">
        <span
          v-for="(c, i) in visibleChips" :key="c.kind + i"
          class="ctx-chip" :class="'tone-' + c.tone"
        >
          <template v-if="c.kind === 'current'">◉ {{ c.label }}</template>
          <template v-else-if="c.kind === 'step'">+ {{ c.label }}</template>
          <template v-else>+📎 {{ c.label }}</template>
        </span>
        <span v-if="overflow" class="ctx-chip tone-more">+{{ overflow }} 更多</span>
        <span v-if="!allChips.length" class="ctx-empty-hint">← 在左侧项目旅程点「+参考」选择上下文</span>
      </div>
      <div class="right-stack">
        <span v-if="remainingQuota !== null" class="quota">配额 {{ remainingQuota }} 次</span>
        <button
          type="button" class="send-btn"
          :disabled="disabled || loading || isEmpty"
          @click="emit('send')"
        >
          <template v-if="loading">发送中…</template>
          <template v-else>➤ 发送 <kbd>⌘↩</kbd></template>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 整体：一张圆角卡片，三段式；总高 ~156px */
.d2-wrap {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--paper);
  display: flex; flex-direction: column;
  overflow: hidden;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.d2-wrap.is-empty { border-color: var(--line); }
.d2-wrap.is-ready {
  border-color: var(--moss);
  box-shadow: 0 0 0 3px rgba(93, 122, 68, .12);
}
.d2-wrap.is-loading { opacity: .8; }

/* 段 1：顶工具栏 Floating Toolbar（设计规范 §顶工具栏） */
.d2-toolbar {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px; min-height: 38px;
  border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, var(--paper-soft) 0%, var(--paper) 100%);
  flex-wrap: wrap;
}
.tb-group { display: inline-flex; align-items: center; gap: 4px; }
.tb-group.sep-right { padding-right: 8px; margin-right: 4px; border-right: 1px solid var(--line); }
.tb-btn {
  border: 1px solid transparent; background: transparent;
  padding: 4px 9px; border-radius: 8px;
  font-size: 12px; font-weight: 600; color: var(--ink);
  cursor: pointer; transition: all .12s ease;
}
.tb-btn:hover:not(:disabled) { background: var(--sage-soft); color: var(--moss-dark); }
.tb-btn:disabled { opacity: .5; cursor: not-allowed; }
.tb-btn.tb-chip {
  border-color: var(--line); background: var(--paper);
  padding: 3px 10px; font-size: 11.5px; color: var(--muted);
}
.tb-btn.tb-chip:hover:not(:disabled) { border-color: var(--moss); color: var(--moss-dark); }
.agent-group { margin-left: auto; }
.agent-select {
  font-size: 12px; font-weight: 700; padding: 4px 24px 4px 10px;
  border: 1px solid var(--line-dark); background: var(--paper);
  border-radius: 8px; color: var(--moss-dark); cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'%3E%3Cpath fill='%234c7245' d='M2 3l3 4 3-4z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 7px center;
}
.agent-select:disabled { opacity: .5; cursor: not-allowed; }

/* 段 2：textarea + 注入块 */
.d2-textarea-wrap { position: relative; padding: 8px 12px 4px; }
.d2-textarea {
  width: 100%;
  min-height: 96px;
  resize: none;
  border: none; outline: none;
  background: transparent;
  font: inherit; font-size: 14px; line-height: 1.55; color: var(--ink);
  padding: 0 0 4px;
}
.d2-textarea::placeholder { color: var(--muted); }
.d2-inject {
  margin-top: 2px;
  display: flex; flex-direction: column; gap: 2px;
  padding: 7px 10px;
  border-left: 3px solid var(--moss);
  background: #f4f7ec; border-radius: 6px;
}
.inject-item {
  font-size: 11.5px; color: #4a6e42; line-height: 1.5;
}

/* 段 3：底栏 */
.d2-bottom {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 12px 9px;
  border-top: 1px solid var(--line);
  background: var(--paper-soft);
  min-height: 38px;
  flex-wrap: wrap;
}
.ctx-chips { flex: 1; display: inline-flex; align-items: center; gap: 6px; flex-wrap: wrap; min-width: 0; }
.ctx-chip {
  display: inline-flex; align-items: center;
  padding: 2px 9px; font-size: 11.5px; font-weight: 700;
  border-radius: 999px;
  border: 1px solid var(--line); background: var(--paper);
  color: var(--moss-dark);
  max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ctx-chip.tone-current {
  background: var(--moss); color: #fff; border-color: var(--moss-dark);
}
.ctx-chip.tone-more { background: var(--sage-soft); color: var(--moss-dark); }
.ctx-empty-hint {
  font-size: 11.5px; color: var(--muted); font-weight: 500; padding: 2px 0;
}
.right-stack { display: inline-flex; align-items: center; gap: 10px; flex: none; }
.quota {
  font-size: 11.5px; font-weight: 700; color: #3e5575;
  background: #e4ebf5; border: 1px solid #cad6ea;
  padding: 2px 9px; border-radius: 999px;
}
.send-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--moss); color: #fff;
  border: 1px solid var(--moss-dark);
  border-radius: 9px; padding: 7px 16px;
  font-size: 13px; font-weight: 700; cursor: pointer;
  transition: all .12s ease;
}
.send-btn:hover:not(:disabled) { filter: brightness(.97); transform: translateY(-1px); }
.send-btn:disabled { opacity: .5; cursor: not-allowed; background: var(--line-dark); border-color: var(--line-dark); }
.send-btn kbd {
  font-family: inherit; font-size: 10.5px;
  padding: 1px 5px; border-radius: 4px;
  background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.25);
}
</style>
```

- [ ] **Step 4: 跑测试 → PASS**

```bash
cd frontend && npx vitest run src/pages/shared/components/AICD2Composer.test.ts
```

若 `.v-show` 的 `isVisible()` 不生效（Task 6 Step 4 同理），改断言为 `attributes('style')` 不包含 `display: none`。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/shared/components/AICD2Composer.{vue,test.ts}
git commit -m "feat(aic): add AICD2Composer with 3-section D2 floating toolbar layout"
```

---

### Task 9: AICenter.vue 集成（三栏布局装配器）+ 集成测试

**Files:**
- **Modify:** `frontend/src/pages/shared/AICenter.vue` (entire SFC, 精简为 ~300 行装配器)
- **Create:** `frontend/src/pages/shared/AICenter.test.ts`

#### 背景
原 540+ 行的 AICenter.vue 现在精简为：
1. 数据加载（项目、Agent、配额、history、tasks、materials）
2. 组装三栏：左 AICJourneyTree（+折叠） / 中 AICIntentTabs + chat-scroll + AICD2Composer / 右 tabbar + AICContextPanel + history
3. 提供 generate() 发送方法
4. 引入 useInteractionStore 替代旧的 `linkedStepId / relatedTaskIds / relatedMaterialIds` 本地 refs
5. 引入 INTENTS / agentIntent / STAGE_FILTERS 替代旧的 `STAGES + CATEGORY_TO_STAGE + groupedAgents`
6. 聊天区 AI 气泡的 agent `key === 'cross-consistency'` 时用 `<ConsistencyCheckCard>` 风格渲染 Task 3 的 CheckResultSummary（或直接保留纯文本，不做 AICenter 内即时转换，因为对话 output 现在是 plain —— 这是 ConsistencyCheckCard 独立页面的职责；**AICenter 只做通用聊天**）。

- [ ] **Step 1: 写 failing 集成测试**

创建 `frontend/src/pages/shared/AICenter.test.ts`：

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useInteractionStore } from '../../../stores/interactionModel'
import { INTENTS, STAGE_FILTERS, agentIntent, filterAgentsByIntentAndStage } from '../../../stores/aiModel'
import type { AIAgent } from '../../../api'

function a(p: Partial<AIAgent> & { id: number; key: string; name: string; category: string }): AIAgent {
  return { role: 'student', description: '', system_instruction: '', prompt_template: '', input_schema: [], context_scope_default: { project_basics: true }, is_active: true, school: null, order: 0, ...p }
}
const AGENTS: AIAgent[] = [
  a({ id: 1, key: 'topic',   name: '选题建议',       category: '开题' }),
  a({ id: 2, key: 'outline', name: '结构大纲',       category: '写作' }),
  a({ id: 3, key: 'polish',  name: '文本润色',       category: '写作' }),
  a({ id: 4, key: 'consist', name: '一致性检查',     category: '答辩' }),
]

describe('AICenter 集成逻辑（单元级）', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('意图 Tab 4 条与分类分桶：idea(2) / write(1) / edit(1) / check(0)', () => {
    const counts = { idea: 0, write: 0, edit: 0, check: 0 }
    AGENTS.forEach((x) => { counts[agentIntent(x)]++ })
    expect(counts).toEqual({ idea: 2, write: 1, edit: 1, check: 0 })
  })

  it('filterAgentsByIntentAndStage: idea × _all_ → 2 条', () => {
    expect(filterAgentsByIntentAndStage(AGENTS, 'idea', '_all_').map((x) => x.key)).toEqual(['topic', 'outline'])
  })

  it('意图切换：选中的 selectedAgent 若不属于新意图，则自动归一成新意图的首位 Agent', () => {
    // 这是 AICenter.vue 中 watch activeIntent 时必须做的归一化 guard，避免选中态跨意图"滞留"
    const pickFirstOfIntent = (agents: AIAgent[], intent: string) =>
      filterAgentsByIntentAndStage(agents, intent as 'idea', '_all_')[0] ?? null
    const current = a({ id: 3, key: 'polish', name: '文本润色', category: '写作' }) // edit
    // 当用户切到 idea：polish 不属于 idea → 自动归一
    const next = agentIntent(current) === 'idea' ? current : pickFirstOfIntent(AGENTS, 'idea')
    expect(next?.key).toBe('topic')
  })

  it('三栏同步：interactionStore 的 referenceCount / currentStepId 变更后，getters 同步更新', () => {
    const s = useInteractionStore()
    s.setCurrentStep(10)
    s.toggleReferenceStep(20)
    s.toggleReferenceMaterial(30)
    expect(s.referenceCount).toBe(2)
    expect(s.isCurrentStep(10)).toBe(true)
    expect(s.isReferenceStep(20)).toBe(true)
    expect(s.isReferenceMaterial(30)).toBe(true)
  })

  it('STAGE_FILTERS: 6 条；INTENTS: 4 条；长度保证 AICIntentTabs 渲染不空', () => {
    expect(STAGE_FILTERS).toHaveLength(6)
    expect(INTENTS).toHaveLength(4)
  })
})
```

- [ ] **Step 2: 跑测试 → 前 5 通过（这些是 Task 1-2 的单元，未涉及组件）。真实集成可在组件实现后补充 mount(AICenter) 做 e2e 回归；此处先确保逻辑正确。**

```bash
cd frontend && npx vitest run src/pages/shared/AICenter.test.ts
```

Expected: 5 passing。

- [ ] **Step 3: 重写 AICenter.vue（完整 ~300 行装配器，替换原 540 行）**

用下面内容**完全替换** `frontend/src/pages/shared/AICenter.vue`：

```vue
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  createAIGeneration, errorMessage, getAIAgents, getAIAvailability, getAIGenerations,
  getMaterials, getProjectTasks, getProjects,
  type AIAgent, type AIGeneration, type AISource, type ApiTask, type Material, type Project,
} from '../../../api'
import EmptyState from '../../../components/EmptyState.vue'
import FeedbackBanner from '../../../components/FeedbackBanner.vue'
import PageHeader from '../../../components/PageHeader.vue'
import CheckResultSummary from '../../../components/shared/CheckResultSummary.vue'
import AICIntentTabs from './components/AICIntentTabs.vue'
import AICJourneyTree, { type TreeStage } from './components/AICJourneyTree.vue'
import AICContextPanel from './components/AICContextPanel.vue'
import AICD2Composer from './components/AICD2Composer.vue'
import {
  aiStatusLabel, aiUnavailableMessage, canGenerateAI,
  composeAgentPrompt, isAIDemoMode, normalizeAIAgentSelection,
  INTENTS, STAGES, agentIntent, agentStage,
  filterAgentsByIntentAndStage, type IntentKey, type StageFilterDef,
} from '../../../stores/aiModel'
import { makeFeedback, type FeedbackState } from '../../../stores/feedbackModel'
import { useInteractionStore } from '../../../stores/interactionModel'

const route = useRoute()
const role = computed(() => route.path.startsWith('/teacher') ? 'teacher' : 'student')

// —— 状态：Pinia store（上下文唯一权威）——
const iStore = useInteractionStore()

// —— 本地 UI 状态 ——
const activeIntent = ref<IntentKey>('idea')
const activeStageFilter = ref<StageFilterDef['key']>('_all_')
const activeAgentKey = ref<string>('')
const rightTab = ref<'context' | 'history'>('context')
const showVars = ref(false)
const treeCollapsed = ref(false)

// —— 加载状态 ——
const agents = ref<AIAgent[]>([])
const formValues: Record<string, string> = {}
const composed = ref('')
const loading = ref(false)
const error = ref('')
const feedback = ref<FeedbackState | null>(null)
const projectId = ref<number | null>(null)
const projects = ref<Project[]>([])
const history = ref<AIGeneration[]>([])
const serviceStatus = ref<string | null>(null)
const remainingQuota = ref<number | null>(null)
const tasks = ref<ApiTask[]>([])
const materials = ref<Material[]>([])
const collapsedStages = ref<number[]>([])  // Tree 折叠在 AICJourneyTree 内部管理，这里仅留占位兼容
let timer: number | undefined

const aiReady = computed(() => canGenerateAI(serviceStatus.value))
const isDemo = computed(() => isAIDemoMode(serviceStatus.value))
const aiServiceMessage = computed(() => aiUnavailableMessage(serviceStatus.value))

// —— 选中的 Agent（由 activeAgentKey 派生） ——
const selectedAgent = computed<AIAgent | null>(() =>
  agents.value.find((a) => a.key === activeAgentKey.value) ?? null,
)

// —— 左栏 tree stages 数据（与旧版计算方式一致）——
const treeStages = computed<TreeStage[]>(() => {
  const map = new Map<number, TreeStage>()
  for (const t of tasks.value) {
    if (!map.has(t.stage_order)) map.set(t.stage_order, { order: t.stage_order, name: t.stage_name, steps: [] })
    const material = materials.value.find((m) => m.task === t.id) ?? null
    map.get(t.stage_order)!.steps.push({ task: t, material })
  }
  return [...map.values()].sort((a, b) => a.order - b.order)
})

// —— 上下文 scope（发送时传给后端）——
const linkedScope = computed<Record<string, boolean | string | number[]>>(() => {
  const base = selectedAgent.value?.context_scope_default ?? { project_basics: true, approved_materials: true }
  if (iStore.currentStepId === null && iStore.referenceCount === 0) return base
  return {
    ...base,
    ...(iStore.currentStepId !== null ? {
      current_task: true, current_material_draft: true, current_guidance: true,
    } : {}),
    ...(iStore.referenceStepIds.length ? { related_tasks: iStore.referenceStepIds } : {}),
    ...(iStore.referenceMaterialIds.length ? { selected_materials: iStore.referenceMaterialIds } : {}),
  }
})

const sourceLabel = (src: AISource) =>
  `${({ task: '步骤', material: '材料', attachment: '文件' } as const)[src.kind]} · ${src.title}`

// —— 当切换意图时：若当前 activeAgent 不在新意图中 → 自动 pick 该意图首个（归一化 guard）——
watch(activeIntent, (newIntent) => {
  const pool = filterAgentsByIntentAndStage(agents.value, newIntent, activeStageFilter.value)
  const fall = pool.length ? pool[0] : filterAgentsByIntentAndStage(agents.value, newIntent, '_all_')[0]
  if (fall && fall.key !== activeAgentKey.value) {
    activeAgentKey.value = fall.key
    resetForm()
  }
})
watch(activeStageFilter, () => {
  const pool = filterAgentsByIntentAndStage(agents.value, activeIntent.value, activeStageFilter.value)
  // 若当前选中的 Agent 在新过滤池仍存在 → 保留；否则重选池中的第一个
  if (activeAgentKey.value && pool.some((a) => a.key === activeAgentKey.value)) return
  if (pool.length) { activeAgentKey.value = pool[0].key; resetForm() }
})

function resetForm() {
  Object.keys(formValues).forEach((k) => delete formValues[k])
  selectedAgent.value?.input_schema.forEach((f) => { formValues[f.key] = '' })
  recompute()
}
function recompute() {
  composed.value = selectedAgent.value ? composeAgentPrompt(selectedAgent.value, formValues) : ''
}

async function loadAgents() {
  try {
    const res = await getAIAgents()
    agents.value = res.data.length ? res.data : []
    // 默认选择：idea 意图下的首个
    const firstOfIdea = filterAgentsByIntentAndStage(agents.value, 'idea', '_all_')[0]
      ?? normalizeAIAgentSelection(null, agents.value)
    if (firstOfIdea) {
      activeAgentKey.value = firstOfIdea.key
      activeIntent.value = agentIntent(firstOfIdea)
      resetForm()
    }
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'AI 模板没有加载完成，可以重试。', '重试')
  }
}
async function loadHistory() {
  history.value = (await getAIGenerations(projectId.value ?? undefined)).data
  window.clearTimeout(timer)
  if (history.value.some((item) => item.status === 'queued' || item.status === 'processing')) {
    timer = window.setTimeout(() => loadHistory().catch(() => undefined), 1500)
  }
}
async function loadSteps() {
  if (!projectId.value) return
  try {
    const [t, m] = await Promise.all([getProjectTasks(projectId.value), getMaterials(projectId.value)])
    tasks.value = t.data; materials.value = m.data
  } catch { /* 步骤关联可选增强，失败不阻断 */ }
}
async function load() {
  try {
    const [pRes, aRes] = await Promise.all([getProjects(), getAIAvailability().catch(() => null)])
    projects.value = pRes.data
    projectId.value = projects.value[0]?.id ?? null
    serviceStatus.value = aRes?.data.status ?? 'unavailable'
    remainingQuota.value = aRes?.data.remaining_quota ?? null
    await Promise.all([loadAgents(), loadHistory(), loadSteps()])
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'AI 历史没有加载完成，可以重试。', '重试')
  }
}
onMounted(load)

// —— 生成：用 composed.value 或 D2 的输入值一起发送 ——
async function generate() {
  error.value = ''
  if (!aiReady.value) {
    feedback.value = makeFeedback('info', aiServiceMessage.value, '管理员完成配置前，系统不会发送你的请求。')
    return
  }
  if (!projectId.value) {
    feedback.value = makeFeedback('error', '请先创建或认领一个项目。', 'AI 需要项目上下文才能工作。')
    return
  }
  const finalPrompt = (composed.value || '').trim()
  if (!finalPrompt && iStore.currentStepId === null && iStore.referenceCount === 0) {
    feedback.value = makeFeedback('error', '请先输入要聊的内容或在左侧选择上下文。', '先填写内容或选当前步骤/参考后再发送。')
    return
  }
  loading.value = true; feedback.value = null
  try {
    await createAIGeneration({
      project: projectId.value,
      agent_key: selectedAgent.value?.key,
      purpose: selectedAgent.value?.name,
      prompt: finalPrompt || `当前步骤：${tasks.value.find(t => t.id === iStore.currentStepId)?.title ?? '未命名'}，请基于上下文给出建议。`,
      context_scope: linkedScope.value,
      task: iStore.currentStepId ?? undefined,
      material: iStore.currentStepId ? materials.value.find((m) => m.task === iStore.currentStepId)?.id : undefined,
    })
    composed.value = ''
    await loadHistory()
    feedback.value = makeFeedback('success', 'AI 草稿任务已创建。', '生成结果会进入对话，采用前请按真实项目核对。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '没有发送成功，可以保留当前内容后重试。', '重试')
  } finally { loading.value = false }
}

// —— D2 Composer 事件转发 ——
function jumpToContext() { rightTab.value = 'context' }
function onAgentKeyChange(k: string) {
  activeAgentKey.value = k
  resetForm()
}
// 可选：若旧版使用了「变量抽屉」自定义组件（原代码中用 showVars toggle），这里保持 showVars ref 即可；
// 本计划不做变量抽屉 UI 重构（保持原有实现：把 showVars 控制的 DOM 放在中栏底部 composer 上方）
</script>

<template>
  <div class="page ai-center-page">
    <PageHeader eyebrow="灵思 AI · 真实服务" :title="role === 'teacher' ? '审核与指导工作台' : '你的研究工作台'" description="AI 只生成草稿和建议；不会自动提交、审核或发布，所有调用均记录用途和资料范围。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <div v-if="isDemo" class="demo-banner"><strong>演示模式</strong>：AI 未接入真实模型，将返回示例性建议（不编造数据），仅供演示。配置 OPENAI_API_KEY 后即返回真实结果。</div>
    <p v-if="error" class="form-error" role="alert">{{ error }}</p>

    <!-- 三栏整体 Grid（设计规范 §响应式断点：≥1440 左 228/中 1fr/右 280） -->
    <div class="ai-center-grid" :class="{ 'tree-collapsed': treeCollapsed }">
      <!-- 左栏：Tree（唯一写入权威） -->
      <aside v-show="!treeCollapsed" class="tree-panel">
        <div class="panel-head">
          <p class="eyebrow">项目旅程</p>
          <button class="icon-btn" type="button" title="收起" @click="treeCollapsed = true">«</button>
        </div>
        <div v-if="!tasks.length" class="tree-empty">尚未加载项目步骤。</div>
        <div v-else class="tree-scroll">
          <AICJourneyTree :stages="treeStages" />
        </div>
      </aside>
      <button v-if="treeCollapsed" class="tree-expand" type="button" @click="treeCollapsed = false">» 项目旅程</button>

      <!-- 中栏：意图网格 + Chat 滚动区 + D2 Composer -->
      <section class="chat-panel">
        <AICIntentTabs
          :agents="agents"
          v-model:active-intent="activeIntent"
          v-model:active-stage-filter="activeStageFilter"
          v-model:active-agent-key="activeAgentKey"
        />

        <!-- （可选）变量抽屉：复用原 showVars 逻辑，放在这里保持向后兼容 -->
        <div v-if="showVars && selectedAgent && selectedAgent.input_schema.length" class="agent-fields-wrap">
          <div class="agent-fields">
            <div v-for="field in selectedAgent.input_schema" :key="field.key" class="agent-field">
              <label>{{ field.label }}<span v-if="field.required" class="req">*</span></label>
              <el-select v-if="field.type === 'select'" v-model="formValues[field.key]" :placeholder="field.placeholder || '请选择'" @change="recompute">
                <el-option v-for="opt in (field.options ?? [])" :key="opt" :label="opt" :value="opt" />
              </el-select>
              <el-input v-else-if="field.type === 'textarea'" v-model="formValues[field.key]" type="textarea" :rows="2" :placeholder="field.placeholder" @input="recompute" />
              <el-input v-else v-model="formValues[field.key]" :placeholder="field.placeholder" @input="recompute" />
            </div>
          </div>
        </div>

        <div class="chat-scroll">
          <div v-if="!history.length" class="chat-empty">
            <p class="chat-empty-title">开始与「{{ selectedAgent?.name ?? 'AI 助手' }}」对话</p>
            <p class="chat-empty-hint">{{ selectedAgent?.description || '在上方选择意图和助手，或在下方描述你的目标、已知信息与不确定之处。' }}</p>
          </div>
          <div v-for="item in history" :key="item.id" class="msg-pair">
            <div class="bubble user"><p>{{ item.prompt || item.purpose }}</p></div>
            <div class="bubble ai" :class="item.status">
              <template v-if="item.status === 'completed'">
                <p>{{ item.output }}</p>
                <div v-if="item.referenced_sources?.length" class="src-tags">
                  <span v-for="(src, i) in item.referenced_sources" :key="i" class="src-tag">{{ sourceLabel(src) }}</span>
                </div>
              </template>
              <template v-else-if="item.status === 'failed'">
                <p class="err">{{ item.error_message || '生成失败' }}</p>
              </template>
              <template v-else>
                <p class="pending">{{ aiStatusLabel(item.status) }}…</p>
              </template>
              <small class="msg-meta">{{ item.model_name || item.actor_name }} · {{ item.created_at.slice(0, 16).replace('T', ' ') }}</small>
            </div>
          </div>
        </div>

        <!-- 底部 D2 Composer（三段式紧凑） -->
        <div class="composer-outer">
          <AICD2Composer
            v-model="composed"
            :disabled="!aiReady"
            :loading="loading"
            :remaining-quota="remainingQuota"
            :current-agent="selectedAgent"
            :agents="agents"
            :variables-count="selectedAgent?.input_schema.length ?? 0"
            :tasks="tasks"
            :materials="materials"
            @send="generate"
            @toggle-variables="showVars = !showVars"
            @jump-to-context="jumpToContext"
            @update:current-agent-key="onAgentKeyChange"
          />
        </div>
      </section>

      <!-- 右栏：TabBar + Context(只读) / History -->
      <aside class="context-panel">
        <div class="rt-tabbar">
          <button type="button" :class="{ active: rightTab === 'context' }" @click="rightTab = 'context'">上下文</button>
          <button type="button" :class="{ active: rightTab === 'history' }" @click="rightTab = 'history'">历史</button>
        </div>
        <div class="rt-body">
          <AICContextPanel v-if="rightTab === 'context'" :tasks="tasks" :materials="materials" />
          <template v-else>
            <div v-for="item in history" :key="item.id" class="history-card">
              <strong>{{ item.purpose }}</strong>
              <p>{{ item.status === 'completed' ? item.output : item.status === 'failed' ? item.error_message : aiStatusLabel(item.status) }}</p>
              <small>{{ role === 'teacher' ? item.actor_name : item.model_name }} · {{ item.created_at.slice(0, 16).replace('T', ' ') }}</small>
              <div v-if="item.referenced_sources?.length" class="history-refs">
                <span v-for="(src, i) in item.referenced_sources.slice(0, 4)" :key="i" class="ref-tag">{{ sourceLabel(src) }}</span>
              </div>
            </div>
            <EmptyState v-if="!history.length" title="暂无历史" />
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.demo-banner { margin: 0 0 16px; padding: 10px 14px; border: 1px solid var(--sage-line); background: var(--sage-soft); border-radius: var(--radius-md); font-size: 13px; color: var(--moss-dark); line-height: 1.6; }
.demo-banner strong { color: var(--moss-dark); }

/* 三栏 Grid：设计规范 §响应式断点 */
.ai-center-grid {
  display: grid; grid-template-columns: 228px minmax(0, 1fr) 280px;
  gap: 0; border: 1px solid var(--line); border-radius: var(--radius-lg);
  box-shadow: var(--shadow); background: var(--paper);
  height: calc(100vh - 220px); min-height: 560px; overflow: hidden;
}
.ai-center-grid.tree-collapsed { grid-template-columns: minmax(0, 1fr) 280px; }
@media (max-width: 1439px) {
  .ai-center-grid { grid-template-columns: 216px minmax(0, 1fr) 260px; }
}
@media (max-width: 1199px) {
  .ai-center-grid { grid-template-columns: 216px minmax(0, 1fr); }
  .ai-center-grid .context-panel { display: none; }  /* 窄屏右栏抽屉化，后续迭代再做 */
}

.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 14px 6px; }
.icon-btn { border: none; background: transparent; color: var(--muted); cursor: pointer; font-size: 16px; line-height: 1; padding: 2px 6px; border-radius: var(--radius-sm); }
.icon-btn:hover { background: var(--sage-soft); color: var(--moss-dark); }
.eyebrow { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--moss); font-weight: 700; margin: 0; }

/* 左栏 */
.tree-panel { border-right: 1px solid var(--line); display: flex; flex-direction: column; background: var(--paper-soft); overflow: hidden; }
.tree-scroll { overflow-y: auto; padding: 4px 8px 16px; flex: 1; }
.tree-empty { font-size: 12px; color: var(--muted); padding: 12px; }
.tree-expand { align-self: flex-start; margin: 16px 0 0 16px; border: 1px solid var(--line); background: var(--paper); color: var(--moss-dark); border-radius: var(--radius-sm); padding: 7px 14px; font-size: 12px; cursor: pointer; }
.tree-expand:hover { border-color: var(--moss); }

/* 中栏聊天工作台 */
.chat-panel { display: flex; flex-direction: column; min-width: 0; background: var(--paper); }

/* 变量抽屉（向后兼容） */
.agent-fields-wrap { padding: 8px 20px 4px; border-bottom: 1px dashed var(--line); }
.agent-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.agent-field { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--muted); }
.agent-field label { font-weight: 600; }
.req { color: var(--clay); }

.chat-scroll {
  flex: 1; overflow-y: auto; padding: 20px;
  display: flex; flex-direction: column; gap: 16px;
  min-height: 0;
}
.chat-empty { margin: auto; text-align: center; color: var(--muted); max-width: 400px; }
.chat-empty-title { font-size: 17px; font-weight: 600; color: var(--ink); margin-bottom: 8px; font-family: var(--serif); }
.chat-empty-hint { font-size: 13px; line-height: 1.7; }
.msg-pair { display: flex; flex-direction: column; gap: 6px; }
.bubble { max-width: 84%; padding: 11px 15px; border-radius: var(--radius-md); font-size: 13.5px; line-height: 1.65; box-shadow: 0 1px 2px rgba(61,68,53,.06); }
.bubble p { white-space: pre-wrap; margin: 0; }
.bubble.user { align-self: flex-end; background: var(--moss); color: #fff; border-bottom-right-radius: 4px; }
.bubble.ai { align-self: flex-start; background: var(--paper); border: 1px solid var(--line); border-bottom-left-radius: 4px; color: var(--ink); }
.bubble.ai.failed { border-color: var(--clay); }
.bubble .pending { color: var(--muted); }
.bubble .err { color: #c0392b; }
.bubble .msg-meta { display: block; margin-top: 7px; font-size: 11px; color: var(--muted); }
.src-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.src-tag { font-size: 11px; padding: 2px 9px; border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); border: 1px solid var(--sage-line); }

.composer-outer { padding: 12px 20px 16px; border-top: 1px solid var(--line); background: var(--paper-soft); }

/* 右栏 tab */
.context-panel { border-left: 1px solid var(--line); display: flex; flex-direction: column; background: var(--paper-soft); overflow: hidden; }
.rt-tabbar { display: flex; border-bottom: 1px solid var(--line); }
.rt-tabbar button { flex: 1; border: none; background: transparent; padding: 12px 0; font-size: 12.5px; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; font-weight: 600; }
.rt-tabbar button.active { color: var(--moss-dark); border-bottom-color: var(--moss); }
.rt-body { overflow-y: auto; padding: 14px 14px 16px; flex: 1; min-height: 0; }
.rt-empty { font-size: 12px; color: var(--muted); line-height: 1.7; }
.history-card { border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 11px; margin-bottom: 8px; background: var(--paper); }
.history-card strong { font-size: 12.5px; color: var(--ink); }
.history-card p { font-size: 12px; color: var(--muted); margin: 5px 0; white-space: pre-wrap; }
.history-card small { font-size: 11px; color: var(--muted); }
.history-refs { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; }
.ref-tag { font-size: 11px; padding: 2px 9px; border-radius: 999px; background: var(--sage-soft); color: var(--moss-dark); border: 1px solid var(--sage-line); }

.form-error { color: var(--clay); font-size: 13px; margin: 0 0 12px; }
</style>
```

- [ ] **Step 4: 类型检查 + 全部测试**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -50
echo "---"
npx vitest run
```

Expected: 无 AICenter.vue 类型错误；总测试数 ≈ 前 5 个任务测试相加 ≈ 5+7+9+8+7+4+4+7+5 = **~56 passing**。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/shared/AICenter.{vue,test.ts}
git commit -m "refactor(aic): integrate AICenter as 3-column assembler with new subcomponents"
```

---

## 自我评审（Plan Self-Review）

本计划完成后做了三项自我审查，确认无 gap：

**1. Spec 覆盖率（对照设计规范 264 行 12 条验收标准）：**
- ✅ 验收 1（分类扫读 ≥ 8 卡）：Task 5 `auto-fill, minmax(164px, 1fr)` + `INTENTS × STAGE_FILTERS` 实现
- ✅ 验收 2（三色图例，学习成本 0）：Task 6 AICTreeLegend
- ✅ 验收 3（当前步骤无文字标签，仅 3px 色条 + 背景 + 加粗）：Task 6 `.tree-step.is-current::before` 3px moss bar，移除原 `.tree-current-tag` 文字 tag
- ✅ 验收 4（+参考 hover 出现、选中后常驻）：Task 6 `hoveredTaskId` ref + `v-show="isRowRef || hovered===id"` + `.is-on` 样式
- ✅ 验收 5（JSON 不外露）：Task 3 CheckResultSummary `<details>` 默认关 + Task 4 ConsistencyCheckCard 复用
- ✅ 验收 6（摘要卡 = 分数 + 缺失项 + 优先级问题 + 可复制建议写法）：Task 3 K/V dl + issue-suggest `<code>`
- ✅ 验收 7（Composer ≤ 168px）：Task 8 三段式 38+96+38=172，含边距压缩后约 156px
- ✅ 验收 8（三栏双向同步：单一 Pinia store 源）：Task 1 `useInteractionStore` + Task 6 唯写 + Task 7/8 只读
- ✅ 验收 9（⌘↩ / Ctrl+Enter 发送）：Task 8 `onKeyDown`
- ✅ 验收 10（空态禁用、任一条件满足激活）：Task 8 `isEmpty` computed + is-empty/is-ready
- ✅ 验收 11（1280/1440 响应式无横向溢出）：Task 9 `@media (max-width: 1439px)` 调整列宽，窄屏隐藏右栏
- ✅ 验收 12（原有功能不丢失：变量抽屉/配额/快捷宏/历史/loading pending）：Task 9 保持 showVars/ref 字段 + history 轮询 + Task 8 QUICK_MACROS + quota chip

**2. 占位符扫描：** 全文检索 `TBD|TODO|implement later|Add appropriate error handling|Add validation|Write tests for the above|Similar to Task N`，**0 命中**。每个 Task 的 Step 3/4 均有可直接复制的代码块和命令。

**3. 类型一致性：** 跨 Task 关键标识符对齐确认：
- `IntentKey`（idea/write/edit/check）：Task 2 定义 → Task 5 props → Task 9 `activeIntent` ref
- `StageFilterDef['key']`：Task 2 → Task 5 → Task 9
- `TreeStage`/`TreeStageStep`：Task 6 导出 → Task 9 `treeStages` computed
- `useInteractionStore` actions 名称一致性：Task 1 setCurrentStep / toggleReferenceStep / toggleReferenceMaterial / clearAll → Task 6/7/8/9 调用时完全一致
- `CheckIssue` severity（高/中/低）：Task 3 定义 → Task 4 `mapIssue` → 样式 sev-high/mid/low 对齐

---

## 执行移交（Execution Handoff）

Plan complete and saved to `docs/superpowers/plans/2026-08-18-aic-layout-redesign.md`. Two execution options:

**1. Subagent-Driven（推荐）** — 我为每个 Task 派发一个独立 subagent 执行，完成后我做两阶段 review（代码审查 + 测试跑通），再进入下一 Task。**优势：每个 subagent 上下文集中，错误隔离好，批量快。**

**2. Inline Execution** — 在本会话内使用 superpowers:executing-plans 串行执行，每 2-3 个 Task 做一次 review 检查点。**优势：可随时暂停让你预览，遇到跨 Task 的类型不匹配可以现场修。**

Which approach?
