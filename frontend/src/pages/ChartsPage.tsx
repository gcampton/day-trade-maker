import { FormEvent, useEffect, useState } from 'react';

import {
  createPaperBrokerOrderSubmission,
  createPaperOrderIntent,
  exportAuditSnapshot,
  getAuditPersistenceStatus,
  getBrokerSafetySummary,
  getMarketDataCandles,
  getPaperBrokerOrderSubmissions,
  getPaperOrderIntents,
  importAuditSnapshot,
  importMarketDataCsv,
  refreshPaperBrokerOrderSubmissionStatus,
  resetAuditState,
  runBacktest,
  runRiskCheck,
  type AuditImportSummary,
  type AuditPersistenceStatus,
  type AuditSnapshot,
  type BacktestRun,
  type BrokerAccountSnapshot,
  type BrokerCapabilities,
  type BrokerConnectivityProbe,
  type BrokerOrderSubmissionCapability,
  type BrokerSafetySummary,
  type BrokerStatus,
  type MarketDataDatasetSummary,
  type PaperBrokerOrderSubmission,
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

const paperBrokerSubmissionConfirmationPhrase = 'SUBMIT IBKR PAPER ORDER';

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
  const [brokerSafetySummary, setBrokerSafetySummary] = useState<BrokerSafetySummary | null>(null);
  const [brokerStatus, setBrokerStatus] = useState<BrokerStatus | null>(null);
  const [brokerCapabilities, setBrokerCapabilities] = useState<BrokerCapabilities | null>(null);
  const [brokerOrderSubmissionCapability, setBrokerOrderSubmissionCapability] =
    useState<BrokerOrderSubmissionCapability | null>(null);
  const [brokerAccount, setBrokerAccount] = useState<BrokerAccountSnapshot | null>(null);
  const [brokerConnectivityProbe, setBrokerConnectivityProbe] = useState<BrokerConnectivityProbe | null>(null);
  const [orderIntent, setOrderIntent] = useState<PaperOrderIntent | null>(null);
  const [orderIntentHistory, setOrderIntentHistory] = useState<PaperOrderIntent[]>([]);
  const [paperBrokerSubmission, setPaperBrokerSubmission] = useState<PaperBrokerOrderSubmission | null>(null);
  const [paperBrokerSubmissionHistory, setPaperBrokerSubmissionHistory] = useState<PaperBrokerOrderSubmission[]>([]);
  const [paperSubmissionConfirmationPhrase, setPaperSubmissionConfirmationPhrase] = useState('');
  const [brokerSideEffectAdminToken, setBrokerSideEffectAdminToken] = useState('');
  const [brokerSideEffectCsrfToken, setBrokerSideEffectCsrfToken] = useState('');
  const [auditSnapshotJson, setAuditSnapshotJson] = useState('');
  const [auditMessage, setAuditMessage] = useState<string | null>(null);
  const [auditPersistenceStatus, setAuditPersistenceStatus] = useState<AuditPersistenceStatus | null>(null);
  const [resetConfirmation, setResetConfirmation] = useState('');
  const [orderSymbol, setOrderSymbol] = useState('AAPL');
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [orderQuantity, setOrderQuantity] = useState('10');
  const [error, setError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isRunningBacktest, setIsRunningBacktest] = useState(false);
  const [isRunningRiskCheck, setIsRunningRiskCheck] = useState(false);
  const [isLoadingBrokerStatus, setIsLoadingBrokerStatus] = useState(false);
  const [isCreatingOrderIntent, setIsCreatingOrderIntent] = useState(false);
  const [isSubmittingPaperBrokerOrder, setIsSubmittingPaperBrokerOrder] = useState(false);
  const [isRefreshingPaperBrokerOrderStatus, setIsRefreshingPaperBrokerOrderStatus] = useState(false);
  const [isExportingAudit, setIsExportingAudit] = useState(false);
  const [isImportingAudit, setIsImportingAudit] = useState(false);
  const [isResettingAudit, setIsResettingAudit] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function restoreWorkflowState() {
      try {
        const [snapshot, status] = await Promise.all([
          exportAuditSnapshot(),
          getAuditPersistenceStatus(),
        ]);
        if (!isMounted) {
          return;
        }
        applyAuditSnapshotToWorkspace(snapshot);
        setAuditPersistenceStatus(status);
      } catch {
        // Startup restore is best-effort so the chart workspace still works before API startup.
      }
    }

    void restoreWorkflowState();

    return () => {
      isMounted = false;
    };
  }, []);

  function applyAuditSnapshotToWorkspace(snapshot: AuditSnapshot) {
    const latestDataset = snapshot.market_data.at(-1);
    if (latestDataset) {
      setDataset(latestDataset);
      setSymbol(latestDataset.symbol);
      setTimeframe(latestDataset.timeframe);
      setCandles(
        latestDataset.candles.map((candle) => ({
          ...candle,
          timestamp: Date.parse(candle.timestamp),
        })),
      );
    }

    const latestBacktest = snapshot.backtests.at(-1);
    if (latestBacktest) {
      setBacktestRun(latestBacktest);
    }

    const latestRiskCheck = snapshot.risk_checks.at(-1);
    if (latestRiskCheck) {
      setRiskCheck(latestRiskCheck);
    }

    setOrderIntentHistory(snapshot.paper_order_intents);
    setPaperBrokerSubmissionHistory(snapshot.paper_broker_order_submissions);
    setPaperBrokerSubmission(snapshot.paper_broker_order_submissions.at(-1) ?? null);
    const latestOrderIntent = snapshot.paper_order_intents.at(-1);
    if (latestOrderIntent) {
      setOrderIntent(latestOrderIntent);
      setOrderSymbol(latestOrderIntent.symbol);
      setOrderSide(latestOrderIntent.side);
      setOrderQuantity(String(latestOrderIntent.quantity));
    }
  }

  function clearAuditWorkspace() {
    setDataset(null);
    setBacktestRun(null);
    setRiskCheck(null);
    setOrderIntent(null);
    setOrderIntentHistory([]);
    setPaperBrokerSubmission(null);
    setPaperBrokerSubmissionHistory([]);
    setPaperSubmissionConfirmationPhrase('');
    setAuditSnapshotJson('');
    setCandles(sampleCandles);
    setSymbol('AAPL');
    setTimeframe('5m');
    setOrderSymbol('AAPL');
    setOrderSide('buy');
    setOrderQuantity('10');
  }

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
      setPaperBrokerSubmission(null);
      setPaperBrokerSubmissionHistory([]);
      setPaperSubmissionConfirmationPhrase('');
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
      setPaperBrokerSubmission(null);
      setPaperBrokerSubmissionHistory([]);
      setPaperSubmissionConfirmationPhrase('');
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
      setPaperBrokerSubmission(null);
      setPaperBrokerSubmissionHistory([]);
      setPaperSubmissionConfirmationPhrase('');
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
      const summary = await getBrokerSafetySummary();
      setBrokerSafetySummary(summary);
      setBrokerStatus(summary.status);
      setBrokerCapabilities(summary.capabilities);
      setBrokerAccount(summary.account);
      setBrokerConnectivityProbe(summary.connectivity_probe);
      setBrokerOrderSubmissionCapability(summary.order_submission_capability);
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
      setPaperBrokerSubmission(null);
      setPaperSubmissionConfirmationPhrase('');
      setOrderIntentHistory(await getPaperOrderIntents());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record paper order intent');
    } finally {
      setIsCreatingOrderIntent(false);
    }
  }

  async function handleSubmitPaperBrokerOrder() {
    if (!orderIntent || paperSubmissionConfirmationPhrase !== paperBrokerSubmissionConfirmationPhrase) {
      return;
    }

    setError(null);
    setIsSubmittingPaperBrokerOrder(true);

    try {
      const created = await createPaperBrokerOrderSubmission(
        {
          order_intent_id: orderIntent.id,
          user_confirmed: true,
          confirmation_phrase: paperSubmissionConfirmationPhrase,
        },
        {
          adminToken: brokerSideEffectAdminToken || undefined,
          csrfToken: brokerSideEffectCsrfToken || undefined,
        },
      );
      setPaperBrokerSubmission(created);
      setPaperBrokerSubmissionHistory(await getPaperBrokerOrderSubmissions());
      setPaperSubmissionConfirmationPhrase('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit to IBKR paper account');
    } finally {
      setIsSubmittingPaperBrokerOrder(false);
    }
  }

  async function handleRefreshPaperBrokerOrderStatus(submission: PaperBrokerOrderSubmission) {
    if (!submission.submitted_to_broker || !submission.broker_order_id) {
      return;
    }

    setError(null);
    setIsRefreshingPaperBrokerOrderStatus(true);

    try {
      const refreshed = await refreshPaperBrokerOrderSubmissionStatus(submission.id, {
        adminToken: brokerSideEffectAdminToken || undefined,
        csrfToken: brokerSideEffectCsrfToken || undefined,
      });
      setPaperBrokerSubmission(refreshed);
      setPaperBrokerSubmissionHistory((current) => {
        if (current.some((item) => item.id === refreshed.id)) {
          return current.map((item) => (item.id === refreshed.id ? refreshed : item));
        }
        return [...current, refreshed];
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh IBKR paper order status');
    } finally {
      setIsRefreshingPaperBrokerOrderStatus(false);
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
      applyAuditSnapshotToWorkspace(snapshot);
      setAuditMessage(formatAuditImportSummary(summary));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import audit snapshot');
    } finally {
      setIsImportingAudit(false);
    }
  }

  async function handleResetAuditState() {
    setError(null);
    setAuditMessage(null);
    setIsResettingAudit(true);

    try {
      const summary = await resetAuditState(resetConfirmation);
      clearAuditWorkspace();
      setResetConfirmation('');
      setAuditPersistenceStatus((current) =>
        current
          ? {
              ...current,
              transcript_count: 0,
              strategy_count: 0,
              market_data_count: 0,
              backtest_count: 0,
              risk_check_count: 0,
              paper_order_intent_count: 0,
              paper_broker_order_submission_count: 0,
            }
          : current,
      );
      setAuditMessage(formatAuditResetSummary(summary));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset local audit state');
    } finally {
      setIsResettingAudit(false);
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
  const canResetAuditState = resetConfirmation === 'RESET LOCAL AUDIT STATE';
  const currentIntentPaperBrokerSubmission = orderIntent
    ? (paperBrokerSubmissionHistory.find((submission) => submission.order_intent_id === orderIntent.id) ?? paperBrokerSubmission)
    : null;
  const isPaperBrokerSubmissionEnabled = Boolean(
    brokerOrderSubmissionCapability?.paper_broker_submission_enabled &&
      brokerOrderSubmissionCapability.broker_order_operation_available &&
      !brokerOrderSubmissionCapability.live_broker_submission_enabled,
  );
  const canSubmitPaperBrokerOrder = Boolean(
    orderIntent &&
      isPaperBrokerSubmissionEnabled &&
      !currentIntentPaperBrokerSubmission &&
      paperSubmissionConfirmationPhrase === paperBrokerSubmissionConfirmationPhrase &&
      !isSubmittingPaperBrokerOrder,
  );

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
            Copy this JSON to save transcripts, strategies, datasets, backtests, risk checks,
            audit-only paper order intents, and IBKR paper broker submission records.
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

        {auditPersistenceStatus ? (
          <dl className="backtest-summary" aria-label="Local audit persistence status">
            <div>
              <dt>Local audit persistence</dt>
              <dd>{auditPersistenceStatus.provider}</dd>
            </div>
            <div>
              <dt>SQLite path</dt>
              <dd>{auditPersistenceStatus.db_path}</dd>
            </div>
            <div>
              <dt>Saved artifacts</dt>
              <dd>
                {auditPersistenceStatus.transcript_count} transcript;{' '}
                {auditPersistenceStatus.paper_order_intent_count} order intent;{' '}
                {auditPersistenceStatus.paper_broker_order_submission_count} paper broker submission
              </dd>
            </div>
          </dl>
        ) : null}

        <div className="form-heading">
          <h3>Reset local audit state</h3>
          <p>
            This clears persisted local transcripts, strategies, datasets, backtests, risk checks,
            audit-only paper order intents, and IBKR paper broker submission records. It does not
            touch broker accounts or submit/cancel IBKR orders.
          </p>
        </div>
        <label>
          Type RESET LOCAL AUDIT STATE to confirm
          <input
            value={resetConfirmation}
            onChange={(event) => setResetConfirmation(event.target.value)}
            placeholder="RESET LOCAL AUDIT STATE"
          />
        </label>
        <button
          type="button"
          disabled={!canResetAuditState || isResettingAudit}
          onClick={handleResetAuditState}
        >
          {isResettingAudit ? 'Resetting local audit state…' : 'Reset local audit state'}
        </button>
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

          {brokerSafetySummary ? (
            <dl className="backtest-summary" aria-label="Broker safety summary">
              <div>
                <dt>Broker safety summary</dt>
                <dd>Interactive Brokers paper, audit-only</dd>
              </div>
              <div>
                <dt>Primary order boundary</dt>
                <dd>
                  {brokerSafetySummary.order_submission_enabled
                    ? 'Order submission enabled by at least one broker boundary'
                    : 'Order submission disabled across status, account, connectivity, and broker order capability'}
                </dd>
              </div>
              <div>
                <dt>Account readiness</dt>
                <dd>
                  Account data loaded: {brokerSafetySummary.account_data_loaded ? 'yes' : 'no'} via{' '}
                  {brokerSafetySummary.account_reader} reader
                </dd>
              </div>
              <div>
                <dt>Connectivity readiness</dt>
                <dd>
                  Probe {brokerSafetySummary.connectivity_probe_status}; attempted:{' '}
                  {brokerSafetySummary.connectivity_probe_attempted ? 'yes' : 'no'}
                </dd>
              </div>
              <div>
                <dt>Broker order operations</dt>
                <dd>
                  {brokerSafetySummary.broker_order_operation_available
                    ? 'Broker order operation available in safety summary'
                    : 'Broker order operation unavailable in safety summary'}
                </dd>
              </div>
              <div>
                <dt>Safety summary note</dt>
                <dd>{brokerSafetySummary.message}</dd>
              </div>
            </dl>
          ) : null}

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
              <div>
                <dt>Configured IBKR gateway</dt>
                <dd>
                  {brokerStatus.configured_host}:{brokerStatus.configured_port}
                </dd>
              </div>
              <div>
                <dt>Client ID</dt>
                <dd>{brokerStatus.configured_client_id}</dd>
              </div>
              <div>
                <dt>Connection diagnostic</dt>
                <dd>{brokerStatus.connection_diagnostic}</dd>
              </div>
            </dl>
          ) : null}

          {brokerAccount ? (
            <dl className="backtest-summary" aria-label="Broker account snapshot">
              <div>
                <dt>Account snapshot</dt>
                <dd>{brokerAccount.account_id ?? 'Read-only empty until connected'}</dd>
              </div>
              <div>
                <dt>Account snapshot enabled</dt>
                <dd>Account snapshot enabled: {brokerAccount.account_snapshot_enabled ? 'yes' : 'no'}</dd>
              </div>
              <div>
                <dt>Account data loaded</dt>
                <dd>Account data loaded: {brokerAccount.account_data_loaded ? 'yes' : 'no'}</dd>
              </div>
              <div>
                <dt>Account reader</dt>
                <dd>Account reader: {brokerAccount.account_reader}</dd>
              </div>
              <div>
                <dt>IBKR dependency</dt>
                <dd>
                  IBKR dependency available: {brokerAccount.ibkr_client_dependency_available ? 'yes' : 'no'}
                </dd>
              </div>
              <div>
                <dt>Balances</dt>
                <dd>{brokerAccount.balances.length} balances</dd>
              </div>
              <div>
                <dt>Positions</dt>
                <dd>{brokerAccount.positions.length} positions</dd>
              </div>
              <div>
                <dt>Account orders</dt>
                <dd>
                  {brokerAccount.order_submission_enabled
                    ? 'Order submission enabled'
                    : 'Order submission disabled'}
                </dd>
              </div>
              <div>
                <dt>Account note</dt>
                <dd>{brokerAccount.message}</dd>
              </div>
            </dl>
          ) : null}

          {brokerConnectivityProbe ? (
            <dl className="backtest-summary" aria-label="IBKR connectivity probe">
              <div>
                <dt>Connectivity probe</dt>
                <dd>Probe {brokerConnectivityProbe.probe_status}</dd>
              </div>
              <div>
                <dt>Probe target</dt>
                <dd>
                  {brokerConnectivityProbe.host}:{brokerConnectivityProbe.port}
                </dd>
              </div>
              <div>
                <dt>Probe enabled</dt>
                <dd>Probe enabled: {brokerConnectivityProbe.probe_enabled ? 'yes' : 'no'}</dd>
              </div>
              <div>
                <dt>Probe attempted</dt>
                <dd>Probe attempted: {brokerConnectivityProbe.probe_attempted ? 'yes' : 'no'}</dd>
              </div>
              <div>
                <dt>Probe timeout</dt>
                <dd>Probe timeout: {brokerConnectivityProbe.timeout_seconds}s</dd>
              </div>
              <div>
                <dt>Account data</dt>
                <dd>Account data loaded: {brokerConnectivityProbe.account_data_loaded ? 'yes' : 'no'}</dd>
              </div>
              <div>
                <dt>Probe orders</dt>
                <dd>
                  {brokerConnectivityProbe.order_submission_enabled
                    ? 'Order submission enabled'
                    : 'Order submission disabled'}
                </dd>
              </div>
              <div>
                <dt>Probe note</dt>
                <dd>{brokerConnectivityProbe.message}</dd>
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

          {brokerOrderSubmissionCapability ? (
            <dl className="backtest-summary" aria-label="Broker order submission capability">
              <div>
                <dt>Paper order submission implementation</dt>
                <dd>
                  {brokerOrderSubmissionCapability.paper_broker_submission_implemented
                    ? 'IBKR paper order submission implemented'
                    : 'IBKR paper order submission not implemented'}
                </dd>
              </div>
              <div>
                <dt>Paper order submission enabled</dt>
                <dd>
                  {brokerOrderSubmissionCapability.paper_broker_submission_enabled
                    ? 'IBKR paper order submission enabled'
                    : 'IBKR paper order submission disabled'}
                </dd>
              </div>
              <div>
                <dt>Live order submission enabled</dt>
                <dd>
                  {brokerOrderSubmissionCapability.live_broker_submission_enabled
                    ? 'IBKR live order submission enabled'
                    : 'IBKR live order submission disabled'}
                </dd>
              </div>
              <div>
                <dt>Broker order operations</dt>
                <dd>
                  {brokerOrderSubmissionCapability.broker_order_operation_available
                    ? 'Broker order operation available'
                    : 'Broker order operation unavailable'}
                </dd>
              </div>
              <div>
                <dt>Order submission note</dt>
                <dd>{brokerOrderSubmissionCapability.message}</dd>
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
                <div>
                  <dt>Order intent execution mode</dt>
                  <dd>Audit-only at recording</dd>
                </div>
                <div>
                  <dt>Intent paper submission</dt>
                  <dd>
                    {orderIntent.paper_broker_submission_enabled
                      ? 'IBKR paper submission enabled at recording'
                      : 'IBKR paper submission disabled at recording'}
                  </dd>
                </div>
                <div>
                  <dt>Intent broker operation</dt>
                  <dd>
                    {orderIntent.broker_order_operation_available
                      ? 'Broker order operation available at recording'
                      : 'Broker order operation unavailable at recording'}
                  </dd>
                </div>
                <div>
                  <dt>Intent capability note</dt>
                  <dd>{orderIntent.broker_submission_capability_message}</dd>
                </div>
              </dl>
            </div>
          ) : null}

          {orderIntent ? (
            <section className="backtest-panel" aria-label="IBKR paper broker submission">
              <div className="form-heading">
                <p className="eyebrow">IBKR Paper Account Submission</p>
                <h3>Submit audit intent to IBKR paper account</h3>
                <p>This order intent is an audit artifact only; no broker order was submitted.</p>
              </div>

              <div className="form-heading">
                <h4>Protected deployment authorization</h4>
                <p>
                  Leave blank for trusted local development. If backend side-effect auth is enabled,
                  provide both tokens before submitting or refreshing an IBKR paper order.
                </p>
              </div>
              <div className="form-row">
                <label>
                  Broker side-effect admin token
                  <input
                    type="password"
                    value={brokerSideEffectAdminToken}
                    onChange={(event) => setBrokerSideEffectAdminToken(event.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label>
                  Broker side-effect CSRF token
                  <input
                    type="password"
                    value={brokerSideEffectCsrfToken}
                    onChange={(event) => setBrokerSideEffectCsrfToken(event.target.value)}
                    autoComplete="off"
                  />
                </label>
              </div>

              {isPaperBrokerSubmissionEnabled && !currentIntentPaperBrokerSubmission ? (
                <>
                  <p className="error">
                    This submits to the configured IBKR paper account only. Live trading is not supported.
                  </p>
                  <label>
                    Type SUBMIT IBKR PAPER ORDER to confirm
                    <input
                      value={paperSubmissionConfirmationPhrase}
                      onChange={(event) => setPaperSubmissionConfirmationPhrase(event.target.value)}
                      placeholder={paperBrokerSubmissionConfirmationPhrase}
                    />
                  </label>
                  <button
                    type="button"
                    disabled={!canSubmitPaperBrokerOrder}
                    onClick={handleSubmitPaperBrokerOrder}
                  >
                    {isSubmittingPaperBrokerOrder
                      ? 'Submitting to IBKR paper account…'
                      : 'Submit to IBKR paper account'}
                  </button>
                </>
              ) : (
                <p className="muted">IBKR paper order submission disabled</p>
              )}

              <p className="muted">Live trading is not supported.</p>

              {currentIntentPaperBrokerSubmission ? (
                <div className={paperBrokerSubmissionClassName(currentIntentPaperBrokerSubmission)}>
                  <p>{formatPaperBrokerSubmissionHeading(currentIntentPaperBrokerSubmission)}</p>
                  <p>Broker order id: {currentIntentPaperBrokerSubmission.broker_order_id ?? 'pending'}</p>
                  <p>Status: {currentIntentPaperBrokerSubmission.status}</p>
                  <p>
                    Latest broker order status:{' '}
                    {formatLatestBrokerOrderStatus(currentIntentPaperBrokerSubmission)}
                  </p>
                  <p>
                    Status checked:{' '}
                    {currentIntentPaperBrokerSubmission.broker_status_checked_at ?? 'not checked yet'}
                  </p>
                  <p>{currentIntentPaperBrokerSubmission.message}</p>
                  {currentIntentPaperBrokerSubmission.submitted_to_broker &&
                  currentIntentPaperBrokerSubmission.broker_order_id ? (
                    <button
                      type="button"
                      disabled={isRefreshingPaperBrokerOrderStatus}
                      onClick={() => handleRefreshPaperBrokerOrderStatus(currentIntentPaperBrokerSubmission)}
                    >
                      {isRefreshingPaperBrokerOrderStatus
                        ? 'Refreshing IBKR paper order status…'
                        : 'Refresh IBKR paper order status'}
                    </button>
                  ) : null}
                </div>
              ) : null}
            </section>
          ) : null}

          {paperBrokerSubmissionHistory.length > 0 ? (
            <section aria-label="IBKR paper broker submission history">
              <h3>IBKR paper broker submission history</h3>
              <ul>
                {paperBrokerSubmissionHistory.map((submission) => (
                  <li key={submission.id}>
                    Broker order {submission.broker_order_id ?? 'pending'} — {submission.status}; latest
                    broker status {formatLatestBrokerOrderStatus(submission)}; live trading disabled;
                    source intent #{submission.order_intent_id}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {orderIntentHistory.length > 0 ? (
            <section aria-label="Paper order intent audit log">
              <h3>Paper order intent audit log</h3>
              <ul>
                {orderIntentHistory.map((intent) => (
                  <li key={intent.id}>
                    {intent.symbol} {intent.side} {intent.quantity} — {intent.status}; no IBKR order
                    was submitted;{' '}
                    {intent.paper_broker_submission_enabled
                      ? 'IBKR paper submission enabled at recording'
                      : 'IBKR paper submission disabled at recording'};{' '}
                    {intent.broker_order_operation_available
                      ? 'broker order operation available at recording'
                      : 'broker order operation unavailable at recording'}
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

function paperBrokerSubmissionClassName(submission: PaperBrokerOrderSubmission): string {
  if (submission.status === 'submission_failed_requires_manual_review') {
    return 'error';
  }
  if (submission.status === 'pending_broker_submission') {
    return 'muted';
  }
  return 'success';
}

function formatPaperBrokerSubmissionHeading(submission: PaperBrokerOrderSubmission): string {
  switch (submission.status) {
    case 'pending_broker_submission':
      return 'IBKR paper broker submission pending';
    case 'submission_failed_requires_manual_review':
      return 'IBKR paper broker submission requires manual review';
    case 'submitted_to_paper_broker':
      return 'IBKR paper broker order submitted';
  }
}

function formatLatestBrokerOrderStatus(submission: PaperBrokerOrderSubmission): string {
  if (submission.latest_broker_order_status) {
    return submission.latest_broker_order_status;
  }
  const brokerResponseStatus = submission.broker_response.status;
  return brokerResponseStatus == null ? 'unknown' : String(brokerResponseStatus);
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatAuditSnapshotMessage(action: string, snapshot: AuditSnapshot): string {
  return `${action} audit snapshot with ${snapshot.transcripts.length} transcript, ${snapshot.paper_order_intents.length} order intent, and ${snapshot.paper_broker_order_submissions.length} paper broker submission`;
}

function formatAuditImportSummary(summary: AuditImportSummary): string {
  return `Imported audit snapshot with ${summary.transcript_count} transcript, ${summary.paper_order_intent_count} order intent, and ${summary.paper_broker_order_submission_count} paper broker submission`;
}

function formatAuditResetSummary(summary: AuditImportSummary): string {
  return `${summary.message} ${summary.transcript_count} transcript, ${summary.paper_order_intent_count} order intent, and ${summary.paper_broker_order_submission_count} paper broker submission remain.`;
}
