import type { AskResponse } from "./api";

// Renders one grounded answer: verdict + confidence badges, the answer text, the cited
// sources, and a compact meta footer (tools used, latency, tokens, cache hit).

function VerdictBadge({ verdict }: { verdict: AskResponse["verdict"] }) {
  const answered = verdict === "ANSWERED";
  return (
    <span className={`badge ${answered ? "badge-answered" : "badge-human"}`}>
      {answered ? "✓ Answered" : "⚠ Needs human"}
    </span>
  );
}

function ConfidenceBadge({ confidence }: { confidence: AskResponse["confidence"] }) {
  return <span className={`badge badge-conf conf-${confidence}`}>confidence: {confidence}</span>;
}

export default function AnswerCard({ data }: { data: AskResponse }) {
  const { answer, sources, confidence, verdict, meta } = data;
  return (
    <article className="card answer-card">
      <div className="badges">
        <VerdictBadge verdict={verdict} />
        <ConfidenceBadge confidence={confidence} />
        {meta?.cache_hit && <span className="badge badge-cache">cached</span>}
      </div>

      <p className="answer-text">{answer}</p>

      {sources.length > 0 && (
        <div className="sources">
          <span className="sources-label">Sources</span>
          <ul>
            {sources.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {meta && (
        <footer className="meta">
          <span title="Tools the agent called">
            🛠 {meta.tools_called.length ? meta.tools_called.join(", ") : "none"}
          </span>
          <span title="End-to-end latency">⏱ {Math.round(meta.latency_ms)} ms</span>
          <span title="Total tokens">🔢 {meta.tokens?.total ?? 0} tok</span>
          <span title="Model">{meta.model}</span>
        </footer>
      )}
    </article>
  );
}
