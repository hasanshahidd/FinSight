import { GitBranch } from "lucide-react";

const LABELS: Record<string, string> = {
  transaction_analyst: "Transaction Analyst",
  knowledge_advisor: "Knowledge Advisor",
  budget_coach: "Budget Coach",
  anomaly_detective: "Anomaly Detective",
};

interface Props {
  route?: string;
  rationale?: string;
}

export function RouteIndicator({ route, rationale }: Props) {
  if (!route) return null;
  const label = LABELS[route] || route;

  return (
    <div className="inline-flex items-start gap-2 px-2.5 py-1.5 rounded-md bg-brand-50 border border-brand-200 max-w-full">
      <GitBranch className="h-3 w-3 text-brand-600 mt-0.5 flex-shrink-0" />
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-wider font-semibold text-brand-700">
          routed to
        </div>
        <div className="text-xs font-semibold text-brand-800 leading-tight">{label}</div>
        {rationale && (
          <div className="text-[11px] text-brand-700/80 leading-snug mt-0.5 line-clamp-2">
            {rationale}
          </div>
        )}
      </div>
    </div>
  );
}
