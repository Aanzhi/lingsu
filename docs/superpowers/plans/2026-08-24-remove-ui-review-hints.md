# Remove UI Review Hints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove role chips and review-only hint blocks from the approved PC UI without changing navigation or console controls.

**Architecture:** Remove shared workbench chrome at its source in `AppTopbar` and `WorkspaceShell`, then remove the equivalent static markup from the public entry, standalone console, and design demo. Keep page identity, navigation links, authentication, and control DOM IDs intact.

**Tech Stack:** Vue 3, TypeScript, Vitest, static HTML/CSS, Python unittest.

---

### Task 1: Lock the requested absence rules

**Files:**
- Create: `frontend/src/uiReviewHints.test.ts`
- Modify: `frontend/src/designDemo.test.ts`
- Modify: `scripts/test_project_console.py`

- [ ] Add source-level assertions that shared role chips, sidebar notes, the public-entry eyebrow, console chrome labels, and Demo review blocks are absent.
- [ ] Run `npm run test -- --run src/uiReviewHints.test.ts src/designDemo.test.ts` and `python3 -m unittest scripts.test_project_console`; expect failures on the current markup.

### Task 2: Remove shared and page-specific hints

**Files:**
- Modify: `frontend/src/components/AppTopbar.vue`
- Modify: `frontend/src/components/WorkspaceShell.vue`
- Modify: `frontend/src/layouts/StudentLayout.vue`
- Modify: `frontend/src/layouts/TeacherLayout.vue`
- Modify: `frontend/src/layouts/PlatformLayout.vue`
- Modify: `frontend/src/pages/public/EntryPage.vue`
- Modify: `scripts/console.html`
- Modify: `frontend/public/design-demo.html`

- [ ] Remove only the approved role chips, sidebar note blocks, public eyebrow, console sidebar label/note, and Demo review/tips markup.
- [ ] Preserve all navigation links, page headings, login state, service-control buttons, and console action IDs.
- [ ] Re-run the focused tests and expect them to pass.

### Task 3: Verify desktop output

**Files:**
- Verify: all files above

- [ ] Run `npm run test -- --run`, `npm run build`, and `python3 -m unittest scripts.test_project_console`.
- [ ] Check student, teacher, platform, public, console, and Demo pages at desktop width; confirm no bottom hint cards, no requested top-left labels, and no horizontal overflow.
- [ ] Run `git diff --check` on the scoped files.
