# IBKR Paper Order Submission Gates Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Add an explicit, opt-in IBKR paper-account order submission path without weakening the existing audit-only order-intent workflow or adding any live-trading capability.

**Architecture:** Keep `PaperOrderIntent` as a frozen audit artifact and add a separate `PaperBrokerOrderSubmission` artifact that can only be created from an existing intent after all safety gates pass. Broker paper submission remains disabled by default, enabled only by explicit env flags, routed through a small tested adapter boundary, and surfaced in the UI with confirmation copy that distinguishes IBKR paper submission from live trading.

**Tech Stack:** FastAPI + Pydantic backend, existing in-memory stores with SQLite audit snapshot persistence, optional `ib_async` broker adapter, React + TypeScript + Vitest frontend.

---

## Current Context / Assumptions

- Active workspace: `/home/garratt/dev/1_myprojects/day-trade-maker`.
- Current branch is clean after `feat: add broker safety summary`.
- Current broker state:
  - `GET /api/broker/safety-summary` aggregates status/account/connectivity/capabilities.
  - `PaperOrderIntent` is audit-only and records `submitted_to_broker=false`.
  - Audit-only intent creation intentionally rejects if broker order operations become available.
  - Read-only account snapshots can use a static reader or optional `ib_async` reader.
  - Live broker submission is not implemented and must remain disabled.
- This plan intentionally does not add live trading.
- This plan intentionally does not mutate existing order intents into broker orders. It adds a separate submission artifact linked to an intent.
- Exact confirmation phrase recommendation: `SUBMIT IBKR PAPER ORDER`.

## Safety Invariants

1. Defaults remain audit-only:
   - no env flags set => no broker order operation available;
   - existing order-intent tests continue to pass;
   - UI cannot imply broker submission is active.
2. Paper broker submission is opt-in and explicit:
   - require `DAY_TRADE_MAKER_IBKR_PAPER_ORDER_SUBMISSION_ENABLED=true`;
   - require `DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_ENABLED=true`;
   - require `DAY_TRADE_MAKER_IBKR_ACCOUNT_SNAPSHOT_READER=ib_async` for the real submitter;
   - require an existing approved/risk-checked paper order intent;
   - require exact confirmation phrase.
3. Live trading stays impossible in this slice:
   - `live_broker_submission_implemented=false`;
   - `live_broker_submission_enabled=false`;
   - no live-mode env flag is introduced.
4. Submission is auditable:
   - request payload, frozen source intent, broker capability snapshot, broker response/order id, checks, and timestamps are persisted/exported.
5. Adapter boundary is testable without real IBKR:
   - tests use fake client factories and fake submitters;
   - real `ib_async` remains optional and is not required for CI.

## Proposed API Shape

### Existing endpoint to update conservatively

- `GET /api/broker/order-submission-capability`
  - disabled default remains equivalent to today's response;
  - when paper submission is enabled and real submitter prerequisites are available, response can report:
    - `current_execution_mode="paper_broker"`
    - `paper_broker_submission_implemented=true`
    - `paper_broker_submission_enabled=true`
    - `broker_order_operation_available=true`
    - `live_broker_submission_implemented=false`
    - `live_broker_submission_enabled=false`

### New endpoint

- `POST /api/broker/paper-order-submissions`
  - request:
    - `order_intent_id: int`
    - `confirmation_phrase: string`
    - `user_confirmed: true`
  - response:
    - `id`
    - `order_intent_id`
    - `status`: `submitted_to_paper_broker` or `rejected`
    - `submitted_to_broker=true`
    - `broker_order_id`
    - `current_execution_mode="paper_broker"`
    - `paper_broker_submission_enabled=true`
    - `live_broker_submission_enabled=false`
    - `checks`
    - `broker_response`
    - `message`
    - `created_at`

## Step-by-Step Plan

### Task 1: Add disabled-by-default paper submission capability tests

**Objective:** Lock the current audit-only default before any implementation changes.

**Files:**
- Modify: `backend/tests/test_broker_status_api.py`
- Test: `backend/tests/test_broker_status_api.py`

**Steps:**
1. Add or extend a test for `GET /api/broker/order-submission-capability` with no env flags.
2. Assert the exact conservative contract:
   - `current_execution_mode == "audit_only"`
   - `paper_broker_submission_implemented is False`
   - `paper_broker_submission_enabled is False`
   - `broker_order_operation_available is False`
   - `live_broker_submission_implemented is False`
   - `live_broker_submission_enabled is False`
3. Add a test for `GET /api/broker/safety-summary` default that mirrors those fields.
4. Run the focused backend test.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_broker_status_api.py -v
```

**Expected result:** tests pass before implementation; this is the regression guard.

### Task 2: Add schema types for paper broker submissions

**Objective:** Model paper broker submission separately from audit-only order intents.

**Files:**
- Modify: `backend/src/day_trade_maker/schemas.py`
- Test: `backend/tests/test_broker_paper_order_submission_api.py`

**Steps:**
1. Broaden `BrokerOrderSubmissionCapability.current_execution_mode` from `Literal["audit_only"]` to `Literal["audit_only", "paper_broker"]`.
2. Broaden `BrokerSafetySummary.current_execution_mode` the same way.
3. Keep `PaperOrderIntent.current_execution_mode` as `Literal["audit_only"]` so historical audit intents cannot become broker submissions.
4. Add `PaperBrokerOrderSubmissionCreate`:
   - `order_intent_id: int = Field(gt=0)`
   - `user_confirmed: bool`
   - `confirmation_phrase: NonEmptyString`
5. Add `PaperBrokerOrderSubmission`:
   - `id: int`
   - `order_intent_id: int`
   - `status: Literal["submitted_to_paper_broker"]`
   - `submitted_to_broker: bool = True`
   - `broker_order_id: str | None`
   - `current_execution_mode: Literal["paper_broker"] = "paper_broker"`
   - `paper_broker_submission_enabled: bool = True`
   - `live_broker_submission_enabled: bool = False`
   - `broker_response: dict[str, str | int | float | bool | None]`
   - `checks: list[str]`
   - `message: str`
   - `created_at: datetime`
6. Add `paper_broker_order_submissions: list[PaperBrokerOrderSubmission]` to `AuditSnapshot` with a default empty list, if `AuditSnapshot` currently lacks it.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_order_intents_api.py tests/test_broker_status_api.py -v
```

**Expected result:** existing tests still pass after type broadening.

### Task 3: Add env settings for paper submission while keeping defaults disabled

**Objective:** Make paper order capability env-driven but disabled unless explicitly opted in.

**Files:**
- Modify: `backend/src/day_trade_maker/broker.py`
- Modify: `.env.example`
- Test: `backend/tests/test_broker_adapter.py`

**Steps:**
1. Add fields to `EnvBrokerSettings`:
   - `paper_order_submission_enabled: bool = False`
   - `paper_order_submission_confirmation_phrase: str = "SUBMIT IBKR PAPER ORDER"`
2. Read env vars:
   - `DAY_TRADE_MAKER_IBKR_PAPER_ORDER_SUBMISSION_ENABLED`
   - `DAY_TRADE_MAKER_IBKR_PAPER_ORDER_CONFIRMATION_PHRASE`
3. Add `.env.example` entries with safe disabled defaults and comments stating this is IBKR paper-only and live trading is unsupported.
4. Extend `test_env_broker_settings_reads_safe_defaults` to assert paper submission disabled by default.
5. Extend `test_env_broker_settings_reads_opt_in_probe_configuration` or add a new test for the opt-in env values.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_broker_adapter.py::test_env_broker_settings_reads_safe_defaults tests/test_broker_adapter.py::test_env_broker_settings_reads_opt_in_probe_configuration -v
```

**Expected result:** env parsing is covered and default remains disabled.

### Task 4: Extract order-submission capability builder

**Objective:** Centralize capability logic so routes, tests, and the UI summary cannot drift.

**Files:**
- Modify: `backend/src/day_trade_maker/broker.py`
- Modify: `backend/src/day_trade_maker/routes/broker.py`
- Modify: `backend/tests/test_broker_adapter.py`
- Modify: `backend/tests/test_broker_status_api.py`

**Steps:**
1. Add a function in `broker.py`:
   - `build_order_submission_capability(settings: EnvBrokerSettings, account_snapshot: BrokerAccountSnapshot | None = None) -> BrokerOrderSubmissionCapability`
2. Disabled/default branch returns today's exact audit-only response.
3. Enabled branch returns paper-broker capability only when all are true:
   - `settings.paper_order_submission_enabled`
   - `settings.account_snapshot_enabled`
   - `settings.account_snapshot_reader == "ib_async"`
   - optional dependency is available or a fake submitter is injected in tests
   - account snapshot has `account_data_loaded=True`
4. If env is enabled but prerequisites are not met, keep `broker_order_operation_available=false` and return a message explaining the missing prerequisite.
5. Update `get_broker_order_submission_capability()` to call this builder with current settings and account snapshot.
6. Update `get_broker_safety_summary()` to reuse the same capability builder so nested and top-level fields match.
7. Add tests for:
   - disabled default;
   - env enabled but account snapshot disabled => unavailable;
   - env enabled and fake loaded account snapshot => paper capability available;
   - live submission remains false in every branch.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_broker_adapter.py tests/test_broker_status_api.py -v
```

**Expected result:** capability transitions are explicit and conservative.

### Task 5: Add broker paper order submitter adapter with fake-client tests

**Objective:** Isolate the real IBKR paper-order side effect behind a small adapter that can be tested without IBKR.

**Files:**
- Create: `backend/src/day_trade_maker/broker_orders.py`
- Create: `backend/tests/test_broker_order_submission_adapter.py`
- Modify: `backend/pyproject.toml` only if adding optional dependency metadata is desired

**Steps:**
1. Define `BrokerPaperOrderRequest` dataclass with fields copied from the source intent:
   - symbol, side, quantity, order_type, limit_price.
2. Define `BrokerPaperOrderResult` dataclass:
   - `broker_order_id: str | None`
   - `status: str`
   - `raw_response: dict[str, str | int | float | bool | None]`
3. Define `PaperOrderSubmitter` protocol with `submit(settings, request) -> BrokerPaperOrderResult`.
4. Implement `UnavailablePaperOrderSubmitter` that raises a domain exception if called while disabled.
5. Implement `IbAsyncPaperOrderSubmitter` that:
   - imports `ib_async` lazily;
   - connects with `readonly=False` only when paper submission is enabled;
   - creates a `Stock(symbol, "SMART", "USD")` contract for v1 equities only;
   - creates `MarketOrder` or `LimitOrder` based on intent;
   - calls `placeOrder`;
   - captures order id/status from the returned trade/order;
   - disconnects in `finally`;
   - never supports live mode.
6. Write adapter tests with fake IB client classes proving:
   - disabled submitter raises before client creation;
   - enabled submitter connects to the configured paper gateway;
   - market orders map side/quantity correctly;
   - limit orders require `limit_price`;
   - disconnect happens on success and on error;
   - no test requires real `ib_async`.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_broker_order_submission_adapter.py -v
```

**Expected result:** adapter behavior is fully covered by fakes.

### Task 6: Add backend store and persistence for paper broker submissions

**Objective:** Persist broker submission artifacts alongside the existing audit snapshot.

**Files:**
- Modify: `backend/src/day_trade_maker/stores.py`
- Modify: `backend/src/day_trade_maker/persistence.py`
- Modify: `backend/tests/test_persistence.py`
- Modify: `backend/tests/test_audit_snapshots_api.py`

**Steps:**
1. Add `PaperBrokerOrderSubmissionStore` with:
   - `create(...)`
   - `list()`
   - `get(id)` if needed
   - `replace_all(...)`
2. Include `paper_broker_order_submission_store` in global store initialization from `_initial_snapshot`.
3. Include submissions in `current_snapshot()`.
4. Update `replace_all(snapshot)` / audit import path to replace submissions too.
5. Update SQLite JSON snapshot persistence tests to save, reload, and count submissions.
6. Update audit export/import tests to include `paper_broker_order_submissions` in summaries.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_persistence.py tests/test_audit_snapshots_api.py -v
```

**Expected result:** broker paper submissions survive export/import and local SQLite persistence.

### Task 7: Add `POST /api/broker/paper-order-submissions` with hard gates

**Objective:** Add the only backend endpoint that can trigger a paper broker order side effect.

**Files:**
- Modify: `backend/src/day_trade_maker/routes/broker.py`
- Create: `backend/tests/test_broker_paper_order_submission_api.py`

**Steps:**
1. Add route `POST /api/broker/paper-order-submissions`.
2. Look up the source `PaperOrderIntent` by id; add `PaperOrderIntentStore.get(intent_id)` if missing.
3. Reject with 404 if the intent is unknown.
4. Reject with 400 if `user_confirmed` is not true.
5. Reject with 400 if `confirmation_phrase` does not equal `settings.paper_order_submission_confirmation_phrase`.
6. Re-check all source intent safety fields:
   - intent exists;
   - `paper_mode is True`;
   - `submitted_to_broker is False` on the source intent;
   - source strategy still exists and is approved;
   - source risk check still exists, matches the strategy, and is passed.
7. Rebuild current capability and reject with 409 unless:
   - `paper_broker_submission_enabled is True`;
   - `broker_order_operation_available is True`;
   - `live_broker_submission_enabled is False`.
8. Use an injectable `paper_order_submitter` module variable for tests, defaulting to the real `IbAsyncPaperOrderSubmitter` only when enabled.
9. On submitter success, create a `PaperBrokerOrderSubmission` store record.
10. Return HTTP 201 with a message such as: `IBKR paper order submitted; live trading remains disabled.`
11. Add tests for rejects:
   - default disabled env => 409;
   - missing confirmation => 400;
   - wrong phrase => 400;
   - unknown intent => 404;
   - failed/stale risk check => 400;
   - live enabled simulated => reject even if paper is enabled.
12. Add success test with fake capability builder/account snapshot/submitter.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_broker_paper_order_submission_api.py tests/test_order_intents_api.py -v
```

**Expected result:** existing audit-only intent behavior remains unchanged; paper submission only works in the explicitly mocked safe path.

### Task 8: Add list endpoint for paper broker submission audit history

**Objective:** Let the UI and audit views render submitted paper-broker artifacts without reusing order-intent history.

**Files:**
- Modify: `backend/src/day_trade_maker/routes/broker.py`
- Modify: `backend/tests/test_broker_paper_order_submission_api.py`

**Steps:**
1. Add `GET /api/broker/paper-order-submissions` returning `list[PaperBrokerOrderSubmission]`.
2. Add tests that create two fake successful submissions and assert list order and safety fields.
3. Ensure listed artifacts include `submitted_to_broker=true`, broker order ids, and `live_broker_submission_enabled=false`.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_broker_paper_order_submission_api.py -v
```

**Expected result:** paper broker submission audit history is separate and visible.

### Task 9: Update frontend API types and client methods

**Objective:** Give the UI typed access to paper submission capability and history.

**Files:**
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/App.test.tsx`

**Steps:**
1. Broaden frontend `BrokerOrderSubmissionCapability.current_execution_mode` to `'audit_only' | 'paper_broker'`.
2. Broaden `BrokerSafetySummary.current_execution_mode` similarly.
3. Keep `PaperOrderIntent.current_execution_mode` as `'audit_only'`.
4. Add types:
   - `PaperBrokerOrderSubmissionCreatePayload`
   - `PaperBrokerOrderSubmission`
5. Add client methods:
   - `createPaperBrokerOrderSubmission(payload)` => `POST /api/broker/paper-order-submissions`
   - `getPaperBrokerOrderSubmissions()` => `GET /api/broker/paper-order-submissions`
6. Update fetch helper tests/mocks if any existing tests assert exact call order.

**Verification command:**

```bash
cd frontend
npm run typecheck
```

**Expected result:** TypeScript accepts the new API surface.

### Task 10: Add frontend paper-submission panel behind capability state

**Objective:** Surface an explicit paper-account submission action without implying live trading.

**Files:**
- Modify: `frontend/src/pages/ChartsPage.tsx`
- Modify: `frontend/src/App.test.tsx`

**Steps:**
1. Add state:
   - `paperBrokerSubmissionHistory`
   - `paperBrokerSubmission`
   - `paperSubmissionConfirmationPhrase`
   - `isSubmittingPaperBrokerOrder`
2. Load submission history when broker readiness is loaded or on mount if appropriate.
3. Render a panel only after an audit-only order intent exists.
4. If `brokerOrderSubmissionCapability.paper_broker_submission_enabled` is false, render disabled copy:
   - `IBKR paper order submission disabled`
   - `This order intent is an audit artifact only; no broker order was submitted.`
5. If enabled, show an explicit warning:
   - `This submits to the configured IBKR paper account only. Live trading is not supported.`
6. Require the user to type `SUBMIT IBKR PAPER ORDER` before enabling the button.
7. Button label should be unambiguous: `Submit to IBKR paper account`.
8. On success, render broker order id/status and append to the paper submission history list.
9. Do not rename existing audit-only order-intent button to `submit`; keep it as `Record audit-only order intent` or equivalent.
10. Add frontend tests for:
    - disabled/default copy;
    - enabled capability still requires phrase;
    - success calls `POST /api/broker/paper-order-submissions` with intent id and confirmation phrase;
    - success renders broker order id;
    - live trading disabled copy remains visible.

**Verification command:**

```bash
cd frontend
npm test -- src/App.test.tsx
npm run typecheck
```

**Expected result:** UI cannot accidentally imply live execution or hidden broker submission.

### Task 11: Update audit export/import UI and persistence status counts

**Objective:** Include paper broker submissions in archive/status visibility.

**Files:**
- Modify: `backend/src/day_trade_maker/schemas.py`
- Modify: `backend/src/day_trade_maker/routes/audit.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/ChartsPage.tsx`
- Modify: `backend/tests/test_audit_snapshots_api.py`
- Modify: `frontend/src/App.test.tsx`

**Steps:**
1. Add `paper_broker_order_submissions_count` to audit import/status summaries if the app currently returns per-artifact counts.
2. Render the count in the frontend audit/archive panel.
3. Include submissions in `applyAuditSnapshotToWorkspace(snapshot)` so import/startup restore shows paper submission history.
4. Add backend tests for export/import counts.
5. Add frontend tests that imported snapshots show paper broker submission history without page refresh.

**Verification command:**

```bash
cd backend
python -m pytest tests/test_audit_snapshots_api.py -v
cd ../frontend
npm test -- src/App.test.tsx
```

**Expected result:** paper broker submissions are not hidden in persistence/archive flows.

### Task 12: Add operator documentation and final validation

**Objective:** Document how to enable and manually verify IBKR paper submission safely.

**Files:**
- Create: `docs/ibkr-paper-order-submission.md`
- Modify: `README.md`
- Modify: `.env.example`

**Steps:**
1. Document prerequisites:
   - IBKR Gateway/TWS paper account running;
   - paper port, usually `4002` for Gateway or `7497` for TWS depending setup;
   - account snapshot enabled and loaded;
   - paper submission env flag enabled;
   - live trading unsupported.
2. Document env vars and safe defaults.
3. Document manual smoke flow:
   - start backend;
   - load broker safety summary;
   - create transcript/strategy/backtest/risk check;
   - record audit-only order intent;
   - type confirmation phrase;
   - submit to IBKR paper account;
   - verify broker order id/status;
   - export audit snapshot.
4. Document emergency fallback:
   - unset `DAY_TRADE_MAKER_IBKR_PAPER_ORDER_SUBMISSION_ENABLED`;
   - restart backend;
   - verify capability endpoint returns `broker_order_operation_available=false`.
5. Run full validation.

**Verification commands:**

```bash
cd backend
python -m pytest -v
python -m ruff check .

cd ../frontend
npm test
npm run typecheck
npm run build
```

**Expected result:** full backend and frontend validation pass; docs make the paper/live boundary explicit.

## Files Likely to Change

### Backend

- `backend/src/day_trade_maker/broker.py`
- `backend/src/day_trade_maker/broker_orders.py` (new)
- `backend/src/day_trade_maker/routes/broker.py`
- `backend/src/day_trade_maker/routes/audit.py`
- `backend/src/day_trade_maker/schemas.py`
- `backend/src/day_trade_maker/stores.py`
- `backend/src/day_trade_maker/persistence.py`
- `backend/tests/test_broker_adapter.py`
- `backend/tests/test_broker_status_api.py`
- `backend/tests/test_broker_order_submission_adapter.py` (new)
- `backend/tests/test_broker_paper_order_submission_api.py` (new)
- `backend/tests/test_order_intents_api.py`
- `backend/tests/test_audit_snapshots_api.py`
- `backend/tests/test_persistence.py`

### Frontend

- `frontend/src/api/client.ts`
- `frontend/src/pages/ChartsPage.tsx`
- `frontend/src/App.test.tsx`

### Docs/config

- `.env.example`
- `README.md`
- `docs/ibkr-paper-order-submission.md` (new)

## Tests / Validation

### Focused backend validation

```bash
cd backend
python -m pytest \
  tests/test_broker_adapter.py \
  tests/test_broker_status_api.py \
  tests/test_broker_order_submission_adapter.py \
  tests/test_broker_paper_order_submission_api.py \
  tests/test_order_intents_api.py \
  -v
```

### Persistence/audit validation

```bash
cd backend
python -m pytest tests/test_persistence.py tests/test_audit_snapshots_api.py -v
```

### Frontend validation

```bash
cd frontend
npm test -- src/App.test.tsx
npm run typecheck
npm run build
```

### Full validation

```bash
cd backend
python -m pytest -v
python -m ruff check .

cd ../frontend
npm test
npm run typecheck
npm run build
```

## Risks, Tradeoffs, and Open Questions

### Risks

- Real `ib_async` order placement can have API-shape details that differ from fakes. Keep the adapter tiny and manually verify only against an IBKR paper account.
- IBKR paper account connectivity can be flaky; endpoint responses must return safe errors without creating partial audit records unless a broker response exists.
- UI copy can become ambiguous if “paper order” is shortened. Use “IBKR paper account” and “live trading unsupported” consistently.
- Existing global stores share state across tests; new tests may need cleanup/import reset patterns consistent with current audit tests.

### Tradeoffs

- Creating a separate `PaperBrokerOrderSubmission` artifact is more schema work than flipping fields on `PaperOrderIntent`, but it preserves historical audit-only semantics.
- Env-gated submission is less convenient than a UI toggle, but safer for the first broker side-effect slice.
- Supporting only SMART/USD stock orders in v1 is narrow, but avoids pretending options/futures/forex contracts are safely modeled.

### Open Questions

- Resolved during continuation: side-effecting paper submission/status-refresh endpoints now support optional admin bearer-token plus CSRF-token auth and fail closed when required but not configured.
- Resolved during continuation: v1 keeps SMART/USD stock market and limit broker-paper submissions, with final broker-request validation and frontend limit-price ticket support for explicit limit intents.
- Resolved during continuation: broker order submissions require a recent broker safety summary timestamp (`safety_summary_checked_at`) and reject missing/stale summaries before reserving or calling `placeOrder`.
- Resolved during continuation: the app persists explicit/operator-triggered IBKR paper order status refreshes on the existing `PaperBrokerOrderSubmission` record (`latest_broker_order_status`, `broker_status_checked_at`, `broker_status_response`).
- Resolved during continuation: the confirmation phrase remains backend-configurable via env and is surfaced through broker capability/safety-summary responses so the UI posts the exact backend-required phrase.
- Resolved during continuation: keep the IBKR paper submission panel visible as disabled educational safety copy unless backend capability enables the exact paper-account submission flow.
- Resolved during continuation: frontend broker-readiness copy now reflects `paper_broker` mode instead of hardcoding audit-only labels, and the UI disables new audit-only intent recording while broker order operations are currently available.

## Recommended Implementation Order

1. Backend schema + disabled capability tests.
2. Env settings + capability builder.
3. Adapter with fake tests.
4. Submission store/persistence.
5. Submission API with hard gates.
6. Frontend types/client.
7. Frontend disabled/enabled panel tests and implementation.
8. Docs and full validation.

Do not start with the real `ib_async` placement code until the disabled-default and reject-path tests are passing.
