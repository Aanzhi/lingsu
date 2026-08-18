<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import AppTopbar from '../components/AppTopbar.vue'
const nav = [
  ['/student/home', '今日旅程'], ['/student/projects', '我的项目'], ['/student/ai', '灵思 AI'],
  ['/student/cases', '案例库'], ['/student/competitions', '赛事'], ['/student/announcements', '消息中心'],
]
</script>
<template><div class="portal student-portal"><AppTopbar role-label="学生端" role-tone="student" /><nav class="student-primary-nav" aria-label="学生端主导航"><RouterLink v-for="item in nav" :key="item[0]" :to="item[0]">{{ item[1] }}</RouterLink></nav><main class="student-main"><RouterView /></main></div></template>
