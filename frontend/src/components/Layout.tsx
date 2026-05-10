import { LayoutDashboard, MessageSquare, Wallet } from "lucide-react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { DataSourcesPanel } from "./DataSourcesPanel";
import { PersonaSwitcher } from "./PersonaSwitcher";
import { usePersona } from "@/hooks/usePersona";
import { cn } from "@/lib/utils";

export function Layout() {
  const persona = usePersona();

  return (
    <div className="h-screen flex bg-slate-50 overflow-hidden">
      {/* Left sidebar */}
      <aside className="w-60 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col">
        <Link
          to="/"
          className="flex items-center gap-2.5 px-5 h-14 border-b border-slate-200"
        >
          <div className="h-8 w-8 rounded-lg bg-brand-600 grid place-items-center">
            <Wallet className="h-4 w-4 text-white" />
          </div>
          <div>
            <div className="font-semibold text-slate-900 tracking-tight leading-none">
              FinSight
            </div>
            <div className="text-[10px] uppercase tracking-wider text-slate-400 mt-0.5">
              AI · Finance
            </div>
          </div>
        </Link>

        <nav className="px-3 py-3 space-y-0.5">
          <SideNavItem to="/" icon={<LayoutDashboard className="h-4 w-4" />} label="Dashboard" exact />
          <SideNavItem to="/chat" icon={<MessageSquare className="h-4 w-4" />} label="Chat" />
        </nav>

        <div className="flex-1" />

        <div className="px-3 pb-4">
          <DataSourcesPanel />
        </div>
      </aside>

      {/* Right column: blue top bar + main content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex-shrink-0 bg-gradient-to-r from-brand-700 to-brand-600 text-white">
          <div className="flex h-14 items-center justify-between px-6">
            <div className="min-w-0">
              <div className="text-xs text-brand-100 leading-none">
                Welcome back
              </div>
              <div className="font-semibold text-white tracking-tight truncate mt-0.5">
                {persona.active?.name ?? "FinSight user"}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden md:flex items-center gap-1.5 text-xs text-brand-100 px-2.5 py-1 rounded-md bg-white/10">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
                agent online
              </div>
              <PersonaSwitcher
                users={persona.users}
                activeId={persona.activeId}
                onSelect={persona.switchTo}
                loading={persona.loading}
                onBlueBackground
              />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-hidden flex flex-col">
          <Outlet context={{ persona }} />
        </main>
      </div>
    </div>
  );
}

function SideNavItem({
  to,
  icon,
  label,
  exact,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  exact?: boolean;
}) {
  return (
    <NavLink
      to={to}
      end={exact}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-md transition",
          isActive
            ? "bg-brand-50 text-brand-700"
            : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
        )
      }
    >
      {icon}
      {label}
    </NavLink>
  );
}
