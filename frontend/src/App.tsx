import { useEffect, useState } from 'react';

import './styles.css';

import { StrategyExtractionPanel } from './components/StrategyExtractionPanel';
import { TranscriptForm } from './components/TranscriptForm';
import type { StrategyCandidate, Transcript } from './api/client';
import { getStrategies, getTranscripts } from './api/client';
import { ChartsPage } from './pages/ChartsPage';

export function App() {
  const [selectedTranscript, setSelectedTranscript] = useState<Transcript | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyCandidate | null>(null);
  const [restoredTranscriptCount, setRestoredTranscriptCount] = useState(0);
  const [restoredStrategies, setRestoredStrategies] = useState<StrategyCandidate[]>([]);

  useEffect(() => {
    let isMounted = true;

    async function restoreResearchState() {
      try {
        const [transcripts, strategies] = await Promise.all([getTranscripts(), getStrategies()]);
        if (!isMounted) {
          return;
        }

        if (Array.isArray(transcripts) && transcripts.length > 0) {
          setSelectedTranscript(transcripts[0]);
          setRestoredTranscriptCount(transcripts.length);
        }

        if (Array.isArray(strategies) && strategies.length > 0) {
          setRestoredStrategies(strategies);
          setSelectedStrategy(strategies[0]);
        }
      } catch {
        // Startup restore is best-effort so local development and tests can run before the API is up.
      }
    }

    void restoreResearchState();

    return () => {
      isMounted = false;
    };
  }, []);

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
        <StrategyExtractionPanel
          transcript={selectedTranscript}
          initialCandidates={restoredStrategies}
          onCandidateSelected={setSelectedStrategy}
        />
      </div>

      {restoredTranscriptCount > 0 ? (
        <p className="success">Restored {restoredTranscriptCount} saved transcript</p>
      ) : null}

      <ChartsPage selectedStrategy={selectedStrategy} />

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
