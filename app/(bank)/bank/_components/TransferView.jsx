"use client";

import { useState } from "react";
import Link from "next/link";
import { MAX_TRANSFER_CENTS, formatMoney, transferFunds } from "@/lib/bankStorage";
import { useBank } from "@/app/(bank)/bank/_components/AppShell";
import {
  Balance,
  DetailRow,
  Field,
  FormAlert,
  MoneyInput,
  PageHeader,
  Panel,
  PrimaryButton,
  SecondaryButton,
  SelectInput,
  SuccessHeader,
  TextInput,
  primaryButtonClass,
} from "@/app/(bank)/bank/_components/ui";

const EMPTY_FORM = { fromAccountNumber: "", toAccountNumber: "", amount: "", memo: "" };
const MEMO_MAX = 50;

function TransferSuccess({ result, onNewTransfer }) {
  return (
    <div id="transfer-success" data-testid="transfer-success">
      <SuccessHeader title="Transfer successful">The funds have been moved.</SuccessHeader>
      <dl className="mt-6 divide-y divide-slate-200 rounded-xl border border-slate-200 px-4 dark:divide-slate-800 dark:border-slate-800">
        <DetailRow label="Reference" valueId="transfer-reference">
          <span className="font-mono">{result.reference}</span>
        </DetailRow>
        <DetailRow label="Amount" valueId="transfer-amount" data-cents={result.amount}>
          {formatMoney(result.amount)}
        </DetailRow>
        <DetailRow label="From account" valueId="transfer-from-account">
          <span className="font-mono">{result.from.number}</span>
        </DetailRow>
        <DetailRow label="To account" valueId="transfer-to-account">
          <span className="font-mono">{result.to.number}</span>
        </DetailRow>
        <div className="flex items-center justify-between gap-4 py-3">
          <dt className="text-sm text-slate-500 dark:text-slate-400">New balance ({result.from.nickname})</dt>
          <dd className="text-sm font-semibold text-slate-900 dark:text-white">
            <Balance id="transfer-new-balance" cents={result.from.balance} />
          </dd>
        </div>
      </dl>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <SecondaryButton type="button" id="new-transfer-button" data-testid="new-transfer-button" onClick={onNewTransfer} className="flex-1">
          Make another transfer
        </SecondaryButton>
        <Link href="/bank/transactions" id="view-transactions-link" data-testid="view-transactions-link" className={`${primaryButtonClass} flex-1`}>
          View transactions
        </Link>
      </div>
    </div>
  );
}

export default function TransferView() {
  const { username, user, accounts } = useBank();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [result, setResult] = useState(null);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));
  const fromAccount = accounts.find((a) => a.number === form.fromAccountNumber);

  function handleSubmit(event) {
    event.preventDefault();
    const res = transferFunds(username, form);
    if (!res.ok) {
      setErrors(res.errors);
      return;
    }
    setErrors({});
    setResult(res);
  }

  function handleNewTransfer() {
    setForm(EMPTY_FORM);
    setResult(null);
  }

  return (
    <>
      <PageHeader title="Transfer" subtitle="Move money between your accounts or to another SecureBank customer." />

      {user.frozen && (
        <FormAlert id="frozen-notice" variant="warning" className="mb-6 max-w-5xl">
          <strong className="font-semibold">Your accounts are frozen.</strong> Outgoing transfers are disabled until the
          freeze is lifted. Please contact support.
        </FormAlert>
      )}

      <div className="grid max-w-5xl gap-6 lg:grid-cols-3">
        <Panel className="p-6 sm:p-8 lg:col-span-2">
          {result ? (
            <TransferSuccess result={result} onNewTransfer={handleNewTransfer} />
          ) : (
            <form id="transfer-form" data-testid="transfer-form" noValidate onSubmit={handleSubmit} className="space-y-5">
              {errors.form && <FormAlert id="transfer-error">{errors.form}</FormAlert>}

              <Field id="from-account" label="From account" error={errors.fromAccount}>
                <SelectInput
                  id="from-account"
                  name="from-account"
                  hasError={Boolean(errors.fromAccount)}
                  value={form.fromAccountNumber}
                  onChange={update("fromAccountNumber")}
                >
                  <option value="">Select account</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.number}>
                      {a.nickname} ({a.number}) — {formatMoney(a.balance)}
                    </option>
                  ))}
                </SelectInput>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Available balance:{" "}
                  {fromAccount ? (
                    <Balance id="available-balance" cents={fromAccount.balance} className="font-semibold text-slate-900 dark:text-white" />
                  ) : (
                    <span id="available-balance" data-testid="available-balance" className="font-semibold">
                      —
                    </span>
                  )}
                </p>
              </Field>

              <Field
                id="to-account"
                label="Recipient account number"
                error={errors.toAccount}
                hint="Any SecureBank account number (10 digits) — yours or another customer's."
              >
                <TextInput
                  id="to-account"
                  hasError={Boolean(errors.toAccount)}
                  inputMode="numeric"
                  autoComplete="off"
                  placeholder="e.g. 1002003002"
                  value={form.toAccountNumber}
                  onChange={update("toAccountNumber")}
                />
              </Field>

              <Field
                id="amount"
                label="Amount"
                error={errors.amount}
                hint={`Up to ${formatMoney(MAX_TRANSFER_CENTS)} per transaction.`}
              >
                <MoneyInput id="amount" hasError={Boolean(errors.amount)} value={form.amount} onChange={update("amount")} />
              </Field>

              <Field id="memo" label="Memo (optional)" error={errors.memo} hint={`${form.memo.length}/${MEMO_MAX} characters`}>
                <TextInput
                  id="memo"
                  hasError={Boolean(errors.memo)}
                  autoComplete="off"
                  placeholder="What's this for?"
                  value={form.memo}
                  onChange={update("memo")}
                />
              </Field>

              <div className="flex justify-end border-t border-slate-200 pt-5 dark:border-slate-800">
                <PrimaryButton type="submit" id="transfer-submit" data-testid="transfer-submit">
                  Transfer Funds
                </PrimaryButton>
              </div>
            </form>
          )}
        </Panel>

        <Panel className="h-fit p-6">
          <h2 className="text-base font-semibold text-slate-900 dark:text-white">Your accounts</h2>
          <ul id="own-accounts" className="mt-4 divide-y divide-slate-200 dark:divide-slate-800">
            {accounts.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 py-3" data-testid="own-account" data-account-number={a.number}>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900 dark:text-white">{a.nickname}</p>
                  <p className="font-mono text-xs text-slate-500 dark:text-slate-400">{a.number}</p>
                </div>
                <Balance cents={a.balance} testId="own-account-balance" className="text-sm font-semibold text-slate-900 dark:text-white" />
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}
