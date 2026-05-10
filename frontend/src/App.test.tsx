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

afterEach(() => {
  vi.restoreAllMocks();
});

describe('App', () => {
  it('renders the trading research dashboard title', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /day trade maker/i })).toBeInTheDocument();
    expect(screen.getByText(/youtube transcript strategy lab/i)).toBeInTheDocument();
  });

  it('submits a pasted transcript to the backend', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(savedTranscript), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    render(<App />);

    await saveTranscriptThroughForm();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/transcripts', expect.any(Object)));

    const request = fetchMock.mock.calls[0][1] as RequestInit;
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

function mockTradingApi() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (url) => {
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

    return new Response(null, { status: 404 });
  });
}
