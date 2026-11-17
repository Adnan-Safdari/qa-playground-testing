"use client";

import Link from "next/link";
import { CirclePlus, CreditCard, PiggyBank } from "lucide-react";
import { ACCOUNT_TYPES, formatMoney } from "@/lib/bankStorage";
import { cn } from "@/lib/utils";
import { useBank } from "@/app/(bank)/bank/_components/AppShell";
import { Balance, PageHeader, Panel, formatDate, primaryButtonClass } from "@/app/(bank)/bank/_components/ui";

export function accountTypeLabel(type) {
  return ACCOUNT_TYPES.find((t) => t.value === type)?.label ?? type;
}

function AccountCard({ account }) {
  const Icon = account.type === "savings" ? PiggyBank : CreditCard;
  return (
    <Panel data-testid="account-card" data-account-number={account.number} className="flex flex-col p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-950 dark:text-brand-300">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <h2 data-testid="account-nickname" className="truncate font-semibold text-slate-900 dark:text-white">
              {account.nickname}
            </h2>
            <p className="font-mono text-sm text-slate-500 dark:text-slate-400" data-testid="account-number">
              {account.number}
            </p>
          </div>
        </div>
        <span
          data-testid="account-type"
          className="shrink-0 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
        >
          {accountTypeLabel(account.type)}
        </span>
      </div>
      <div className="mt-6">
        <p className="text-sm text-slate-500 dark:text-slate-400">Available balance</p>
        <Balance
          testId="account-balance"
          cents={account.balance}
          className="mt-1 block text-[28px] font-bold leading-tight text-slate-900 dark:text-white"
        />
      </div>
      <p className="mt-4 border-t border-slate-200 pt-4 text-xs text-slate-500 dark:border-slate-800 dark:text-slate-400">
        Opened {formatDate(account.openedAt)}
      </p>
    </Panel>
  );
}

export default function AccountsView() {
  const { accounts } = useBank();
  const total = accounts.reduce((sum, a) => sum + a.balance, 0);

  return (
    <>
      <PageHeader
        title="Accounts"
        subtitle={`${accounts.length} ${accounts.length === 1 ? "account" : "accounts"} · Total balance ${formatMoney(total)}`}
        action={
          <Link href="/bank/accounts/open" id="open-account-button" data-testid="open-account-button" className={primaryButtonClass}>
            <CirclePlus className="h-4 w-4" aria-hidden="true" />
            Open Account
          </Link>
        }
      />
      <div id="account-list" data-testid="account-list" className={cn("grid gap-5 md:grid-cols-2 xl:grid-cols-3")}>
        {accounts.map((account) => (
          <AccountCard key={account.id} account={account} />
        ))}
      </div>
    </>
  );
}
