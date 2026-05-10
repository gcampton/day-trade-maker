# IBKR YouTube Strategy Dashboard Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a local-first trading research and execution dashboard that ingests popular day-trader YouTube transcripts, extracts strategy ideas, turns them into testable trading strategies, backtests them, visualizes them on charts, and can later route approved paper/live trades through Interactive Brokers.

**Architecture:** Use a web dashboard with a TypeScript/React frontend and a Python backend. Keep strategy generation, backtesting, risk checks, and Interactive Brokers integration behind explicit service boundaries so AI-generated ideas never place trades without validation and approval. Start with paper trading / simulation, then add IBKR paper account connectivity, and only consider live trading after separate explicit approval.

**Tech Stack:** React + TypeScript + Vite frontend; FastAPI backend; PostgreSQL or SQLite for local development; SQLModel/SQLAlchemy for persistence; pandas/numpy for data and backtesting; ib_insync or ibapi for Interactive Brokers; LiteLLM/OpenAI-compatible LLM adapter for transcript-to-strategy extraction; KLineCharts Pro or TradingView Lightweight Charts for charting.

---

## Current Context / Assumptions

- Active workspace: `/home/garratt/dev/1_myprojects/day-trade-maker`.
- This is a new repo. Current files only include prior plan material under `.hermes/plans/`.
- User wants a platform/dashboard, not just a CLI.
- Core product idea:
  - Paste/import YouTube transcripts from popular day traders.
  - Extract trading concepts, setups, indicators, entry/exit rules, timeframes, risk rules, and caveats.
  - Convert those ideas into structured strategy specs.
  - Backtest and compare strategy variants.
  - Display price/action charts with strategy overlays.
  - Integrate with Interactive Brokers for account data, market data, paper trading, and eventually live execution.
- Charting preference:
  - TradingView Lightweight Charts is simpler/free and good for compact chart panels.
  - KLineCharts Pro has more features and is better for larger layouts.
  - Recommendation: build an adapter layer and start with KLineCharts Pro for the main strategy workspace; keep a simple chart component boundary so TradingView Lightweight Charts can be swapped in for smaller widgets later.
- Safety assumption: AI-generated strategy ideas must be treated as hypotheses. The app must force backtesting, paper-trading, and risk checks before any real IBKR order path.

## Product Principles

1. **Research first, execution second:** transcript ingestion and backtesting must work before any live order flow.
2. **Human approval required:** no AI-generated strategy can execute trades automatically without explicit user enablement.
3. **Paper trading default:** IBKR paper account mode should be the first broker integration milestone.
4. **Auditable strategies:** store transcript source, extracted rules, generated code/config, test results, and user approvals.
5. **Strategy specs before code:** LLM output should be validated structured JSON/YAML, not arbitrary executable code.
6. **Composable frontend:** charts, transcript viewer, extracted rules, backtest results, and broker status should be independent dashboard panels.

## Proposed Application Shape

### Backend services

- `TranscriptService`: stores pasted transcripts and metadata.
- `StrategyExtractionService`: uses LLM prompts to extract structured trading ideas from transcripts.
- `StrategyCompiler`: converts validated strategy specs into internal executable strategy objects.
- `BacktestService`: runs historical simulations with risk controls and metrics.
- `MarketDataService`: pulls historical/intraday bars from local files first, then IBKR or other providers.
- `BrokerService`: connects to IBKR Gateway/TWS, initially read-only and paper-only.
- `RiskService`: position sizing, max loss, max trades/day, allowed instruments, trading windows.
- `AuditService`: records generated ideas, approvals, backtests, and order intents.

### Frontend dashboard areas

- Transcript Library: add YouTube URL/transcript, tag creator, symbol, market, timeframe.
- Extraction Workspace: show transcript beside extracted setups/rules.
- Strategy Builder: edit generated strategy spec before backtest.
- Chart Workspace: KLineCharts Pro candlestick chart with overlays/signals/trades.
- Backtest Results: equity curve, drawdown, trade table, metrics, parameter variants.
- IBKR Panel: connection status, account summary, positions, paper/live mode indicator.
- Risk & Approval Panel: strategy safety checks and manual approval steps.

## Recommended Chart Decision

### Start with KLineCharts Pro for the primary chart

Reasoning:
- Better suited for larger layouts and advanced trading-dashboard experiences.
- More built-in technical analysis affordances.
- Good fit for a main strategy research workspace.

### Keep charting behind an app-level adapter

Create a frontend abstraction so chart components receive normalized props:

```ts
type Candle = {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type StrategyMarker = {
  timestamp: number;
  price: number;
  side: 'buy' | 'sell' | 'exit' | 'warning';
  label: string;
};
```

This allows later components:
- `KLineStrategyChart.tsx` for the large workspace.
- `LightweightMiniChart.tsx` for compact dashboard cards.

## Step-by-Step Plan

### Task 1: Initialize monorepo structure

**Objective:** Create a clean full-stack repo layout for backend and frontend.

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `backend/pyproject.toml`
- Create: `backend/src/day_trade_maker/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`

**Steps:**
1. Initialize git with `git init`.
2. Create `backend/` Python FastAPI package.
3. Create `frontend/` Vite React TypeScript app.
4. Add root README explaining this is research/paper-trading first.
5. Add `.gitignore` for Python, Node, env files, database files, and logs.
6. Run backend smoke test command.
7. Run frontend type/build smoke command.
8. Commit: `chore: initialize full-stack trading dashboard repo`.

**Verification:**
- `cd backend && python -m pytest` passes.
- `cd frontend && npm install && npm run build` passes.
- No secrets or `.env` files are committed.

### Task 2: Add backend FastAPI app shell

**Objective:** Expose a health endpoint and establish API structure.

**Files:**
- Create: `backend/src/day_trade_maker/api.py`
- Create: `backend/src/day_trade_maker/config.py`
- Create: `backend/tests/test_api_health.py`
- Modify: `backend/pyproject.toml`

**Steps:**
1. Write a failing test for `GET /health` returning `{ "status": "ok" }`.
2. Implement FastAPI app factory.
3. Add basic settings class for environment-driven config.
4. Add dev command documentation: `uvicorn day_trade_maker.api:app --reload`.
5. Run `python -m pytest backend/tests/test_api_health.py -v` from repo root or backend.
6. Commit: `feat: add fastapi health endpoint`.

**Verification:**
- Test passes.
- Health response is stable JSON.

### Task 3: Add database models and migrations baseline

**Objective:** Persist transcripts, strategy specs, backtest runs, and audit events.

**Files:**
- Create: `backend/src/day_trade_maker/db.py`
- Create: `backend/src/day_trade_maker/models.py`
- Create: `backend/tests/test_models.py`
- Modify: `backend/pyproject.toml`

**Steps:**
1. Choose SQLite for local development, with PostgreSQL-compatible models.
2. Define models:
   - `Transcript`
   - `StrategyIdea`
   - `StrategySpec`
   - `BacktestRun`
   - `AuditEvent`
3. Write tests that create and query records in an in-memory test database.
4. Add timestamps and source fields.
5. Commit: `feat: add persistence models`.

**Verification:**
- Tests do not require an external database.
- Every AI-generated strategy spec links back to transcript/source records.

### Task 4: Add transcript ingestion API

**Objective:** Allow pasted YouTube transcripts to be saved and listed.

**Files:**
- Create: `backend/src/day_trade_maker/routes/transcripts.py`
- Create: `backend/src/day_trade_maker/schemas.py`
- Create: `backend/tests/test_transcripts_api.py`
- Modify: `backend/src/day_trade_maker/api.py`

**Steps:**
1. Write API tests for creating a transcript with fields:
   - `title`
   - `source_url`
   - `creator`
   - `raw_text`
   - `symbols`
   - `timeframes`
2. Implement `POST /api/transcripts`.
3. Implement `GET /api/transcripts`.
4. Implement `GET /api/transcripts/{id}`.
5. Add validation for empty transcript text.
6. Commit: `feat: add transcript ingestion api`.

**Verification:**
- Empty transcripts fail with 422 or 400.
- Saved transcripts can be retrieved with stable IDs.

### Task 5: Add frontend dashboard shell

**Objective:** Create a dashboard layout with navigation for transcript, strategy, chart, backtest, and broker areas.

**Files:**
- Create: `frontend/src/layout/DashboardLayout.tsx`
- Create: `frontend/src/pages/TranscriptsPage.tsx`
- Create: `frontend/src/pages/StrategiesPage.tsx`
- Create: `frontend/src/pages/BacktestsPage.tsx`
- Create: `frontend/src/pages/BrokerPage.tsx`
- Create: `frontend/src/styles.css`
- Modify: `frontend/src/App.tsx`

**Steps:**
1. Add app routes or simple tab state.
2. Create a sidebar/top nav with sections:
   - Transcripts
   - Strategy Builder
   - Charts
   - Backtests
   - IBKR
3. Add placeholder panels with clear empty states.
4. Run frontend build.
5. Commit: `feat: add dashboard shell`.

**Verification:**
- App renders without API dependency.
- Build succeeds.
- Layout has room for a large chart workspace.

### Task 6: Add transcript input UI

**Objective:** Let the user paste transcripts and save them through the backend.

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/TranscriptForm.tsx`
- Create: `frontend/src/components/TranscriptList.tsx`
- Modify: `frontend/src/pages/TranscriptsPage.tsx`

**Steps:**
1. Add API client base URL config.
2. Build transcript form with title, URL, creator, symbols, timeframes, raw text.
3. Save via `POST /api/transcripts`.
4. List saved transcripts from `GET /api/transcripts`.
5. Show validation errors.
6. Commit: `feat: add transcript input ui`.

**Verification:**
- Pasted transcript persists and appears in list.
- UI handles backend validation errors.

### Task 7: Define strategy spec schema

**Objective:** Create a safe structured schema for extracted trading strategies.

**Files:**
- Create: `backend/src/day_trade_maker/strategy_spec.py`
- Create: `backend/tests/test_strategy_spec.py`

**Steps:**
1. Define a strategy spec with fields:
   - `name`
   - `description`
   - `market`
   - `symbols`
   - `timeframe`
   - `indicators`
   - `entry_rules`
   - `exit_rules`
   - `risk_rules`
   - `invalidations`
   - `source_quotes`
2. Add strict validation.
3. Reject arbitrary code fields.
4. Require source quote references back to transcript snippets.
5. Commit: `feat: add validated strategy spec schema`.

**Verification:**
- Malformed specs fail validation.
- No generated Python/JavaScript execution is accepted from LLM output.

### Task 8: Add LLM strategy extraction service

**Objective:** Convert transcript text into validated strategy idea/spec candidates.

**Files:**
- Create: `backend/src/day_trade_maker/llm.py`
- Create: `backend/src/day_trade_maker/services/strategy_extraction.py`
- Create: `backend/tests/test_strategy_extraction.py`
- Modify: `backend/src/day_trade_maker/config.py`

**Steps:**
1. Add LLM adapter interface so providers can be swapped.
2. Write tests with a fake LLM returning JSON.
3. Prompt the model to extract:
   - setup context
   - indicators mentioned
   - entry trigger
   - exit trigger
   - stop loss
   - target/profit-taking
   - timeframe
   - market conditions
   - direct transcript quotes
4. Validate output through `StrategySpec` schema.
5. Store both raw extraction response and normalized spec.
6. Commit: `feat: extract strategy specs from transcripts`.

**Verification:**
- Unit tests use fake LLM only.
- Invalid LLM JSON is rejected and logged.
- Extracted strategies remain editable hypotheses, not executable orders.

### Task 9: Add strategy extraction API and UI

**Objective:** Let the user select a transcript and generate strategy candidates.

**Files:**
- Create: `backend/src/day_trade_maker/routes/strategies.py`
- Create: `backend/tests/test_strategies_api.py`
- Create: `frontend/src/components/StrategyExtractionPanel.tsx`
- Modify: `frontend/src/pages/StrategiesPage.tsx`
- Modify: `backend/src/day_trade_maker/api.py`

**Steps:**
1. Implement `POST /api/transcripts/{id}/extract-strategies`.
2. Implement `GET /api/strategies`.
3. Implement `GET /api/strategies/{id}`.
4. Frontend: select transcript, run extraction, display extracted rules and source quotes.
5. Add UI affordance for editing/approving strategy spec before backtest.
6. Commit: `feat: add strategy extraction workflow`.

**Verification:**
- API persists strategy candidates.
- UI clearly labels AI output as unverified.

### Task 10: Add market data model and CSV import

**Objective:** Support backtests with uploaded/imported candle data before relying on IBKR data.

**Files:**
- Create: `backend/src/day_trade_maker/market_data.py`
- Create: `backend/src/day_trade_maker/routes/market_data.py`
- Create: `backend/tests/fixtures/sample_bars.csv`
- Create: `backend/tests/test_market_data.py`

**Steps:**
1. Define normalized candle fields:
   - timestamp
   - open
   - high
   - low
   - close
   - volume
2. Implement CSV import parser.
3. Add API endpoint for uploading or referencing CSV files.
4. Add tests for valid and invalid candles.
5. Commit: `feat: add market data csv import`.

**Verification:**
- Candle data sorted by timestamp.
- Invalid OHLCV values are rejected.

### Task 11: Add charting with KLineCharts Pro

**Objective:** Display candlestick data with strategy markers and indicators.

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/charts/types.ts`
- Create: `frontend/src/charts/KLineStrategyChart.tsx`
- Create: `frontend/src/pages/ChartsPage.tsx`
- Modify: `frontend/src/App.tsx`

**Steps:**
1. Install KLineCharts Pro package according to its current docs.
2. Create normalized chart types (`Candle`, `StrategyMarker`, `IndicatorOverlay`).
3. Render a chart from sample/static candles first.
4. Add markers for strategy entries/exits.
5. Add a large chart layout suitable for multi-panel workspace.
6. Commit: `feat: add kline strategy chart`.

**Verification:**
- Frontend build passes.
- Chart renders sample candles.
- Markers can be displayed independently of backend.

### Task 12: Add chart API integration

**Objective:** Feed real imported market data and strategy markers into the frontend chart.

**Files:**
- Modify: `backend/src/day_trade_maker/routes/market_data.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/charts/KLineStrategyChart.tsx`
- Modify: `frontend/src/pages/ChartsPage.tsx`

**Steps:**
1. Add `GET /api/market-data/{dataset_id}/candles`.
2. Add frontend API method to fetch candles.
3. Add chart page controls for selecting dataset and strategy.
4. Render candles from backend.
5. Overlay placeholder strategy markers.
6. Commit: `feat: connect chart to market data api`.

**Verification:**
- Imported sample dataset renders on chart.
- Empty data shows a useful empty state.

### Task 13: Add deterministic strategy compiler

**Objective:** Convert validated strategy specs into internal rule evaluators for backtesting.

**Files:**
- Create: `backend/src/day_trade_maker/strategy_compiler.py`
- Create: `backend/src/day_trade_maker/indicators.py`
- Create: `backend/tests/test_strategy_compiler.py`

**Steps:**
1. Start with a limited supported rule set:
   - moving average crossovers
   - RSI threshold
   - volume confirmation
   - fixed stop loss
   - fixed take profit
2. Map natural-language extracted rules into structured supported rules during extraction/editing.
3. Reject unsupported rules with clear messages instead of guessing.
4. Write tests for one moving-average strategy and one RSI strategy.
5. Commit: `feat: compile supported strategy specs`.

**Verification:**
- Compiler never executes LLM-generated code.
- Unsupported rules fail safely.

### Task 14: Add backtesting engine

**Objective:** Evaluate compiled strategies over historical candles with realistic accounting basics.

**Files:**
- Create: `backend/src/day_trade_maker/backtest.py`
- Create: `backend/tests/test_backtest.py`

**Steps:**
1. Implement long-only paper backtest first.
2. Add trade records with entry, exit, quantity, fees, slippage, PnL.
3. Add position sizing from risk settings.
4. Add equity curve.
5. Add metrics: total return, win rate, max drawdown, profit factor, average win/loss.
6. Commit: `feat: add backtesting engine`.

**Verification:**
- Accounting tests use tiny deterministic fixtures.
- Repeated buy/sell edge cases are tested.

### Task 15: Add backtest API and UI

**Objective:** Let the user run a backtest for a selected strategy and dataset.

**Files:**
- Create: `backend/src/day_trade_maker/routes/backtests.py`
- Create: `backend/tests/test_backtests_api.py`
- Create: `frontend/src/components/BacktestRunForm.tsx`
- Create: `frontend/src/components/BacktestResultsPanel.tsx`
- Modify: `frontend/src/pages/BacktestsPage.tsx`

**Steps:**
1. Implement `POST /api/backtests` with strategy ID, dataset ID, cash, fees, slippage.
2. Persist backtest result and metrics.
3. Implement `GET /api/backtests/{id}`.
4. Frontend: run backtest and display summary metrics.
5. Show trade markers on chart after run.
6. Commit: `feat: add backtest workflow`.

**Verification:**
- API returns stable result object.
- UI shows metrics and trade table.
- Chart markers match trades.

### Task 16: Add risk and approval workflow

**Objective:** Prevent unreviewed strategies from reaching broker execution.

**Files:**
- Create: `backend/src/day_trade_maker/risk.py`
- Create: `backend/src/day_trade_maker/routes/approvals.py`
- Create: `backend/tests/test_risk.py`
- Create: `frontend/src/components/RiskApprovalPanel.tsx`

**Steps:**
1. Define risk settings:
   - max position size
   - max daily loss
   - max trades/day
   - allowed symbols
   - paper/live mode lock
2. Require a successful backtest before paper-trade approval.
3. Require explicit user approval for strategy activation.
4. Persist approval audit events.
5. Commit: `feat: add strategy risk approval workflow`.

**Verification:**
- Unapproved strategies cannot create broker order intents.
- Audit events capture who/what/when for approvals.

### Task 17: Add IBKR connection status service

**Objective:** Connect to IBKR Gateway/TWS in read-only/paper-safe mode first.

**Files:**
- Create: `backend/src/day_trade_maker/brokers/ibkr.py`
- Create: `backend/src/day_trade_maker/routes/broker.py`
- Create: `backend/tests/test_ibkr_adapter.py`
- Modify: `backend/src/day_trade_maker/config.py`
- Create: `docs/ibkr-setup.md`

**Steps:**
1. Add config for IBKR host, port, client ID, and paper/live mode.
2. Use an adapter interface so tests can fake IBKR.
3. Implement connection status endpoint without placing orders.
4. Implement account summary/positions read endpoints if connected.
5. Document TWS/Gateway paper setup.
6. Commit: `feat: add ibkr read-only adapter`.

**Verification:**
- Unit tests do not require real IBKR.
- Real connection can be manually tested with paper gateway.
- Live mode is visibly disabled by default.

### Task 18: Add IBKR paper order intents

**Objective:** Allow approved strategies to create paper-trade order intents through explicit user action.

**Files:**
- Modify: `backend/src/day_trade_maker/brokers/ibkr.py`
- Create: `backend/src/day_trade_maker/orders.py`
- Create: `backend/src/day_trade_maker/routes/orders.py`
- Create: `backend/tests/test_orders.py`
- Create: `frontend/src/components/OrderIntentPanel.tsx`

**Steps:**
1. Model `OrderIntent` separately from broker orders.
2. Require approved strategy and risk check for every order intent.
3. Default to paper mode only.
4. Add a final UI confirmation button before submission.
5. Persist request, response, and broker order ID if submitted.
6. Commit: `feat: add paper order intent workflow`.

**Verification:**
- Tests prove unapproved strategies cannot submit.
- Tests prove paper mode is required unless future live mode flag exists.
- UI clearly distinguishes generated signal vs submitted order.

### Task 19: Add audit log UI

**Objective:** Make all AI, backtest, approval, and broker actions traceable.

**Files:**
- Create: `backend/src/day_trade_maker/routes/audit.py`
- Create: `backend/tests/test_audit_api.py`
- Create: `frontend/src/pages/AuditPage.tsx`
- Modify: `frontend/src/App.tsx`

**Steps:**
1. Log transcript ingestion.
2. Log LLM extraction requests/responses.
3. Log strategy edits and approvals.
4. Log backtest runs.
5. Log broker connection attempts and order intents.
6. Add dashboard audit page.
7. Commit: `feat: add audit log`.

**Verification:**
- Every important action creates an audit event.
- Audit page can filter by transcript/strategy/order.

### Task 20: Final documentation and local dev workflow

**Objective:** Make the project runnable and understandable from a fresh checkout.

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/safety.md`
- Create: `docs/strategy-spec.md`
- Modify: `docs/ibkr-setup.md`

**Steps:**
1. Document backend setup.
2. Document frontend setup.
3. Document environment variables.
4. Document how to paste transcripts and extract strategy candidates.
5. Document charting choice and adapter approach.
6. Document IBKR paper setup.
7. Document safety constraints and live-trading non-goals.
8. Commit: `docs: add full local development guide`.

**Verification:**
- A fresh developer can start backend and frontend from README.
- Documentation explicitly says AI-generated strategies require validation and are not financial advice.

## Files Likely to Change

### Root

- `README.md`
- `.gitignore`
- `.env.example`
- `docs/architecture.md`
- `docs/safety.md`
- `docs/strategy-spec.md`
- `docs/ibkr-setup.md`

### Backend

- `backend/pyproject.toml`
- `backend/src/day_trade_maker/__init__.py`
- `backend/src/day_trade_maker/api.py`
- `backend/src/day_trade_maker/config.py`
- `backend/src/day_trade_maker/db.py`
- `backend/src/day_trade_maker/models.py`
- `backend/src/day_trade_maker/schemas.py`
- `backend/src/day_trade_maker/strategy_spec.py`
- `backend/src/day_trade_maker/llm.py`
- `backend/src/day_trade_maker/market_data.py`
- `backend/src/day_trade_maker/indicators.py`
- `backend/src/day_trade_maker/strategy_compiler.py`
- `backend/src/day_trade_maker/backtest.py`
- `backend/src/day_trade_maker/risk.py`
- `backend/src/day_trade_maker/orders.py`
- `backend/src/day_trade_maker/routes/transcripts.py`
- `backend/src/day_trade_maker/routes/strategies.py`
- `backend/src/day_trade_maker/routes/market_data.py`
- `backend/src/day_trade_maker/routes/backtests.py`
- `backend/src/day_trade_maker/routes/approvals.py`
- `backend/src/day_trade_maker/routes/broker.py`
- `backend/src/day_trade_maker/routes/orders.py`
- `backend/src/day_trade_maker/routes/audit.py`
- `backend/src/day_trade_maker/services/strategy_extraction.py`
- `backend/src/day_trade_maker/brokers/ibkr.py`
- `backend/tests/**/*.py`
- `backend/tests/fixtures/sample_bars.csv`

### Frontend

- `frontend/package.json`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/layout/DashboardLayout.tsx`
- `frontend/src/pages/TranscriptsPage.tsx`
- `frontend/src/pages/StrategiesPage.tsx`
- `frontend/src/pages/ChartsPage.tsx`
- `frontend/src/pages/BacktestsPage.tsx`
- `frontend/src/pages/BrokerPage.tsx`
- `frontend/src/pages/AuditPage.tsx`
- `frontend/src/charts/types.ts`
- `frontend/src/charts/KLineStrategyChart.tsx`
- `frontend/src/components/TranscriptForm.tsx`
- `frontend/src/components/TranscriptList.tsx`
- `frontend/src/components/StrategyExtractionPanel.tsx`
- `frontend/src/components/BacktestRunForm.tsx`
- `frontend/src/components/BacktestResultsPanel.tsx`
- `frontend/src/components/RiskApprovalPanel.tsx`
- `frontend/src/components/OrderIntentPanel.tsx`
- `frontend/src/styles.css`

## Tests / Validation

### Backend per-task validation

```bash
cd backend
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
```

### Frontend per-task validation

```bash
cd frontend
npm install
npm run build
npm run typecheck
npm run lint
```

### Full local smoke validation

```bash
# terminal 1
cd backend
uvicorn day_trade_maker.api:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
```

Manual checks:
- Open frontend dashboard.
- Paste a transcript.
- Save transcript.
- Extract strategy candidates using fake/dev LLM mode first.
- Import sample candle CSV.
- Render chart with candles.
- Run backtest.
- See strategy markers and metrics.
- Confirm IBKR panel shows disconnected or paper connection status.

## Risks, Tradeoffs, and Open Questions

### Risks

- **AI hallucination:** Transcripts may contain vague or contradictory advice. Force structured specs, source quotes, and user edits.
- **Unsafe execution:** Never let LLM text become executable code. Compile only supported structured rule types.
- **Financial risk:** Paper mode must be default. Live mode should require a separate plan and explicit opt-in.
- **IBKR complexity:** TWS/Gateway setup, market data permissions, pacing limits, and paper/live differences can be painful. Isolate in adapter and test with fakes.
- **Backtest realism:** Naive backtests can overstate performance. Include fees, slippage, spreads, liquidity assumptions, and realistic session timing as early as practical.
- **Chart library churn:** KLineCharts Pro docs/API may change. Keep chart usage isolated in `frontend/src/charts/`.

### Tradeoffs

- **FastAPI + React** is more setup than a single Streamlit app, but it is a better fit for a serious dashboard and IBKR service boundary.
- **KLineCharts Pro first** gives richer charting for the large workspace, while an adapter keeps the door open for TradingView Lightweight Charts.
- **SQLite first** is easiest locally; PostgreSQL compatibility should be preserved if the app grows.
- **Structured strategy specs** are less flexible than arbitrary generated code, but much safer and easier to backtest/audit.

### Open Questions

- Which markets should the first version prioritize: US equities, futures, forex, or crypto?
- Should transcript import support direct YouTube URL fetching, or is paste-only enough for v1?
- Which LLM provider should be used locally/configurably?
- Should strategy generation create multiple variants per transcript, or one canonical strategy first?
- What minimum backtest performance criteria should be required before paper trading approval?
- Should live trading be explicitly out of scope for the first milestone?

## Recommended Milestones

### Milestone 1: Local research dashboard

- Full-stack shell.
- Transcript paste/list.
- Strategy extraction with fake/dev LLM.
- KLineCharts Pro sample chart.

### Milestone 2: Backtesting workspace

- Validated strategy specs.
- CSV market data import.
- Strategy compiler.
- Backtest engine and results UI.
- Chart overlays for trades.

### Milestone 3: IBKR paper integration

- IBKR read-only connection.
- Account/position display.
- Paper order intents only.
- Risk approval workflow.
- Audit log.

### Milestone 4: Production hardening before any live trading

- Better market data handling.
- More realistic backtests.
- Robust risk limits.
- Secrets management.
- Monitoring/logging.
- Explicit live-trading review and separate implementation plan.
