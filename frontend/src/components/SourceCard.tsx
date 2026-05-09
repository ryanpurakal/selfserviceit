import type { Source } from "../api/client";

interface Props {
  source: Source;
  index: number;
}

// Thresholds calibrated for sentence-transformer cosine similarities;
// >= 0.5 is a strong semantic match for all-MiniLM-L6-v2 in practice.
function relevanceTone(score: number): string {
  if (score >= 0.5) return "bg-emerald-100 text-emerald-700 ring-emerald-200";
  if (score >= 0.3) return "bg-amber-100 text-amber-700 ring-amber-200";
  return "bg-slate-100 text-slate-600 ring-slate-200";
}

function relevanceLabel(score: number): string {
  if (score >= 0.5) return "Strong match";
  if (score >= 0.3) return "Partial match";
  return "Weak match";
}

export function SourceCard({ source, index }: Props) {
  const preview = source.text.length > 220 ? `${source.text.slice(0, 220).trim()}…` : source.text;

  return (
    <li className="group rounded-lg border border-slate-200 bg-white/70 p-4 shadow-sm transition hover:border-slate-300 hover:shadow-md">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <span className="grid h-6 w-6 place-items-center rounded-full bg-slate-900 text-xs text-white">
            {index + 1}
          </span>
          <span className="truncate" title={source.source}>
            {source.source}
          </span>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${relevanceTone(
            source.relevance,
          )}`}
        >
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-current" />
          {relevanceLabel(source.relevance)} · {(source.relevance * 100).toFixed(0)}%
        </span>
      </div>
      <p className="mt-2 whitespace-pre-line text-sm text-slate-600">{preview}</p>
    </li>
  );
}
