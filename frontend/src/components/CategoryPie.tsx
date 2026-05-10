import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { CategoryTotal } from "@/lib/types";
import { formatMoney } from "@/lib/utils";

const COLORS = [
  "#2563eb",
  "#3b82f6",
  "#60a5fa",
  "#93c5fd",
  "#1e40af",
  "#1d4ed8",
  "#bfdbfe",
];

export function CategoryPie({ items }: { items: CategoryTotal[] }) {
  return (
    <div className="flex items-center gap-4">
      <div className="h-36 w-36 flex-shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              contentStyle={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: 8,
                fontSize: 12,
              }}
              formatter={(v: number) => formatMoney(v)}
            />
            <Pie
              data={items}
              dataKey="total"
              nameKey="category"
              innerRadius={42}
              outerRadius={64}
              paddingAngle={2}
              stroke="none"
            >
              {items.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>

      <ul className="flex-1 min-w-0 space-y-1.5">
        {items.slice(0, 5).map((c, i) => (
          <li key={c.category} className="flex items-center gap-2 text-xs">
            <span
              className="h-2 w-2 rounded-full flex-shrink-0"
              style={{ background: COLORS[i % COLORS.length] }}
            />
            <span className="flex-1 truncate text-slate-700">{c.category}</span>
            <span className="font-mono text-slate-500">{formatMoney(c.total)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
