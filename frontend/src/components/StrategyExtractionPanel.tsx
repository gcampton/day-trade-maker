import { useState } from 'react';

import {
  extractStrategyCandidates,
  type StrategyCandidate,
  type Transcript,
} from '../api/client';

type StrategyExtractionPanelProps = {
  transcript: Transcript | null;
};

export function StrategyExtractionPanel({ transcript }: StrategyExtractionPanelProps) {
  const [candidates, setCandidates] = useState<StrategyCandidate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);

  async function handleExtract() {
    if (!transcript) {
      return;
    }

    setError(null);
    setIsExtracting(true);

    try {
      const extracted = await extractStrategyCandidates(transcript.id);
      setCandidates(extracted);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to extract strategy candidates');
    } finally {
      setIsExtracting(false);
    }
  }

  return (
    <section className="strategy-panel" aria-label="Strategy extraction">
      <div className="form-heading">
        <p className="eyebrow">Strategy Builder</p>
        <h2>Extract strategy candidates</h2>
        <p>
          Use the saved transcript as source material, then review the structured strategy before
          backtesting or any broker workflow.
        </p>
      </div>

      {transcript ? (
        <div className="selected-source">
          <span>Selected transcript</span>
          <strong>{transcript.title}</strong>
        </div>
      ) : (
        <p className="muted">Save a transcript first to unlock strategy extraction.</p>
      )}

      <button type="button" disabled={!transcript || isExtracting} onClick={handleExtract}>
        {isExtracting ? 'Extracting…' : 'Extract strategy candidates'}
      </button>

      {error ? <p className="error">{error}</p> : null}

      {candidates.map((candidate) => (
        <article className="strategy-card" key={candidate.id}>
          <div className="strategy-card-header">
            <h3>{candidate.spec.name}</h3>
            <span>{candidate.status}</span>
          </div>
          <p>{candidate.spec.description}</p>
          <dl>
            <div>
              <dt>Symbols</dt>
              <dd>{candidate.spec.symbols.join(', ')}</dd>
            </div>
            <div>
              <dt>Timeframe</dt>
              <dd>{candidate.spec.timeframe}</dd>
            </div>
            <div>
              <dt>Risk</dt>
              <dd>{candidate.spec.risk_rules[0]?.description ?? 'No risk rule'}</dd>
            </div>
          </dl>
          <blockquote>{candidate.spec.source_quotes[0]?.quote}</blockquote>
        </article>
      ))}
    </section>
  );
}
