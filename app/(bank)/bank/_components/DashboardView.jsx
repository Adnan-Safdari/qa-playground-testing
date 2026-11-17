"use client";

import Link from "next/link";
import {
  ArrowLeftRight,
  CirclePlus,
  History,
  KeyRound,
  PiggyBank,
  TrendingDown,
  TrendingUp,
  User,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatMoney, summarizeFinances } from "@/lib/bankStorage";
import { useBank } from "@/app/(bank)/bank/_components/AppShell";
import { Amount, CategoryBadge, PageHeader, Panel, formatDate } from "@/app/(bank)/bank/_components/ui";

const RECENT_LIMIT = 5;

const QUICK_ACTIONS = [
  { id: "qa-open-account", href: "/bank/accounts/open", icon: CirclePlus, title: "Open Account", text: "Add a checking or savings account" },
  { id: "qa-transfer", href: "/bank/transfer", icon: ArrowLeftRight, title: "Transfer Money", text: "Send funds to any account number" },
  { id: "qa-transactions", href: "/bank/transactions", icon: History, title: "Transactions", text: "View all account activity" },
  { id: "qa-profile", href: "/bank/profile", icon: User, title: "Profile", text: "Update your contact details" },
  { id: "qa-change-password", href: "/bank/change-password", icon: KeyRound, title: "Change Password", text: "Keep your account secure" },
];

const TONES = {
  brand: "bg-brand-100 text-brand-600 dark:bg-brand-950 dark:text-brand-300",
  amber: "bg-amber-100 text-amber-600 dark:bg-amber-950 dark:text-amber-300",
  emerald: "bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-300",
  rose: "bg-rose-100 text-rose-600 dark:bg-rose-950 dark:text-rose-300",
};

function StatCard({ id, icon: Icon, tone, label, cents, text, valueClass, footer }) {
  return (
    <Panel className="p-5" data-testid="stat-card">
      <div className="flex items-center gap-3">
        <span className={cn("flex h-10 w-10 items-center justify-center rounded-xl", TONES[tone])}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
        <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{label}</span>
      </div>
      <p id={id} data-testid={id} data-cents={cents} className={cn("mt-4 text-[28px] font-bold leading-tight tabular-nums", valueClass)}>
        {text}
      </p>
      <div className="mt-1 text-sm text-slate-500 dark:text-slate-400">{footer}</div>
    </Panel>
  );
}

function signedTone(cents) {
  if (cents > 0) return "text-emerald-600 dark:text-emerald-400";
  if (cents < 0) return "text-rose-600 dark:text-rose-400";
  return "text-slate-900 dark:text-white";
}

export default function DashboardView() {
  const { user, accounts, transactions } = useBank();
  const stats = summarizeFinances(accounts, transactions);
  const firstName = user.profile.fullName.split(/\s+/)[0];
  const recent = transactions.slice(0, RECENT_LIMIT);

  return (
    <>
      <PageHeader title={`Welcome back, ${firstName}`} subtitle="Here's your financial overview." />

      <section aria-label="Summary" className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          id="stat-net-worth"
          icon={Wallet}
          tone="brand"
          label="Total Net Worth"
          cents={stats.netWorth}
          text={formatMoney(stats.netWorth)}
          valueClass={stats.netWorth < 0 ? "text-rose-600 dark:text-rose-400" : "text-slate-900 dark:text-white"}
          footer={
            <span id="stat-account-count" data-testid="stat-account-count">
              Across {stats.accountCount} accounts
            </span>
          }
        />
        <StatCard
          id="stat-net-change"
          icon={PiggyBank}
          tone="amber"
          label="Net Change"
          cents={stats.netChange}
          text={formatMoney(stats.netChange, { signed: true })}
          valueClass={signedTone(stats.netChange)}
          footer="This month"
        />
        <StatCard
          id="stat-income"
          icon={TrendingUp}
          tone="emerald"
          label="Income"
          cents={stats.income}
          text={formatMoney(stats.income, { signed: true })}
          valueClass="text-emerald-600 dark:text-emerald-400"
          footer="This month"
        />
        <StatCard
          id="stat-expenses"
          icon={TrendingDown}
          tone="rose"
          label="Expenses"
          cents={stats.expenses}
          text={formatMoney(stats.expenses)}
          valueClass="text-rose-600 dark:text-rose-400"
          footer="This month"
        />
      </section>

      <section aria-labelledby="quick-actions-title" className="mt-10">
        <h2 id="quick-actions-title" className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">
          Quick Actions
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
          {QUICK_ACTIONS.map(({ id, href, icon: Icon, title, text }) => (
            <Link
              key={id}
              id={id}
              data-testid={id}
              href={href}
              className="group flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-700"
            >
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 transition group-hover:bg-brand-100 dark:bg-brand-950 dark:text-brand-300">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <span className="min-w-0">
                <span className="block font-semibold text-slate-900 dark:text-white">{title}</span>
                <span className="block text-sm text-slate-500 dark:text-slate-400">{text}</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section aria-labelledby="recent-title" className="mt-10 border-t border-slate-200 pt-8 dark:border-slate-800">
        <div className="mb-4 flex items-center justify-between">
          <h2 id="recent-title" className="text-lg font-semibold text-slate-900 dark:text-white">
            Recent Transactions
          </h2>
          <Link
            href="/bank/transactions"
            id="view-all-transactions"
            data-testid="view-all-transactions"
            className="text-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400"
          >
            View all
          </Link>
        </div>
        <Panel className="overflow-hidden">
          <div className="overflow-x-auto">
            <table id="recent-transactions" data-testid="recent-transactions" className="w-full min-w-[640px] text-left">
              <thead className="border-b border-slate-200 bg-slate-50 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <tr>
                  <th className="px-5 py-3.5 font-semibold">Date</th>
                  <th className="px-5 py-3.5 font-semibold">Description</th>
                  <th className="px-5 py-3.5 font-semibold">Category</th>
                  <th className="px-5 py-3.5 text-right font-semibold">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {recent.map((t) => (
                  <tr key={t.id} data-testid="recent-transaction-row" data-reference={t.reference || undefined}>
                    <td className="whitespace-nowrap px-5 py-4 text-sm text-slate-500 dark:text-slate-400">{formatDate(t.date)}</td>
                    <td className="px-5 py-4 font-medium text-slate-900 dark:text-white">{t.description}</td>
                    <td className="px-5 py-4">
                      <CategoryBadge category={t.category} />
                    </td>
                    <td className="whitespace-nowrap px-5 py-4 text-right">
                      <Amount cents={t.amount} testId="recent-transaction-amount" />
                    </td>
                  </tr>
                ))}
                {recent.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
                      No transactions yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>
    </>
  );
}
