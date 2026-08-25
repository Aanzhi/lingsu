<script setup lang="ts">
import type { Project } from '../../api'

defineProps<{ project: Project | null }>()
const emit = defineEmits<{ (event: 'prompt', value: string): void; (event: 'choose-project'): void }>()
</script>

<template>
  <section class="ai-goal-panel" aria-label="当前项目 AI 目标">
    <template v-if="project">
      <div><p class="eyebrow">当前项目 · {{ project.title }}</p><h2>你现在想解决什么？</h2><p>先选一个目标，AI 只围绕当前项目和当前任务提供帮助。</p></div>
      <div class="ai-goal-grid">
        <button type="button" @click="emit('prompt', '请结合当前项目，帮我把下一步任务拆成三个可以马上执行的小步骤。')"><strong>我不知道下一步怎么做</strong><small>把当前任务拆成可执行的小步骤</small></button>
        <button type="button" @click="emit('prompt', '请先追问我，再帮我检查当前研究问题的对象、范围和可验证证据。')"><strong>我想完善研究问题</strong><small>检查问题边界，不新建项目</small></button>
        <button type="button" @click="emit('prompt', '我有一个具体问题，请结合当前项目材料回答，并说明依据和不确定的地方。')"><strong>我有一个具体问题</strong><small>先提问，再决定是否保存建议</small></button>
      </div>
    </template>
    <div v-else class="ai-goal-empty"><p class="eyebrow">已有课题 · 还没有选中项目</p><strong>从“我的项目”选择一个项目后再开始</strong><small>这样 AI 才能读取正确的研究问题、任务和材料。</small><button class="secondary-button" type="button" @click="emit('choose-project')">选择项目 →</button></div>
  </section>
</template>

<style scoped>
.ai-goal-panel { display: grid; gap: 16px; margin: 0; padding: 0; border: 0; border-radius: 0; background: transparent; }
.ai-goal-panel h2 { margin: 0 0 4px; font: 700 20px/1.35 var(--sans); }
.ai-goal-panel p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.55; }
.ai-goal-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.ai-goal-grid button { min-width: 0; padding: 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); color: var(--ink); text-align: left; cursor: pointer; }
.ai-goal-grid button:hover, .ai-goal-grid button:focus-visible { border-color: var(--moss); background: #fff; }
.ai-goal-grid strong, .ai-goal-grid small { display: block; overflow-wrap: anywhere; }
.ai-goal-grid strong { font-size: 12px; }
.ai-goal-grid small { margin-top: 5px; color: var(--muted); font-size: 11px; line-height: 1.45; }
.ai-goal-empty { display: grid; gap: 8px; }
.ai-goal-empty strong { font: 700 17px/1.4 var(--sans); }
.ai-goal-empty small { color: var(--muted); font-size: 12px; }
.ai-goal-empty .secondary-button { width: fit-content; margin-top: 4px; }
@media (max-width: 980px) { .ai-goal-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 780px) { .ai-goal-panel { margin-inline: 14px; } .ai-goal-grid { grid-template-columns: 1fr; } }
</style>
