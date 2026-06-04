import { useRef, useState } from "react";
import { ask, ApiError, type AskResponse } from "./api";
import AnswerCard from "./AnswerCard";

const EXAMPLES = [
  "What is the current price of Bitcoin?",
  "Explain impermanent loss in DeFi.",
  "If I went long 0.5 BTC at $30000 and sold at $35000, what's my profit?",
  "Should I buy Ethereum right now?",
];

export default function App() {
  const [question, setQuestion] = useState("");
  const [data, setData] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function submit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || loading) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setData(null);
    try {
      const res = await ask(trimmed, controller.signal);
      setData(res);
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <h1>Markets Assistant</h1>
        <p className="tagline">
          A tool-using finance &amp; markets agent. Every answer is grounded in tool output — it
          escalates instead of guessing.
        </p>
      </header>

      <form
        className="ask-form"
        onSubmit={(e) => {
          e.preventDefault();
          submit(question);
        }}
      >
        <textarea
          className="question-input"
          placeholder="Ask about crypto prices, market concepts, or P/L math…"
          value={question}
          rows={3}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              submit(question);
            }
          }}
        />
        <div className="form-row">
          <span className="hint">⌘/Ctrl + Enter to send</span>
          <button type="submit" className="submit-btn" disabled={loading || !question.trim()}>
            {loading ? "Thinking…" : "Ask"}
          </button>
        </div>
      </form>

      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            className="example-chip"
            disabled={loading}
            onClick={() => {
              setQuestion(ex);
              submit(ex);
            }}
          >
            {ex}
          </button>
        ))}
      </div>

      <section className="results" aria-live="polite">
        {loading && (
          <div className="card placeholder">
            <span className="spinner" /> Routing to tools and grounding an answer…
          </div>
        )}
        {error && !loading && <div className="card error">{error}</div>}
        {data && !loading && <AnswerCard data={data} />}
      </section>

      <footer className="page-footer">
        Grounded answers only · not financial advice · powered by a LangGraph agent
      </footer>
    </div>
  );
}
