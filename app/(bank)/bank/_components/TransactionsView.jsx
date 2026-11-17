"use client";

import { useState } from "react";
import { Inbox } from "lucide-react";
import { useBank } from "@/app/(bank)/bank/_components/AppShell";
import { Amount, Balance, CategoryBadge, PageHeader, Panel, SelectInput, formatDate } from "@/app/(bank)/bank/_components/ui";

/** Account number of a transaction (older rows only carry accountId = "acc_<number>"). */
function txnAccountNumber(t) {
  return t.accountNumber || t.accountId.replace(/^acc_/, "");
}

export default function TransactionsView() {
  const { accounts, transactions } = useBank();
  const [accountFilter, setAccountFilter] = useState("");
  const rows = accountFilter ? transactions.filter((t) => txnAccountNumber(t) === accountFilter) : transactions;

  return (
    <>
      <PageHeader title="Transactions" subtitle="Your complete account activity, newest first." />

      <Panel className="overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-200 p-5 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
            <label htmlFor="account-filter" className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Account
            </label>
            <SelectInput
              id="account-filter"
              name="account-filter"
              value={accountFilter}
              onChange={(e) => setAccountFilter(e.target.value)}
              className="sm:w-80"
            >
              <option value="">All accounts</option>
              {accounts.map((a) => (
                <option key={a.id} value={a.number}>
                  {a.nickname} ({a.number})
                </option>
              ))}
            </SelectInput>
          </div>
          <p id="transaction-count" data-testid="transaction-count" className="text-sm text-slate-500 dark:text-slate-400">
            {rows.length} {rows.length === 1 ? "transaction" : "transactions"}
          </p>
        </div>

        {rows.length === 0 ? (
          <div id="no-transactions" data-testid="no-transactions" className="flex flex-col items-center px-5 py-16 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800">
              <Inbox className="h-6 w-6" aria-hidden="true" />
            </span>
            <p className="mt-4 font-medium text-slate-900 dark:text-white">No transactions found</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">There is no activity for this account yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table id="transactions-table" data-testid="transactions-table" className="w-full min-w-[860px] text-left">
              <thead className="border-b border-slate-200 bg-slate-50 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
                <tr>
                  <th className="px-5 py-3.5 font-semibold">Date</th>
                  <th className="px-5 py-3.5 font-semibold">Description</th>
                  <th className="px-5 py-3.5 font-semibold">Account</th>
                  <th className="px-5 py-3.5 font-semibold">Category</th>
                  <th className="px-5 py-3.5 text-right font-semibold">Amount</th>
                  <th className="px-5 py-3.5 text-right font-semibold">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {rows.map((t) => (
                  <tr
                    key={t.id}
                    data-testid="transaction-row"
                    data-transaction-id={t.id}
                    data-reference={t.reference || undefined}
                    data-account-number={txnAccountNumber(t)}
                  >
                    <td data-testid="transaction-date" className="whitespace-nowrap px-5 py-4 text-sm text-slate-500 dark:text-slate-400">
                      {formatDate(t.date)}
                    </td>
                    <td data-testid="transaction-description" className="px-5 py-4 font-medium text-slate-900 dark:text-white">
                      {t.description}
                    </td>
                    <td data-testid="transaction-account" className="whitespace-nowrap px-5 py-4 font-mono text-sm text-slate-600 dark:text-slate-300">
                      {txnAccountNumber(t)}
                    </td>
                    <td className="px-5 py-4">
                      <CategoryBadge category={t.category} />
                    </td>
                    <td className="whitespace-nowrap px-5 py-4 text-right">
                      <Amount cents={t.amount} testId="transaction-amount" />
                    </td>
                    <td className="whitespace-nowrap px-5 py-4 text-right text-sm text-slate-600 dark:text-slate-300">
                      <Balance cents={t.balanceAfter} testId="transaction-balance" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
