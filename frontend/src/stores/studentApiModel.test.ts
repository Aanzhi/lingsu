import { describe, expect, it } from 'vitest'

import { selectHomeTask, selectPriorityTask, taskActionLabel, taskCompletion, validateTaskSubmission, type ApiTask } from './studentApiModel'

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
})
