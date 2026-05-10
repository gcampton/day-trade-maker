import { FormEvent, useState } from 'react';

import {
  getMarketDataCandles,
  importMarketDataCsv,
  runBacktest,
  type BacktestRun,
  type MarketDataDatasetSummary,
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
  const [error, setError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [isRunningBacktest, setIsRunningBacktest] = useState(false);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsImporting(true);

    try {
      const imported = await importMarketDataCsv({ symbol, timeframe, csv_text: csvText });
      const loadedCandles = await getMarketDataCandles(imported.id);
      setDataset(imported);
      setBacktestRun(null);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run backtest');
    } finally {
      setIsRunningBacktest(false);
    }
  }

  const backtestMarkers: StrategyMarker[] = backtestRun
    ? backtestRun.result.markers.map((marker) => ({
        ...marker,
        timestamp: Date.parse(marker.timestamp),
      }))
    : sampleMarkers;

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

        <KLineStrategyChart candles={candles} markers={backtestMarkers} />
      </section>
    </section>
  );
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}
