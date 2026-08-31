# Student Content Resources View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved Option A content views for student competitions and school notices without changing APIs or routing.

**Architecture:** Keep both existing first-level routes on `ContentLibrary.vue`. Make competition and announcement data render through a shared full-width content-stream structure, with a featured competition plus list rows and a notification timeline. Keep case-library code and public-application behavior untouched.

**Tech Stack:** Vue 3, TypeScript, Element Plus icons, scoped Vue CSS, Vitest.

---

### Task 1: Define the view-level data contract

**Files:**
- Modify: `/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend/src/pages/shared/ContentLibrary.vue`
- Test: `/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend/src/contentLibraryStyles.test.ts`

- [ ] **Step 1: Add failing static assertions for the approved structure**

Add assertions that the production template contains `resource-content-page`, `competition-feature`, `competition-list-row`, and `announcement-feed`, and does not contain `.slice(0, 3)` or the student content-page filter button.

- [ ] **Step 2: Run the focused test and verify the new assertions fail**

Run:

```bash
npm --prefix frontend test -- --run src/contentLibraryStyles.test.ts
```

Expected: existing assertions pass and the new structure assertions fail until the template is changed.

- [ ] **Step 3: Add deterministic computed helpers**

Use the existing `Competition` and `Announcement` types and add helpers with these contracts:

```ts
function formatResourceDate(value?: string): string
function formatCompetitionMonth(value?: string): string
function formatCompetitionDay(value?: string): string
function competitionStatus(item: Competition): string
function announcementSource(item: Announcement): string
```

The helpers must return `时间待定` for missing dates, preserve meaningful backend status labels, and never invent a record.

- [ ] **Step 4: Run the focused test again**

Run the same Vitest command. It may still fail on template assertions; helper behavior must be covered by the existing component test environment or direct pure-function assertions if that test file already exposes helpers.

### Task 2: Implement the Option A competition stream

**Files:**
- Modify: `/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend/src/pages/shared/ContentLibrary.vue`

- [ ] **Step 1: Make student content search immediate**

Keep `appliedKeyword` for the case-library flow, but bind competition and announcement filters to the current `keyword` value. Render the `筛选` button only for cases that still use explicit application, so competition and announcement pages do not render a no-op control.

- [ ] **Step 2: Replace the fixed three-card competition template**

Render `filteredCompetitions[0]` as one featured article and `filteredCompetitions.slice(1)` as list rows. Include title, description, status, registration deadline, event dates, audience, and a deterministic missing-time label. Render the existing `EmptyState` when the filtered list is empty.

- [ ] **Step 3: Preserve teacher and student role descriptions**

Keep role-specific heading text, but use the same competition layout and real data for both roles. Do not add unsupported registration or favorite actions.

### Task 3: Implement the Option A announcement timeline

**Files:**
- Modify: `/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend/src/pages/shared/ContentLibrary.vue`

- [ ] **Step 1: Remove the duplicate scope note**

Delete the separate `content-scope-note` block. Update the student announcement description to explain that school/platform arrangements are here and personal review/invitation events remain in message center.

- [ ] **Step 2: Replace the narrow card grid**

Render all `filteredNotices` inside one `announcement-feed` card using aligned timeline items. Each item must show source, unread state when present, title, body, and date. Keep the existing empty-state title logic.

- [ ] **Step 3: Ensure no hidden duplicate action remains**

Do not add a read button, detail link, or filter button unless it changes an existing supported state. The notification content itself must remain fully visible and naturally wrap.

### Task 4: Align styles and validate the focused surface

**Files:**
- Modify: `/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend/src/pages/shared/ContentLibrary.vue`
- Modify: `/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend/src/styles/workspace.css` only if shared rules are necessary
- Test: `/Users/anzhi/Desktop/雷灵/星辰/lingsu/frontend/src/contentLibraryStyles.test.ts`

- [ ] **Step 1: Add the shared layout rules**

Define the new classes with the existing CSS variables: full-width section heading, featured competition card, date block, list rows, timeline line, source/status labels, and responsive-safe `min-width: 0` rules. Do not introduce mobile breakpoints.

- [ ] **Step 2: Verify the focused test and type/build surface**

Run:

```bash
npm --prefix frontend test -- --run src/contentLibraryStyles.test.ts
npm --prefix frontend run build
git diff --check
```

Expected: focused test passes, build succeeds, and `git diff --check` has no output.

- [ ] **Step 3: Inspect both routes at desktop width**

Open `/student/competitions` and `/student/announcements` at 1280px and 1440px. Verify that the list uses all returned records, search updates immediately, the competition does not duplicate when there is one item, and the notification feed has no horizontal or nested scrollbar.

## Self-review checklist

- Both existing routes remain unchanged.
- No API, database, permission, or case-library behavior is modified.
- No Option A mock-only copy is introduced into production.
- No `.slice(0, 3)` remains in the competition production template.
- Student content pages have no meaningless `筛选` button.
- Every rendered button has a real existing behavior; this design adds no unsupported action.
- Loading, empty, and error branches remain intact.
