<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Key, Setting } from '@element-plus/icons-vue'
import { errorMessage, getServiceStatus, type ServiceStatus } from '../../api'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const status = ref<ServiceStatus | null>(null)
const feedback = ref<FeedbackState | null>(null)
const loading = ref(true)
const labels: Record<keyof ServiceStatus, string> = { database: '数据库', task_queue: '任务队列', virus_scan: '病毒扫描', document_converter: '文档转换', storage: '文件存储', ai: 'AI 服务' }
function statusLabel(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? '正常' : value === 'not_configured' ? '未配置' : '不可用' }
function statusTone(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? 'active' : 'disabled' }
async function load() {
  loading.value = true
  try { status.value = (await getServiceStatus()).data }
  catch (reason) { status.value = null; feedback.value = makeFeedback('error', errorMessage(reason), '服务状态没有加载完成，可以重试。', '重试') }
  finally { loading.value = false }
}
onMounted(load)
</script>

<template>
  <div class="page platform-page">
    <PageHeader eyebrow="设置" title="系统设置" description="查看安全策略和服务健康状态，低频配置不进入日常运营页。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <div class="demo-settings-layout"><div class="demo-settings-main"><section class="paper-card"><div class="settings-section-head"><div><h2>安全策略</h2><p class="section-note">当前环境仅提供策略查看，修改入口将在配置能力启用后开放。</p></div><span class="chip">只读</span></div><div class="demo-settings-list"><div><span><strong>新学校默认授权</strong><small>新建学校后需要管理员手动启用</small></span><span class="chip">关闭</span></div><div><span><strong>学生公开成果申请</strong><small>需要教师审核后进入平台展示</small></span><span class="chip">需审核</span></div></div></section><section class="paper-card"><h2>服务健康</h2><p v-if="loading" class="loading-state" role="status">正在读取服务状态…</p><div v-else-if="status" class="demo-settings-list"><div v-for="(value, key) in status" :key="key"><span>{{ labels[key as keyof ServiceStatus] }}</span><StatusTag :status="statusTone(value)" /></div></div><p v-else class="form-hint" role="status">服务状态暂时不可用，请使用上方“重试”。</p></section></div><aside class="paper-card"><h2>修改原则</h2><p class="muted">设置只影响平台策略，不直接改变学生和教师的业务流程。敏感密钥与密码仍只保存在服务端。</p></aside></div>
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
</style>
