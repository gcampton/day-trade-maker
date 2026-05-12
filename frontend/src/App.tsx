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
      <header className="terminal-topbar">
        <div>
          <p className="eyebrow">YouTube transcript strategy lab</p>
          <h1>Day Trade Maker</h1>
        </div>
        <div className="topbar-status" aria-label="Execution safety status">
          <span className="status-dot" />
          <span>IBKR live disabled</span>
          <span>Paper gates required</span>
        </div>
      </header>

      <div className="terminal-layout">
        <aside className="terminal-rail" aria-label="Workspace navigation">
          <p className="rail-title">Research desk</p>
          <a href="#research-flow">01 Intake → Strategy</a>
          <a href="#market-workspace">02 Chart + Backtest</a>
          <a href="#safety-gates">03 IBKR Safety Gates</a>
          <a href="#audit-archive">04 Audit Archive</a>
          <div className="rail-card">
            <span>Mode</span>
            <strong>Audit-first</strong>
            <small>No broker side effects unless the paper submission gates pass.</small>
          </div>
        </aside>

        <section className="terminal-main">
          <section className="hero-panel">
            <p className="eyebrow">Fintech terminal workspace</p>
            <h2>Compact research cockpit</h2>
            <p className="lede">
              Extract strategy hypotheses from transcripts, validate them against OHLCV data, and
              keep Interactive Brokers execution behind explicit paper-account safety controls.
            </p>
          </section>

          {restoredTranscriptCount > 0 ? (
            <p className="success">Restored {restoredTranscriptCount} saved transcript</p>
          ) : null}

          <section id="research-flow" className="workflow-grid" aria-label="Transcript and strategy workflow">
            <TranscriptForm onSaved={setSelectedTranscript} />
            <StrategyExtractionPanel
              transcript={selectedTranscript}
              initialCandidates={restoredStrategies}
              onCandidateSelected={setSelectedStrategy}
            />
          </section>

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
        </section>
      </div>
    </main>
  );
}
