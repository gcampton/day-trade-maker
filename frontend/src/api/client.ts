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
  created_at: string;
};

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
