import { useState } from "react";
import { ChatInterface } from "./components/ChatInterface";
import { AnalyticsDashboard } from "./components/AnalyticsDashboard";
import { TabNavigation, type AssistantTab } from "./components/TabNavigation";

type ViewTab = "chat" | "analytics";

const CHAT_CONFIG: Record<
  AssistantTab,
  {
    collectionName: "it_docs" | "onboarding_docs";
    placeholder: string;
    systemContext: string;
  }
> = {
  it: {
    collectionName: "it_docs",
    placeholder: "Ask about VPN, passwords, WiFi, access issues...",
    systemContext: "IT support",
  },
  onboarding: {
    collectionName: "onboarding_docs",
    placeholder: "Ask about trading protocols, compliance, platform tools...",
    systemContext: "trader onboarding",
  },
};

export default function App() {
  const [viewTab, setViewTab] = useState<ViewTab>("chat");
  const [activeTab, setActiveTab] = useState<AssistantTab>("it");
  const chatConfig = CHAT_CONFIG[activeTab];

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/70 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-900 text-white shadow-sm">
              <Logo />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900">Trumid Assistants</p>
              <p className="text-xs text-slate-500">
                IT self-service and trader onboarding in one place.
              </p>
            </div>
          </div>
          <nav className="flex items-center gap-1 rounded-full bg-slate-100 p-1 text-sm">
            <TabButton active={viewTab === "chat"} onClick={() => setViewTab("chat")}>
              Ask
            </TabButton>
            <TabButton
              active={viewTab === "analytics"}
              onClick={() => setViewTab("analytics")}
            >
              Analytics
            </TabButton>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        {viewTab === "chat" ? (
          <div className="space-y-6">
            <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
            <ChatInterface
              key={activeTab}
              collectionName={chatConfig.collectionName}
              placeholder={chatConfig.placeholder}
              systemContext={chatConfig.systemContext}
            />
          </div>
        ) : (
          <AnalyticsDashboard />
        )}
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
