import { ArrowDownRight, ArrowUpRight, BookOpen, FolderTree, ReceiptText, TrendingUp, Wallet2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { CategoryPie } from "@/components/CategoryPie";
import { SpendingChart } from "@/components/SpendingChart";
import {
  fetchSummary,
  fetchTransactions,
  fetchTrend,
} from "@/lib/api";
import type { SpendingSummary, Transaction, TrendResponse } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/utils";

interface Ctx {
  persona: { activeId: string };
}

export function DashboardPage() {
  const { persona } = useOutletContext<Ctx>();
  const [summary, setSummary] = useState<SpendingSummary | null>(null);
  const [trend, setTrend] = useState<TrendResponse | null>(null);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    (async () => {
      try {
        const [s, t, txns] = await Promise.all([
          fetchSummary("last_30_days"),
          fetchTrend("last_30_days"),
          fetchTransactions({ limit: 10 }),
        ]);
        if (!alive) return;
        setSummary(s);
        setTrend(t);
        setRecent(txns);
      } catch {
        // backend may not be up
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [persona.activeId]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-8 py-6 space-y-5">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Spending overview</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Last 30 days · auto-derived from your mock-banking transactions
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Stat
            label="Total spent"
            value={summary ? formatMoney(summary.total_spent) : "-"}
            icon={<Wallet2 className="h-4 w-4" />}
            delta={trend?.pct_change_vs_previous}
            loading={loading}
          />
          <Stat
            label="Total income"
            value={summary ? formatMoney(summary.total_income) : "-"}
            icon={<TrendingUp className="h-4 w-4" />}
            tone="positive"
            loading={loading}
          />
          <Stat
            label="Net"
            value={summary ? formatMoney(summary.net) : "-"}
            icon={<TrendingUp className="h-4 w-4" />}
            tone={summary && summary.net >= 0 ? "positive" : "negative"}
            loading={loading}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card title="Spending trend" subtitle="last 30 days" icon={<TrendingUp className="h-4 w-4" />}>
            {trend ? (
              <SpendingChart data={trend.points} />
            ) : (
              <Skeleton h="h-40" />
            )}
          </Card>
          <Card title="Top categories" subtitle="last 30 days" icon={<FolderTree className="h-4 w-4" />}>
            {summary && summary.top_categories.length > 0 ? (
              <CategoryPie items={summary.top_categories} />
            ) : (
              <Skeleton h="h-36" />
            )}
          </Card>
        </div>

        <Card title="Recent transactions" subtitle={`${recent.length} most recent`} icon={<ReceiptText className="h-4 w-4" />}>
          {recent.length === 0 ? (
            <Skeleton h="h-32" />
          ) : (
            <ul className="divide-y divide-slate-100 -mx-2">
              {recent.map((t) => (
                <li key={t.id} className="flex items-center gap-3 px-2 py-2.5">
                  <div className="h-8 w-8 rounded-md bg-slate-100 grid place-items-center text-xs font-semibold text-slate-600 flex-shrink-0">
                    {t.merchant.slice(0, 1).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-900 truncate">{t.merchant}</div>
                    <div className="text-[11px] text-slate-500">
                      {t.category} · {formatDate(t.timestamp)}
                    </div>
                  </div>
                  <div className={`text-sm font-mono font-semibold ${t.amount < 0 ? "text-slate-700" : "text-emerald-600"}`}>
                    {formatMoney(t.amount)}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Knowledge base" subtitle="powering RAG advice" icon={<BookOpen className="h-4 w-4" />}>
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <div className="h-2 w-2 rounded-full bg-emerald-500" />
            21 documents · ~131 chunks · hybrid retrieval (dense + BM25)
          </div>
        </Card>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  icon,
  delta,
  tone = "neutral",
  loading,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  delta?: number | null;
  tone?: "neutral" | "positive" | "negative";
  loading?: boolean;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {label}
        </span>
        <span className="text-slate-400">{icon}</span>
      </div>
      <div className="flex items-end justify-between gap-2">
        <div className="text-2xl font-bold tracking-tight text-slate-900 tabular-nums">
          {loading ? <span className="opacity-30">···</span> : value}
        </div>
        {delta != null && (
          <span
            className={`flex items-center gap-0.5 text-xs font-semibold ${
              delta >= 0 ? "text-rose-600" : "text-emerald-600"
            }`}
          >
            {delta >= 0 ? (
              <ArrowUpRight className="h-3 w-3" />
            ) : (
              <ArrowDownRight className="h-3 w-3" />
            )}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>
      {tone === "positive" && (
        <div className="mt-1 text-[11px] text-emerald-600">Income inflow</div>
      )}
      {tone === "negative" && (
        <div className="mt-1 text-[11px] text-rose-600">Net outflow</div>
      )}
    </div>
  );
}

function Card({
  title,
  subtitle,
  icon,
  children,
}: {
  title: string;
  subtitle?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <span className="text-brand-600">{icon}</span>
          {title}
        </div>
        {subtitle && <span className="text-[11px] text-slate-500">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

function Skeleton({ h = "h-20" }: { h?: string }) {
  return <div className={`${h} rounded-lg bg-slate-100 animate-pulse`} />;
}
