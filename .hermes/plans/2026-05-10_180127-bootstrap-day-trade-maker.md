# Bootstrap Day Trade Maker Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Bootstrap the empty `day-trade-maker` workspace into a small, testable application for collecting market data, defining day-trading rules, backtesting them, and producing simulated trade recommendations without executing real orders.

**Architecture:** Start with a local-first Python CLI/library rather than a broker-connected trading bot. Keep the core domain pure and testable: market data ingestion, indicators, strategy signals, backtesting, risk controls, and reporting live in separate modules. Defer live brokerage integration until the simulator, risk model, and audit logs are reliable.

**Tech Stack:** Python 3.11+, `uv` or `pip` for environment management, `pytest` for tests, `ruff` for lint/format, `typer` for CLI, `pandas`/`numpy` for time-series data, optional `yfinance` for initial free data ingestion.

---

## Current Context / Assumptions

- Active workspace: `/home/garratt/dev/1_myprojects/day-trade-maker`.
- The directory is currently empty and is not a git repository.
- No product requirements were provided, so this plan assumes the safest useful default: a research/backtesting tool that can generate simulated day-trading signals but cannot place real trades.
- This is not financial advice. Implementation should include explicit paper-trading/simulation language and hard guards against accidental live execution.
- Prefer small, verified increments with tests before implementation.

## Proposed Approach

1. Create a minimal Python package with CLI entry points and quality tooling.
2. Define core domain models for bars, signals, trades, positions, and portfolio state.
3. Add market data loading from local CSV first, then optional remote download.
4. Implement indicators and one simple baseline strategy.
5. Add a backtesting engine with deterministic tests.
6. Add risk controls and reporting before any notion of live integration.
7. Document safe usage and future extension points.

## Step-by-Step Plan

### Task 1: Initialize repository skeleton

**Objective:** Create a minimal Python project structure that can run tests and linting.

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/day_trade_maker/__init__.py`
- Create: `tests/__init__.py`

**Steps:**
1. Initialize git repository with `git init`.
2. Create `pyproject.toml` with package metadata and dev dependencies:
   - `pytest`
   - `ruff`
   - `typer`
   - `pandas`
   - `numpy`
3. Add a CLI entry point named `dtm` pointing to `day_trade_maker.cli:app`.
4. Add a short `README.md` stating that the project is simulation-only.
5. Run: `python -m pytest`.
6. Run: `python -m ruff check .`.
7. Commit: `chore: initialize python project skeleton`.

**Verification:**
- `python -m pytest` exits 0, even with no substantive tests yet.
- `python -m ruff check .` exits 0.
- `python -c "import day_trade_maker; print(day_trade_maker.__version__)"` works.

### Task 2: Add CLI smoke test and command shell

**Objective:** Provide a working CLI with a version command.

**Files:**
- Create: `src/day_trade_maker/cli.py`
- Create: `tests/test_cli.py`
- Modify: `pyproject.toml`

**Steps:**
1. Write a failing test using `typer.testing.CliRunner` that runs `dtm version`.
2. Implement `src/day_trade_maker/cli.py` with a Typer app and `version` subcommand.
3. Ensure version reads from `day_trade_maker.__version__`.
4. Run: `python -m pytest tests/test_cli.py -v`.
5. Run: `python -m ruff check .`.
6. Commit: `feat: add cli version command`.

**Verification:**
- `python -m pytest tests/test_cli.py -v` passes.
- `python -m day_trade_maker.cli` is not required; the package entry point is the supported interface.

### Task 3: Define market data domain models

**Objective:** Add typed data structures for OHLCV bars and validation rules.

**Files:**
- Create: `src/day_trade_maker/models.py`
- Create: `tests/test_models.py`

**Steps:**
1. Write failing tests for a valid bar and invalid bars:
   - high lower than open/close
   - low higher than open/close
   - negative volume
2. Implement a `Bar` dataclass or Pydantic-style model without adding unnecessary dependencies.
3. Add fields: `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`.
4. Add validation in `__post_init__`.
5. Run: `python -m pytest tests/test_models.py -v`.
6. Commit: `feat: add market data bar model`.

**Verification:**
- Invalid OHLCV values raise `ValueError` with clear messages.
- Valid bars are immutable or treated as value objects.

### Task 4: Add CSV market data loader

**Objective:** Load OHLCV data from local CSV into normalized `Bar` objects.

**Files:**
- Create: `src/day_trade_maker/data.py`
- Create: `tests/fixtures/sample_bars.csv`
- Create: `tests/test_data.py`

**Steps:**
1. Create a tiny CSV fixture with columns: `timestamp,open,high,low,close,volume`.
2. Write failing tests for `load_bars_from_csv(path, symbol)`.
3. Implement CSV loading with `pandas.read_csv` and conversion to `Bar` objects.
4. Validate required columns and return helpful errors for missing columns.
5. Run: `python -m pytest tests/test_data.py -v`.
6. Commit: `feat: load market bars from csv`.

**Verification:**
- Fixture loads deterministically.
- Missing columns produce a useful exception.
- Output order is timestamp ascending.

### Task 5: Implement indicators module

**Objective:** Provide simple moving average and return calculations for strategies.

**Files:**
- Create: `src/day_trade_maker/indicators.py`
- Create: `tests/test_indicators.py`

**Steps:**
1. Write failing tests for simple moving average over known close prices.
2. Write failing tests for percentage returns.
3. Implement `simple_moving_average(values, window)`.
4. Implement `percentage_returns(values)`.
5. Validate invalid windows, empty input, and insufficient data.
6. Run: `python -m pytest tests/test_indicators.py -v`.
7. Commit: `feat: add basic indicators`.

**Verification:**
- Numeric expectations use exact simple fixtures or `pytest.approx`.
- Edge cases are explicitly tested.

### Task 6: Add strategy interface and baseline strategy

**Objective:** Define strategy contracts and implement a moving-average crossover signal generator.

**Files:**
- Create: `src/day_trade_maker/strategies.py`
- Create: `tests/test_strategies.py`

**Steps:**
1. Define signal values: `BUY`, `SELL`, `HOLD`.
2. Write failing tests for a known price sequence that triggers a BUY crossover.
3. Write failing tests for a SELL crossover.
4. Implement `MovingAverageCrossoverStrategy(short_window, long_window)`.
5. Ensure invalid configuration raises `ValueError` when `short_window >= long_window`.
6. Run: `python -m pytest tests/test_strategies.py -v`.
7. Commit: `feat: add moving average crossover strategy`.

**Verification:**
- Strategy emits deterministic signals for deterministic input.
- Strategy does not know about cash, brokerage, or execution.

### Task 7: Add backtesting engine

**Objective:** Simulate trades from strategy signals over historical bars.

**Files:**
- Create: `src/day_trade_maker/backtest.py`
- Create: `tests/test_backtest.py`

**Steps:**
1. Write failing tests for a simple buy-then-sell sequence.
2. Define minimal domain objects: `Trade`, `BacktestResult`.
3. Implement a single-position long-only simulator.
4. Track starting cash, ending cash, open position, realized PnL, and trade list.
5. Apply simple fees/slippage as configurable numeric values defaulting to zero.
6. Run: `python -m pytest tests/test_backtest.py -v`.
7. Commit: `feat: add long-only backtesting engine`.

**Verification:**
- Cash accounting is tested with exact expected values.
- No short selling or leverage exists unless explicitly added later.
- Repeated BUY while already long is ignored or rejected consistently.

### Task 8: Add risk controls

**Objective:** Prevent unsafe simulated recommendations and encode basic day-trading guardrails.

**Files:**
- Create: `src/day_trade_maker/risk.py`
- Create: `tests/test_risk.py`
- Modify: `src/day_trade_maker/backtest.py`

**Steps:**
1. Write failing tests for max position size.
2. Write failing tests for max daily loss.
3. Write failing tests for no-trade behavior when risk limits are exceeded.
4. Implement `RiskConfig` and `RiskManager`.
5. Wire risk checks into backtest order simulation.
6. Run: `python -m pytest tests/test_risk.py tests/test_backtest.py -v`.
7. Commit: `feat: add simulation risk controls`.

**Verification:**
- Risk limits are enforced before trades are recorded.
- Risk decisions are auditable in result output.

### Task 9: Add reporting output

**Objective:** Generate readable summaries for backtest results.

**Files:**
- Create: `src/day_trade_maker/reporting.py`
- Create: `tests/test_reporting.py`

**Steps:**
1. Write failing tests for a summary dictionary containing key metrics.
2. Include metrics: total trades, win rate, net PnL, return percentage, max drawdown if feasible.
3. Implement `summarize_backtest(result)`.
4. Add a plain-text rendering function for CLI output.
5. Run: `python -m pytest tests/test_reporting.py -v`.
6. Commit: `feat: summarize backtest results`.

**Verification:**
- Summary values are deterministic for fixed fixtures.
- Text output is stable enough for snapshot-style assertions if desired.

### Task 10: Add `dtm backtest` CLI command

**Objective:** Let users run a backtest from a CSV file via CLI.

**Files:**
- Modify: `src/day_trade_maker/cli.py`
- Create: `tests/test_cli_backtest.py`

**Steps:**
1. Write failing CLI test using the sample CSV fixture.
2. Add `dtm backtest --symbol SYMBOL --csv PATH --short-window N --long-window N --cash AMOUNT`.
3. Call the CSV loader, strategy, backtester, and reporter.
4. Ensure output clearly says `SIMULATION ONLY`.
5. Run: `python -m pytest tests/test_cli_backtest.py tests/test_cli.py -v`.
6. Commit: `feat: add backtest cli command`.

**Verification:**
- CLI exits 0 for valid input.
- CLI exits non-zero with clear errors for missing files or invalid windows.
- Output contains no broker/live-trading language.

### Task 11: Add optional market data downloader

**Objective:** Add a convenience command to download historical data, while keeping CSV as the core interface.

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/day_trade_maker/data.py`
- Modify: `src/day_trade_maker/cli.py`
- Create: `tests/test_data_download.py`

**Steps:**
1. Decide whether to use `yfinance` as an optional dependency.
2. Add tests that mock the downloader rather than hitting the network.
3. Implement `download_bars(symbol, start, end, interval)` behind a small adapter function.
4. Add CLI command `dtm download --symbol SYMBOL --start YYYY-MM-DD --end YYYY-MM-DD --out file.csv`.
5. Run tests without network access.
6. Commit: `feat: add optional historical data download`.

**Verification:**
- Unit tests mock all network calls.
- CLI errors clearly if optional dependency is missing.

### Task 12: Add safety and documentation pass

**Objective:** Make project intent, limitations, and safe usage obvious.

**Files:**
- Modify: `README.md`
- Create: `docs/safety.md`
- Create: `docs/architecture.md`

**Steps:**
1. Document setup commands.
2. Document `dtm backtest` examples.
3. Add a clear disclaimer: simulation/research only, no live orders.
4. Document architecture and extension points.
5. Document why live broker integration is out of scope for the initial version.
6. Run full validation.
7. Commit: `docs: add usage and safety documentation`.

**Verification:**
- A new developer can run tests and a sample backtest using README alone.
- Documentation does not imply guaranteed profitability or financial advice.

## Files Likely to Change

- `pyproject.toml`
- `README.md`
- `src/day_trade_maker/__init__.py`
- `src/day_trade_maker/cli.py`
- `src/day_trade_maker/models.py`
- `src/day_trade_maker/data.py`
- `src/day_trade_maker/indicators.py`
- `src/day_trade_maker/strategies.py`
- `src/day_trade_maker/backtest.py`
- `src/day_trade_maker/risk.py`
- `src/day_trade_maker/reporting.py`
- `tests/__init__.py`
- `tests/test_cli.py`
- `tests/test_cli_backtest.py`
- `tests/test_models.py`
- `tests/test_data.py`
- `tests/test_indicators.py`
- `tests/test_strategies.py`
- `tests/test_backtest.py`
- `tests/test_risk.py`
- `tests/test_reporting.py`
- `tests/fixtures/sample_bars.csv`
- `docs/safety.md`
- `docs/architecture.md`

## Tests / Validation

Run these after each task where relevant:

```bash
python -m pytest tests/<target_test_file>.py -v
python -m ruff check .
```

Run these before final handoff:

```bash
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
dtm version
dtm backtest --symbol TEST --csv tests/fixtures/sample_bars.csv --short-window 3 --long-window 5 --cash 10000
```

Expected final state:
- All tests pass.
- Lint and format checks pass.
- CLI can run a deterministic sample backtest.
- README documents setup and safe simulation-only usage.

## Risks, Tradeoffs, and Open Questions

- **Financial safety:** Avoid live trading in the first version. Broker APIs should require a separate plan with explicit user approval.
- **Data quality:** Free market data can be delayed, incomplete, or adjusted. Backtest results must not be treated as production signals.
- **Overfitting:** A moving-average crossover strategy is a baseline for plumbing, not a claim of profitable performance.
- **Day-trading constraints:** Pattern day trader rules, taxes, exchange holidays, partial fills, spreads, and latency are out of scope for the first local simulator.
- **Dependency choice:** `pandas` is practical for time-series work but heavier than pure Python. Acceptable for this project unless the user wants a lightweight dependency footprint.
- **Package manager:** Choose `uv` if available; otherwise use standard `python -m venv` and `pip`.
- **Open question:** Should the app remain CLI-first, or should a web dashboard be planned after the simulator is working?
- **Open question:** Which market/timeframe should initial examples target: equities, crypto, or forex?

## Recommended Next Step

Implement Task 1 only, verify it, then proceed task-by-task. Do not add live brokerage connectivity until the backtester, risk controls, and reporting are complete and tested.
