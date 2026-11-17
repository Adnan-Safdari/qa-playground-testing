"use client";

import { useState } from "react";
import Link from "next/link";
import { ACCOUNT_TYPES, MIN_OPENING_DEPOSIT_CENTS, formatMoney, openAccount } from "@/lib/bankStorage";
import { useBank } from "@/app/(bank)/bank/_components/AppShell";
import { accountTypeLabel } from "@/app/(bank)/bank/_components/AccountsView";
import {
  Balance,
  Checkbox,
  DetailRow,
  Field,
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

const EMPTY_FORM = { type: "", nickname: "", initialDeposit: "", acceptTerms: false };

function OpenAccountSuccess({ account, onOpenAnother }) {
  return (
    <div id="open-account-success" data-testid="open-account-success">
      <SuccessHeader title="Account opened successfully">Your new account is ready to use.</SuccessHeader>
      <dl className="mt-6 divide-y divide-slate-200 rounded-xl border border-slate-200 px-4 dark:divide-slate-800 dark:border-slate-800">
        <DetailRow label="Account number" valueId="new-account-number">
          <span className="font-mono">{account.number}</span>
        </DetailRow>
        <DetailRow label="Nickname" valueId="new-account-nickname">
          {account.nickname}
        </DetailRow>
        <DetailRow label="Type" valueId="new-account-type">
          {accountTypeLabel(account.type)}
        </DetailRow>
        <div className="flex items-center justify-between gap-4 py-3">
          <dt className="text-sm text-slate-500 dark:text-slate-400">Opening balance</dt>
          <dd className="text-sm font-semibold text-slate-900 dark:text-white">
            <Balance id="new-account-balance" cents={account.balance} />
          </dd>
        </div>
      </dl>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <SecondaryButton type="button" id="open-another-account" data-testid="open-another-account" onClick={onOpenAnother} className="flex-1">
          Open another account
        </SecondaryButton>
        <Link href="/bank/accounts" id="view-accounts" data-testid="view-accounts" className={`${primaryButtonClass} flex-1`}>
          View accounts
        </Link>
      </div>
    </div>
  );
}

export default function OpenAccountView() {
  const { username } = useBank();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [created, setCreated] = useState(null);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  function handleSubmit(event) {
    event.preventDefault();
    const res = openAccount(username, form);
    if (!res.ok) {
      setErrors(res.errors);
      return;
    }
    setErrors({});
    setCreated(res.account);
  }

  function handleOpenAnother() {
    setForm(EMPTY_FORM);
    setCreated(null);
  }

  return (
    <>
      <PageHeader title="Open Account" subtitle="Add a new checking or savings account to your profile." />
      <Panel className="max-w-2xl p-6 sm:p-8">
        {created ? (
          <OpenAccountSuccess account={created} onOpenAnother={handleOpenAnother} />
        ) : (
          <form id="open-account-form" data-testid="open-account-form" noValidate onSubmit={handleSubmit} className="space-y-5">
            <Field id="account-type" label="Account type" error={errors.type}>
              <SelectInput id="account-type" name="account-type" hasError={Boolean(errors.type)} value={form.type} onChange={update("type")}>
                <option value="">Select account type</option>
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </SelectInput>
            </Field>

            <Field id="nickname" label="Account nickname" error={errors.nickname} hint="3–30 characters, e.g. “Vacation Fund”.">
              <TextInput
                id="nickname"
                hasError={Boolean(errors.nickname)}
                autoComplete="off"
                placeholder="Vacation Fund"
                value={form.nickname}
                onChange={update("nickname")}
              />
            </Field>

            <Field
              id="initial-deposit"
              label="Initial deposit"
              error={errors.initialDeposit}
              hint={`Minimum ${formatMoney(MIN_OPENING_DEPOSIT_CENTS)}, maximum $100,000.00.`}
            >
              <MoneyInput
                id="initial-deposit"
                hasError={Boolean(errors.initialDeposit)}
                value={form.initialDeposit}
                onChange={update("initialDeposit")}
              />
            </Field>

            <Checkbox
              id="accept-terms"
              label="I accept the terms and conditions"
              error={errors.acceptTerms}
              checked={form.acceptTerms}
              onChange={update("acceptTerms")}
            />

            <div className="flex justify-end border-t border-slate-200 pt-5 dark:border-slate-800">
              <PrimaryButton type="submit" id="open-account-submit" data-testid="open-account-submit">
                Open Account
              </PrimaryButton>
            </div>
          </form>
        )}
      </Panel>
    </>
  );
}
