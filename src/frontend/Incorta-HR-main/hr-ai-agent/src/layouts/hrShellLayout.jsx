import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { FiBriefcase, FiUsers, FiChevronLeft, FiChevronRight } from "react-icons/fi";
import Navbar from "../components/navBar";

const NAV_ITEMS = [
  { to: "/hr", label: "Requisitions", icon: FiBriefcase, match: (path) => path === "/hr" || path.startsWith("/requisition/") },
  { to: "/candidates", label: "Candidates", icon: FiUsers, match: (path) => path === "/candidates" },
];

const SIDEBAR_KEY = "incorta_hr_sidebar_collapsed";

export default function HrShellLayout({ children, fullHeight = false, hideSidebar = false }) {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(SIDEBAR_KEY) === "true";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(SIDEBAR_KEY, String(collapsed));
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-canvas">
      <Navbar compact={fullHeight} />

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {!hideSidebar && (
          <aside
            className={`hidden md:flex shrink-0 flex-col border-r border-border bg-surface py-4 transition-[width] duration-200 ${
              collapsed ? "w-[68px] px-2" : "w-56 px-3"
            }`}
          >
            {!collapsed && (
              <p className="px-3 mb-2 text-[10px] font-bold uppercase tracking-[0.1em] text-muted whitespace-nowrap">
                Workspace
              </p>
            )}

            <nav className="flex flex-col gap-1 flex-1">
              {NAV_ITEMS.map(({ to, label, icon: Icon, match }) => {
                const active = match(location.pathname);
                return (
                  <Link
                    key={to}
                    to={to}
                    title={collapsed ? label : undefined}
                    className={`flex items-center rounded-[10px] text-sm font-semibold transition ${
                      collapsed ? "justify-center p-2.5" : "gap-2.5 px-3 py-2.5"
                    } ${
                      active
                        ? collapsed
                          ? "bg-brand-600/10 text-brand-700"
                          : "bg-brand-600/10 text-brand-700 border-l-[3px] border-brand-600 -ml-px pl-[11px]"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    }`}
                  >
                    <Icon size={16} className={`shrink-0 ${active ? "text-brand-600" : "text-muted"}`} />
                    {!collapsed && <span className="truncate">{label}</span>}
                  </Link>
                );
              })}
            </nav>

            <button
              type="button"
              onClick={() => setCollapsed((c) => !c)}
              className={`mt-2 flex items-center rounded-[10px] border border-border text-muted hover:bg-gray-50 hover:text-gray-900 transition ${
                collapsed ? "justify-center p-2.5 mx-auto" : "gap-2 px-3 py-2 text-xs font-semibold w-full"
              }`}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <FiChevronRight size={16} /> : <FiChevronLeft size={16} />}
              {!collapsed && <span>Collapse</span>}
            </button>
          </aside>
        )}

        <main
          className={
            fullHeight
              ? "flex-1 min-w-0 min-h-0 overflow-hidden flex flex-col max-w-none mx-0 px-0"
              : "flex-1 min-w-0 min-h-0 overflow-y-auto"
          }
        >
          {children}
        </main>
      </div>
    </div>
  );
}
