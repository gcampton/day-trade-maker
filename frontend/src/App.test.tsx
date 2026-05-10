import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';

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
      new Response(
        JSON.stringify({
          id: 1,
          title: 'Opening Range Breakout',
          source_url: 'https://www.youtube.com/watch?v=example',
          creator: 'Example Trader',
          raw_text: 'Buy the breakout after the first 15 minute range confirms with volume.',
          symbols: ['AAPL'],
          timeframes: ['15m'],
          created_at: '2026-05-10T18:20:00Z',
        }),
        { status: 201, headers: { 'Content-Type': 'application/json' } },
      ),
    );

    render(<App />);

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
});
