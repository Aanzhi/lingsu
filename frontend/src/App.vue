<script setup lang="ts">
import { ref } from 'vue'
import { RouterView, useRouter } from 'vue-router'

const router = useRouter()
const routeReady = ref(false)
void router.isReady().then(() => { routeReady.value = true }).catch(() => { routeReady.value = true })
</script>
<template>
  <div v-if="!routeReady" class="app-bootstrap-shell" role="status" aria-label="正在打开灵溯">
    <header class="app-bootstrap-shell__topbar">
      <span class="app-bootstrap-shell__mark">溯</span>
      <strong>灵溯</strong>
      <span class="app-bootstrap-shell__line" />
      <span class="app-bootstrap-shell__subtitle">青少年科学创新项目工作台</span>
    </header>
    <div class="app-bootstrap-shell__body">
      <aside class="app-bootstrap-shell__sidebar"><i /><i /><i /><i /></aside>
      <main class="app-bootstrap-shell__content">
        <span class="app-bootstrap-shell__eyebrow">正在打开工作台</span>
        <span class="app-bootstrap-shell__title">正在打开灵溯</span>
        <span class="app-bootstrap-shell__text" />
        <div class="app-bootstrap-shell__cards"><i /><i /></div>
      </main>
    </div>
  </div>
  <RouterView v-else />
</template>

<style scoped>
.app-bootstrap-shell {
  min-height: 100vh;
  background: var(--color-bg-canvas, #f4f6f1);
  color: var(--color-text-primary, #20382b);
}
.app-bootstrap-shell__topbar {
  display: flex;
  height: 66px;
  align-items: center;
  gap: 12px;
  padding: 0 clamp(20px, 3vw, 40px);
  border-bottom: 1px solid var(--line, #dce4dc);
  background: var(--paper, #fff);
}
.app-bootstrap-shell__mark {
  display: inline-grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 6px;
  background: var(--moss-dark, #365c45);
  color: #fff;
  font-weight: 700;
}
.app-bootstrap-shell__topbar strong { font-size: 23px; letter-spacing: .07em; }
.app-bootstrap-shell__line { width: 1px; height: 24px; background: var(--line, #dce4dc); }
.app-bootstrap-shell__subtitle { color: var(--muted, #708077); font-size: 13px; }
.app-bootstrap-shell__body { display: grid; min-height: calc(100vh - 66px); grid-template-columns: 232px minmax(0, 1fr); }
.app-bootstrap-shell__sidebar { display: grid; align-content: start; gap: 12px; padding: 38px 28px; border-right: 1px solid var(--line, #dce4dc); background: var(--paper, #fff); }
.app-bootstrap-shell__sidebar i { width: 130px; height: 12px; border-radius: 999px; background: var(--paper-muted, #edf1ec); }
.app-bootstrap-shell__sidebar i:nth-child(2) { width: 156px; height: 38px; border-radius: 8px; background: var(--sage-soft, #e4eee5); }
.app-bootstrap-shell__content { display: grid; align-content: start; gap: 14px; width: 100%; max-width: 1120px; min-width: 0; box-sizing: border-box; margin: 0 auto; padding: 52px clamp(24px, 5vw, 80px); }
.app-bootstrap-shell__eyebrow, .app-bootstrap-shell__text { width: 150px; height: 12px; border-radius: 999px; background: var(--paper-muted, #e9eee9); }
.app-bootstrap-shell__title { width: min(430px, 65%); height: 40px; border-radius: 8px; background: var(--paper, #fff); box-shadow: var(--shadow-soft, 0 8px 20px rgba(32,56,43,.06)); }
.app-bootstrap-shell__text { width: min(560px, 78%); }
.app-bootstrap-shell__cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 26px; }
.app-bootstrap-shell__cards i { min-height: 210px; border: 1px solid var(--line, #dce4dc); border-radius: 12px; background: var(--paper, #fff); box-shadow: var(--shadow-soft, 0 8px 20px rgba(32,56,43,.06)); }
@media (max-width: 800px) {
  .app-bootstrap-shell__body { grid-template-columns: 1fr; }
  .app-bootstrap-shell__sidebar { display: none; }
}
</style>
