"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import {
  ArrowLeftRight,
  CirclePlus,
  CreditCard,
  History,
  KeyRound,
  Landmark,
  LayoutGrid,
  LogOut,
  Menu,
  Moon,
  Sun,
  User,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { compareTransactionsNewestFirst, logout, SLOW_USER_DELAY_MS } from "@/lib/bankStorage";
import { useBankDb, useIsClient, useSessionUsername } from "@/app/(bank)/bank/_components/bankHooks";
import { PageLoader } from "@/app/(bank)/bank/_components/ui";

const NAV_SECTIONS = [
  {
    label: "Main",
    items: [
      { href: "/bank/dashboard", label: "Dashboard", icon: LayoutGrid, id: "nav-dashboard" },
      { href: "/bank/accounts", label: "Accounts", icon: CreditCard, id: "nav-accounts" },
      { href: "/bank/accounts/open", label: "Open Account", icon: CirclePlus, id: "nav-open-account" },
      { href: "/bank/transfer", label: "Transfer", icon: ArrowLeftRight, id: "nav-transfer" },
      { href: "/bank/transactions", label: "Transactions", icon: History, id: "nav-transactions" },
    ],
  },
  {
    label: "Account",
    items: [
      { href: "/bank/profile", label: "Profile", icon: User, id: "nav-profile" },
      { href: "/bank/change-password", label: "Change Password", icon: KeyRound, id: "nav-change-password" },
    ],
  },
];

const BankContext = createContext(null);

/** { username, user, accounts, transactions } for the logged-in user. */
export function useBank() {
  return useContext(BankContext);
}

export function initials(name) {
  return (name || "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isClient = useIsClient();
  const dark = isClient && resolvedTheme === "dark";
  return (
    <button
      type="button"
      id="theme-toggle"
      data-testid="theme-toggle"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-slate-100 text-slate-600 transition hover:bg-slate-200 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
    >
      {dark ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
    </button>
  );
}

function SidebarNav({ pathname, onNavigate }) {
  return (
    <nav aria-label="Main navigation" id="sidebar-nav" className="flex-1 space-y-6 overflow-y-auto px-3 py-6">
      {NAV_SECTIONS.map((section, i) => (
        <div key={section.label} className={cn(i > 0 && "border-t border-slate-200 pt-6 dark:border-slate-800")}>
          <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {section.label}
          </p>
          <ul className="space-y-1">
            {section.items.map(({ href, label, icon: Icon, id }) => {
              const active = pathname === href;
              return (
                <li key={href}>
                  <Link
                    href={href}
                    id={id}
                    data-testid={id}
                    aria-current={active ? "page" : undefined}
                    onClick={onNavigate}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] font-medium transition",
                      active
                        ? "bg-brand-600 text-white shadow-sm"
                        : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
                    )}
                  >
                    <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export default function AppShell({ children }) {
  const pathname = usePathname();
  const username = useSessionUsername();
  const db = useBankDb();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [readyPath, setReadyPath] = useState(null);
  const loggingOut = useRef(false);

  // Auth guard: no session → back to login.
  useEffect(() => {
    if (username === null && !loggingOut.current) window.location.replace("/bank/login?reason=auth");
  }, [username]);

  const rawUser = username && db ? db.users[username] : null;
  const slow = Boolean(rawUser?.slow);

  // slow_user: every page waits before showing data (exercise explicit waits).
  useEffect(() => {
    if (!slow) return undefined;
    const timer = setTimeout(() => setReadyPath(pathname), SLOW_USER_DELAY_MS);
    return () => clearTimeout(timer);
  }, [slow, pathname]);
  const ready = !slow || readyPath === pathname;

  const value = useMemo(() => {
    if (!rawUser) return null;
    const { password: _password, ...user } = rawUser;
    const accounts = db.accounts.filter((a) => a.owner === username);
    const transactions = db.transactions.filter((t) => t.owner === username).sort(compareTransactionsNewestFirst);
    return { username, user, accounts, transactions };
  }, [db, rawUser, username]);

  function handleLogout() {
    loggingOut.current = true;
    logout();
    window.location.replace("/bank/login?reason=logged_out");
  }

  if (!value) return <PageLoader />;

  return (
    <BankContext.Provider value={value}>
      <div className="flex min-h-screen flex-col">
        {/* Top bar */}
        <header
          id="app-header"
          className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-slate-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-900 sm:px-5"
        >
          <div className="flex items-center gap-3">
            <button
              type="button"
              id="mobile-menu-toggle"
              data-testid="mobile-menu-toggle"
              aria-label={mobileOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen((o) => !o)}
              className="rounded-lg p-2 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 lg:hidden"
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
            <Link href="/bank/dashboard" id="brand-link" data-testid="brand-link" className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
                <Landmark className="h-5 w-5" aria-hidden="true" />
              </span>
              <span className="text-lg font-bold text-slate-900 dark:text-white">SecureBank</span>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <button
              type="button"
              id="logout-button"
              data-testid="logout-button"
              onClick={handleLogout}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-[15px] font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
            >
              <LogOut className="h-[18px] w-[18px]" aria-hidden="true" />
              Logout
            </button>
          </div>
        </header>

        <div className="flex flex-1">
          {/* Sidebar */}
          <aside
            id="sidebar"
            className={cn(
              "fixed inset-y-0 left-0 top-[72px] z-20 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform dark:border-slate-800 dark:bg-slate-900",
              "lg:sticky lg:h-[calc(100vh-72px)] lg:translate-x-0",
              mobileOpen ? "translate-x-0" : "-translate-x-full",
            )}
          >
            <SidebarNav pathname={pathname} onNavigate={() => setMobileOpen(false)} />
            <div className="mx-3 flex items-center gap-3 border-t border-slate-200 px-3 py-4 dark:border-slate-800">
              <span
                id="user-avatar"
                className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white"
              >
                {initials(value.user.profile.fullName)}
              </span>
              <div className="min-w-0">
                <p id="user-full-name" data-testid="user-full-name" className="truncate text-sm font-medium text-slate-900 dark:text-white">
                  {value.user.profile.fullName}
                </p>
                <p id="current-username" data-testid="current-username" className="truncate text-xs text-slate-500 dark:text-slate-400">
                  {username}
                </p>
              </div>
            </div>
          </aside>

          {mobileOpen && (
            <button
              type="button"
              aria-label="Close menu"
              className="fixed inset-0 top-[72px] z-10 bg-slate-900/30 lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
          )}

          {/* Content */}
          <main id="main-content" className="min-w-0 flex-1 px-4 py-8 sm:px-8">
            <div className="mx-auto max-w-7xl">{ready ? children : <PageLoader />}</div>
          </main>
        </div>
      </div>
    </BankContext.Provider>
  );
}
