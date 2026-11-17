"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, LoaderCircle } from "lucide-react";
import { useIsClient } from "@/app/(bank)/bank/_components/bankHooks";
import { MIN_OPENING_DEPOSIT_CENTS, formatMoney, registerCustomer } from "@/lib/bankStorage";
import AuthLayout, { AuthCard } from "@/app/(bank)/bank/_components/AuthLayout";
import {
  Balance,
  DetailRow,
  Field,
  MoneyInput,
  PasswordInput,
  PrimaryButton,
  SuccessHeader,
  TextInput,
  primaryButtonClass,
} from "@/app/(bank)/bank/_components/ui";
import { cn } from "@/lib/utils";

function RegisterSuccess({ result, fullName }) {
  return (
    <div id="register-success" data-testid="register-success">
      <SuccessHeader title="Account created successfully">
        Welcome to SecureBank, {fullName}. You are now signed in.
      </SuccessHeader>
      <dl className="mt-6 divide-y divide-slate-200 rounded-xl border border-slate-200 px-4 dark:divide-slate-800 dark:border-slate-800">
        <DetailRow label="Username" valueId="new-username">
          {result.username}
        </DetailRow>
        <DetailRow label="Account" valueId="new-account-nickname">
          {result.account.nickname}
        </DetailRow>
        <DetailRow label="Account number" valueId="new-account-number">
          <span className="font-mono">{result.account.number}</span>
        </DetailRow>
        <div className="flex items-center justify-between gap-4 py-3">
          <dt className="text-sm text-slate-500 dark:text-slate-400">Opening balance</dt>
          <dd className="text-sm font-semibold text-slate-900 dark:text-white">
            <Balance id="new-account-balance" cents={result.account.balance} />
          </dd>
        </div>
      </dl>
      <Link
        href="/bank/dashboard"
        id="go-to-dashboard"
        data-testid="go-to-dashboard"
        className={cn(primaryButtonClass, "mt-6 w-full py-3 text-[15px]")}
      >
        Go to Dashboard
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </div>
  );
}

export default function RegisterView() {
  const [form, setForm] = useState({ fullName: "", email: "", password: "", initialDeposit: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [result, setResult] = useState(null);
  // Render the form only after hydration so automation never submits a non-interactive form.
  const isClient = useIsClient();

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function handleSubmit(event) {
    event.preventDefault();
    const res = registerCustomer(form);
    if (!res.ok) {
      setErrors(res.errors);
      return;
    }
    setErrors({});
    setResult(res);
  }

  return (
    <AuthLayout subtitle={result ? "Your account is ready" : "Open your account in minutes"}>
      <h1 className="sr-only">Create Account</h1>
      <AuthCard>
        {!isClient ? (
          <div className="flex h-[480px] items-center justify-center">
            <LoaderCircle className="h-7 w-7 animate-spin text-brand-600" aria-hidden="true" />
          </div>
        ) : result ? (
          <RegisterSuccess result={result} fullName={form.fullName.trim()} />
        ) : (
          <form id="register-form" data-testid="register-form" noValidate onSubmit={handleSubmit} className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Create Account</h2>
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                You&apos;ll get an Everyday Checking account funded with your initial deposit.
              </p>
            </div>

            <Field id="full-name" label="Full name" error={errors.fullName}>
              <TextInput
                id="full-name"
                hasError={Boolean(errors.fullName)}
                autoComplete="name"
                placeholder="Jane Doe"
                value={form.fullName}
                onChange={update("fullName")}
              />
            </Field>

            <Field id="email" label="Email" error={errors.email} hint="You will use your email to sign in.">
              <TextInput
                id="email"
                hasError={Boolean(errors.email)}
                type="email"
                autoComplete="email"
                placeholder="jane@example.com"
                value={form.email}
                onChange={update("email")}
              />
            </Field>

            <Field
              id="password"
              label="Password"
              error={errors.password}
              hint="At least 8 characters, including a letter and a number."
            >
              <PasswordInput
                id="password"
                toggleId="toggle-password"
                hasError={Boolean(errors.password)}
                visible={showPassword}
                onToggle={() => setShowPassword((v) => !v)}
                autoComplete="new-password"
                value={form.password}
                onChange={update("password")}
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

            <PrimaryButton type="submit" id="register-button" data-testid="register-button" className="w-full py-3 text-[15px]">
              Create Account
            </PrimaryButton>

            <p className="text-center text-sm text-slate-500 dark:text-slate-400">
              Already have an account?{" "}
              <Link
                href="/bank/login"
                id="login-link"
                data-testid="login-link"
                className="font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400"
              >
                Sign in
              </Link>
            </p>
          </form>
        )}
      </AuthCard>
    </AuthLayout>
  );
}
