export type TaskStatus = 'locked' | 'available' | 'pending_review' | 'revision_required' | 'approved' | 'completed'

export interface ApiTask {
  id: number
  project: number
  stage_name: string
  stage_order: number
  title: string
  description: string
  evidence_requirements: string[]
  order: number
  status: TaskStatus
  xp_reward: number
  due_at: string | null
}

// ── 研究旅程统一模型（消除三重复投影） ──────────────────────

/** 学生视角的 4 态（从 6 种 task 状态 + material 审核状态收敛而来） */
export type StepStatus = 'locked' | 'active' | 'revision' | 'done'

/** StepStatus 的中文标签与语义色名 */
export const STEP_STATUS_LABEL: Record<StepStatus, string> = {
  locked: '待解锁',
  active: '进行中',
  revision: '需修订',
  done: '已交付',
}
export const STEP_STATUS_TONE: Record<StepStatus, 'neutral' | 'current' | 'danger' | 'success'> = {
  locked: 'neutral',
  active: 'current',
  revision: 'danger',
  done: 'success',
}

/**
 * 把后端 task 状态 + material 是否通过，收敛为学生视角的唯一状态。
 *
 * - locked → locked
 * - revision_required → revision（最高优先，学生必须立刻处理）
 * - approved / completed / material.approved → done
 * - available / pending_review → active（"可开始"和"审核中"对学生都是"正在处理这一步"）
 */
export function deriveStepStatus(task: ApiTask, materialApproved: boolean): StepStatus {
  if (task.status === 'locked') return 'locked'
  if (task.status === 'revision_required') return 'revision'
  if (task.status === 'approved' || task.status === 'completed' || materialApproved) return 'done'
  return 'active'
}

/**
 * 研究旅程中的「一步」= 一个 ProjectTask + 它关联的 Material。
 *
 * 默认蓝图是严格的 1 task : 1 material，所以每一步都有明确的：
 * - 做什么（title / description）
 * - 交什么（deliverable = material.title）
 * - 当前状态（status，4 态）
 * - 属于哪个大阶段（phase，从 stage_name 切分）
 */
export interface JourneyStep {
  id: number               // task.id
  order: number            // 步骤序号 1..10（全局线性）
  phase: string            // stage_name 按 "·" 切分第 1 段，如 "立项与开题"
  theme: string            // stage_name 最后一段（短标签），如 "选题"、"建模"
  title: string            // task.title（动作），如 "问题初筛与查新"
  description: string      // task.description
  evidence: string[]       // task.evidence_requirements
  xpReward: number         // task.xp_reward
  status: StepStatus       // 唯一展示状态（4 态）
  taskStatus: TaskStatus   // 保留原始状态供逻辑判断
  materialId: number | null
  deliverable: string      // material.title —— "我要交什么"
  reportSection: string    // material.report_section —— 进入报告哪一节
  guidance: string         // material.guidance —— 教师指引/系统默认指引
  hasReference: boolean    // material.reference !== null
  isCurrent: boolean       // 是否是当前应聚焦的步骤（第一个非 done 的）
}

/**
 * 研究旅程中的「一章」= 同一大阶段（phase）下的一组步骤。
 *
 * 把 22 步按 phase 聚合成 5 大章节，形成「游戏关卡」式的结构：
 * 每个章节有自己的标题、进度、状态、XP 与任务列表。
 */
export interface JourneyChapter {
  index: number             // 章节序号 1..5
  name: string              // 阶段名，如 "立项与开题"
  steps: JourneyStep[]      // 该章包含的步骤（保持全局顺序）
  total: number             // 任务总数
  done: number              // 已完成任务数
  percent: number           // 完成百分比 0..100
  xp: number                // 该章总 XP
  status: 'todo' | 'active' | 'done'   // 章节状态：待开始 / 进行中 / 已通关
  containsCurrent: boolean  // 是否包含当前应聚焦的步骤
}

/**
 * 从有序的 JourneyStep[] 聚合出 5 大章节。
 * 按 phase 分组，章节顺序 = 各 phase 首步的全局顺序。
 */
export function buildChapters(steps: JourneyStep[]): JourneyChapter[] {
  const byPhase = new Map<string, JourneyStep[]>()
  for (const s of steps) {
    const arr = byPhase.get(s.phase)
    if (arr) arr.push(s)
    else byPhase.set(s.phase, [s])
  }
  const ordered = [...byPhase.entries()].sort((a, b) => a[1][0].order - b[1][0].order)
  return ordered.map(([name, chSteps], i) => {
    const total = chSteps.length
    const done = chSteps.filter((s) => s.status === 'done').length
    const containsCurrent = chSteps.some((s) => s.isCurrent)
    const xp = chSteps.reduce((sum, s) => sum + (s.xpReward ?? 0), 0)
    let status: JourneyChapter['status'] = 'todo'
    if (done === total) status = 'done'
    else if (containsCurrent || done > 0) status = 'active'
    return {
      index: i + 1,
      name,
      steps: chSteps,
      total,
      done,
      percent: total ? Math.round((done / total) * 100) : 0,
      xp,
      status,
      containsCurrent,
    } satisfies JourneyChapter
  })
}

/**
 * 从 tasks + materials 数组构建有序的 JourneyStep[]。
 *
 * @param tasks - 同一项目的全部任务（须按 order 排序）
 * @param materials - 同一项目的全部材料
 * @param currentStageOrder - 当前活跃阶段的 stage_order（用于标记 isCurrent）
 */
export function buildStepModels(
  tasks: ApiTask[],
  materials: Array<{
    id: number
    task: number | null
    title: string
    status: string
    report_section: string
    guidance: string
    reference: { url: string; original_name: string } | null
  }>,
  currentStageOrder: number,
): JourneyStep[] {
  const materialMap = new Map(materials.map((m) => [m.task, m]))

  let foundFirstActive = false
  return tasks
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((task) => {
      const mat = materialMap.get(task.id)
      const materialApproved = mat?.status === 'approved'

      // 解析 stage_name："立项与开题 · 一 · 选题" → phase="立项与开题", theme="选题"
      const parts = task.stage_name.split('·').map((s) => s.trim())
      const phase = parts[0] ?? task.stage_name
      const theme = parts[parts.length - 1] ?? task.stage_name

      const status = deriveStepStatus(task, materialApproved)

      // isCurrent = 第一个未完成的步骤（locked/active/revision 都算"未完成"）
      const isDone = status === 'done'
      const current = !isDone && !foundFirstActive
      if (!isDone && !foundFirstActive) foundFirstActive = true

      return {
        id: task.id,
        order: task.order,
        phase,
        theme,
        title: task.title,
        description: task.description,
        evidence: task.evidence_requirements ?? [],
        xpReward: task.xp_reward ?? 100,
        status,
        taskStatus: task.status,
        materialId: mat?.id ?? null,
        deliverable: mat?.title ?? '',
        reportSection: mat?.report_section ?? '',
        guidance: mat?.guidance ?? '',
        hasReference: mat?.reference !== null && mat?.reference !== undefined,
        isCurrent: current,
      } satisfies JourneyStep
    })
}

export function taskActionLabel(status: ApiTask['status']) {
  return ({
    revision_required: '查看反馈并修订',
    available: '开始任务',
    pending_review: '查看提交版本',
    locked: '查看解锁条件',
    approved: '查看成果',
    completed: '查看成果',
  } as Record<ApiTask['status'], string>)[status]
}

export function taskCompletion(tasks: ApiTask[]) {
  const completed = tasks.filter((task) => task.status === 'approved' || task.status === 'completed').length
  return { completed, total: tasks.length, percent: tasks.length ? Math.round((completed / tasks.length) * 100) : 0 }
}

export function selectPriorityTask(tasks: ApiTask[]) {
  return [...tasks]
    .sort((left, right) => {
      const priority = (value: ApiTask) => value.status === 'revision_required' ? 0 : value.status === 'available' ? 1 : 2
      return priority(left) - priority(right) || left.order - right.order
    })
    .find((item) => item.status === 'revision_required' || item.status === 'available')
}

export function selectHomeTask(tasks: ApiTask[]) {
  return selectPriorityTask(tasks)
    ?? [...tasks].sort((left, right) => left.order - right.order).find((item) => item.status === 'pending_review')
    ?? [...tasks].sort((left, right) => left.order - right.order).find((item) => item.status === 'locked')
    ?? [...tasks].sort((left, right) => right.order - left.order).find((item) => ['approved', 'completed'].includes(item.status))
}

export function validateTaskSubmission(task: ApiTask, body: string, files: File[] | unknown[], truthConfirmed: boolean) {
  if (task.status === 'locked') return '该任务尚未解锁。'
  if (task.status === 'pending_review') return '该任务正在等待教师审核。'
  if (!body.trim() && files.length === 0) return '请填写正文或附件。'
  if (!truthConfirmed) return '提交前必须确认材料真实性。'
  return null
}
