<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { type AIAgent, createAIAgent, deleteAIAgent, errorMessage, getAIAgents, updateAIAgent } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const agents = ref<AIAgent[]>([])
const loading = ref(true)
const saving = ref(false)
const feedback = ref<FeedbackState | null>(null)
const dialogOpen = ref(false)
const editingId = ref<number | null>(null)
const confirmDelete = ref<AIAgent | null>(null)
const formError = ref('')

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
    agents.value = (await getAIAgents()).data
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'AI 模板没有加载完成，可以重试。', '重试')
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
    feedback.value = makeFeedback('success', 'AI 模板已保存。', '师生端的 AI 助手列表会立即按角色更新。')
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
    feedback.value = makeFeedback('success', 'AI 模板已删除。', '该模板不再出现在师生端的助手列表中。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '没有删除成功，可以重试。', '重试')
  }
}

const sortedAgents = computed(() => [...agents.value].sort((a, b) => a.order - b.order || a.id - b.id))

onMounted(load)
</script>

<template>
  <div class="page platform-page">
    <PageHeader eyebrow="平台配置" title="AI 助手模板" description="在这里维护面向学生与教师的 AI 助手：每个助手拥有独立的系统指令、提示词模板与输入变量。管理员维护的是全局模板，教师可在本校范围内覆盖。" />
    <FeedbackBanner v-model="feedback" />
    <section class="paper-card agent-admin-panel">
      <div class="section-heading">
        <div><p class="eyebrow">模板库</p><h2>共 {{ agents.length }} 个 AI 助手</h2></div>
        <button class="primary-button" type="button" @click="openCreate"><el-icon><MagicStick /></el-icon> 新建 AI 助手</button>
      </div>
      <el-table v-if="sortedAgents.length" :data="sortedAgents" class="agent-table">
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="key" label="key" min-width="150" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">{{ roleLabels[row.role as AIAgent['role']] }}</template>
        </el-table-column>
        <el-table-column prop="category" label="分组" min-width="100" />
        <el-table-column label="归属" width="100">
          <template #default="{ row }">{{ row.school ? '校本' : '全局' }}</template>
        </el-table-column>
        <el-table-column label="启用" width="90">
          <template #default="{ row }"><el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="order" label="排序" width="80" />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <button class="text-link" type="button" @click="openEdit(row)">编辑</button>
            <button class="text-link danger" type="button" @click="confirmDelete = row">删除</button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else-if="!loading" title="暂无 AI 助手模板" description="点击右上角新建第一个 AI 助手。" />
    </section>

    <el-dialog v-model="dialogOpen" :title="editingId ? '编辑 AI 助手' : '新建 AI 助手'" width="720px">
      <div v-if="formError" class="form-error" role="alert">{{ formError }}</div>
      <form class="agent-form" @submit.prevent="save">
        <div class="form-row">
          <label>key（唯一标识）<input v-model="form.key" :disabled="!!editingId" placeholder="如 opening-report"></label>
          <label>名称<input v-model="form.name" placeholder="如 开题报告助手"></label>
        </div>
        <label>描述<input v-model="form.description" placeholder="一句话说明这个助手做什么"></label>
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
          <button class="secondary-button" type="button" @click="dialogOpen = false">取消</button>
          <button class="primary-button" type="submit" :disabled="saving">{{ saving ? '正在保存…' : '保存' }}</button>
        </footer>
      </form>
    </el-dialog>

    <ConfirmDialog
      v-if="confirmDelete" :model-value="true" title="删除 AI 助手？"
      :description="`「${confirmDelete.name}」删除后不再出现在师生端助手列表中，已生成的历史记录不受影响。`"
      confirm-text="确认删除" danger @update:model-value="confirmDelete = null" @confirm="confirmRemove"
    />
  </div>
</template>
