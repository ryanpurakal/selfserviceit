import { useMemo, useState } from "react";
import { marked } from "marked";

import {
  askQuestion,
  escalateTicket,
  recordFeedback,
  type AnswerResponse,
} from "../api/client";
import { ConfidenceBar } from "./ConfidenceBar";
import { SourceCard } from "./SourceCard";

const SUGGESTIONS = [
  "I can't connect to the VPN",
  "How do I reset my password?",
  "My laptop won't turn on",
  "WiFi keeps asking me to authenticate",
  "How do I add a printer?",
];

type Stage = "idle" | "loading" | "answer" | "deflected" | "escalated" | "error";

interface EscalationState {
  ticketId: string;
}

export function ChatInterface() {
  const [question, setQuestion] = useState("");
  const [activeQuestion, setActiveQuestion] = useState("");
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [escalation, setEscalation] = useState<EscalationState | null>(null);
  const [escalating, setEscalating] = useState(false);

  marked.setOptions({ breaks: true, gfm: true });

  const renderedAnswer = useMemo(() => {
    if (!answer) return "";
    return marked.parse(answer.answer) as string;
  }, [answer]);

  const reset = () => {
    setQuestion("");
    setActiveQuestion("");
    setAnswer(null);
    setStage("idle");
    setError(null);
    setEscalation(null);
  };

  const submit = async (queryOverride?: string) => {
    const query = (queryOverride ?? question).trim();
    if (!query) return;

    setQuestion(query);
    setActiveQuestion(query);
    setStage("loading");
    setAnswer(null);
    setError(null);
    setEscalation(null);

    try {
      const response = await askQuestion(query);
      setAnswer(response);
      setStage("answer");
    } catch (err) {
      setStage("error");
      setError(err instanceof Error ? err.message : "Something went wrong.");
    }
  };

  const handleDeflect = async () => {
    if (!answer) return;
    try {
      await recordFeedback(answer.question_id, true);
    } catch {
      // Non-blocking; analytics will catch up next time.
    }
    setStage("deflected");
  };

  const handleEscalate = async () => {
    if (!answer) return;
    setEscalating(true);
    try {
      const result = await escalateTicket({
        question_id: answer.question_id,
        original_question: activeQuestion,
        attempted_solutions: answer.sources.map(
          (s) => `${s.source}: ${s.text.slice(0, 200)}`,
        ),
        user_feedback: "User reported the self-service answer didn't resolve the issue.",
      });
      setEscalation({ ticketId: result.ticket_id });
      setStage("escalated");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket.");
      setStage("error");
    } finally {
      setEscalating(false);
    }
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <label htmlFor="question" className="block text-sm font-medium text-slate-700">
          What do you need help with?
        </label>
        <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 focus-within:border-sky-400 focus-within:bg-white focus-within:ring-2 focus-within:ring-sky-100">
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="e.g. I can't connect to the VPN and Okta keeps timing out"
            rows={3}
            className="w-full resize-none rounded-xl bg-transparent p-4 text-sm text-slate-900 outline-none placeholder:text-slate-400"
          />
          <div className="flex items-center justify-between border-t border-slate-200 px-4 py-2.5">
            <span className="text-xs text-slate-500">
              <kbd className="rounded border border-slate-300 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                ⌘
              </kbd>{" "}
              +{" "}
              <kbd className="rounded border border-slate-300 bg-white px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                Enter
              </kbd>{" "}
              to submit
            </span>
            <button
              type="button"
              onClick={() => submit()}
              disabled={stage === "loading" || !question.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {stage === "loading" ? (
                <>
                  <Spinner /> Searching docs…
                </>
              ) : (
                <>
                  Ask the assistant
                  <ArrowIcon />
                </>
              )}
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-400">Try:</span>
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => submit(suggestion)}
              className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </section>

      {stage === "error" && error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          <p className="font-semibold">Something went wrong</p>
          <p className="mt-1">{error}</p>
        </div>
      )}

      {(stage === "answer" || stage === "deflected" || stage === "escalated") && answer && (
        <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Question</p>
              <p className="mt-1 text-sm font-medium text-slate-700">{activeQuestion}</p>
            </div>
            <div className="flex items-center gap-3">
              {!answer.used_llm && (
                <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                  Template fallback
                </span>
              )}
              <ConfidenceBar value={answer.confidence} />
            </div>
          </header>

          <article className="answer-prose" dangerouslySetInnerHTML={{ __html: renderedAnswer }} />

          {answer.related_topics.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Related topics</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {answer.related_topics.map((topic) => (
                  <span
                    key={topic}
                    className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-medium text-sky-700"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {answer.sources.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">Sources</p>
              <ul className="mt-2 space-y-2">
                {answer.sources.map((source, idx) => (
                  <SourceCard key={source.chunk_id || idx} source={source} index={idx} />
                ))}
              </ul>
            </div>
          )}

          {stage === "answer" && (
            <FeedbackPrompt
              onDeflect={handleDeflect}
              onEscalate={handleEscalate}
              escalating={escalating}
            />
          )}

          {stage === "deflected" && <DeflectedBanner onReset={reset} />}
          {stage === "escalated" && escalation && (
            <EscalatedBanner ticketId={escalation.ticketId} onReset={reset} />
          )}
        </section>
      )}
    </div>
  );
}

function FeedbackPrompt({
  onDeflect,
  onEscalate,
  escalating,
}: {
  onDeflect: () => void;
  onEscalate: () => void;
  escalating: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50/70 p-4">
      <p className="text-sm font-medium text-amber-900">Did this solve your problem?</p>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onDeflect}
          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700"
        >
          <CheckIcon />
          Yes, I'm all set
        </button>
        <button
          type="button"
          onClick={onEscalate}
          disabled={escalating}
          className="inline-flex items-center gap-2 rounded-lg border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-600 shadow-sm transition hover:bg-rose-50 disabled:opacity-50"
        >
          {escalating ? <Spinner /> : <TicketIcon />}
          {escalating ? "Creating ticket…" : "No, escalate to IT"}
        </button>
      </div>
    </div>
  );
}

function DeflectedBanner({ onReset }: { onReset: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-emerald-500 text-white">
          <CheckIcon />
        </span>
        <div>
          <p className="text-sm font-semibold text-emerald-900">Ticket deflected</p>
          <p className="text-xs text-emerald-700">
            Saved the IT team an estimated 12 minutes of triage. Logged for analytics.
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onReset}
        className="text-sm font-semibold text-emerald-800 hover:text-emerald-900"
      >
        Ask another question →
      </button>
    </div>
  );
}

function EscalatedBanner({ ticketId, onReset }: { ticketId: string; onReset: () => void }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-sky-200 bg-sky-50 p-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-sky-600 text-white">
          <TicketIcon />
        </span>
        <div>
          <p className="text-sm font-semibold text-sky-900">
            Ticket {ticketId} created
          </p>
          <p className="text-xs text-sky-700">
            The IT team has the original question and the suggestions you saw. Expect a follow-up
            in Slack soon.
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onReset}
        className="text-sm font-semibold text-sky-800 hover:text-sky-900"
      >
        Ask another question →
      </button>
    </div>
  );
}

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeOpacity="0.25" strokeWidth="4" />
      <path
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M5 12h14m0 0-5-5m5 5-5 5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M5 13l4 4L19 7"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TicketIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4V8Zm6 0v8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
