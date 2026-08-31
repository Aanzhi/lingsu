import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./components/ai/AIResultCard.vue', import.meta.url), 'utf8')

describe('AI result confirmation surface', () => {
  it('only exposes compact confirmation actions after an AI result exists', () => {
    expect(source).toContain('确认创建项目')
    expect(source).toContain('保存为材料')
    expect(source).toContain('role="alertdialog"')
    expect(source).toContain('重新生成')
    expect(source).toContain('查看核验项')
    expect(source).not.toContain('研究对象与场景')
    expect(source).not.toContain('第 1 步')
    expect(source).toContain('开题草稿')
    expect(source).toContain('研究建议')
    expect(source).toContain('成果表达建议')
    expect(source).not.toContain('灵思 AI 生成结果')
    expect(source).not.toContain('paper-title-abstract')
  })
})
