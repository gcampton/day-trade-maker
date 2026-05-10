import { useState } from 'react';

import './styles.css';

import { StrategyExtractionPanel } from './components/StrategyExtractionPanel';
import { TranscriptForm } from './components/TranscriptForm';
import type { Transcript } from './api/client';

export function App() {
  const [selectedTranscript, setSelectedTranscript] = useState<Transcript | null>(null);

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">YouTube transcript strategy lab</p>
        <h1>Day Trade Maker</h1>
        <p className="lede">
          Research day-trading ideas from transcripts, turn them into structured strategy
          hypotheses, backtest them, and keep Interactive Brokers execution behind paper-mode
          risk controls.
        </p>
      </section>

      <div className="workflow-grid">
        <TranscriptForm onSaved={setSelectedTranscript} />
        <StrategyExtractionPanel transcript={selectedTranscript} />
      </div>

      <section className="dashboard-grid" aria-label="Dashboard sections">
        <article>
          <h2>Transcripts</h2>
          <p>Paste day-trader YouTube transcripts and keep source context attached.</p>
        </article>
        <article>
          <h2>Strategy Builder</h2>
          <p>Extract rules, indicators, entries, exits, stops, and invalidations.</p>
        </article>
        <article>
          <h2>Charts</h2>
          <p>KLineCharts Pro workspace planned for candlesticks, overlays, and trade markers.</p>
        </article>
        <article>
          <h2>IBKR Paper Trading</h2>
          <p>Interactive Brokers integration starts read-only and paper-only by default.</p>
        </article>
      </section>
    </main>
  );
}
