<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Key } from '@element-plus/icons-vue'
import { errorMessage, getPlatformAIConfig, getServiceStatus, savePlatformAIConfig, type PlatformAIConfig, type PlatformAIConfigPayload, type ServiceStatus } from '../../api'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const status = ref<ServiceStatus | null>(null)
const config = ref<PlatformAIConfig | null>(null)
const apiKeyInput = ref('')
const modelInput = ref('')
const baseUrlInput = ref('')
const feedback = ref<FeedbackState | null>(null)
const loading = ref(true)
const saving = ref(false)
const canSaveConfig = computed(() => Boolean(
  config.value
  && modelInput.value.trim()
  && baseUrlInput.value.trim()
  && (config.value.configured || apiKeyInput.value.trim())
  && !saving.value,
))
const labels: Record<keyof ServiceStatus, string> = { database: '数据库', task_queue: '任务队列', virus_scan: '病毒扫描', document_converter: '文档转换', storage: '文件存储', ai: 'AI 服务' }
function statusLabel(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? '正常' : value === 'not_configured' ? '未配置' : '不可用' }
function statusTone(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? 'active' : 'disabled' }
async function load() {
  loading.value = true
  try {
    const [serviceResponse, configResponse] = await Promise.all([getServiceStatus(), getPlatformAIConfig()])
    status.value = serviceResponse.data
    config.value = configResponse.data
    modelInput.value = configResponse.data.model
    baseUrlInput.value = configResponse.data.base_url
  } catch (reason) {
    status.value = null
    config.value = null
    feedback.value = makeFeedback('error', errorMessage(reason), '平台设置没有加载完成，可以重试。', '重试')
  }
  finally { loading.value = false }
}
async function saveApiConfig() {
  const apiKey = apiKeyInput.value.trim()
  const model = modelInput.value.trim()
  const baseUrl = baseUrlInput.value.trim()
  if (!model) {
    feedback.value = makeFeedback('error', '模型名称不能为空。', '请输入模型名称后再保存。')
    return
  }
  if (!baseUrl) {
    feedback.value = makeFeedback('error', 'Base URL 不能为空。', '请输入 AI 服务 Base URL 后再保存。')
    return
  }
  if (!config.value?.configured && !apiKey) {
    feedback.value = makeFeedback('error', 'API Key 不能为空。', '首次配置请输入 API Key 后再保存。')
    return
  }
  saving.value = true
  try {
    const payload: PlatformAIConfigPayload = { model, base_url: baseUrl }
    if (apiKey) payload.api_key = apiKey
    config.value = (await savePlatformAIConfig(payload)).data
    apiKeyInput.value = ''
    modelInput.value = config.value.model
    baseUrlInput.value = config.value.base_url
    feedback.value = makeFeedback('success', 'AI 服务配置已安全更新。', '页面只保留 API Key 首尾 4 位，完整 Key 不会再次显示。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), 'API Key 没有保存成功，可以检查配置后重试。')
  } finally { saving.value = false }
}
onMounted(load)
</script>

<template>
  <div class="page platform-page">
    <PageHeader eyebrow="设置" title="系统设置" description="查看安全策略和服务健康状态，低频配置不进入日常运营页。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <div class="demo-settings-layout">
      <div class="demo-settings-main">
        <section class="paper-card ai-config-card">
          <div class="settings-section-head">
            <div>
              <div class="section-title-with-icon"><el-icon :size="18" aria-hidden="true"><Key /></el-icon><h2>AI 服务配置</h2></div>
              <p class="section-note">平台统一配置，所有学校共用。完整 API Key 只在首次输入时提交，首次保存后不会再次显示完整 API Key。</p>
            </div>
            <span class="chip">平台级</span>
          </div>
          <p v-if="loading" class="loading-state" role="status">正在读取 AI 配置…</p>
          <div v-else-if="config" class="ai-config-form">
            <div class="masked-key-panel">
              <span class="masked-key-label">当前 API Key</span>
              <strong v-if="config.configured" class="masked-key-value">{{ config.masked_key }}</strong>
              <span v-else class="muted">尚未配置</span>
              <small>{{ config.model }}<span v-if="config.base_url"> · {{ config.base_url }}</span></small>
            </div>
            <label class="field-label" for="platform-ai-model">模型名称</label>
            <input id="platform-ai-model" v-model="modelInput" class="text-input" type="text" autocomplete="off" placeholder="例如 deepseek-v4-flash-260425" :disabled="saving" />
            <label class="field-label" for="platform-ai-base-url">Base URL</label>
            <input id="platform-ai-base-url" v-model="baseUrlInput" class="text-input" type="url" inputmode="url" autocomplete="url" placeholder="例如 https://api.openai.com/v1" :disabled="saving" />
            <label class="field-label" for="platform-ai-key">{{ config.configured ? '替换 API Key（可选）' : '输入 API Key' }}</label>
            <input id="platform-ai-key" v-model="apiKeyInput" class="text-input" type="password" autocomplete="new-password" :placeholder="config.configured ? '留空表示保留当前 Key' : '请输入 API Key'" :disabled="saving" />
            <div class="ai-config-actions">
              <small class="form-hint">API Key 保存后仅显示首尾 4 位；已配置时留空即可只更新模型和 Base URL。</small>
              <button class="primary-button" type="button" :disabled="!canSaveConfig" @click="saveApiConfig">{{ saving ? '保存中…' : '保存 AI 配置' }}</button>
            </div>
          </div>
          <p v-else class="form-hint" role="status">AI 配置暂时不可用，请使用上方“重试”。</p>
        </section>
        <section class="paper-card">
          <div class="settings-section-head"><div><h2>安全策略</h2><p class="section-note">当前环境仅提供策略查看，修改入口将在配置能力启用后开放。</p></div><span class="chip">只读</span></div>
          <div class="demo-settings-list"><div><span><strong>新学校默认授权</strong><small>新建学校后需要管理员手动启用</small></span><span class="chip">关闭</span></div><div><span><strong>学生公开成果申请</strong><small>需要教师审核后进入平台展示</small></span><span class="chip">需审核</span></div></div>
        </section>
        <section class="paper-card">
          <h2>服务健康</h2>
          <p v-if="loading" class="loading-state" role="status">正在读取服务状态…</p>
          <div v-else-if="status" class="demo-settings-list"><div v-for="(value, key) in status" :key="key"><span>{{ labels[key as keyof ServiceStatus] }}</span><StatusTag :status="statusTone(value)" /></div></div>
          <p v-else class="form-hint" role="status">服务状态暂时不可用，请使用上方“重试”。</p>
        </section>
      </div>
      <aside class="paper-card"><h2>修改原则</h2><p class="muted">设置只影响平台策略，不直接改变学生和教师的业务流程。敏感密钥与密码仍只保存在服务端；页面刷新后也不会保留完整 API Key。</p></aside>
    </div>
  </div>
</template>

<style scoped>
.demo-settings-layout { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(260px, .6fr); gap: 20px; align-items: start; }
.demo-settings-main { display: grid; gap: 16px; }
.demo-settings-layout .paper-card { padding: 26px; }
.demo-settings-layout h2 { margin: 0 0 14px; font-size: 20px; }
.settings-section-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.settings-section-head .section-note { margin: -7px 0 14px; color: var(--muted); font-size: 12px; line-height: 1.6; }
.demo-settings-list { display: grid; }
.demo-settings-list > div { display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 52px; border-top: 1px solid var(--line); font-size: 12px; }
.demo-settings-list > div:first-child { border-top: 0; }
.demo-settings-list > div > span:first-child { display: grid; gap: 3px; }
.demo-settings-list small { color: var(--muted); }
.demo-settings-layout aside .secondary-button { margin-top: 16px; }
.section-title-with-icon { display: flex; align-items: center; gap: 8px; }
.section-title-with-icon .el-icon { width: 18px; height: 18px; flex: 0 0 18px; }
.section-title-with-icon h2 { margin-bottom: 0; }
.ai-config-form { display: grid; gap: 10px; }
.masked-key-panel { display: grid; gap: 4px; padding: 14px 16px; border: 1px solid var(--line); border-radius: 10px; background: var(--paper-soft); }
.masked-key-label, .field-label { color: var(--muted); font-size: 12px; }
.masked-key-value { color: var(--ink); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 15px; letter-spacing: .04em; }
.masked-key-panel small { color: var(--muted); font-size: 11px; }
.text-input { width: 100%; box-sizing: border-box; min-height: 42px; padding: 0 12px; border: 1px solid var(--line-strong); border-radius: 8px; background: var(--paper); color: var(--ink); font: inherit; }
.text-input:focus { outline: 2px solid var(--color-focus-ring); border-color: var(--moss); }
.text-input:disabled { cursor: not-allowed; opacity: .65; }
.ai-config-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.ai-config-actions .primary-button { flex: 0 0 auto; }
@media (max-width: 720px) { .ai-config-actions { align-items: flex-start; flex-direction: column; } }
</style>
