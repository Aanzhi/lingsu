<script setup lang="ts">
import type { Project } from '../../api'
import type { ResearchQuestionArtifact, ResearchQuestionInputs } from '../../stores/aiConversationModel'
import { studentProjectRoute } from '../../stores/pageContracts'

type ResearchProjectDraft = {
  title: string
  problem: string
  plan: string
  project_type: Project['project_type']
}

const props = defineProps<{
  workspaceMode: 'brainstorm' | 'project'
  workspaceContextLabel: string
  researchStep: 1 | 2 | 3 | 4
  researchInputs: ResearchQuestionInputs
  researchArtifact: ResearchQuestionArtifact | null
  researchSelectedIndex: number | null
  researchDraft: string
  researchSaveConfirm: boolean
  researchSaved: boolean
  researchSaveError: string
  researchFallback: string
  projectDraft: ResearchProjectDraft
  currentProject: Project | null
  sending: boolean
  creatingProject: boolean
  projectCreated: boolean
}>()

const emit = defineEmits<{
  (event: 'update:research-step', value: 1 | 2 | 3 | 4): void
  (event: 'update:research-draft', value: string): void
  (event: 'update:research-save-confirm', value: boolean): void
  (event: 'update:research-fallback', value: string): void
  (event: 'advance-from-observation'): void
  (event: 'generate'): void
  (event: 'choose-candidate', index: number): void
  (event: 'edit-candidate', index: number, value: string): void
  (event: 'open-draft'): void
  (event: 'request-save'): void
  (event: 'create-project'): void
  (event: 'save-question'): void
  (event: 'copy-question'): void
}>()

function setStep(value: 1 | 2 | 3 | 4) {
  emit('update:research-step', value)
}
</script>

<template>
  <section class="research-workbench" aria-label="研究问题工作台">
    <div class="research-heading">
      <div>
        <span class="eyebrow">{{ props.workspaceMode === 'brainstorm' ? '无课题 · 选题引导' : '已有课题 · 问题完善' }}</span>
        <h2>{{ props.workspaceMode === 'brainstorm' ? '从一个真实观察开始' : '把当前研究问题想得更清楚' }}</h2>
        <p>{{ props.workspaceMode === 'project' ? 'AI 只提供追问、候选和理由，最后由你确认写入当前项目。' : 'AI 不直接替你命题，会先追问、比较，最后由你确认项目草稿。' }}</p>
      </div>
      <span class="research-project">{{ props.workspaceContextLabel }}</span>
    </div>

    <div class="research-steps ai-stepper-simple" aria-label="研究问题步骤">
      <button class="ai-step-simple" type="button" :class="{ active: props.researchStep === 1, done: props.researchStep > 1 }" @click="setStep(1)"><span>{{ props.researchStep > 1 ? '✓' : '1' }}</span><small>发现现象</small></button>
      <button class="ai-step-simple" type="button" :class="{ active: props.researchStep === 2, done: props.researchStep > 2 }" @click="setStep(2)"><span>{{ props.researchStep > 2 ? '✓' : '2' }}</span><small>打开问题</small></button>
      <button class="ai-step-simple" type="button" :class="{ active: props.researchStep === 3, done: props.researchStep > 3 }" @click="setStep(3)"><span>{{ props.researchStep > 3 ? '✓' : '3' }}</span><small>头脑风暴</small></button>
      <button class="ai-step-simple" type="button" :class="{ active: props.researchStep === 4 }" @click="setStep(4)"><span>4</span><small>共同成题</small></button>
    </div>

    <form v-if="props.researchStep === 1" class="research-step-card" @submit.prevent="emit('advance-from-observation')">
      <p class="step-kicker">第 1 步 · 发现现象</p>
      <label>
        <strong>先说一件真实的小事</strong>
        <small>我不会先替你给出一个项目题目。请写下最近注意到、好奇或觉得不方便的事情。</small>
        <textarea v-model="props.researchInputs.phenomenon" rows="4" placeholder="例如：下雨后校园操场的一侧总是积水，放晴很久仍然很湿。" />
      </label>
      <p v-if="props.researchSaveError" class="research-error">{{ props.researchSaveError }}</p>
      <div class="research-actions"><span>不用写正式题目，先从事实开始。</span><button class="primary-button" type="submit">记录观察，继续追问 →</button></div>
    </form>

    <form v-else-if="props.researchStep === 2" class="research-step-card" @submit.prevent="emit('generate')">
      <p class="step-kicker">第 2 步 · 打开问题</p>
      <label><strong>研究对象与场景：把现象拆开看看</strong><small>谁受到影响？什么时候最明显？你已经知道什么？</small><input v-model="props.researchInputs.object_context" placeholder="例如：本校操场东侧、每次降雨后的 2 小时" /></label>
      <label><strong>你想弄清楚哪个方向？</strong><small>说明你希望解释、比较或验证什么。</small><textarea v-model="props.researchInputs.goal" rows="3" placeholder="例如：比较不同地面坡度与积水持续时间的关系。" /></label>
      <label><strong>时间、设备、样本或资源限制（可选）</strong><textarea v-model="props.researchInputs.constraints" rows="2" placeholder="例如：只有两周、手机和简单的量尺。" /></label>
      <p v-if="props.researchSaveError" class="research-error">{{ props.researchSaveError }}</p>
      <div class="research-actions"><button class="secondary-button" type="button" :disabled="props.sending" @click="setStep(1)">上一步</button><button class="primary-button" type="submit" :disabled="props.sending">{{ props.sending ? '正在整理方向…' : '进入头脑风暴 →' }}</button></div>
    </form>

    <section v-else-if="props.researchStep === 3" class="research-step-card candidate-review">
      <p class="step-kicker">第 3 步 · 头脑风暴</p>
      <div class="step-heading"><div><h3>先比较几个可研究方向</h3><p>下面是讨论方向，不是 AI 替你决定的答案。请选择一个你愿意继续观察的方向。</p></div><span class="draft-status">{{ props.researchSelectedIndex === null ? '等待选择' : '已选择方向' }}</span></div>
      <div v-if="props.researchArtifact" class="candidate-grid">
        <article v-for="(candidate, index) in props.researchArtifact.candidates" :key="index" class="candidate-card" :class="{ selected: props.researchSelectedIndex === index }">
          <label class="candidate-select"><input type="radio" name="research-candidate" :checked="props.researchSelectedIndex === index" @change="emit('choose-candidate', index)" /><span>方向 {{ String.fromCharCode(65 + index) }}<small v-if="props.researchArtifact?.recommended_index === index">AI 建议先看</small></span></label>
          <textarea :value="candidate.question" rows="3" aria-label="候选研究问题" @focus="emit('choose-candidate', index)" @input="emit('edit-candidate', index, ($event.target as HTMLTextAreaElement).value)" />
          <dl><div><dt>研究边界</dt><dd>{{ candidate.scope || '请补充对象和范围' }}</dd></div><div><dt>可获得的证据</dt><dd>{{ candidate.evidence_plan || '请写下可观察或可测量的证据' }}</dd></div><div><dt>可能的限制</dt><dd>{{ candidate.limitations || '请评估样本、时间和设备限制' }}</dd></div></dl>
          <div class="score-grid"><span>可研究性 <b>{{ candidate.scores.researchability }}/5</b></span><span>可验证性 <b>{{ candidate.scores.verifiability }}/5</b></span></div>
        </article>
      </div>
      <div v-else class="research-fallback"><strong>模型返回了可编辑文本</strong><p>结构化候选暂时不可用，请保留原始文本并手动整理研究问题。</p><textarea :value="props.researchFallback" rows="6" @input="emit('update:research-fallback', ($event.target as HTMLTextAreaElement).value)" /></div>
      <p v-if="props.researchArtifact?.missing_information?.length" class="research-missing">继续前还需核验：{{ props.researchArtifact.missing_information.join('；') }}</p>
      <p v-if="props.researchSaveError" class="research-error">{{ props.researchSaveError }}</p>
      <div class="research-actions"><button class="secondary-button" type="button" :disabled="props.sending" @click="setStep(2)">返回修改条件</button><button class="secondary-button" type="button" :disabled="props.sending" @click="emit('generate')">重新生成</button><button class="primary-button" type="button" :disabled="props.sending || !props.researchDraft.trim()" @click="emit('open-draft')">继续形成项目草稿 →</button></div>
    </section>

    <section v-else class="research-step-card research-draft-step">
      <p class="step-kicker">第 4 步 · 共同成题</p>
      <div class="step-heading"><div><h3>{{ props.workspaceMode === 'brainstorm' ? '把你的思路整理成项目草稿' : '确认要写入当前项目的问题' }}</h3><p>{{ props.workspaceMode === 'brainstorm' ? '标题、研究问题和初步方案都可以修改；确认前不会创建项目。' : '先检查 AI 建议，再决定是否保存到当前项目。' }}</p></div><span class="draft-status">{{ props.researchSaved ? '已保存' : props.workspaceMode === 'brainstorm' && props.projectCreated ? '已创建' : '待你确认' }}</span></div>
      <div v-if="props.workspaceMode === 'brainstorm'" class="research-project-draft"><label>项目标题<input v-model="props.projectDraft.title" placeholder="给这个研究项目起一个清晰的名字" /></label><label>项目类型<select v-model="props.projectDraft.project_type"><option value="research">研究型</option><option value="invention">发明型</option><option value="engineering">工程型</option></select></label><label>研究问题<textarea v-model="props.projectDraft.problem" rows="3" placeholder="确认一个可观察、可验证的问题" /></label><label>初步方案（可选）<textarea v-model="props.projectDraft.plan" rows="3" placeholder="准备如何观察、制作、比较或验证？" /></label><p class="research-safety-note">确认并生成项目前不会创建空项目；创建失败时草稿会保留。</p></div>
      <div v-else class="research-project-draft"><label>当前项目研究问题<textarea :value="props.researchDraft" rows="4" placeholder="确认一个可观察、可验证的问题" @input="emit('update:research-draft', ($event.target as HTMLTextAreaElement).value)" /></label><p class="research-safety-note">保存后会更新当前项目的问题，不会创建新项目。</p></div>
      <p v-if="props.researchSaveError" class="research-error">{{ props.researchSaveError }}</p>
      <div class="research-actions"><button class="secondary-button" type="button" :disabled="props.sending || props.creatingProject" @click="setStep(3)">返回比较方向</button><button v-if="props.workspaceMode === 'project'" class="primary-button" type="button" :disabled="props.sending || props.creatingProject || !props.researchDraft.trim()" @click="emit('request-save')">选择并保存到当前项目</button><button v-else class="primary-button" type="button" :disabled="props.sending || props.creatingProject || !props.projectDraft.title.trim() || !props.projectDraft.problem.trim()" @click="emit('create-project')">{{ props.creatingProject ? '正在生成项目…' : '确认并生成项目' }}</button></div>
      <div v-if="props.workspaceMode === 'project' && props.researchSaveConfirm" class="research-confirm"><strong>确认写入当前项目的问题？</strong><div><small>当前项目原问题</small><p>{{ props.currentProject?.problem || '（暂为空）' }}</p></div><div><small>将保存的新问题</small><textarea :value="props.researchDraft" rows="3" @input="emit('update:research-draft', ($event.target as HTMLTextAreaElement).value)" /></div><div class="research-actions"><button class="secondary-button" type="button" @click="emit('update:research-save-confirm', false)">取消</button><button class="primary-button" type="button" :disabled="props.sending" @click="emit('save-question')">确认保存</button></div></div>
      <div v-if="props.researchSaved" class="research-saved"><strong>研究问题已保存到项目。</strong><span>下一步可以完善研究背景、拆解研究目标或制定实施方案。</span><div><RouterLink class="secondary-button" :to="props.currentProject ? studentProjectRoute(props.currentProject.id) : '/student/projects'">返回项目</RouterLink><button class="secondary-button" type="button" @click="emit('copy-question')">复制问题</button></div></div>
    </section>
  </section>
</template>

<style scoped>
.research-workbench { margin: 0 26px 24px; padding: 22px; border: 1px solid var(--sage-line); border-radius: var(--radius-md); background: #fcfdf9; }
.research-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.research-heading h2 { margin: 4px 0 6px; font: 700 23px/1.35 var(--sans); }
.research-heading p, .step-heading p { margin: 0; max-width: 650px; color: var(--muted); font-size: 12px; line-height: 1.65; }
.research-project { max-width: 38%; color: var(--moss-dark); font-size: 12px; text-align: right; overflow-wrap: anywhere; }
.research-steps.ai-stepper-simple { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin: 20px 0 14px; color: var(--muted); font-size: 11px; }
.research-steps .ai-step-simple { display: flex; align-items: center; gap: 7px; min-width: 0; padding: 0; border: 0; border-radius: 0; background: transparent; color: var(--muted-light); text-align: left; cursor: pointer; }
.research-steps .ai-step-simple span { display: grid; width: 24px; height: 24px; flex: 0 0 auto; place-items: center; border-radius: 50%; background: var(--paper-muted); color: var(--muted); font-size: 10px; font-weight: 700; }
.research-steps .ai-step-simple small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.research-steps .ai-step-simple.active { color: var(--moss-dark); font-weight: 700; }
.research-steps .ai-step-simple.active span, .research-steps .ai-step-simple.done span { background: var(--moss); color: #fff; }
.research-steps .ai-step-simple:hover, .research-steps .ai-step-simple:focus-visible { color: var(--moss-dark); }
.research-step-card { display: grid; gap: 16px; padding: 18px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); }
.step-kicker { margin: 0; color: var(--moss); font-size: 11px; font-weight: 800; letter-spacing: .08em; }
.research-step-card label { display: grid; gap: 7px; color: var(--ink); font-size: 12px; }
.research-step-card label small { color: var(--muted); line-height: 1.55; }
.research-step-card input, .research-step-card textarea, .research-project-draft input, .research-project-draft select, .research-project-draft textarea { width: 100%; box-sizing: border-box; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); background: #fff; color: var(--ink); font: inherit; padding: 10px; }
.research-step-card textarea { resize: vertical; line-height: 1.55; }
.research-actions { display: flex; align-items: center; justify-content: flex-end; flex-wrap: wrap; gap: 8px; }
.research-actions > span { margin-right: auto; color: var(--muted); font-size: 11px; }
.research-error { margin: 0; color: #9b4d3e; font-size: 12px; }
.step-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.step-heading h3 { margin: 0 0 5px; font: 700 19px/1.4 var(--sans); }
.draft-status { padding: 4px 8px; border-radius: 999px; background: var(--paper-soft); color: var(--muted); font-size: 10px; white-space: nowrap; }
.candidate-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.candidate-card { display: grid; gap: 9px; min-width: 0; padding: 13px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper); }
.candidate-card.selected { border-color: var(--moss); box-shadow: 0 0 0 2px rgba(76,114,69,.1); }
.candidate-select { display: flex !important; align-items: center; gap: 7px; color: var(--moss-dark) !important; font-size: 12px !important; font-weight: 700; }
.candidate-select span { display: flex; align-items: center; gap: 7px; }
.candidate-select small { color: var(--muted); font-weight: 400; }
.candidate-card dl { display: grid; gap: 7px; margin: 0; }
.candidate-card dl div { display: grid; gap: 2px; }
.candidate-card dt { color: var(--moss); font-size: 10px; font-weight: 700; }
.candidate-card dd { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.5; overflow-wrap: anywhere; }
.score-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; color: var(--muted); font-size: 10px; }
.score-grid span { display: flex; justify-content: space-between; gap: 4px; padding: 4px 5px; border-radius: var(--radius-sm); background: var(--paper-soft); }
.score-grid b { color: var(--moss-dark); }
.research-fallback { display: grid; gap: 7px; padding: 12px; border: 1px dashed var(--line-dark); border-radius: var(--radius-sm); }
.research-fallback p, .research-fallback strong { margin: 0; font-size: 12px; }
.research-fallback p { color: var(--muted); }
.research-fallback textarea { resize: vertical; }
.research-missing, .research-safety-note { margin: 0; padding: 9px 11px; border-radius: var(--radius-sm); background: var(--sage-soft); color: var(--moss-dark); font-size: 11px; line-height: 1.55; }
.research-project-draft { display: grid; gap: 12px; padding: 16px; border: 1px solid var(--sage-line); border-radius: var(--radius-md); background: var(--paper-soft); }
.research-project-draft label { font-weight: 700; }
.research-confirm { display: grid; gap: 8px; padding: 12px; border: 1px solid var(--moss); border-radius: var(--radius-md); background: var(--sage-soft); }
.research-confirm > div { display: grid; gap: 3px; }
.research-confirm small { color: var(--muted); font-size: 10px; }
.research-confirm p { margin: 0; font-size: 12px; line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; }
.research-confirm textarea { width: 100%; box-sizing: border-box; }
.research-saved { display: grid; gap: 6px; padding: 11px; border-radius: var(--radius-sm); background: var(--sage-soft); color: var(--moss-dark); font-size: 12px; }
.research-saved span { color: var(--muted); font-size: 11px; }
.research-saved > div { display: flex; flex-wrap: wrap; gap: 7px; }
.research-saved a { display: inline-flex; align-items: center; text-decoration: none; }
@media (max-width: 980px) { .candidate-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 780px) { .research-workbench { margin-inline: 14px; padding: 16px; } .research-heading { display: block; } .research-project { max-width: none; margin-top: 6px; text-align: left; } .candidate-grid { grid-template-columns: 1fr; } .step-heading { display: block; } .draft-status { display: inline-flex; margin-top: 8px; } }
@media (max-width: 430px) { .research-workbench { margin-inline: 10px; padding: 13px; } .research-actions { align-items: stretch; flex-direction: column; } .research-actions > span { margin-right: 0; } .research-actions > button { width: 100%; } }
</style>
