# AI Conversation Permanent Delete Implementation Plan

> **For agentic workers:** Execute this plan inline in the current session. Do not dispatch subagents.

**Goal:** Add a confirmed, permanent delete action to the AI conversation history while preserving authorization, current-session cleanup, and the existing three-mode history experience.

**Architecture:** The history drawer owns the delete affordance and confirmation dialog, while `AICenter.vue` owns the API request and route/state cleanup. The backend exposes the existing ModelViewSet destroy behavior through `DELETE`; Django cascades conversation messages and keeps generation logs as detached audit records through the existing `SET_NULL` relationships.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Axios, Django REST Framework `ModelViewSet`, Django `TestCase`/`APIClient`, Vitest.

---

## File map

- Modify `frontend/src/api.ts`: expose the typed `deleteAIConversation(id)` request.
- Modify `frontend/src/components/ai/AIConversationHistory.vue`: render a sibling delete control for each record, own the confirmation dialog, and emit delete intent without nesting buttons.
- Modify `frontend/src/pages/shared/AICenter.vue`: call the delete API, remove deleted records from local collections, clear the current conversation when necessary, and surface request errors.
- Modify `backend/apps/core/views.py`: allow `DELETE` on `AIConversationViewSet` while retaining its owner/project queryset boundary.
- Modify `frontend/src/api.test.ts`: verify the exact delete request.
- Modify `frontend/src/aiConversationHistoryUI.test.ts`: verify the row/delete/confirmation accessibility contract.
- Modify `frontend/src/aiCenterUI.test.ts`: verify the page-to-history deletion wiring.
- Modify `backend/apps/core/tests/test_ai_conversations.py`: verify permanent deletion, ownership isolation, message cascade, detached generation logs, and archived conversation deletion.

## Task 1: Lock the API and backend deletion contract with failing tests

**Files:**
- Modify: `frontend/src/api.test.ts`
- Modify: `frontend/src/aiConversationHistoryUI.test.ts`
- Modify: `frontend/src/aiCenterUI.test.ts`
- Modify: `backend/apps/core/tests/test_ai_conversations.py`

- [ ] **Step 1: Add the frontend API test first.**

Import `deleteAIConversation` in `frontend/src/api.test.ts` and add:

```ts
it('permanently deletes an AI conversation by id', async () => {
  const del = vi.spyOn(api, 'delete').mockResolvedValue({} as never)

  await deleteAIConversation(12)

  expect(del).toHaveBeenCalledWith('ai-conversations/12/')
  del.mockRestore()
})
```

- [ ] **Step 2: Add the history component contract tests.**

Append a test in `frontend/src/aiConversationHistoryUI.test.ts`:

```ts
it('provides an explicit permanent delete confirmation for each history item', () => {
  expect(source).toContain("(event: 'delete', item: AIConversation): void")
  expect(source).toContain("emit('delete', pendingDelete.value)")
  expect(source).toContain('@click.stop="requestDelete(item)"')
  expect(source).toContain('永久删除会话')
  expect(source).toContain('删除后对话和消息不可恢复')
  expect(source).toContain('永久删除')
  expect(source).toContain('role="dialog"')
  expect(source).toContain(':disabled="deletingId === pendingDelete.id"')
})
```

- [ ] **Step 3: Add the page wiring contract test.**

Append a test in `frontend/src/aiCenterUI.test.ts`:

```ts
it('connects history deletion to page state and the delete API', () => {
  expect(source).toContain('deleteAIConversation')
  expect(source).toContain('deletingConversationId')
  expect(source).toContain('conversationDeleteError')
  expect(source).toContain('@delete="void deleteConversation($event)"')
  expect(source).toContain('historyConversations.value = historyConversations.value.filter')
  expect(source).toContain('resetConversationSelection()')
})
```

- [ ] **Step 4: Add the backend behavior test.**

Add this method to `AIConversationAPITests` in `backend/apps/core/tests/test_ai_conversations.py`:

```python
def test_student_can_permanently_delete_conversation_and_detach_audit_log(self):
    conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening", is_archived=True)
    other_conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening")
    self.assertEqual(
        self.api_client(self.other).delete(f"/api/ai-conversations/{other_conversation.id}/").status_code,
        404,
    )
    log = AIGenerationLog.objects.create(
        actor=self.student,
        conversation=conversation,
        project=None,
        purpose="开题对话",
        prompt="删除测试",
    )
    message = AIConversationMessage.objects.create(
        conversation=conversation,
        role=AIConversationMessage.Role.USER,
        content="待删除的问题",
        generation_log=log,
    )
    log.message = message
    log.save(update_fields=["message"])

    response = self.api_client(self.student).delete(f"/api/ai-conversations/{conversation.id}/")

    self.assertEqual(response.status_code, 204)
    self.assertFalse(AIConversation.objects.filter(pk=conversation.id).exists())
    self.assertFalse(AIConversationMessage.objects.filter(pk=message.id).exists())
    log.refresh_from_db()
    self.assertIsNone(log.conversation_id)
    self.assertIsNone(log.message_id)
```

- [ ] **Step 5: Run only these focused tests and verify they fail for the missing behavior.**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/aiConversationHistoryUI.test.ts src/aiCenterUI.test.ts
python backend/manage.py test apps.core.tests.test_ai_conversations.AIConversationAPITests.test_student_can_permanently_delete_conversation_and_detach_audit_log
```

Expected: failures identify the missing `deleteAIConversation`, history delete contract, page wiring, and backend `DELETE` support; no production implementation is present yet.

## Task 2: Implement the API and backend destroy route

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `backend/apps/core/views.py`

- [ ] **Step 1: Add the typed Axios helper.**

Place beside the existing archive helper in `frontend/src/api.ts`:

```ts
export const deleteAIConversation = (id: number) => api.delete(`ai-conversations/${id}/`)
```

- [ ] **Step 2: Enable the existing ModelViewSet destroy action.**

Change `AIConversationViewSet.http_method_names` in `backend/apps/core/views.py` from:

```python
http_method_names = ["get", "post", "patch", "head", "options"]
```

to:

```python
http_method_names = ["get", "post", "patch", "delete", "head", "options"]
```

Do not add a second delete endpoint or bypass `get_queryset`; the existing queryset guarantees that another owner receives 404. The model relationships already cascade messages and set `conversation_id`/`message_id` on generation logs to null.

- [ ] **Step 3: Run the API and backend tests.**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts
python backend/manage.py test apps.core.tests.test_ai_conversations.AIConversationAPITests.test_student_can_permanently_delete_conversation_and_detach_audit_log
```

Expected: both pass.

## Task 3: Implement the history-row delete interaction

**Files:**
- Modify: `frontend/src/components/ai/AIConversationHistory.vue`

- [ ] **Step 1: Add controlled delete props, events, and local pending state.**

Extend the props with:

```ts
deletingId?: number | null
deleteError?: string
```

with defaults `{ modeFilter: 'opening', deletingId: null, deleteError: '' }`. Extend emits with:

```ts
(event: 'delete', item: AIConversation): void
(event: 'clear-delete-error'): void
```

Add `ref` and `watch` imports, then add:

```ts
const pendingDelete = ref<AIConversation | null>(null)

function requestDelete(item: AIConversation) {
  emit('clear-delete-error')
  pendingDelete.value = item
}

function cancelDelete() {
  if (props.deletingId !== null) return
  pendingDelete.value = null
}

function confirmDelete() {
  if (!pendingDelete.value || props.deletingId !== null) return
  emit('delete', pendingDelete.value)
}

watch(() => props.groups, (groups) => {
  if (!pendingDelete.value || props.deletingId !== null) return
  const stillExists = groups.some((group) => group.items.some((item) => item.id === pendingDelete.value?.id))
  if (!stillExists) pendingDelete.value = null
}, { deep: true })
```

- [ ] **Step 2: Replace nested history buttons with sibling controls.**

Inside the existing `v-for`, replace the outer `button.conversation-item` with a `div` and use this structure:

```vue
<div v-for="item in group.items" :key="item.id" class="conversation-item" :class="{ active: item.id === selectedId }">
  <button class="conversation-item__select" type="button" :disabled="sending || deletingId !== null" @click="emit('select', item)">
    <span class="conversation-item__top"><span class="conversation-item__mode">{{ modeLabel(item) }}</span><time>{{ formatDate(item.updated_at) }}</time></span>
    <strong>{{ itemTitle(item) }}</strong>
    <small>{{ item.project_title || '未绑定项目' }} · {{ item.is_archived ? '已归档' : '进行中' }}</small>
    <span v-if="item.id === selectedId" class="conversation-item__current">当前会话</span>
  </button>
  <button class="conversation-item__delete" type="button" :disabled="sending || deletingId !== null" :aria-label="`永久删除会话：${itemTitle(item)}`" :title="`永久删除会话：${itemTitle(item)}`" @click.stop="requestDelete(item)">{{ deletingId === item.id ? '删除中…' : '删除' }}</button>
</div>
```

The delete button remains a sibling of the selection button so the HTML is valid and `@click.stop` cannot restore the conversation accidentally.

- [ ] **Step 3: Add the confirmation dialog.**

Place it inside the existing `Teleport` after the drawer:

```vue
<div v-if="pendingDelete" class="conversation-delete-backdrop" role="presentation" @click.self="cancelDelete">
  <section class="conversation-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="conversation-delete-title" aria-describedby="conversation-delete-description">
    <span class="eyebrow">灵思 AI · 历史会话</span>
    <h2 id="conversation-delete-title">永久删除这段对话？</h2>
    <p id="conversation-delete-description">“{{ itemTitle(pendingDelete) }}”删除后，对话和消息不可恢复。</p>
    <p v-if="deleteError" class="conversation-delete-error" role="alert">{{ deleteError }}</p>
    <footer>
      <button class="secondary-button" type="button" :disabled="deletingId !== null" @click="cancelDelete">取消</button>
      <button class="danger-button" type="button" :disabled="deletingId === pendingDelete.id" @click="confirmDelete">{{ deletingId === pendingDelete.id ? '删除中…' : '永久删除' }}</button>
    </footer>
  </section>
</div>
```

- [ ] **Step 4: Update styles without changing the drawer dimensions.**

Use a parent `div.conversation-item`, a full-width `.conversation-item__select`, and an absolute `.conversation-item__delete` that is visible on hover/focus-within and always reachable by keyboard. Keep the current selected badge clear of the delete button:

```css
.conversation-item { position: relative; min-width: 0; }
.conversation-item__select { position: relative; width: 100%; display: block; box-sizing: border-box; border: 1px solid transparent; background: transparent; color: var(--ink); text-align: left; padding: 11px 58px 11px 12px; border-radius: var(--radius-sm); cursor: pointer; }
.conversation-item.active .conversation-item__select, .conversation-item:hover .conversation-item__select, .conversation-item:focus-within .conversation-item__select { border-color: var(--sage-line); background: var(--sage-soft); outline: 0; }
.conversation-item__delete { position: absolute; top: 10px; right: 10px; min-height: 24px; padding: 3px 6px; border: 1px solid transparent; border-radius: 5px; background: var(--paper); color: var(--clay-deep); font: inherit; font-size: 9px; font-weight: 700; cursor: pointer; opacity: 0; pointer-events: none; }
.conversation-item:hover .conversation-item__delete, .conversation-item:focus-within .conversation-item__delete { opacity: 1; pointer-events: auto; }
.conversation-item__delete:hover:not(:disabled), .conversation-item__delete:focus-visible { border-color: var(--clay-deep); background: #fff7f4; outline: 0; }
.conversation-item__current { right: 50px; }
.conversation-delete-backdrop { position: fixed; inset: 0; z-index: 110; display: grid; place-items: center; padding: 24px; background: rgba(35, 51, 31, .18); }
.conversation-delete-dialog { display: grid; gap: 12px; width: min(100%, 390px); box-sizing: border-box; padding: 22px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-hover); }
.conversation-delete-dialog h2, .conversation-delete-dialog p { margin: 0; }
.conversation-delete-dialog h2 { color: var(--ink); font: 700 20px/1.3 var(--sans); }
.conversation-delete-dialog p { color: var(--muted); font-size: 12px; line-height: 1.6; }
.conversation-delete-dialog footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
.danger-button { min-height: 34px; padding: 7px 13px; border: 1px solid var(--clay-deep); border-radius: var(--radius-sm); background: var(--clay-deep); color: #fff; font: inherit; font-size: 11px; font-weight: 700; cursor: pointer; }
.danger-button:hover:not(:disabled), .danger-button:focus-visible { background: #8e4438; }
.danger-button:disabled { cursor: wait; opacity: .6; }
.conversation-delete-error { padding: 9px 10px; border-radius: var(--radius-sm); background: #fff7f4; color: var(--clay-deep) !important; }
```

- [ ] **Step 5: Run the focused history tests.**

Run:

```bash
npm --prefix frontend test -- --run src/aiConversationHistoryUI.test.ts
```

Expected: all history presentation tests pass.

## Task 4: Wire deletion into the student AI workbench

**Files:**
- Modify: `frontend/src/pages/shared/AICenter.vue`

- [ ] **Step 1: Add deletion state and import.**

Import `deleteAIConversation` from `../../api`, then add:

```ts
const deletingConversationId = ref<number | null>(null)
const conversationDeleteError = ref('')
```

- [ ] **Step 2: Implement the delete handler.**

Add this function beside the history handlers:

```ts
async function deleteConversation(conversation: AIConversation) {
  if (deletingConversationId.value !== null) return
  conversationDeleteError.value = ''
  deletingConversationId.value = conversation.id
  const deletedDraftKey = draftKey(conversation.id, conversation.workspace_mode || workbenchMode.value)
  try {
    await deleteAIConversation(conversation.id)
    historyConversations.value = historyConversations.value.filter((item) => item.id !== conversation.id)
    conversations.value = conversations.value.filter((item) => item.id !== conversation.id)
    delete draftsByConversation.value[deletedDraftKey]
    if (selectedId.value === conversation.id) {
      resetConversationSelection()
      historyOpen.value = false
    }
  } catch (requestError) {
    conversationDeleteError.value = errorMessage(requestError)
  } finally {
    deletingConversationId.value = null
  }
}
```

This keeps non-current conversations in the same drawer and resets only the deleted current conversation. A failed request leaves all local collections unchanged and lets the dialog show the error.

- [ ] **Step 3: Pass controlled deletion state to the history component.**

Update the existing `AIConversationHistory` invocation to include:

```vue
:deleting-id="deletingConversationId"
:delete-error="conversationDeleteError"
@delete="void deleteConversation($event)"
@clear-delete-error="conversationDeleteError = ''"
```

Also pass `:sending="sending || deletingConversationId !== null"` so switching modes or selecting another record cannot race a destructive request.

- [ ] **Step 4: Run the focused page and API tests.**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/aiConversationHistoryUI.test.ts src/aiCenterUI.test.ts
```

Expected: all selected frontend tests pass.

## Task 5: Verify the complete scoped change

**Files:**
- No new files.

- [ ] **Step 1: Run the focused backend conversation test module.**

Run:

```bash
python backend/manage.py test apps.core.tests.test_ai_conversations
```

Expected: the existing AI conversation tests and the new deletion test pass. Do not run the backend test suite outside this module.

- [ ] **Step 2: Run the scoped frontend tests and production build.**

Run:

```bash
npm --prefix frontend test -- --run src/api.test.ts src/aiConversationHistoryUI.test.ts src/aiCenterUI.test.ts src/aiWorkbenchLayout.test.ts
npm --prefix frontend run build
git diff --check
```

Expected: selected tests pass, build exits 0, and `git diff --check` produces no output.

- [ ] **Step 3: Manually verify the browser flow.**

At the existing AI workbench URL, verify these exact cases:

1. Open history and hover/focus a row; the delete control appears without changing the row height or drawer width.
2. Click delete; the confirmation shows the conversation title and irreversible warning.
3. Cancel and press Escape; the row remains and no route changes.
4. Delete a non-current conversation; the row disappears while the drawer, mode filter, and search remain.
5. Delete the current conversation; the drawer closes and the page returns to the current mode's new-conversation state.
6. Open an archived conversation list and delete one; it disappears permanently.

- [ ] **Step 4: Review the diff and preserve unrelated worktree changes.**

Run:

```bash
git status --short
git diff -- frontend/src/api.ts frontend/src/components/ai/AIConversationHistory.vue frontend/src/pages/shared/AICenter.vue frontend/src/api.test.ts frontend/src/aiConversationHistoryUI.test.ts frontend/src/aiCenterUI.test.ts backend/apps/core/views.py backend/apps/core/tests/test_ai_conversations.py
```

Only the planned files should be intentionally changed by this feature; do not reset or overwrite unrelated existing work.
