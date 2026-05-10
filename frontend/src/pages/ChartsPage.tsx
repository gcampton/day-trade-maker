import { FormEvent, useState } from 'react';

import {
  createPaperOrderIntent,
  exportAuditSnapshot,
  getBrokerCapabilities,
  getBrokerStatus,
  getMarketDataCandles,
  getPaperOrderIntents,
  importAuditSnapshot,
  importMarketDataCsv,
  runBacktest,
  runRiskCheck,
  type AuditImportSummary,
  type AuditSnapshot,
  type BacktestRun,
  type BrokerCapabilities,
  type BrokerStatus,
  type MarketDataDatasetSummary,
  type PaperOrderIntent,
  type RiskCheckRun,
  type StrategyCandidate,
} from '../api/client';
import { KLineStrategyChart } from '../charts/KLineStrategyChart';
import type { Candle, StrategyMarker } from '../charts/types';

const sampleCandles: Candle[] = [
  { timestamp: 1, open: 100, high: 101.2, low: 99.7, close: 100.8, volume: 120000 },
  { timestamp: 2, open: 100.8, high: 102.4, low: 100.6, close: 102.1, volume: 180000 },
  { timestamp: 3, open: 102.1, high: 103.8, low: 101.9, close: 103.5, volume: 240000 },
  { timestamp: 4, open: 103.5, high: 103.9, low: 102.2, close: 102.6, volume: 210000 },
  { timestamp: 5, open: 102.6, high: 104.6, low: 102.5, close: 104.2, volume: 310000 },
];

const sampleMarkers: StrategyMarker[] = [
  { timestamp: 3, price: 103.5, side: 'buy', label: 'Buy breakout' },
  { timestamp: 4, price: 102.2, side: 'exit', label: 'Exit risk' },
];

const exampleCsv = `timestamp,open,high,low,close,volume
2026-05-10T14:30:00Z,100,101.5,99.5,101,150000
2026-05-10T14:35:00Z,101,103,100.5,102,200000
`;

type ChartsPageProps = {
  selectedStrategy: StrategyCandidate | null;
};

export function ChartsPage({ selectedStrategy }: ChartsPageProps) {
  const [symbol, setSymbol] = useState('AAPL');
  const [timeframe, setTimeframe] = useState('5m');
  const [csvText, setCsvText] = useState(exampleCsv);
  const [candles, setCandles] = useState<Candle[]>(sampleCandles);
  const [dataset, setDataset] = useState<MarketDataDatasetSummary | null>(null);
  const [backtestRun, setBacktestRun] = useState<BacktestRun | null>(null);
  const [riskCheck, setRiskCheck] = useState<RiskCheckRun | null>(null);
  const [brokerStatus, setBrokerStatus] = useState<BrokerStatus | null>(null);
  const [brokerCapabilities, setBrokerCapabilities] = useState<BrokerCapabilities | null>(null);
  const [orderIntent, setOrderIntent] = useState<PaperOrderIntent | null>(null);
  const [orderIntentHistory, setOrderIntentHistory] = useState<PaperOrderIntent[]>([]);
  const [auditSnapshotJson, setAuditSnapshotJson] = useState('');
  const [auditMessage, setAuditMessage] = useState<string | null>(null);
  const [orderSymbol, setOrderSymbol] = useState('AAPL');
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [orderQuantity, setOrderQuantity] = useState('10');
  const [error, setError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isRunningBacktest, setIsRunningBacktest] = useState(false);
  const [isRunningRiskCheck, setIsRunningRiskCheck] = useState(false);
  const [isLoadingBrokerStatus, setIsLoadingBrokerStatus] = useState(false);
  const [isCreatingOrderIntent, setIsCreatingOrderIntent] = useState(false);
  const [isExportingAudit, setIsExportingAudit] = useState(false);
  const [isImportingAudit, setIsImportingAudit] = useState(false);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsImporting(true);

    try {
      const imported = await importMarketDataCsv({ symbol, timeframe, csv_text: csvText });
      const loadedCandles = await getMarketDataCandles(imported.id);
      setDataset(imported);
      setBacktestRun(null);
      setRiskCheck(null);
      setOrderIntent(null);
      setOrderIntentHistory([]);
      setCandles(
        loadedCandles.map((candle) => ({
          ...candle,
          timestamp: Date.parse(candle.timestamp),
        })),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import market data');
    } finally {
      setIsImporting(false);
    }
  }

  async function handleBacktest() {
    if (!selectedStrategy || !dataset) {
      return;
    }

    setError(null);
    setIsRunningBacktest(true);

    try {
      const created = await runBacktest({
        strategy_id: selectedStrategy.id,
        dataset_id: dataset.id,
        starting_cash: 10000,
      });
      setBacktestRun(created);
      setRiskCheck(null);
      setOrderIntent(null);
      setOrderIntentHistory([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run backtest');
    } finally {
      setIsRunningBacktest(false);
    }
  }

  async function handleRiskCheck() {
    if (!selectedStrategy || !backtestRun) {
      return;
    }

    setError(null);
    setIsRunningRiskCheck(true);

    try {
      const created = await runRiskCheck({
        strategy_id: selectedStrategy.id,
        backtest_id: backtestRun.id,
        paper_mode: true,
        max_risk_percent: 1,
      });
      setRiskCheck(created);
      setOrderIntent(null);
      setOrderIntentHistory([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run broker readiness check');
    } finally {
      setIsRunningRiskCheck(false);
    }
  }

  async function handleBrokerStatus() {
    setError(null);
    setIsLoadingBrokerStatus(true);

    try {
      const [statusSnapshot, capabilitiesSnapshot] = await Promise.all([
        getBrokerStatus(),
        getBrokerCapabilities(),
      ]);
      setBrokerStatus(statusSnapshot);
      setBrokerCapabilities(capabilitiesSnapshot);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load IBKR broker status');
    } finally {
      setIsLoadingBrokerStatus(false);
    }
  }

  async function handleCreateOrderIntent() {
    const quantity = Number(orderQuantity);
    if (
      !selectedStrategy ||
      !riskCheck ||
      riskCheck.status !== 'passed' ||
      !orderSymbol.trim() ||
      !Number.isInteger(quantity) ||
      quantity <= 0
    ) {
      return;
    }

    setError(null);
    setIsCreatingOrderIntent(true);

    try {
      const created = await createPaperOrderIntent({
        strategy_id: selectedStrategy.id,
        risk_check_id: riskCheck.id,
        symbol: orderSymbol,
        side: orderSide,
        quantity,
        order_type: 'market',
        paper_mode: true,
        user_confirmed: true,
      });
      setOrderIntent(created);
      setOrderIntentHistory(await getPaperOrderIntents());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record paper order intent');
    } finally {
      setIsCreatingOrderIntent(false);
    }
  }

  async function handleExportAuditSnapshot() {
    setError(null);
    setAuditMessage(null);
    setIsExportingAudit(true);

    try {
      const snapshot = await exportAuditSnapshot();
      setAuditSnapshotJson(JSON.stringify(snapshot, null, 2));
      setAuditMessage(formatAuditSnapshotMessage('Exported', snapshot));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export audit snapshot');
    } finally {
      setIsExportingAudit(false);
    }
  }

  async function handleImportAuditSnapshot() {
    setError(null);
    setAuditMessage(null);
    setIsImportingAudit(true);

    try {
      const snapshot = JSON.parse(auditSnapshotJson) as AuditSnapshot;
      const summary = await importAuditSnapshot(snapshot);
      setAuditMessage(formatAuditImportSummary(summary));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import audit snapshot');
    } finally {
      setIsImportingAudit(false);
    }
  }

  const backtestMarkers: StrategyMarker[] = backtestRun
    ? backtestRun.result.markers.map((marker) => ({
        ...marker,
        timestamp: Date.parse(marker.timestamp),
      }))
    : sampleMarkers;
  const parsedOrderQuantity = Number(orderQuantity);
  const isOrderTicketValid = orderSymbol.trim().length > 0 && Number.isInteger(parsedOrderQuantity) && parsedOrderQuantity > 0;

  return (
    <section className="chart-workspace-grid" aria-label="Market data chart workspace">
      <form className="market-data-form" onSubmit={handleImport}>
        <div className="form-heading">
          <p className="eyebrow">Market Data</p>
          <h2>Import OHLCV CSV</h2>
          <p>Paste candle data to feed the chart workspace before IBKR market data is wired in.</p>
        </div>

        <div className="form-row">
          <label>
            Market symbol
            <input value={symbol} onChange={(event) => setSymbol(event.target.value)} required />
          </label>
          <label>
            Market timeframe
            <input value={timeframe} onChange={(event) => setTimeframe(event.target.value)} required />
          </label>
        </div>

        <label>
          OHLCV CSV
          <textarea
            rows={7}
            value={csvText}
            onChange={(event) => setCsvText(event.target.value)}
            required
          />
        </label>

        <button type="submit" disabled={isImporting}>
          {isImporting ? 'Importing…' : 'Import candles'}
        </button>

        {dataset ? (
          <p className="success">
            Imported {dataset.symbol} {dataset.timeframe} dataset with {dataset.candle_count} candles
          </p>
        ) : null}
        {error ? <p className="error">{error}</p> : null}
      </form>

      <section className="market-data-form" aria-label="Audit snapshot controls">
        <div className="form-heading">
          <p className="eyebrow">Audit Archive</p>
          <h2>Export/import local audit snapshot</h2>
          <p>
            Copy this JSON to save transcripts, strategies, datasets, backtests, risk checks, and
            paper order intents before a real database is wired in.
          </p>
        </div>

        <div className="form-row">
          <button type="button" disabled={isExportingAudit} onClick={handleExportAuditSnapshot}>
            {isExportingAudit ? 'Exporting audit snapshot…' : 'Export audit snapshot'}
          </button>
          <button
            type="button"
            disabled={isImportingAudit || auditSnapshotJson.trim().length === 0}
            onClick={handleImportAuditSnapshot}
          >
            {isImportingAudit ? 'Importing audit snapshot…' : 'Import audit snapshot'}
          </button>
        </div>

        <label>
          Audit snapshot JSON
          <textarea
            rows={8}
            value={auditSnapshotJson}
            onChange={(event) => setAuditSnapshotJson(event.target.value)}
            placeholder="Export a snapshot or paste saved audit JSON here."
          />
        </label>

        {auditMessage ? <p className="success">{auditMessage}</p> : null}
      </section>

      <section className="chart-stack">
        <section className="backtest-panel" aria-label="Backtest controls">
          <div className="form-heading">
            <p className="eyebrow">Backtesting</p>
            <h2>Run extracted strategy</h2>
            <p>
              Uses the selected structured strategy and imported candle dataset. Starting cash is
              fixed at $10,000 for this first safe research slice.
            </p>
          </div>

          <button
            type="button"
            disabled={!selectedStrategy || !dataset || isRunningBacktest}
            onClick={handleBacktest}
          >
            {isRunningBacktest ? 'Running backtest…' : 'Run backtest'}
          </button>

          {!selectedStrategy ? <p className="muted">Extract a strategy candidate first.</p> : null}
          {!dataset ? <p className="muted">Import market data before running a backtest.</p> : null}

          {backtestRun ? (
            <dl className="backtest-summary">
              <div>
                <dt>Backtest net PnL</dt>
                <dd>{formatUsd(backtestRun.result.net_pnl)}</dd>
              </div>
              <div>
                <dt>Trades</dt>
                <dd>{backtestRun.result.total_trades} trade</dd>
              </div>
              <div>
                <dt>Win rate</dt>
                <dd>{Math.round(backtestRun.result.win_rate * 100)}%</dd>
              </div>
            </dl>
          ) : null}
        </section>

        <section className="backtest-panel" aria-label="Broker readiness controls">
          <div className="form-heading">
            <p className="eyebrow">IBKR Safety Gate</p>
            <h2>Broker readiness</h2>
            <p>
              Paper mode is required. This only checks readiness for future broker workflows; it
              does not place orders.
            </p>
          </div>

          <button
            type="button"
            disabled={isLoadingBrokerStatus}
            onClick={handleBrokerStatus}
          >
            {isLoadingBrokerStatus ? 'Checking IBKR status…' : 'Check IBKR status'}
          </button>

          {brokerStatus ? (
            <dl className="backtest-summary">
              <div>
                <dt>Broker</dt>
                <dd>Interactive Brokers</dd>
              </div>
              <div>
                <dt>Mode</dt>
                <dd>Paper mode</dd>
              </div>
              <div>
                <dt>Access</dt>
                <dd>{brokerStatus.read_only ? 'Read-only' : 'Writable'}</dd>
              </div>
              <div>
                <dt>Orders</dt>
                <dd>
                  {brokerStatus.order_submission_enabled
                    ? 'Order submission enabled'
                    : 'Order submission disabled'}
                </dd>
              </div>
            </dl>
          ) : null}

          {brokerCapabilities ? (
            <dl className="backtest-summary">
              <div>
                <dt>Execution mode</dt>
                <dd>Audit-only order intents</dd>
              </div>
              <div>
                <dt>Paper broker submission</dt>
                <dd>
                  {brokerCapabilities.supports_paper_broker_submission
                    ? 'Paper broker submission enabled'
                    : 'Paper broker submission disabled'}
                </dd>
              </div>
              <div>
                <dt>Live broker submission</dt>
                <dd>
                  {brokerCapabilities.supports_live_broker_submission
                    ? 'Live broker submission enabled'
                    : 'Live broker submission disabled'}
                </dd>
              </div>
              <div>
                <dt>Capability note</dt>
                <dd>{brokerCapabilities.message}</dd>
              </div>
            </dl>
          ) : null}

          <button
            type="button"
            disabled={!selectedStrategy || !backtestRun || isRunningRiskCheck}
            onClick={handleRiskCheck}
          >
            {isRunningRiskCheck ? 'Checking readiness…' : 'Run broker readiness check'}
          </button>

          {!backtestRun ? <p className="muted">Run a backtest before broker readiness.</p> : null}

          {riskCheck ? (
            <div className={riskCheck.status === 'passed' ? 'success' : 'error'}>
              <p>Broker readiness {riskCheck.status}</p>
              <ul>
                {(riskCheck.status === 'passed' ? riskCheck.checks : riskCheck.failures).map(
                  (item) => (
                    <li key={item}>{item}</li>
                  ),
                )}
              </ul>
            </div>
          ) : null}

          <div className="form-row">
            <label>
              Order symbol
              <input
                value={orderSymbol}
                onChange={(event) => setOrderSymbol(event.target.value.toUpperCase())}
                required
              />
            </label>
            <label>
              Order side
              <select
                value={orderSide}
                onChange={(event) => setOrderSide(event.target.value as 'buy' | 'sell')}
              >
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </label>
            <label>
              Order quantity
              <input
                type="number"
                min="1"
                step="1"
                value={orderQuantity}
                onChange={(event) => setOrderQuantity(event.target.value)}
                required
              />
            </label>
          </div>

          <button
            type="button"
            disabled={riskCheck?.status !== 'passed' || !isOrderTicketValid || isCreatingOrderIntent}
            onClick={handleCreateOrderIntent}
          >
            {isCreatingOrderIntent ? 'Recording paper order intent…' : 'Record paper order intent'}
          </button>
          <p className="muted">
            This records an explicit paper-mode order intent for audit only; it does not submit to
            IBKR.
          </p>

          {orderIntent ? (
            <div className="success">
              <p>Paper order intent recorded</p>
              <dl className="backtest-summary">
                <div>
                  <dt>Status</dt>
                  <dd>{orderIntent.status}</dd>
                </div>
                <div>
                  <dt>Quantity</dt>
                  <dd>
                    {orderIntent.quantity} {orderIntent.symbol}
                  </dd>
                </div>
                <div>
                  <dt>Broker submission</dt>
                  <dd>{orderIntent.submitted_to_broker ? 'Submitted' : 'No IBKR order was submitted'}</dd>
                </div>
              </dl>
            </div>
          ) : null}

          {orderIntentHistory.length > 0 ? (
            <section aria-label="Paper order intent audit log">
              <h3>Paper order intent audit log</h3>
              <ul>
                {orderIntentHistory.map((intent) => (
                  <li key={intent.id}>
                    {intent.symbol} {intent.side} {intent.quantity} — {intent.status}; no IBKR order
                    was submitted
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </section>

        <KLineStrategyChart candles={candles} markers={backtestMarkers} />
      </section>
    </section>
  );
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatAuditSnapshotMessage(action: string, snapshot: AuditSnapshot): string {
  return `${action} audit snapshot with ${snapshot.transcripts.length} transcript and ${snapshot.paper_order_intents.length} order intent`;
}

function formatAuditImportSummary(summary: AuditImportSummary): string {
  return `Imported audit snapshot with ${summary.transcript_count} transcript and ${summary.paper_order_intent_count} order intent`;
}
