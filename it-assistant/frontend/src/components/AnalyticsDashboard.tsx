import { useEffect, useState } from "react";
import { fetchAnalytics, type AnalyticsResponse } from "../api/client";

export function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      setData(await fetchAnalytics());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const interval = window.setInterval(refresh, 10_000);
    return () => window.clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
        Loading analytics…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 shadow-sm">
        {error}
      </div>
    );
  }

  if (!data) return null;

  const decided = data.deflected + data.escalated;
  const deflectionPct = decided ? Math.round(data.deflection_rate * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Questions asked"
          value={data.total_questions.toLocaleString()}
          hint={`${data.pending} awaiting feedback`}
        />
        <Stat
          label="Deflection rate"
          value={`${deflectionPct}%`}
          hint={`${data.deflected} of ${decided || 0} decided`}
          tone={deflectionPct >= 40 ? "good" : deflectionPct >= 20 ? "warn" : "neutral"}
        />
        <Stat
          label="Escalated"
          value={data.escalated.toLocaleString()}
          hint="Tickets sent to IT"
        />
        <Stat
          label="Time saved"
          value={`${data.estimated_time_saved_minutes} min`}
          hint="Estimated IT triage avoided"
          tone="good"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Top questions" subtitle="Reveals the highest-volume tickets in your knowledge base.">
          {data.top_questions.length === 0 ? (
            <Empty>No questions logged yet.</Empty>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.top_questions.map((q) => (
                <li key={q.query} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                  <span className="truncate text-slate-700" title={q.query}>
                    {q.query}
                  </span>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
                      ×{q.count}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 font-medium ${
                        q.deflection_rate >= 0.5
                          ? "bg-emerald-100 text-emerald-700"
                          : q.deflection_rate > 0
                            ? "bg-amber-100 text-amber-700"
                            : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {Math.round(q.deflection_rate * 100)}% deflected
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Recent escalations"
          subtitle="Tickets created when self-service didn't resolve the issue."
        >
          {data.recent_escalations.length === 0 ? (
            <Empty>No escalations yet — every question has deflected so far.</Empty>
          ) : (
            <ul className="divide-y divide-slate-100">
              {data.recent_escalations.map((e) => (
                <li key={e.ticket_id} className="py-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono text-xs font-semibold text-sky-700">
                      {e.ticket_id}
                    </span>
                    <span className="text-xs text-slate-400">
                      {new Date(e.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-slate-700" title={e.original_question}>
                    {e.original_question}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 text-xs text-slate-500 shadow-sm">
        Average answer confidence:{" "}
        <span className="font-semibold text-slate-700">
          {Math.round(data.average_confidence * 100)}%
        </span>{" "}
        · auto-refreshes every 10 seconds.
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "good" | "warn" | "neutral";
}) {
  const toneClass =
    tone === "good"
      ? "from-emerald-50 to-white ring-emerald-200"
      : tone === "warn"
        ? "from-amber-50 to-white ring-amber-200"
        : "from-slate-50 to-white ring-slate-200";

  return (
    <div className={`rounded-2xl bg-gradient-to-b p-5 ring-1 shadow-sm ${toneClass}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-3 py-6 text-center text-xs text-slate-500">
      {children}
    </div>
  );
}
