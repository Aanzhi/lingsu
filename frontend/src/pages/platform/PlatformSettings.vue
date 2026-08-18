<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { Collection, Key, Medal, Reading, School, Setting } from '@element-plus/icons-vue'
import { errorMessage, getServiceStatus, type ServiceStatus } from '../../api'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'

const status = ref<ServiceStatus | null>(null)
const feedback = ref<FeedbackState | null>(null)
const labels: Record<keyof ServiceStatus, string> = { database: '数据库', task_queue: '任务队列', virus_scan: '病毒扫描', document_converter: '文档转换', storage: '文件存储', ai: 'AI 服务' }
function statusLabel(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? '正常' : value === 'not_configured' ? '未配置' : '不可用' }
function statusTone(value: string) { return value === 'healthy' || value === 'configured' || value === 'local' ? 'active' : 'disabled' }
async function load() { try { status.value = (await getServiceStatus()).data } catch (reason) { feedback.value = makeFeedback('error', errorMessage(reason), '服务状态没有加载完成，可以重试。', '重试') } }
onMounted(load)
</script>

<template>
  <div class="page platform-page">
    <PageHeader eyebrow="平台配置" title="安全与服务状态" description="平台只展示服务是否可用，不在浏览器中暴露密钥、密码或项目过程数据。" />
    <FeedbackBanner v-model="feedback" @action="load" />
    <div class="settings-grid">
      <section class="settings-card"><el-icon><Setting /></el-icon><div><h2>平台安全策略</h2><p>学校数据强制隔离，平台账号不能进入学校项目过程。</p></div><StatusTag status="active" /></section>
      <section class="settings-card"><el-icon><Key /></el-icon><div><h2>敏感配置边界</h2><p>AI 密钥、数据库密码与站点配置仅保存在服务端环境变量。</p></div><StatusTag status="active" /></section>
    </div>
    <p class="settings-note">本页为只读状态台。所有可写配置（AI 密钥、站点参数、学校授权与配额）均在服务端环境变量与各校管理页维护，不会在浏览器中暴露或编辑。</p>
    <nav class="quick-nav">
      <RouterLink to="/platform/schools"><el-icon><School /></el-icon><div><strong>学校管理</strong><small>授权、配额与邀请码</small></div></RouterLink>
      <RouterLink to="/platform/competitions"><el-icon><Medal /></el-icon><div><strong>赛事信息</strong><small>维护可报名赛事</small></div></RouterLink>
      <RouterLink to="/platform/announcements"><el-icon><Reading /></el-icon><div><strong>通知公告</strong><small>发布平台级公告</small></div></RouterLink>
      <RouterLink to="/platform/cases"><el-icon><Collection /></el-icon><div><strong>案例治理</strong><small>公开案例二级审核</small></div></RouterLink>
    </nav>
    <section class="service-status-panel paper-card"><div class="section-heading"><div><p class="eyebrow">运行诊断</p><h2>平台服务健康</h2></div><span v-if="status">已读取</span></div><div v-if="status" class="service-status-grid"><article v-for="(value, key) in status" :key="key"><div><strong>{{ statusLabel(value) }}</strong><small>{{ labels[key as keyof ServiceStatus] }}</small></div><StatusTag :status="statusTone(value)" /></article></div><p v-else class="form-hint">正在读取服务状态…</p><p class="form-hint">“正常”表示已完成可达性检查；“未配置”表示该能力不会在当前环境执行。</p></section>
  </div>
</template>

<style scoped>
.settings-note {
  margin: 0 0 20px;
  padding: 12px 16px;
  border: 1px solid var(--amber-line);
  background: var(--amber-soft);
  border-radius: var(--radius-md);
  color: var(--clay-deep);
  font-size: 13px;
  line-height: 1.7;
}
.quick-nav {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin-bottom: 28px;
}
.quick-nav a {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--paper);
  text-decoration: none;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.quick-nav a:hover {
  border-color: var(--sage-line);
  box-shadow: var(--shadow);
}
.quick-nav .el-icon {
  font-size: 20px;
  color: var(--moss);
}
.quick-nav strong {
  display: block;
  color: var(--ink);
  font-size: 14px;
}
.quick-nav small {
  color: var(--muted);
  font-size: 12px;
}
</style>
