# Cleanup Plan

This plan identifies unused or legacy files and ranks them by removal risk. The goal is to steadily reduce dead code while avoiding regressions. Only the lowest-risk items are removed immediately; the rest await review.

## Criteria
- Unreferenced by code (no imports/usages across repo)
- Superseded by newer modules and clearly marked `deprecate`/`deprecated`
- Test/demo artifacts not wired into build or runtime

## Removed now (Low risk)
These files had zero references across the codebase and were manual demos/tests:

1) backend/ws_client.py
   - Reason: No imports/usages found. Superseded by WebSocket handling in backend endpoints.

2) backend/demo_cli.py
   - Reason: Standalone demo script; no imports/usages found.

3) src/components/WebSocketIntegrationTest.tsx
   - Reason: Manual integration test component; not imported anywhere.

4) src/components/WebSocketServicesIntegrationTest.tsx
   - Reason: Manual integration test component; not imported anywhere.

5) backend/test_with_cleanup.sh
   - Reason: No references in code or docs. Duplicates functionality achievable via direct commands.

6) All archived component files (kept folders and README.md for future use):
   - src/icui/components/archived/*.tsx (13 deprecated components)
   - src/components/archived/*.tsx (5 legacy components)
   - Reason: Re-exports removed first, then files deleted. These were superseded by newer implementations.

7) Outdated test files that referenced deleted archived components:
   - tests/integration/icui/ICUITest3.tsx, ICUITest4.tsx, ICUITest4.5.tsx, ICUITest4.9.tsx
   - tests/integration/icui/ICUITest8.2.tsx, ICUIMainPage.tsx, ICUIReferenceLayouts.tsx
   - tests/integration/icui/ICUIEditorComparison.tsx, icuiTerminaltest.tsx
   - tests/integration/components/IntegratedHome.tsx
   - Reason: These test files were testing deprecated components and had broken imports after cleanup.

8) Deprecated SQLite chat database system:
   - backend/chat.db (file removed)
   - SQLite imports and dependencies (sqlite3, aiosqlite) removed from chat_service.py
   - _initialize_database() method removed from ChatService
   - db_path parameter removed from ChatService constructor
   - aiosqlite dependency removed from requirements.txt and pyproject.toml
   - Updated tests to remove database initialization and db_path references
   - Reason: Chat history now uses JSONL files per session, SQLite system was deprecated.



## Candidates (High risk) — informational only
- backend/main_original_backup.py
  - Kept intentionally as a reference after the refactor; suggest keeping until backend stabilizes fully.

## Next steps proposed
1) ✅ COMPLETED: Remove re-exports of archived components from index files
2) ✅ COMPLETED: Run build and unit tests; verified green after deletions
3) ✅ COMPLETED: Delete archived component files (kept folders and README.md for future use)
4) Consider additional cleanup candidates in future passes (see "New review" section below)

---

## New review (2025-10-01): Specific files assessment

Reviewed the following files to determine usage and logical need. Results grouped by recommendation.

### Keep (in use or logically required)
- src/test-setup.ts
   - Used by vitest config (vitest.config.ts: setupFiles) and tsconfig.test.json; required for test environment.
- src/vite-env.d.ts
   - Standard Vite TypeScript types reference; safe to keep to avoid missing types in TS builds.
- tests/integration/simplechat.tsx
   - Imported and routed in src/App.tsx (/simple-chat); used for live testing.
- tests/integration/simpleeditor.tsx
   - Imported and routed in src/App.tsx (/simple-editor); used for live testing.
- tests/integration/simpleexplorer.tsx
   - Imported and routed in src/App.tsx (/simple-explorer); used for live testing.
- tests/integration/simpleterminal.tsx
   - Imported and routed in src/App.tsx (/simple-terminal); used for live testing.

### Candidates (Medium risk) — keep for now, pending review
- backend/setup_chat_agent.py
   - Not referenced programmatically; manual setup utility for configuring an OpenAI agent. Potentially useful for ops; keep until we formalize an ops path or document replacement.
- backend/test_gpt5_compatibility.py
   - Not wired into pytest; referenced by docs/gpt5_compatibility_update.md as an example suite. Removing would break docs; keep or move under docs/examples in a later pass.
- tests/integration/chat_phase_1_2_test.tsx
   - Not routed/imported; useful integration testing page; retain for QA until we consolidate test pages.
- tests/integration/chat_phase_3_4_test.tsx
   - Same as above; retain for QA until consolidation.
- tests/integration/chat_phase_4_5_test.tsx
   - Same as above; retain for QA until consolidation.
