// Typed client for the Markets Assistant backend. Mirrors the FastAPI response shape from
// app/agent/graph.py (synthesised response) + app/main.py (cache_hit on meta).

export type Verdict = "ANSWERED" | "NEEDS_HUMAN";
export type Confidence = "high" | "medium" | "low";

export interface AskMeta {
  tools_called: string[];
  latency_ms: number;
  model: string;
  tokens: { prompt: number; completion: number; total: number };
  cache_hit: boolean;
}

export interface AskResponse {
  answer: string;
  sources: string[];
  confidence: Confidence;
  verdict: Verdict;
  meta: AskMeta;
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

// Relative path so the Vite dev proxy / nginx forwards to the backend (single origin).
const ASK_URL = "/ask";

export async function ask(question: string, signal?: AbortSignal): Promise<AskResponse> {
  let res: Response;
  try {
    res = await fetch(ASK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError("Could not reach the server. Is the backend running?", 0);
  }

  if (res.status === 429) {
    throw new ApiError("Rate limit exceeded — please wait a minute and try again.", 429);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* keep default detail */
    }
    throw new ApiError(detail, res.status);
  }

  return (await res.json()) as AskResponse;
}
