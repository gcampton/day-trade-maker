import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';

const savedTranscript = {
  id: 1,
  title: 'Opening Range Breakout',
  source_url: 'https://www.youtube.com/watch?v=example',
  creator: 'Example Trader',
  raw_text: 'Buy the breakout after the first 15 minute range confirms with volume.',
  symbols: ['AAPL'],
  timeframes: ['15m'],
  created_at: '2026-05-10T18:20:00Z',
};

const importedDataset = {
  id: 1,
  symbol: 'AAPL',
  timeframe: '5m',
  candle_count: 2,
  created_at: '2026-05-10T18:19:00Z',
};

const importedCandles = [
  {
    timestamp: '2026-05-10T14:30:00Z',
    open: 100,
    high: 101.5,
    low: 99.5,
    close: 101,
    volume: 150000,
  },
  {
    timestamp: '2026-05-10T14:35:00Z',
    open: 101,
    high: 103,
    low: 100.5,
    close: 102,
    volume: 200000,
  },
];

const extractedStrategy = {
  id: 1,
  transcript_id: 1,
  status: 'candidate',
  created_at: '2026-05-10T18:21:00Z',
  spec: {
    name: 'Opening Range Breakout With Volume',
    description: 'Enter when price breaks the opening range with volume confirmation.',
    market: 'US equities',
    symbols: ['AAPL'],
    timeframe: '15m',
    side: 'long',
    indicators: [{ name: 'opening_range', parameters: { minutes: 15 } }],
    entry_rules: [
      {
        type: 'price_breakout',
        description: 'Enter long when price breaks above the opening range high.',
        parameters: { direction: 'long' },
      },
    ],
    exit_rules: [
      {
        type: 'stop_loss',
        description: 'Exit if price falls below the opening range low.',
        parameters: { stop: 'opening_range_low' },
      },
    ],
    risk_rules: [
      {
        type: 'max_risk_per_trade',
        description: 'Risk no more than 1% of account equity per trade.',
        parameters: { percent: 1 },
      },
    ],
    invalidations: ['Skip if breakout volume is weak.'],
    source_quotes: [
      {
        transcript_id: 1,
        quote: 'Buy the breakout after the first 15 minute range confirms with volume.',
        start_seconds: null,
      },
    ],
  },
};

const approvedStrategy = {
  ...extractedStrategy,
  status: 'approved',
  approved_by: 'Garratt',
  approval_notes: 'Reviewed source quote, entry, exit, and 1% risk rule.',
  approved_at: '2026-05-10T18:21:30Z',
};

const createdBacktest = {
  id: 1,
  strategy_id: 1,
  dataset_id: 1,
  created_at: '2026-05-10T18:22:00Z',
  result: {
    starting_cash: 10000,
    ending_cash: 10001,
    net_pnl: 1,
    total_trades: 1,
    win_rate: 1,
    trades: [
      {
        entry_timestamp: '2026-05-10T14:35:00Z',
        exit_timestamp: '2026-05-10T14:35:00Z',
        entry_price: 101,
        exit_price: 102,
        quantity: 1,
        pnl: 1,
      },
    ],
    markers: [
      {
        timestamp: '2026-05-10T14:35:00Z',
        price: 101,
        side: 'buy',
        label: 'Buy breakout',
      },
      {
        timestamp: '2026-05-10T14:35:00Z',
        price: 102,
        side: 'exit',
        label: 'Exit close',
      },
    ],
  },
};

const createdRiskCheck = {
  id: 1,
  strategy_id: 1,
  backtest_id: 1,
  paper_mode: true,
  max_risk_percent: 1,
  status: 'passed',
  checks: ['approved strategy', 'backtest matches strategy', 'backtest produced trades', 'paper mode enabled'],
  failures: [],
  created_at: '2026-05-10T18:23:00Z',
};

const brokerStatus = {
  provider: 'interactive_brokers',
  mode: 'paper',
  connection_status: 'not_connected',
  read_only: true,
  order_submission_enabled: false,
  account_id: null,
  net_liquidation: null,
  currency: 'USD',
  message: 'IBKR read-only scaffold is configured; no broker session is connected.',
};

const brokerCapabilities = {
  provider: 'interactive_brokers',
  current_execution_mode: 'audit_only',
  supports_order_intents: true,
  supports_paper_broker_submission: false,
  supports_live_broker_submission: false,
  order_submission_enabled: false,
  message: 'Current broker mode records audit-only paper order intents; no IBKR orders are submitted.',
};

const createdOrderIntent = {
  id: 1,
  strategy_id: 1,
  risk_check_id: 1,
  symbol: 'AAPL',
  side: 'buy',
  quantity: 10,
  order_type: 'market',
  limit_price: null,
  paper_mode: true,
  user_confirmed: true,
  status: 'created_not_submitted',
  submitted_to_broker: false,
  order_submission_enabled: false,
  checks: ['approved strategy', 'passed risk check', 'paper mode enabled', 'explicit user confirmation'],
  message: 'Paper order intent recorded for audit only; no IBKR order was submitted.',
  created_at: '2026-05-10T18:24:00Z',
};

const orderIntentHistory = [createdOrderIntent];

const auditSnapshot = {
  version: 1,
  exported_at: '2026-05-10T18:25:00Z',
  transcripts: [savedTranscript],
  strategies: [approvedStrategy],
  market_data: [{ ...importedDataset, candles: importedCandles }],
  backtests: [createdBacktest],
  risk_checks: [createdRiskCheck],
  paper_order_intents: [createdOrderIntent],
};

const auditImportSummary = {
  version: 1,
  transcript_count: 1,
  strategy_count: 1,
  market_data_count: 1,
  backtest_count: 1,
  risk_check_count: 1,
  paper_order_intent_count: 1,
  message: 'Audit snapshot imported into in-memory stores.',
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('App', () => {
  it('renders the trading research dashboard title', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /day trade maker/i })).toBeInTheDocument();
    expect(screen.getByText(/youtube transcript strategy lab/i)).toBeInTheDocument();
  });

  it('loads persisted transcripts and strategy candidates on startup', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (url === '/api/transcripts') {
        return new Response(JSON.stringify([savedTranscript]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      if (url === '/api/strategies') {
        return new Response(JSON.stringify([approvedStrategy]), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      return new Response(null, { status: 404 });
    });

    render(<App />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/transcripts');
      expect(fetchMock).toHaveBeenCalledWith('/api/strategies');
    });
    expect(await screen.findByText(/restored 1 saved transcript/i)).toBeInTheDocument();
    expect(screen.getByText(/selected transcript/i)).toBeInTheDocument();
    expect(screen.getByText(/opening range breakout with volume/i)).toBeInTheDocument();
    expect(screen.getByText(/approved by garratt/i)).toBeInTheDocument();
  });

  it('restores persisted chart and broker workflow state on startup', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/audit/export');
    });
    expect(await screen.findByText(/imported aapl 5m dataset with 2 candles/i)).toBeInTheDocument();
    expect(screen.getByText(/backtest net pnl/i)).toBeInTheDocument();
    expect(screen.getByText(/broker readiness passed/i)).toBeInTheDocument();
    expect(screen.getByText(/paper order intent audit log/i)).toBeInTheDocument();
    expect(screen.getByText(/AAPL buy 10/i)).toBeInTheDocument();
  });

  it('submits a pasted transcript to the backend', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
      if (url === '/api/transcripts' && init?.method === 'POST') {
        return new Response(JSON.stringify(savedTranscript), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      return new Response(null, { status: 404 });
    });

    render(<App />);

    await saveTranscriptThroughForm();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/transcripts', expect.any(Object)));

    const request = fetchMock.mock.calls.find(
      ([url, init]) => url === '/api/transcripts' && init?.method === 'POST',
    )?.[1] as RequestInit;
    expect(request.method).toBe('POST');
    expect(JSON.parse(request.body as string)).toMatchObject({
      title: 'Opening Range Breakout',
      creator: 'Example Trader',
      symbols: ['AAPL'],
      timeframes: ['15m'],
    });
    expect(await screen.findByText(/saved transcript #1/i)).toBeInTheDocument();
  });

  it('extracts and displays a strategy candidate from the saved transcript', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
      if (url === '/api/transcripts') {
        return new Response(JSON.stringify(savedTranscript), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      if (url === '/api/transcripts/1/extract-strategies') {
        return new Response(JSON.stringify([extractedStrategy]), {
          status: 201,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      return new Response(null, { status: 404 });
    });

    render(<App />);

    await saveTranscriptThroughForm();
    fireEvent.click(await screen.findByRole('button', { name: /extract strategy candidates/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/transcripts/1/extract-strategies', {
        method: 'POST',
      });
    });
    expect(await screen.findByText(/opening range breakout with volume/i)).toBeInTheDocument();
    expect(screen.getAllByText(/candidate/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/risk no more than 1%/i)).toBeInTheDocument();
  });

  it('approves an extracted strategy candidate after review', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    await saveTranscriptThroughForm();
    fireEvent.click(await screen.findByRole('button', { name: /extract strategy candidates/i }));
    await screen.findByText(/opening range breakout with volume/i);

    fireEvent.click(await screen.findByRole('button', { name: /approve reviewed strategy/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/strategies/1/approve', expect.any(Object));
    });
    const request = fetchMock.mock.calls.find(([url]) => url === '/api/strategies/1/approve')?.[1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      approved_by: 'Garratt',
      notes: 'Reviewed source quote, entry, exit, and 1% risk rule.',
    });
    expect(await screen.findByText(/approved by garratt/i)).toBeInTheDocument();
  });

  it('imports CSV market data and renders backend candles on the chart', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    await importMarketDataThroughForm();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/market-data/import-csv', expect.any(Object));
    });
    expect(fetchMock).toHaveBeenCalledWith('/api/market-data/1/candles');
    expect(await screen.findByText(/imported aapl 5m dataset with 2 candles/i)).toBeInTheDocument();
    expect(screen.getByText(/last close/i)).toBeInTheDocument();
    expect(screen.getByText('102.00')).toBeInTheDocument();
  });

  it('loads read-only IBKR paper broker status without enabling orders', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /check ibkr status/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/broker/status');
    });
    expect(await screen.findByText('Broker')).toBeInTheDocument();
    expect(screen.getAllByText(/interactive brokers/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/paper mode/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/read-only/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/order submission disabled/i)).toBeInTheDocument();
  });

  it('renders broker execution capability boundaries', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /check ibkr status/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/broker/capabilities');
    });
    expect(await screen.findByText(/execution mode/i)).toBeInTheDocument();
    expect(screen.getByText(/audit-only order intents/i)).toBeInTheDocument();
    expect(screen.getByText(/paper broker submission disabled/i)).toBeInTheDocument();
    expect(screen.getByText(/live broker submission disabled/i)).toBeInTheDocument();
    expect(screen.getByText(/no IBKR orders are submitted/i)).toBeInTheDocument();
  });

  it('runs a paper-mode risk check after approval and backtest', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    await saveTranscriptThroughForm();
    fireEvent.click(await screen.findByRole('button', { name: /extract strategy candidates/i }));
    await screen.findByText(/opening range breakout with volume/i);
    fireEvent.click(await screen.findByRole('button', { name: /approve reviewed strategy/i }));
    await screen.findByText(/approved by garratt/i);
    await importMarketDataThroughForm();
    fireEvent.click(await screen.findByRole('button', { name: /run backtest/i }));
    await screen.findByText(/backtest net pnl/i);

    fireEvent.click(await screen.findByRole('button', { name: /run broker readiness check/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/risk-checks', expect.any(Object));
    });
    const request = fetchMock.mock.calls.find(([url]) => url === '/api/risk-checks')?.[1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      strategy_id: 1,
      backtest_id: 1,
      paper_mode: true,
      max_risk_percent: 1,
    });
    expect(await screen.findByText(/broker readiness passed/i)).toBeInTheDocument();
    expect(screen.getByText(/paper mode enabled/i)).toBeInTheDocument();
  });

  it('records a paper order intent only after readiness passed and explicit confirmation', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    await reachPassedBrokerReadiness();

    fireEvent.click(await screen.findByRole('button', { name: /record paper order intent/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/broker/order-intents', expect.any(Object));
    });
    const request = fetchMock.mock.calls.find(([url]) => url === '/api/broker/order-intents')
      ?.[1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      strategy_id: 1,
      risk_check_id: 1,
      symbol: 'AAPL',
      side: 'buy',
      quantity: 10,
      order_type: 'market',
      paper_mode: true,
      user_confirmed: true,
    });
    expect(await screen.findByText(/paper order intent recorded/i)).toBeInTheDocument();
    expect(screen.getAllByText(/no ibkr order was submitted/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/created_not_submitted/i).length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith('/api/broker/order-intents');
    expect(screen.getByText(/paper order intent audit log/i)).toBeInTheDocument();
    expect(screen.getByText(/AAPL buy 10/i)).toBeInTheDocument();
  });

  it('uses editable paper order ticket values when recording an intent', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    await reachPassedBrokerReadiness();
    fireEvent.change(await screen.findByLabelText(/order symbol/i), { target: { value: 'TSLA' } });
    fireEvent.change(screen.getByLabelText(/order side/i), { target: { value: 'sell' } });
    fireEvent.change(screen.getByLabelText(/order quantity/i), { target: { value: '3' } });

    fireEvent.click(await screen.findByRole('button', { name: /record paper order intent/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/broker/order-intents', expect.any(Object));
    });
    const request = fetchMock.mock.calls.find(([url]) => url === '/api/broker/order-intents')
      ?.[1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      symbol: 'TSLA',
      side: 'sell',
      quantity: 3,
      order_type: 'market',
      paper_mode: true,
      user_confirmed: true,
    });
  });

  it('keeps the paper order intent action disabled for invalid quantity', async () => {
    mockTradingApi();

    render(<App />);

    await reachPassedBrokerReadiness();
    fireEvent.change(await screen.findByLabelText(/order quantity/i), { target: { value: '0' } });

    expect(screen.getByRole('button', { name: /record paper order intent/i })).toBeDisabled();
  });

  it('exports the audit snapshot as editable local JSON', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /export audit snapshot/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/audit/export');
    });
    expect(await screen.findByText(/exported audit snapshot with 1 transcript and 1 order intent/i)).toBeInTheDocument();
    expect((screen.getByLabelText(/audit snapshot json/i) as HTMLTextAreaElement).value).toContain(
      '"paper_order_intents"',
    );
  });

  it('imports a pasted audit snapshot into the backend stores', async () => {
    const fetchMock = mockTradingApi();

    render(<App />);

    fireEvent.change(screen.getByLabelText(/audit snapshot json/i), {
      target: { value: JSON.stringify(auditSnapshot) },
    });
    fireEvent.click(screen.getByRole('button', { name: /import audit snapshot/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/audit/import', expect.any(Object));
    });
    const request = fetchMock.mock.calls.find(([url]) => url === '/api/audit/import')?.[1] as RequestInit;
    expect(JSON.parse(request.body as string)).toMatchObject({
      version: 1,
      paper_order_intents: [{ symbol: 'AAPL', submitted_to_broker: false }],
    });
    expect(await screen.findByText(/imported audit snapshot with 1 transcript and 1 order intent/i)).toBeInTheDocument();
  });
});

async function saveTranscriptThroughForm() {
  fireEvent.change(screen.getByLabelText(/title/i), {
    target: { value: 'Opening Range Breakout' },
  });
  fireEvent.change(screen.getByLabelText(/youtube url/i), {
    target: { value: 'https://www.youtube.com/watch?v=example' },
  });
  fireEvent.change(screen.getByLabelText(/creator/i), {
    target: { value: 'Example Trader' },
  });
  fireEvent.change(screen.getByLabelText(/symbols/i), {
    target: { value: 'AAPL' },
  });
  fireEvent.change(screen.getByLabelText(/timeframes/i), {
    target: { value: '15m' },
  });
  fireEvent.change(screen.getByLabelText(/transcript text/i), {
    target: { value: 'Buy the breakout after the first 15 minute range confirms with volume.' },
  });
  fireEvent.click(screen.getByRole('button', { name: /save transcript/i }));

  await screen.findByText(/saved transcript #1/i);
}

async function importMarketDataThroughForm() {
  fireEvent.change(screen.getByLabelText(/market symbol/i), { target: { value: 'AAPL' } });
  fireEvent.change(screen.getByLabelText(/market timeframe/i), { target: { value: '5m' } });
  fireEvent.change(screen.getByLabelText(/ohlcv csv/i), {
    target: {
      value:
        'timestamp,open,high,low,close,volume\n' +
        '2026-05-10T14:30:00Z,100,101.5,99.5,101,150000\n' +
        '2026-05-10T14:35:00Z,101,103,100.5,102,200000\n',
    },
  });
  fireEvent.click(screen.getByRole('button', { name: /import candles/i }));

  await screen.findByText(/imported aapl 5m dataset with 2 candles/i);
}

async function reachPassedBrokerReadiness() {
  await saveTranscriptThroughForm();
  fireEvent.click(await screen.findByRole('button', { name: /extract strategy candidates/i }));
  await screen.findByText(/opening range breakout with volume/i);
  fireEvent.click(await screen.findByRole('button', { name: /approve reviewed strategy/i }));
  await screen.findByText(/approved by garratt/i);
  await importMarketDataThroughForm();
  fireEvent.click(await screen.findByRole('button', { name: /run backtest/i }));
  await screen.findByText(/backtest net pnl/i);
  fireEvent.click(await screen.findByRole('button', { name: /run broker readiness check/i }));
  await screen.findByText(/broker readiness passed/i);
}

function mockTradingApi() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
    if (url === '/api/transcripts') {
      return new Response(JSON.stringify(savedTranscript), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/transcripts/1/extract-strategies') {
      return new Response(JSON.stringify([extractedStrategy]), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/strategies/1/approve') {
      return new Response(JSON.stringify(approvedStrategy), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/market-data/import-csv') {
      return new Response(JSON.stringify(importedDataset), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/market-data/1/candles') {
      return new Response(JSON.stringify(importedCandles), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/backtests') {
      return new Response(JSON.stringify(createdBacktest), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/risk-checks') {
      return new Response(JSON.stringify(createdRiskCheck), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/broker/status') {
      return new Response(JSON.stringify(brokerStatus), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/broker/capabilities') {
      return new Response(JSON.stringify(brokerCapabilities), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/broker/order-intents' && init?.method === 'POST') {
      return new Response(JSON.stringify(createdOrderIntent), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/broker/order-intents') {
      return new Response(JSON.stringify(orderIntentHistory), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/audit/export') {
      return new Response(JSON.stringify(auditSnapshot), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (url === '/api/audit/import') {
      return new Response(JSON.stringify(auditImportSummary), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    return new Response(null, { status: 404 });
  });
}
