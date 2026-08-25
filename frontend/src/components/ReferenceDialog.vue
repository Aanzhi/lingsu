<script setup lang="ts">
import { Download, Document } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: boolean
  title?: string
  guidance: string
  referenceUrl: string | null
  originalName: string | null
}>()
const emit = defineEmits<{ 'update:modelValue': [boolean] }>()
function close() { emit('update:modelValue', false) }
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title ?? '材料参考范本'"
    width="640px"
    align-center
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="reference-dialog">
      <section v-if="guidance" class="reference-guidance">
        <p class="eyebrow">这份材料要写什么</p>
        <p class="reference-guidance__text">{{ guidance }}</p>
      </section>
      <section v-else class="reference-guidance reference-guidance--empty">
        <p>这份材料还没有结构化指引，可参考下方模板或直接进入任务按要求提交。</p>
      </section>
      <section v-if="referenceUrl" class="reference-download">
        <el-icon class="reference-download__icon"><Document /></el-icon>
        <div class="reference-download__meta">
          <strong>{{ originalName ?? '参考范本' }}</strong>
          <small>空白范本，已按指引排好章节，下载后直接填写。</small>
        </div>
        <a class="primary-button" :href="referenceUrl" :download="originalName ?? '参考范本'">
          <el-icon><Download /></el-icon> 下载范本
        </a>
      </section>
      <p v-else class="reference-hint">暂无可下载的空白范本，按上面指引直接提交即可。</p>
    </div>
    <template #footer>
      <button class="secondary-button" type="button" @click="close">关闭</button>
    </template>
  </el-dialog>
</template>

<style scoped>
.reference-dialog { display: flex; flex-direction: column; gap: 18px; }
.reference-guidance {
  padding: 14px 16px;
  border: 1px solid var(--sage-line);
  border-left: 3px solid var(--moss);
  background: var(--sage-soft);
  border-radius: var(--radius-md);
}
.reference-guidance__text { margin: 6px 0 0; white-space: pre-wrap; line-height: 1.7; color: var(--ink); font-size: 13.5px; }
.reference-guidance--empty { border-left-color: var(--line); background: var(--paper-soft); }
.reference-guidance--empty p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
.reference-download {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px dashed var(--sage-line);
  border-radius: var(--radius-md);
  background: var(--paper);
}
.reference-download__icon { font-size: 22px; color: var(--moss); flex: 0 0 auto; }
.reference-download__meta { flex: 1 1 auto; min-width: 0; }
.reference-download__meta strong { display: block; font-size: 13.5px; color: var(--ink); }
.reference-download__meta small { display: block; color: var(--muted); font-size: 12px; margin-top: 2px; }
.reference-download .primary-button { flex: 0 0 auto; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
.reference-hint { margin: 0; font-size: 12.5px; color: var(--muted); }
</style>
