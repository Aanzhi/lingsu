# Student Projects Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved A layout for the student project page: a featured current-project panel plus a paginated two-column project shelf.

**Architecture:** Keep all existing project loading, lifecycle handlers, router contracts, and creation dialog in `StudentProjects.vue`. Add derived presentation state for the featured project and the remaining project grid, while keeping the existing six-item pagination contract for the grid. Keep page-specific layout styles scoped to the page and reuse the existing Scheme B tokens.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Vue Router, Vitest, Vite, scoped CSS, Element Plus.

---

### Task 1: Lock the approved layout contract with a failing test

**Files:**
- Modify: `frontend/src/studentWorkflowUI.test.ts`

- [ ] **Step 1: Add the A-layout source contract test**

Assert that `StudentProjects.vue` exposes a featured current-project surface, a separate project grid, the existing six-item pagination, and the real teacher name field. Also assert that the old four-column list-item surface is no longer used.

- [ ] **Step 2: Run the focused test and verify it fails for the missing A surface**

Run: `npm --prefix frontend test -- --run src/studentWorkflowUI.test.ts`

Expected: the new A-layout test fails because the current page has no featured current-project panel or project grid.

### Task 2: Implement derived project presentation state

**Files:**
- Modify: `frontend/src/pages/student/StudentProjects.vue` near the project collection computed values.

- [ ] **Step 1: Add featured-project selection**

Derive `featuredProject` only for the active tab without a search query, preferring `is_primary` and falling back to the first active project. Derive `shelfProjects` by excluding the featured project only in that active unfiltered state; keep all projects for search, archived, and trashed views.

- [ ] **Step 2: Preserve six-item pagination for the shelf**

Compute `totalPages`, `visibleProjects`, `pageStart`, and `pageEnd` from `shelfProjects`, reset the page when tab/search changes, and keep empty/loading/error behavior unchanged.

### Task 3: Replace the page composition with the approved A layout

**Files:**
- Modify: `frontend/src/pages/student/StudentProjects.vue` template.

- [ ] **Step 1: Add the featured current-project panel**

Render the project identity, status, problem, plan, member count, real teacher name, lifecycle date, and a single “继续研究”/“继续编辑” route action. Keep the lifecycle menu in the panel.

- [ ] **Step 2: Add the paginated project shelf**

Render a `student-project-grid` section with two project cards per row, preserving the current project actions and all lifecycle-specific menus. Use “其他项目” for the unfiltered active shelf and “项目列表” for search/archive/trash contexts.

- [ ] **Step 3: Keep the existing creation dialog and empty states**

Do not change the create API, AI opening entry, feedback actions, route targets, or lifecycle handlers.

### Task 4: Restyle the page for desktop visual hierarchy

**Files:**
- Modify: `frontend/src/pages/student/StudentProjects.vue` scoped styles.

- [ ] **Step 1: Add featured-panel styles**

Create the full-width pale-sage panel with a dominant title column, research summary, facts, and action rail using existing Scheme B variables.

- [ ] **Step 2: Add two-column shelf card styles**

Create stable card grids, bounded text clamping, bottom-aligned actions, and archived/trash variants. Ensure long titles wrap within cards and controls never overflow.

- [ ] **Step 3: Keep desktop breakpoints bounded**

At the existing PC baseline, maintain the two-column shelf and no page-level horizontal overflow. Do not introduce mobile-specific behavior beyond the existing project page fallback.

### Task 5: Update regression expectations and run targeted verification

**Files:**
- Modify: `frontend/src/remainingPageParity.test.ts` for the new student project surface expectations.
- Test: `frontend/src/studentWorkflowUI.test.ts`
- Test: `frontend/src/remainingPageParity.test.ts`

- [ ] **Step 1: Update stale source-contract assertions**

Replace assertions for the removed `.project-list-item` surface with the featured panel and project-grid classes; retain assertions for `PROJECTS_PAGE_SIZE = 6`, pagination, project plan, lifecycle handlers, and focus state.

- [ ] **Step 2: Run focused tests**

Run: `npm --prefix frontend test -- --run src/studentWorkflowUI.test.ts src/remainingPageParity.test.ts`

Expected: both files pass with no unresolved component warnings.

- [ ] **Step 3: Build and inspect the working tree**

Run: `npm --prefix frontend run build` and `git diff --check`.

Expected: TypeScript/Vite build exits 0 and the diff has no whitespace errors. Full E2E remains deferred unless the focused browser check exposes a route or rendering regression.
