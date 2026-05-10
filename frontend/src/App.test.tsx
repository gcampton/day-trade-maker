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

  it('renders a KLineCharts-ready chart panel with candles and strategy markers', () => {
    render(<App />);

    expect(screen.getByRole('heading', { name: /chart workspace/i })).toBeInTheDocument();
    expect(screen.getByText(/klinecharts pro ready/i)).toBeInTheDocument();
    expect(screen.getByText(/sample candles/i)).toBeInTheDocument();
    expect(screen.getByText(/buy breakout/i)).toBeInTheDocument();
    expect(screen.getByText(/exit risk/i)).toBeInTheDocument();
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
