<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { type AIAgent, createAIAgent, deleteAIAgent, errorMessage, getAIAgents, updateAIAgent } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const agents = ref<AIAgent[]>([])
const loading = ref(true)
const saving = ref(false)
const feedback = ref<FeedbackState | null>(null)
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const confirmDelete = ref<AIAgent | null>(null)
const formError = ref('')
const search = ref('')
const roleFilter = ref<'all' | AIAgent['role']>('all')
const categoryFilter = ref('all')
const statusFilter = ref<'all' | 'active' | 'inactive'>('all')
const page = ref(1)
const pageSize = 3

const roleLabels: Record<AIAgent['role'], string> = { student: '学生', teacher: '教师', both: '师生通用' }

const emptyForm = () => ({
  key: '', name: '', description: '', role: 'student' as AIAgent['role'], category: '',
  system_instruction: '', prompt_template: '', input_schema_text: '[]',
  context_scope_text: '{\n  "project_basics": true,\n  "approved_materials": true\n}', is_active: true, order: 0,
})
const form = reactive(emptyForm())

function openCreate() {
  Object.assign(form, emptyForm())
  editingId.value = null
  formError.value = ''
  dialogOpen.value = true
}
function openEdit(agent: AIAgent) {
  Object.assign(form, {
    key: agent.key, name: agent.name, description: agent.description, role: agent.role,
    category: agent.category, system_instruction: agent.system_instruction, prompt_template: agent.prompt_template,
    input_schema_text: JSON.stringify(agent.input_schema, null, 2),
    context_scope_text: JSON.stringify(agent.context_scope_default, null, 2),
    is_active: agent.is_active, order: agent.order,
  })
  editingId.value = agent.id
  formError.value = ''
  dialogOpen.value = true
}

async function load() {
  loading.value = true
  try {
    agents.value = []
    agents.value = (await getAIAgents()).data
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'Skill 没有加载完成，可以重试。', '重试')
  } finally { loading.value = false }
}

function parseJsonField(text: string, fieldName: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`「${fieldName}」不是合法的 JSON。`)
  }
}

async function save() {
  formError.value = ''
  if (!form.key.trim() || !form.name.trim() || !form.system_instruction.trim() || !form.prompt_template.trim()) {
    formError.value = 'key、名称、系统指令与提示词模板均为必填。'
    return
  }
  let inputSchema: unknown
  let contextScope: unknown
  try {
    inputSchema = parseJsonField(form.input_schema_text, '输入变量')
    contextScope = parseJsonField(form.context_scope_text, '资料范围')
  } catch (e) {
    formError.value = (e as Error).message
    return
  }
  const payload = {
    key: form.key.trim(), name: form.name.trim(), description: form.description.trim(), role: form.role,
    category: form.category.trim(), system_instruction: form.system_instruction, prompt_template: form.prompt_template,
    input_schema: inputSchema as AIAgent['input_schema'],
    context_scope_default: contextScope as Record<string, boolean>,
    is_active: form.is_active, order: form.order,
  }
  saving.value = true
  try {
    if (editingId.value) await updateAIAgent(editingId.value, payload)
    else await createAIAgent(payload)
    dialogOpen.value = false
    await load()
    feedback.value = makeFeedback('success', 'Skill 已保存。', '师生端的 Skill 列表会立即按角色更新。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '未保存的内容仍保留，可以修正后重试。', '重试')
  } finally { saving.value = false }
}

async function confirmRemove() {
  if (!confirmDelete.value) return
  const target = confirmDelete.value
  confirmDelete.value = null
  try {
    await deleteAIAgent(target.id)
    await load()
    feedback.value = makeFeedback('success', 'Skill 已删除。', '该 Skill 不再出现在师生端的技能列表中。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '没有删除成功，可以重试。', '重试')
  }
}

async function toggleAgent(agent: AIAgent) {
  saving.value = true
  try {
    await updateAIAgent(agent.id, { is_active: !agent.is_active })
    await load()
    feedback.value = makeFeedback('success', agent.is_active ? 'Skill 已停用。' : 'Skill 已启用。', agent.is_active ? '学生和教师不会再看到该 Skill。' : 'Skill 已按角色重新出现在可用列表。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'Skill 启用状态没有改变，可以重试。', '重试')
  } finally { saving.value = false }
}

const categories = computed(() => ['all', ...new Set(agents.value.map((agent) => agent.category?.trim()).filter(Boolean) as string[])])
const sortedAgents = computed(() => [...agents.value]
  .filter((agent) => {
    const keyword = search.value.trim().toLowerCase()
    const matchesSearch = !keyword || `${agent.name} ${agent.key} ${agent.description}`.toLowerCase().includes(keyword)
    const matchesRole = roleFilter.value === 'all' || agent.role === roleFilter.value
    const matchesCategory = categoryFilter.value === 'all' || (agent.category || '其他') === categoryFilter.value
    const matchesStatus = statusFilter.value === 'all' || (statusFilter.value === 'active' ? agent.is_active : !agent.is_active)
    return matchesSearch && matchesRole && matchesCategory && matchesStatus
  })
  .sort((a, b) => a.order - b.order || a.id - b.id))
const totalPages = computed(() => Math.max(1, Math.ceil(sortedAgents.value.length / pageSize)))
const pagedAgents = computed(() => sortedAgents.value.slice((page.value - 1) * pageSize, page.value * pageSize))

watch([search, roleFilter, categoryFilter, statusFilter], () => { page.value = 1 })
watch(totalPages, (value) => { if (page.value > value) page.value = value })

onMounted(load)
</script>

<template>
  <div class="page platform-page">
    <PageHeader eyebrow="Skill 管理" title="Skills" description="维护师生端可用的 Skill、角色、分组、上下文范围和启用状态。使用流程从师生任务入口进入。"><template #actions><button class="primary-button" type="button" @click="openCreate">+ 新建 Skill</button></template></PageHeader>
    <FeedbackBanner v-model="feedback" @action="load" />
    <section class="paper-card agent-admin-panel">
      <div class="agent-filters filter-bar" role="search" aria-label="筛选 Skill">
        <input v-model="search" class="input" type="search" placeholder="搜索 Skill 名称" />
        <select v-model="roleFilter" class="select"><option value="all">全部角色</option><option value="student">学生</option><option value="teacher">教师</option><option value="both">师生通用</option></select>
        <select v-model="categoryFilter" class="select"><option v-for="category in categories" :key="category" :value="category">{{ category === 'all' ? '全部分组' : category }}</option></select>
        <select v-model="statusFilter" class="select"><option value="all">全部状态</option><option value="active">已启用</option><option value="inactive">已停用</option></select>
      </div>
      <p v-if="loading" class="loading-state" role="status">正在读取 Skills…</p>
      <div v-if="!loading && sortedAgents.length" class="demo-agent-table table-wrap"><table><thead><tr><th>Skill 名称</th><th>角色</th><th>分组</th><th>最近更新</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="agent in pagedAgents" :key="agent.id"><td><div class="row-title">{{ agent.name }}</div><div class="row-meta">{{ agent.description || '暂无描述' }}</div></td><td>{{ roleLabels[agent.role] }}</td><td><span class="chip">{{ agent.category || '其他' }}</span></td><td>今天</td><td><StatusTag :status="agent.is_active ? 'active' : 'disabled'" /></td><td><div class="agent-table-actions"><button class="secondary-button" type="button" @click="openEdit(agent)">编辑</button><button class="text-link" type="button" @click="toggleAgent(agent)">{{ agent.is_active ? '停用' : '启用' }}</button></div></td></tr></tbody></table></div>
      <div v-if="!loading && sortedAgents.length" class="agent-card-list agent-card-list--mobile">
        <article v-for="agent in pagedAgents" :key="agent.id" class="agent-card">
          <div class="agent-card__heading"><div><strong>{{ agent.name }}</strong><small>{{ roleLabels[agent.role] }} · {{ agent.category || '其他' }}</small></div><el-tag :type="agent.is_active ? 'success' : 'info'" size="small">{{ agent.is_active ? '启用' : '停用' }}</el-tag></div>
          <p>{{ agent.description || '暂无描述' }}</p>
          <dl><div><dt>key</dt><dd>{{ agent.key }}</dd></div><div><dt>归属</dt><dd>{{ agent.school ? '校本' : '全局' }}</dd></div><div><dt>排序</dt><dd>{{ agent.order }}</dd></div></dl>
          <div class="agent-card__actions"><button class="secondary-button" type="button" @click="openEdit(agent)">编辑</button><button class="text-link" type="button" @click="toggleAgent(agent)">{{ agent.is_active ? '停用' : '启用' }}</button><button class="text-link danger" type="button" @click="confirmDelete = agent">删除</button></div>
        </article>
      </div>
      <nav v-if="sortedAgents.length > pageSize" class="agent-pagination" aria-label="Skill 分页">
        <button class="secondary-button" type="button" :disabled="page === 1" @click="page -= 1">上一页</button>
        <span>第 {{ page }} / {{ totalPages }} 页</span>
        <button class="secondary-button" type="button" :disabled="page === totalPages" @click="page += 1">下一页</button>
      </nav>
      <EmptyState v-else-if="agents.length && !sortedAgents.length" title="没有匹配 Skill" description="调整关键词或筛选条件后重试。" compact />
      <EmptyState v-else-if="!loading" title="暂无 Skill" description="点击右上角新建第一个 Skill。" />
    </section>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑 Skill' : '新建 Skill'" width="720px">
      <div v-if="formError" class="form-error" role="alert">{{ formError }}</div>
      <form class="agent-form" @submit.prevent="save">
        <div class="form-row">
          <label>key（Skill 唯一标识）<input v-model="form.key" :disabled="!!editingId" placeholder="如 opening-report"></label>
          <label>Skill 名称<input v-model="form.name" placeholder="如 研究问题助手"></label>
        </div>
        <label>描述<input v-model="form.description" placeholder="一句话说明这个 Skill 做什么"></label>
        <div class="form-row">
          <label>角色
            <select v-model="form.role">
              <option value="student">学生</option>
              <option value="teacher">教师</option>
              <option value="both">师生通用</option>
            </select>
          </label>
          <label>分组<input v-model="form.category" placeholder="如 开题 / 实验 / 写作"></label>
          <label>排序<input v-model.number="form.order" type="number" min="0"></label>
        </div>
        <label>系统指令（system prompt，含护栏）<textarea v-model="form.system_instruction" rows="3" placeholder="你是青少年科创项目教练……"></textarea></label>
        <label>提示词模板（用 {变量名} 占位）<textarea v-model="form.prompt_template" rows="4" placeholder="请结合以下信息：&#10;项目题目：{project_title}"></textarea></label>
        <label>输入变量（JSON 数组）<textarea v-model="form.input_schema_text" rows="5" placeholder='[{"key":"project_title","label":"项目题目","required":true,"type":"text"}]'></textarea></label>
        <label>资料范围默认（JSON）<textarea v-model="form.context_scope_text" rows="4"></textarea></label>
        <label class="switch-line">启用 <el-switch v-model="form.is_active" /></label>
        <footer class="dialog-footer">
          <button v-if="editingId" class="text-link danger" type="button" @click="confirmDelete = agents.find((agent) => agent.id === editingId) || null; dialogOpen = false">删除 Skill</button>
          <button class="secondary-button" type="button" @click="dialogOpen = false">取消</button>
          <button class="primary-button" type="submit" :disabled="saving">{{ saving ? '正在保存…' : '保存' }}</button>
        </footer>
      </form>
    </el-dialog>

    <ConfirmDialog
      v-if="confirmDelete" :model-value="true" title="删除 Skill？"
      :description="`「${confirmDelete.name}」删除后不再出现在师生端 Skill 列表中，已生成的历史记录不受影响。`"
      confirm-text="确认删除" danger @update:model-value="confirmDelete = null" @confirm="confirmRemove"
    />
  </div>
</template>

<style scoped>
.agent-admin-panel { padding: 26px; }
.agent-filters { display: grid; grid-template-columns: minmax(180px, 1.8fr) repeat(3, minmax(120px, 1fr)); gap: 10px; margin: 0 0 8px; padding: 0; border: 0; background: transparent; }
.agent-filters label { display: grid; gap: 5px; color: var(--muted); font-size: 11px; }
.agent-filters input, .agent-filters select { width: 100%; box-sizing: border-box; }
.demo-agent-table table { min-width: 850px; }
.agent-table-actions { display: inline-flex; align-items: center; gap: 9px; }
.agent-card-list--mobile { display: none; }
.agent-pagination { display: flex; align-items: center; justify-content: center; gap: 12px; margin-top: 16px; color: var(--muted); font-size: 12px; }
.agent-form { display: grid; gap: 14px; }
.agent-form .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.agent-form label { min-width: 0; display: grid; gap: 7px; color: var(--muted); font-size: 12px; font-weight: 700; }
.agent-form input, .agent-form textarea, .agent-form select { width: 100%; min-height: 42px; padding: 10px 12px; border: 1px solid var(--line-dark); border-radius: var(--radius-sm); background: var(--paper); color: var(--ink); outline: none; resize: vertical; transition: border-color .16s ease, box-shadow .16s ease; }
.agent-form textarea { line-height: 1.55; }
.agent-form input:focus, .agent-form textarea:focus, .agent-form select:focus { border-color: var(--moss); box-shadow: 0 0 0 3px var(--color-focus-ring); }
.agent-form input:disabled { color: var(--muted); background: var(--paper-muted); cursor: not-allowed; }
.agent-form .switch-line { display: flex; align-items: center; justify-content: space-between; min-height: 42px; padding: 0 12px; border: 1px solid var(--line); border-radius: var(--radius-sm); background: var(--paper-soft); }
.dialog-footer { display: flex; align-items: center; justify-content: flex-end; gap: 10px; padding-top: 4px; border-top: 1px solid var(--line); }
.dialog-footer .danger { margin-right: auto; }
@media (max-width: 700px) {
  .agent-admin-panel { padding: 16px; }
  .agent-admin-panel > .section-heading { flex-direction: column; align-items: flex-start; gap: 12px; width: 100%; }
  .agent-admin-panel > .section-heading h2 { font-size: 20px; line-height: 1.35; }
  .agent-admin-panel > .section-heading .primary-button { width: 100%; justify-content: center; }
  .agent-filters { grid-template-columns: 1fr 1fr; }
  .agent-filters label:first-child { grid-column: 1 / -1; }
  .agent-card-list--mobile { display: grid; gap: 10px; }
  .agent-card { display: grid; gap: 10px; padding: 14px; border: 1px solid var(--line); border-radius: var(--radius-md); background: var(--paper); }
  .agent-card__heading, .agent-card__actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .agent-card__heading strong, .agent-card__heading small { display: block; overflow-wrap: anywhere; }
  .agent-card__heading strong { font: 700 16px/1.35 var(--sans); }
  .agent-card__heading small, .agent-card p, .agent-card dt { color: var(--muted); font-size: 11px; }
  .agent-card p { margin: 0; line-height: 1.55; }
  .agent-card dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 0; }
  .agent-card dl div { display: grid; gap: 2px; min-width: 0; }
  .agent-card dt { font-size: 10px; }
  .agent-card dd { margin: 0; overflow-wrap: anywhere; font-size: 11px; }
  .agent-card__actions { justify-content: flex-start; }
}
</style>
