import { FormEvent, useState } from 'react';

import { createTranscript, type Transcript } from '../api/client';

type TranscriptFormProps = {
  onSaved?: (transcript: Transcript) => void;
};

function splitTags(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function TranscriptForm({ onSaved }: TranscriptFormProps) {
  const [title, setTitle] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [creator, setCreator] = useState('');
  const [symbols, setSymbols] = useState('');
  const [timeframes, setTimeframes] = useState('');
  const [rawText, setRawText] = useState('');
  const [savedTranscript, setSavedTranscript] = useState<Transcript | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSaving(true);

    try {
      const saved = await createTranscript({
        title,
        source_url: sourceUrl.trim() || null,
        creator: creator.trim() || null,
        raw_text: rawText,
        symbols: splitTags(symbols),
        timeframes: splitTags(timeframes),
      });
      setSavedTranscript(saved);
      onSaved?.(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save transcript');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form className="transcript-form" onSubmit={handleSubmit}>
      <div className="form-heading">
        <p className="eyebrow">Transcript Intake</p>
        <h2>Save a YouTube trading transcript</h2>
        <p>
          Paste transcript text here first. Strategy extraction will stay linked to this source
          context for auditability.
        </p>
      </div>

      <label>
        Title
        <input value={title} onChange={(event) => setTitle(event.target.value)} required />
      </label>

      <label>
        YouTube URL
        <input value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} />
      </label>

      <label>
        Creator
        <input value={creator} onChange={(event) => setCreator(event.target.value)} />
      </label>

      <div className="form-row">
        <label>
          Symbols
          <input
            placeholder="AAPL, TSLA, SPY"
            value={symbols}
            onChange={(event) => setSymbols(event.target.value)}
          />
        </label>

        <label>
          Timeframes
          <input
            placeholder="1m, 5m, 15m"
            value={timeframes}
            onChange={(event) => setTimeframes(event.target.value)}
          />
        </label>
      </div>

      <label>
        Transcript text
        <textarea
          minLength={1}
          rows={8}
          value={rawText}
          onChange={(event) => setRawText(event.target.value)}
          required
        />
      </label>

      <button type="submit" disabled={isSaving}>
        {isSaving ? 'Saving…' : 'Save transcript'}
      </button>

      {savedTranscript ? <p className="success">Saved transcript #{savedTranscript.id}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </form>
  );
}
