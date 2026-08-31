# Platform AI Key and Sidebar Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a server-side encrypted, platform-wide AI API Key configuration flow with masked-only frontend visibility, and make the student sidebar use one consistent semantic icon set.

**Architecture:** Store one encrypted AI Key record in PostgreSQL, using a deployment-provided `AI_CONFIG_ENCRYPTION_KEY`. A focused `ai_config` service is the only runtime reader/writer; APIs expose metadata and masked values, while AI views and Celery tasks read the current value through that service. The frontend settings page sends a new Key only during save and keeps the returned masked value; navigation metadata maps each student capability to a distinct Element Plus line icon.

**Tech Stack:** Django 5, Django REST Framework, PostgreSQL, Celery, `cryptography.Fernet`, Vue 3, TypeScript, Element Plus Icons, Vitest.

---

## File Map

- Create `backend/apps/core/ai_config.py`: encryption, masking, singleton lookup, and runtime Key access.
- Create `backend/apps/core/migrations/0041_platform_ai_configuration.py`: singleton configuration schema.
- Create `frontend/src/platformSettingsUI.test.ts`: settings-page source contracts.
- Modify `backend/apps/core/models.py`: add `PlatformAIConfiguration`.
- Modify `backend/apps/core/views.py` and `backend/apps/core/urls.py`: add the platform-only configuration API and use the dynamic Key reader in readiness checks.
- Modify `backend/apps/core/tasks.py`: use the dynamic Key reader for every OpenAI client.
- Modify `backend/apps/core/tests/test_ai_config.py`, `test_platform_configuration.py`, and `test_ai_service.py`: service, authorization, masking, and runtime tests.
- Modify `backend/requirements.txt`, `backend/config/settings.py`, `.env.example`, and `deploy/production.env.example`: add Fernet and deployment configuration.
- Modify `frontend/src/api.ts` and `frontend/src/pages/platform/PlatformSettings.vue`: typed API calls and the masked Key form.
- Modify `frontend/src/stores/navigationRegistry.ts`, `frontend/src/components/WorkspaceShell.vue`, and `frontend/src/components/WorkspaceFrame.vue`: unique semantic icons and icon-based sidebar toggles.
- Modify `frontend/src/stores/navigationRegistry.test.ts`, `frontend/src/remainingPageParity.test.ts`, and `frontend/src/pageContentContracts.test.ts`: icon contracts and the two stale invitation-page contracts.

## Task 1: Add encrypted singleton storage and masking service

**Files:** `backend/requirements.txt`, `backend/config/settings.py:84-94`, `.env.example:27-30`, `deploy/production.env.example:34-37`, `backend/apps/core/models.py` after `School`, new `backend/apps/core/ai_config.py`, new migration `0041_platform_ai_configuration.py`, and new `backend/apps/core/tests/test_ai_config.py`.

- [ ] **Step 1: Write failing service tests.** Create `test_ai_config.py` with a `TestCase` that generates `Fernet.generate_key()` in `setUp`, creates a platform admin, and asserts: `mask_ai_api_key("sk-proj-0123456789-END") == "sk-p********END"`; an 8-character value becomes exactly `********`; empty becomes empty; saving without `AI_CONFIG_ENCRYPTION_KEY` raises `AIConfigError` and creates no record; with an encryption key, the database value wins over `OPENAI_API_KEY`, the returned mask is `sk-d********alue`, and the encrypted field does not contain the plaintext.
- [ ] **Step 2: Run the red test.** Run `docker compose exec -T backend python manage.py test apps.core.tests.test_ai_config`. Expected: import/collection failure because the model and service do not exist.
- [ ] **Step 3: Add dependency and settings.** Append `cryptography>=43,<46` to `backend/requirements.txt`. Add `AI_CONFIG_ENCRYPTION_KEY = os.getenv("AI_CONFIG_ENCRYPTION_KEY", "")` near the existing AI settings. Add `AI_CONFIG_ENCRYPTION_KEY=` to both example env files and state in the production example that it must be generated and stored outside the repository; do not include a sample secret.
- [ ] **Step 4: Add the model.** Insert `PlatformAIConfiguration` after `School` with `key = CharField(max_length=32, unique=True, default="default")`, `encrypted_api_key = TextField()`, `masked_api_key = CharField(max_length=128)`, nullable `updated_by = ForeignKey(settings.AUTH_USER_MODEL, on_delete=SET_NULL, related_name="updated_platform_ai_configurations")`, and `updated_at = DateTimeField(auto_now=True)`. Do not add a school foreign key.
- [ ] **Step 5: Implement the service.** In `ai_config.py`, implement `AIConfigError`, `mask_ai_api_key`, `_fernet`, `get_ai_configuration_state`, `get_configured_ai_api_key`, and `save_configured_ai_api_key`. Empty values mask to empty; values of length 8 or less mask to eight stars; longer values use `value[:4] + "********" + value[-4:]`. `_fernet` rejects missing/invalid deployment keys. Database configuration takes precedence over the environment fallback. A present but corrupted database record returns an empty runtime Key and logs only the exception type. Saving trims, rejects empty values and values over 4096 characters, encrypts before saving, locks the singleton row inside `transaction.atomic()`, updates the mask and actor, and returns metadata only. Never log plaintext or ciphertext.
- [ ] **Step 6: Generate and inspect the migration.** Run `docker compose exec -T backend python manage.py makemigrations core` and `docker compose exec -T backend python manage.py sqlmigrate core 0041`. Expected: one configuration table, a unique `key` constraint, and no data migration copying environment secrets. Keep the generated file at the planned path.
- [ ] **Step 7: Run green tests and commit.** Run the focused test again; expected all tests pass. Commit with `git add backend/requirements.txt backend/config/settings.py .env.example deploy/production.env.example backend/apps/core/models.py backend/apps/core/ai_config.py backend/apps/core/migrations/0041_platform_ai_configuration.py backend/apps/core/tests/test_ai_config.py && git commit -m "feat: add encrypted platform AI configuration"`.

## Task 2: Add the platform-only API and route all AI runtime reads through it

**Files:** `backend/apps/core/views.py:1-30,482-528,1241-1412,1562-1580`, `backend/apps/core/urls.py:1-35`, `backend/apps/core/tasks.py:1-20,250-270,410-445,590-630`, `backend/apps/core/tests/test_platform_configuration.py`, and `backend/apps/core/tests/test_ai_service.py`.

- [ ] **Step 1: Write failing API tests.** Add tests that save `sk-live-1234567890-END` as a platform admin and assert PUT/GET return `masked_key == "sk-l********-END"`, never include the plaintext or `encrypted_api_key`, and return only metadata. Assert a teacher and unauthenticated client cannot read or write. Assert missing `AI_CONFIG_ENCRYPTION_KEY` returns 503 and creates no record. Add a runtime test that a saved database Key is selected instead of `settings.OPENAI_API_KEY`.
- [ ] **Step 2: Run the red tests.** Run `docker compose exec -T backend python manage.py test apps.core.tests.test_platform_configuration apps.core.tests.test_ai_service apps.core.tests.test_ai_conversations`. Expected: the new endpoint tests fail with 404 or missing runtime integration.
- [ ] **Step 3: Implement the API.** Add `PlatformAIConfigurationView(APIView)` near `ServiceStatusView`. Both GET and PUT must reject every role except `Account.Role.PLATFORM_ADMIN`. GET returns `configured`, `masked_key`, `settings.OPENAI_MODEL`, and `settings.OPENAI_BASE_URL`. PUT accepts only `request.data.get("api_key")`, maps `ValueError` to 400 and `AIConfigError` to 503, and returns metadata only. Register `path("platform-ai-config/", PlatformAIConfigurationView.as_view())` in `backend/apps/core/urls.py`.
- [ ] **Step 4: Update views.** Import `get_configured_ai_api_key` and replace direct `settings.OPENAI_API_KEY` checks in service status, AI availability, conversation creation, and general-AI branches with a local dynamic value. Verify `rg -n "settings\\.OPENAI_API_KEY" backend/apps/core/views.py` returns no runtime reads.
- [ ] **Step 5: Update Celery tasks.** Import the same helper in `backend/apps/core/tasks.py`; every `OpenAI(...)` call in general conversation, agents, material, and report generation must receive the helper result. Preserve existing demo/error behavior when it returns empty. Verify `rg -n "settings\\.OPENAI_API_KEY|OpenAI\\(" backend/apps/core/tasks.py` shows OpenAI calls but no direct setting reads.
- [ ] **Step 6: Run focused tests and commit.** Run the three backend modules from Step 2; expected all selected tests pass and no API response contains plaintext/ciphertext. Commit with `git add backend/apps/core/views.py backend/apps/core/urls.py backend/apps/core/tasks.py backend/apps/core/tests/test_platform_configuration.py backend/apps/core/tests/test_ai_service.py backend/apps/core/tests/test_ai_conversations.py && git commit -m "feat: expose masked platform AI key configuration"`.

## Task 3: Add the platform settings UI and typed API client

**Files:** `frontend/src/api.ts:120-140`, `frontend/src/pages/platform/PlatformSettings.vue`, and new `frontend/src/platformSettingsUI.test.ts`.

- [ ] **Step 1: Write failing UI contracts.** Create a Vitest source-contract test that reads `PlatformSettings.vue` and `api.ts`, then asserts the source contains `platform-ai-config/`, `type="password"`, `autocomplete="new-password"`, `masked_key`, `保存后无法查看完整 Key`, `保存 Key`, and `替换 Key`; assert it does not contain a hard-coded `value="sk-`.
- [ ] **Step 2: Run the red test.** Run `npm test -- --run src/platformSettingsUI.test.ts`. Expected: failure because the current page has no Key endpoint or password form.
- [ ] **Step 3: Add typed API calls.** Add `PlatformAIConfig { configured: boolean; masked_key: string; model: string; base_url: string }`, `getPlatformAIConfig()`, and `savePlatformAIConfig(apiKey)` to `frontend/src/api.ts`. Do not cache or persist the input.
- [ ] **Step 4: Implement the form.** Add `aiConfig`, `aiKey`, and `aiKeySaving` refs to `PlatformSettings.vue`. Load metadata with service status. Add an AI configuration card before “服务健康”; the input stays empty on load, uses password type and `autocomplete="new-password"`, and displays only `aiConfig.masked_key`. On submit, trim/reject empty input, call the PUT client, clear the input only after success, update metadata, and show existing feedback states. Use existing card/input/button tokens and stack the form at the mobile breakpoint.
- [ ] **Step 5: Run UI tests and build.** Run `npm test -- --run src/platformSettingsUI.test.ts src/api.test.ts` and `npm run build`. Expected: selected tests and TypeScript/Vite build pass.
- [ ] **Step 6: Commit the UI.** Run `git add frontend/src/api.ts frontend/src/pages/platform/PlatformSettings.vue frontend/src/platformSettingsUI.test.ts && git commit -m "feat: add platform AI key settings UI"`.

## Task 4: Make student navigation icons semantic and consistent

**Files:** `frontend/src/stores/navigationRegistry.ts`, `frontend/src/components/WorkspaceShell.vue`, `frontend/src/components/WorkspaceFrame.vue`, and `frontend/src/stores/navigationRegistry.test.ts`.

- [ ] **Step 1: Write failing icon contracts.** Extend `navigationRegistry.test.ts` to assert the student icon map is exactly `{ home: 'home', projects: 'projects', ai: 'ai', journey: 'journey', invitations: 'members', cases: 'cases', competitions: 'competitions', announcements: 'announcements' }` and all values are unique. Add a source assertion that `WorkspaceFrame.vue` uses `ArrowLeft`/`ArrowRight` components and not the literal `sidebarCollapsed ? '›' : '‹'` expression.
- [ ] **Step 2: Run the red test.** Run `npm test -- --run src/stores/navigationRegistry.test.ts`. Expected: failure because public student entries reuse `content` and the toggle uses literal arrows.
- [ ] **Step 3: Update the registry.** Add `cases`, `competitions`, and `announcements` to `NavigationIcon`; use them in both student navigation builders. Add a `childIcons` lookup in `navigationChildren()` so teacher/platform child pages get semantic icons without changing routes or active-state logic.
- [ ] **Step 4: Update component maps.** Import `ArrowLeft`, `ArrowRight`, `Bell`, `FolderOpened`, `House`, `MagicStick`, `MapLocation`, `Reading`, `Trophy`, and `User` from `@element-plus/icons-vue`. Map student capabilities to House, FolderOpened, MagicStick, MapLocation, User, Reading, Trophy, and Bell. In `WorkspaceFrame.vue`, render ArrowRight when collapsed and ArrowLeft when expanded; keep all existing aria labels, title, and aria-expanded values unchanged.
- [ ] **Step 5: Run navigation tests and build.** Run `npm test -- --run src/stores/navigationRegistry.test.ts src/fullSiteVisualConsistency.test.ts` and `npm run build`. Expected: all selected tests and build pass.
- [ ] **Step 6: Commit navigation.** Run `git add frontend/src/stores/navigationRegistry.ts frontend/src/components/WorkspaceShell.vue frontend/src/components/WorkspaceFrame.vue frontend/src/stores/navigationRegistry.test.ts && git commit -m "fix: unify semantic workspace navigation icons"`.

## Task 5: Update stale contracts and run the verification matrix

**Files:** `frontend/src/remainingPageParity.test.ts`, `frontend/src/pageContentContracts.test.ts`, and `backend/apps/core/tests/test_platform_configuration.py` if final response assertions need tightening.

- [ ] **Step 1: Update stale invitation contracts.** Replace the removed `demo-invitation-list paper-card` assertion with `class="invite-columns"`; replace the old slogan assertion with `在这里处理收到的加入邀请，也能查看自己发出的邀请进度。`. Keep both tests and assert current structure/copy.
- [ ] **Step 2: Run all frontend tests.** Run `npm test -- --run`. Expected: all frontend test files and tests pass.
- [ ] **Step 3: Run backend checks without destructive cleanup.** Run `docker compose exec -T backend python manage.py check`, `docker compose exec -T backend python manage.py makemigrations --check --dry-run`, and `docker compose exec -T backend python manage.py test apps.core.tests --keepdb --verbosity 1`. Expected: the first two exit 0 and the suite reports 244 tests with no failures. `--keepdb` avoids deleting the pre-existing `test_lingsu_integration` database; if it is stale, report the blocker and do not drop it.
- [ ] **Step 4: Run hygiene/dependency checks.** Run `git diff --check HEAD~5..HEAD`, `docker compose exec -T backend python -m pip check`, and `npm audit --omit=dev --registry=https://registry.npmjs.org`. Expected: no whitespace errors, broken Python dependencies, or production npm vulnerabilities.
- [ ] **Step 5: Inspect the secret boundary.** Run `rg -n "OPENAI_API_KEY|encrypted_api_key|api_key|masked_key" backend/apps/core frontend/src --glob '!**/*.map'`. Confirm no serializer/GET response exposes ciphertext, no frontend input binds to a returned Key, no log interpolates the raw Key, every OpenAI constructor uses the dynamic reader, and only platform admins reach the endpoint.
- [ ] **Step 6: Commit contracts.** Run `git add frontend/src/remainingPageParity.test.ts frontend/src/pageContentContracts.test.ts backend/apps/core/tests/test_platform_configuration.py && git commit -m "test: align contracts with AI settings and navigation updates"`.

## Task 6: Final review and push

- [ ] **Step 1: Review the complete diff.** Run `git status --short --branch`, `git diff origin/codex/ui-audit-consistency..HEAD --stat`, and `git log --oneline -8`. Confirm only approved AI configuration, sidebar icons, migration, tests, and docs are included; no secret values or generated local files are staged.
- [ ] **Step 2: Run the release-level frontend build.** Run `npm run build`. Expected: exit 0. Record the existing large-chunk warning separately; do not suppress it by raising the warning threshold.
- [ ] **Step 3: Push after verification.** Run `git push origin codex/ui-audit-consistency` and `git status --short --branch`. Expected: remote advances to the final local commit and the worktree is clean. Mention that the existing branch publish workflow is triggered by the push and that the published image is not release-ready until frontend tests are green.
