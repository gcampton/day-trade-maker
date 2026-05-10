export type TranscriptPayload = {
  title: string;
  source_url: string | null;
  creator: string | null;
  raw_text: string;
  symbols: string[];
  timeframes: string[];
};

export type Transcript = TranscriptPayload & {
  id: number;
  created_at: string;
};

export type StrategyRule = {
  type: string;
  description: string;
  parameters: Record<string, unknown>;
};

export type StrategySpec = {
  name: string;
  description: string;
  market: string;
  symbols: string[];
  timeframe: string;
  side: 'long' | 'short' | 'both';
  indicators: Array<{ name: string; parameters: Record<string, unknown> }>;
  entry_rules: StrategyRule[];
  exit_rules: StrategyRule[];
  risk_rules: StrategyRule[];
  invalidations: string[];
  source_quotes: Array<{
    transcript_id: number;
    quote: string;
    start_seconds: number | null;
  }>;
};

export type StrategyCandidate = {
  id: number;
  transcript_id: number;
  spec: StrategySpec;
  status: string;
  created_at: string;
};

export type MarketDataImportPayload = {
  symbol: string;
  timeframe: string;
  csv_text: string;
};

export type MarketDataDatasetSummary = {
  id: number;
  symbol: string;
  timeframe: string;
  candle_count: number;
  created_at: string;
};

export type MarketDataCandle = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type BacktestCreatePayload = {
  strategy_id: number;
  dataset_id: number;
  starting_cash: number;
};

export type BacktestRun = {
  id: number;
  strategy_id: number;
  dataset_id: number;
  result: {
    starting_cash: number;
    ending_cash: number;
    net_pnl: number;
    total_trades: number;
    win_rate: number;
    trades: Array<{
      entry_timestamp: string;
      exit_timestamp: string;
      entry_price: number;
      exit_price: number;
      quantity: number;
      pnl: number;
    }>;
    markers: Array<{
      timestamp: string;
      price: number;
      side: 'buy' | 'sell' | 'exit' | 'warning';
      label: string;
    }>;
  };
  created_at: string;
};

export async function createTranscript(payload: TranscriptPayload): Promise<Transcript> {
  const response = await fetch('/api/transcripts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to save transcript');
  }

  return response.json() as Promise<Transcript>;
}

export async function extractStrategyCandidates(
  transcriptId: number,
): Promise<StrategyCandidate[]> {
  const response = await fetch(`/api/transcripts/${transcriptId}/extract-strategies`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to extract strategy candidates');
  }

  return response.json() as Promise<StrategyCandidate[]>;
}

export async function importMarketDataCsv(
  payload: MarketDataImportPayload,
): Promise<MarketDataDatasetSummary> {
  const response = await fetch('/api/market-data/import-csv', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to import market data');
  }

  return response.json() as Promise<MarketDataDatasetSummary>;
}

export async function getMarketDataCandles(datasetId: number): Promise<MarketDataCandle[]> {
  const response = await fetch(`/api/market-data/${datasetId}/candles`);

  if (!response.ok) {
    throw new Error('Failed to load market data candles');
  }

  return response.json() as Promise<MarketDataCandle[]>;
}

export async function runBacktest(payload: BacktestCreatePayload): Promise<BacktestRun> {
  const response = await fetch('/api/backtests', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to run backtest');
  }

  return response.json() as Promise<BacktestRun>;
}
