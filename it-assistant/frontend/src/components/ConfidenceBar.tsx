interface Props {
  value: number;
}

// Thresholds calibrated for sentence-transformer cosine similarities, where
// >= 0.5 is a strong on-topic match for all-MiniLM-L6-v2 in practice.
function barColor(value: number): string {
  if (value >= 0.5) return "bg-emerald-500";
  if (value >= 0.3) return "bg-amber-500";
  return "bg-rose-500";
}

function label(value: number): string {
  if (value >= 0.5) return "High confidence";
  if (value >= 0.3) return "Medium confidence";
  return "Low confidence";
}

export function ConfidenceBar({ value }: Props) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div className="flex items-center gap-3" aria-label={`${label(value)}: ${(pct * 100).toFixed(0)}%`}>
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label(value)}
      </span>
      <div className="relative h-2 w-32 overflow-hidden rounded-full bg-slate-200">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-[width] duration-500 ease-out ${barColor(value)}`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
      <span className="w-10 text-right text-sm font-semibold tabular-nums text-slate-700">
        {(pct * 100).toFixed(0)}%
      </span>
    </div>
  );
}
