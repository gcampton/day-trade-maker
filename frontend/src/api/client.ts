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
  approved_by: string | null;
  approval_notes: string | null;
  approved_at: string | null;
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

export type RiskCheckCreatePayload = {
  strategy_id: number;
  backtest_id: number;
  paper_mode: boolean;
  max_risk_percent: number;
};

export type RiskCheckRun = RiskCheckCreatePayload & {
  id: number;
  status: 'passed' | 'failed';
  checks: string[];
  failures: string[];
  created_at: string;
};

export type BrokerStatus = {
  provider: 'interactive_brokers';
  mode: 'paper';
  connection_status: 'not_connected' | 'connected';
  read_only: boolean;
  order_submission_enabled: boolean;
  account_id: string | null;
  net_liquidation: number | null;
  currency: string;
  message: string;
};

export type BrokerCapabilities = {
  provider: 'interactive_brokers';
  current_execution_mode: 'audit_only';
  supports_order_intents: boolean;
  supports_paper_broker_submission: boolean;
  supports_live_broker_submission: boolean;
  order_submission_enabled: boolean;
  message: string;
};

export type PaperOrderIntentCreatePayload = {
  strategy_id: number;
  risk_check_id: number;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  order_type: 'market' | 'limit';
  limit_price?: number | null;
  paper_mode: boolean;
  user_confirmed: boolean;
};

export type PaperOrderIntent = PaperOrderIntentCreatePayload & {
  id: number;
  status: 'created_not_submitted';
  submitted_to_broker: boolean;
  order_submission_enabled: boolean;
  checks: string[];
  message: string;
  created_at: string;
};

export type AuditSnapshot = {
  version: 1;
  exported_at: string;
  transcripts: Transcript[];
  strategies: StrategyCandidate[];
  market_data: Array<MarketDataDatasetSummary & { candles: MarketDataCandle[] }>;
  backtests: BacktestRun[];
  risk_checks: RiskCheckRun[];
  paper_order_intents: PaperOrderIntent[];
};

export type AuditImportSummary = {
  version: 1;
  transcript_count: number;
  strategy_count: number;
  market_data_count: number;
  backtest_count: number;
  risk_check_count: number;
  paper_order_intent_count: number;
  message: string;
};

export type AuditPersistenceStatus = {
  provider: 'sqlite';
  db_path: string;
  snapshot_exists: boolean;
  transcript_count: number;
  strategy_count: number;
  market_data_count: number;
  backtest_count: number;
  risk_check_count: number;
  paper_order_intent_count: number;
};

export async function getTranscripts(): Promise<Transcript[]> {
  const response = await fetch('/api/transcripts');

  if (!response.ok) {
    throw new Error('Failed to load saved transcripts');
  }

  return response.json() as Promise<Transcript[]>;
}

export async function getStrategies(): Promise<StrategyCandidate[]> {
  const response = await fetch('/api/strategies');

  if (!response.ok) {
    throw new Error('Failed to load strategy candidates');
  }

  return response.json() as Promise<StrategyCandidate[]>;
}

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

export async function approveStrategy(strategyId: number): Promise<StrategyCandidate> {
  const response = await fetch(`/api/strategies/${strategyId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      approved_by: 'Garratt',
      notes: 'Reviewed source quote, entry, exit, and 1% risk rule.',
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to approve strategy');
  }

  return response.json() as Promise<StrategyCandidate>;
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

export async function runRiskCheck(payload: RiskCheckCreatePayload): Promise<RiskCheckRun> {
  const response = await fetch('/api/risk-checks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to run broker readiness check');
  }

  return response.json() as Promise<RiskCheckRun>;
}

export async function getBrokerStatus(): Promise<BrokerStatus> {
  const response = await fetch('/api/broker/status');

  if (!response.ok) {
    throw new Error('Failed to load IBKR broker status');
  }

  return response.json() as Promise<BrokerStatus>;
}

export async function getBrokerCapabilities(): Promise<BrokerCapabilities> {
  const response = await fetch('/api/broker/capabilities');

  if (!response.ok) {
    throw new Error('Failed to load broker capabilities');
  }

  return response.json() as Promise<BrokerCapabilities>;
}

export async function createPaperOrderIntent(
  payload: PaperOrderIntentCreatePayload,
): Promise<PaperOrderIntent> {
  const response = await fetch('/api/broker/order-intents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Failed to record paper order intent');
  }

  return response.json() as Promise<PaperOrderIntent>;
}

export async function getPaperOrderIntents(): Promise<PaperOrderIntent[]> {
  const response = await fetch('/api/broker/order-intents');

  if (!response.ok) {
    throw new Error('Failed to load paper order intent history');
  }

  return response.json() as Promise<PaperOrderIntent[]>;
}

export async function exportAuditSnapshot(): Promise<AuditSnapshot> {
  const response = await fetch('/api/audit/export');

  if (!response.ok) {
    throw new Error('Failed to export audit snapshot');
  }

  return response.json() as Promise<AuditSnapshot>;
}

export async function getAuditPersistenceStatus(): Promise<AuditPersistenceStatus> {
  const response = await fetch('/api/audit/status');

  if (!response.ok) {
    throw new Error('Failed to load audit persistence status');
  }

  return response.json() as Promise<AuditPersistenceStatus>;
}

export async function resetAuditState(confirmation: string): Promise<AuditImportSummary> {
  const response = await fetch('/api/audit/reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirmation }),
  });

  if (!response.ok) {
    throw new Error('Failed to reset local audit state');
  }

  return response.json() as Promise<AuditImportSummary>;
}

export async function importAuditSnapshot(snapshot: AuditSnapshot): Promise<AuditImportSummary> {
  const response = await fetch('/api/audit/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(snapshot),
  });

  if (!response.ok) {
    throw new Error('Failed to import audit snapshot');
  }

  return response.json() as Promise<AuditImportSummary>;
}
