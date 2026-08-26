import { createMemoryHistory, createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { auth } from './stores/auth'
import { resolveNavigation } from './stores/authModel'

const StudentLayout = () => import('./layouts/StudentLayout.vue')
const TeacherLayout = () => import('./layouts/TeacherLayout.vue')
const PlatformLayout = () => import('./layouts/PlatformLayout.vue')

export const routeRecords: RouteRecordRaw[] = [
  { path: '/', name: 'entry', component: () => import('./pages/public/EntryPage.vue') },
  { path: '/login', name: 'login', component: () => import('./pages/public/LoginPage.vue'), meta: { public: true } },
  { path: '/register', name: 'register', component: () => import('./pages/public/RegisterPage.vue'), meta: { public: true } },
  { path: '/platform/login', name: 'platform-login', component: () => import('./pages/public/PlatformLoginPage.vue'), meta: { public: true } },
  {
    path: '/student', component: StudentLayout, meta: { role: 'student' }, redirect: '/student/home', children: [
      { path: 'home', name: 'student-home', component: () => import('./pages/student/StudentHome.vue'), meta: { layout: 'hero' } },
      { path: 'projects', name: 'student-projects', component: () => import('./pages/student/StudentProjects.vue') },
      { path: 'projects/:id', name: 'student-project-redirect', redirect: (to) => ({ name: 'student-map', params: { id: to.params.id }, query: to.query }) },
      { path: 'projects/:id/map', name: 'student-map', component: () => import('./pages/student/StudentProject.vue'), meta: { surface: 'map' } },
      { path: 'projects/:id/tasks/:taskId', name: 'student-task', component: () => import('./pages/student/StudentTask.vue') },
      { path: 'projects/:id/materials', redirect: (to) => ({ name: 'student-map', params: { id: to.params.id }, query: to.query }) },
      { path: 'projects/:id/report', name: 'student-report', component: () => import('./pages/student/StudentProject.vue'), meta: { surface: 'report' } },
      { path: 'ai', name: 'student-ai', component: () => import('./pages/shared/AICenter.vue') },
      { path: 'notifications', name: 'student-notifications', component: () => import('./pages/student/StudentNotifications.vue') },
      { path: 'cases', name: 'student-cases', component: () => import('./pages/shared/ContentLibrary.vue'), meta: { surface: 'cases' } },
      { path: 'public-applications', name: 'student-public-applications', component: () => import('./pages/student/PublicCaseApplication.vue') },
      { path: 'invitations', name: 'student-invitations', component: () => import('./pages/student/StudentInvitations.vue') },
      { path: 'competitions', name: 'student-competitions', component: () => import('./pages/shared/ContentLibrary.vue'), meta: { surface: 'competitions' } },
      { path: 'announcements', name: 'student-announcements', component: () => import('./pages/shared/ContentLibrary.vue'), meta: { surface: 'announcements' } },
    ],
  },
  {
    path: '/teacher', component: TeacherLayout, meta: { role: 'teacher' }, redirect: '/teacher/home', children: [
      { path: 'home', name: 'teacher-home', component: () => import('./pages/teacher/TeacherWorkbench.vue'), meta: { surface: 'home', layout: 'hero' } },
      { path: 'pool', name: 'teacher-pool', component: () => import('./pages/teacher/TeacherWorkbench.vue'), meta: { surface: 'pool' } },
      { path: 'projects', name: 'teacher-projects', component: () => import('./pages/teacher/TeacherWorkbench.vue'), meta: { surface: 'projects' } },
      { path: 'projects/:id', name: 'teacher-project', component: () => import('./pages/teacher/TeacherProjectDetail.vue') },
      { path: 'projects/:id/template', name: 'teacher-project-template', component: () => import('./pages/teacher/TeacherProjectTemplate.vue') },
      { path: 'reviews', name: 'teacher-reviews', component: () => import('./pages/teacher/TeacherWorkbench.vue'), meta: { surface: 'reviews' } },
      { path: 'reviews/:submissionId', name: 'teacher-review', component: () => import('./pages/teacher/TeacherWorkbench.vue'), meta: { surface: 'review' } },
      { path: 'members', name: 'teacher-members', component: () => import('./pages/teacher/TeacherWorkbench.vue'), meta: { surface: 'members' } },
      { path: 'ai', name: 'teacher-ai', component: () => import('./pages/teacher/TeacherAICenter.vue'), meta: { layout: 'ai' } },
      { path: 'notifications', name: 'teacher-notifications', component: () => import('./pages/teacher/TeacherNotifications.vue') },
      { path: 'cases', name: 'teacher-cases', component: () => import('./pages/shared/ContentLibrary.vue'), meta: { surface: 'cases' } },
      { path: 'competitions', name: 'teacher-competitions', component: () => import('./pages/shared/ContentLibrary.vue'), meta: { surface: 'competitions' } },
      { path: 'announcements', name: 'teacher-announcements', component: () => import('./pages/teacher/TeacherAnnouncements.vue') },
    ],
  },
  {
    path: '/platform', component: PlatformLayout, meta: { role: 'platform_admin' }, redirect: '/platform/home', children: [
      { path: 'home', name: 'platform-home', component: () => import('./pages/platform/PlatformConsole.vue'), meta: { surface: 'home' } },
      { path: 'schools', name: 'platform-schools', component: () => import('./pages/platform/PlatformConsole.vue'), meta: { surface: 'schools' } },
      { path: 'schools/:id', name: 'platform-school', component: () => import('./pages/platform/SchoolDetail.vue') },
      { path: 'licenses', redirect: '/platform/schools' },
      { path: 'competitions', name: 'platform-competitions', component: () => import('./pages/platform/PlatformConsole.vue'), meta: { surface: 'competitions' } },
      { path: 'announcements', name: 'platform-announcements', component: () => import('./pages/platform/PlatformConsole.vue'), meta: { surface: 'announcements' } },
      { path: 'cases', name: 'platform-cases', component: () => import('./pages/platform/PlatformCases.vue'), meta: { surface: 'cases' } },
      { path: 'settings', name: 'platform-settings', component: () => import('./pages/platform/PlatformSettings.vue') },
      { path: 'ai-agents', name: 'platform-ai-agents', component: () => import('./pages/platform/PlatformAIAgents.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({ history: typeof window === 'undefined' ? createMemoryHistory() : createWebHistory(), routes: routeRecords })

router.beforeEach(async (to) => {
  await auth.restore()
  const decision = resolveNavigation(auth.user.value, to.path)
  if (!decision) return true
  if ('redirect' in decision) return { path: decision.path, query: { redirect: decision.redirect } }
  return decision.path
})
