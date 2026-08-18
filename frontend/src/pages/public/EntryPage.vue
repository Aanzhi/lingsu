<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { auth } from '../../stores/auth'
import { routeForAuthRole } from '../../stores/authModel'

const router = useRouter()
onMounted(async () => {
  const user = await auth.restore()
  await router.replace(user ? routeForAuthRole(user.role) : '/login')
})
</script>

<template><div class="entry-loader" aria-label="正在进入灵溯"><span class="brand-mark">S</span><p>正在进入灵溯…</p></div></template>
