import { useState } from "react";
import { ChatInterface } from "./components/ChatInterface";
import { AnalyticsDashboard } from "./components/AnalyticsDashboard";

type Tab = "chat" | "analytics";

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-900 text-white shadow-sm">
              <Logo />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Trumid IT Assistant</p>
              <p className="text-xs text-slate-500">Self-service answers, with a ticket fallback.</p>
            </div>
          </div>
          <nav className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-sm">
            <TabButton active={tab === "chat"} onClick={() => setTab("chat")}>
              Ask
            </TabButton>
            <TabButton active={tab === "analytics"} onClick={() => setTab("analytics")}>
              Analytics
            </TabButton>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        {tab === "chat" ? <ChatInterface /> : <AnalyticsDashboard />}
      </main>

      <footer className="border-t border-slate-200/70 bg-white/60">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-2 px-4 py-4 text-xs text-slate-500 sm:flex-row sm:px-6">
          <span>RAG over local docs · ChromaDB · FastAPI · Gemini</span>
          <span>Prototype for the Trumid interview · v0.1.0</span>
        </div>
      </footer>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 font-medium transition ${
        active
          ? "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
          : "text-slate-500 hover:text-slate-800"
      }`}
    >
      {children}
    </button>
  );
}

function Logo() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M5 18 L12 6 L19 18 L15.5 18 L12 12 L8.5 18 Z"
        fill="#38bdf8"
      />
      <circle cx="12" cy="20" r="1.25" fill="#38bdf8" />
    </svg>
  );
}
