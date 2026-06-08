# Day Trade Maker

![X](https://img.shields.io/twitter/follow/gcampton)

Day Trade Maker is a local-first research dashboard for turning day-trading YouTube transcripts into structured, testable strategy ideas.

The first milestones are research, charting, backtesting, and Interactive Brokers paper-trading support. Live trading is intentionally out of scope until the strategy compiler, backtesting, risk controls, approvals, and audit trail are proven.

## Planned stack

- Backend: Python, FastAPI, SQLite/PostgreSQL-compatible persistence
- Frontend: React, TypeScript, Vite
- Charts: KLineCharts Pro first for the main workspace, with an adapter boundary for TradingView Lightweight Charts later
- Broker: Interactive Brokers Gateway/TWS, paper/read-only first

## Safety stance

AI-generated strategies are hypotheses, not financial advice. The app must validate, backtest, risk-check, and require explicit approval before any broker order workflow.

IBKR paper-account order submission is disabled by default and remains separate from audit-only order intents. When enabled, it requires a matching configured `DU...` paper account id, a loaded read-only account snapshot, exact confirmation phrase, approved strategy, passed risk check, and live-trading-disabled capability snapshot.

See `docs/ibkr-paper-order-submission.md` for the manual paper-account smoke flow and emergency disable steps.
