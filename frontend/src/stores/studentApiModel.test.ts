import { describe, expect, it } from 'vitest'

import { buildChapters, buildStepModels, projectJourneySummary, selectHomeTask, selectPriorityTask, studentPrimaryAction, taskActionLabel, taskCompletion, validateTaskSubmission, type ApiTask } from './studentApiModel'

const task = (id: number, status: ApiTask['status'], order: number): ApiTask => ({
  id,
  project: 8,
  stage_name: '立项与开题',
  stage_order: 1,
  title: `任务 ${id}`,
  description: '',
  evidence_requirements: [],
  order,
  status,
  xp_reward: 100,
  due_at: null,
})

describe('student API model', () => {
  it('puts a returned repair task ahead of a newly available task', () => {
    expect(selectPriorityTask([
      task(1, 'available', 2),
      task(2, 'revision_required', 5),
    ])?.id).toBe(2)
  })

  it('blocks locked, empty, or unconfirmed submissions', () => {
    expect(validateTaskSubmission(task(1, 'locked', 1), '真实记录', [], true)).toContain('尚未解锁')
    expect(validateTaskSubmission(task(1, 'available', 1), '', [], true)).toContain('正文或附件')
    expect(validateTaskSubmission(task(1, 'available', 1), '真实记录', [], false)).toContain('真实性')
    expect(validateTaskSubmission(task(1, 'available', 1), '真实记录', [], true)).toBeNull()
  })

  it('gives every task state a distinct next action and completion summary', () => {
    expect(taskActionLabel('revision_required')).toBe('查看反馈并修订')
    expect(taskActionLabel('available')).toBe('开始任务')
    expect(taskActionLabel('pending_review')).toBe('查看提交版本')
    expect(taskActionLabel('locked')).toBe('查看解锁条件')
    expect(taskCompletion([task(1, 'completed', 1), task(2, 'approved', 2), task(3, 'available', 3)])).toEqual({ completed: 2, total: 3, percent: 67 })
  })

  it('keeps a waiting or locked task visible when there is no actionable task', () => {
    expect(selectHomeTask([task(1, 'pending_review', 1), task(2, 'locked', 2)])?.status).toBe('pending_review')
    expect(selectHomeTask([task(1, 'locked', 1)])?.status).toBe('locked')
  })

  it('groups the linear task chain into ordered research chapters with one active chapter', () => {
    const phaseNames = ['立项与开题', '方案与设计', '调研与实验', '分析与写作', '答辩与展示']
    const tasks = phaseNames.map((phase, index) => ({
      ...task(index + 1, index < 2 ? 'approved' : 'available', index + 1),
      stage_name: `${phase} · 一 · 阶段任务`,
      stage_order: index + 1,
    }))
    const chapters = buildChapters(buildStepModels(tasks, [], 3))

    expect(chapters.map((chapter) => chapter.name)).toEqual(phaseNames)
    expect(chapters.map((chapter) => chapter.status)).toEqual(['done', 'done', 'active', 'todo', 'todo'])
    expect(chapters[2].containsCurrent).toBe(true)
  })

  it('summarizes project progress by five chapters instead of exposing the raw task count', () => {
    const phaseNames = ['问题提出', '资料查找', '方案设计', '实践验证', '成果表达']
    const tasks = phaseNames.flatMap((phase, chapterIndex) => [
      { ...task(chapterIndex * 2 + 1, chapterIndex < 2 ? 'completed' : 'available', chapterIndex * 2 + 1), stage_name: phase + ' · 章节任务一', stage_order: chapterIndex + 1 },
      { ...task(chapterIndex * 2 + 2, chapterIndex < 1 ? 'approved' : 'locked', chapterIndex * 2 + 2), stage_name: phase + ' · 章节任务二', stage_order: chapterIndex + 1 },
    ])

    expect(projectJourneySummary(tasks, []).summary).toEqual({ completed: 1, total: 5, percent: 20 })
    expect(projectJourneySummary(tasks, []).chapters).toHaveLength(5)
  })

  it('selects one primary student action from the current project state', () => {
    expect(studentPrimaryAction({ currentTaskId: 8, projectId: 3, reportReady: false }))
      .toEqual({ label: '开始当前任务', to: '/student/projects/3/tasks/8' })
    expect(studentPrimaryAction({ currentTaskId: null, projectId: 3, reportReady: true }))
      .toEqual({ label: '查看研究报告', to: '/student/projects/3/report' })
    expect(studentPrimaryAction({ currentTaskId: null, projectId: 3, reportReady: false }))
      .toEqual({ label: '查看研究进度', to: '/student/projects/3/map' })
  })
})
