export type AssistantTab = "it" | "onboarding";

interface TabNavigationProps {
  activeTab: AssistantTab;
  onTabChange: (tab: AssistantTab) => void;
}

const TABS: {
  id: AssistantTab;
  title: string;
  description: string;
}[] = [
  {
    id: "it",
    title: "IT Support",
    description: "Self-service for technical issues",
  },
  {
    id: "onboarding",
    title: "Trader Onboarding",
    description: "Platform and compliance guidance",
  },
];

export function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`rounded-2xl border p-4 text-left transition ${
              isActive
                ? "border-sky-300 bg-white shadow-sm ring-2 ring-sky-100"
                : "border-slate-200 bg-slate-50/80 hover:border-slate-300 hover:bg-white"
            }`}
          >
            <h3
              className={`text-sm font-semibold ${
                isActive ? "text-slate-900" : "text-slate-600"
              }`}
            >
              {tab.title}
            </h3>
            <p
              className={`mt-1 text-xs ${
                isActive ? "text-slate-600" : "text-slate-400"
              }`}
            >
              {tab.description}
            </p>
          </button>
        );
      })}
    </div>
  );
}
