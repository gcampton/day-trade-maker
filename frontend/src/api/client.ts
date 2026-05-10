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
