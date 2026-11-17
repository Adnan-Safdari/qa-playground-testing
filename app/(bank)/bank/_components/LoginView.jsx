"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LoaderCircle, RotateCcw } from "lucide-react";
import { getRememberedUsername, login, resetDemoData, TEST_USERS } from "@/lib/bankStorage";
import { useIsClient, useSessionUsername } from "@/app/(bank)/bank/_components/bankHooks";
import AuthLayout, { AuthCard } from "@/app/(bank)/bank/_components/AuthLayout";
import { Checkbox, Field, FormAlert, PasswordInput, PrimaryButton, TextInput } from "@/app/(bank)/bank/_components/ui";

/** Message for /bank/login?reason=… — read from window.location (client-only component). */
function ReasonMessage() {
  const [reason] = useState(() => new URLSearchParams(window.location.search).get("reason"));
  if (reason === "logged_out") {
    return (
      <FormAlert id="logout-message" variant="success" className="mb-6">
        You have been logged out.
      </FormAlert>
    );
  }
  if (reason === "auth") {
    return (
      <FormAlert id="auth-required-message" variant="warning" className="mb-6">
        Please sign in to continue.
      </FormAlert>
    );
  }
  return null;
}

function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState(() => getRememberedUsername());
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(() => Boolean(getRememberedUsername()));
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});

  function handleSubmit(event) {
    event.preventDefault();
    const result = login(username, password, rememberMe);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    router.replace("/bank/dashboard");
  }

  return (
    <form id="login-form" data-testid="login-form" noValidate onSubmit={handleSubmit} className="space-y-5">
      <ReasonMessage />
      {errors.form && <FormAlert id="login-error">{errors.form}</FormAlert>}

      <Field id="username" label="Username" error={errors.username}>
        <TextInput
          id="username"
          hasError={Boolean(errors.username)}
          type="text"
          autoComplete="username"
          placeholder="Username or email"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </Field>

      <Field id="password" label="Password" error={errors.password}>
        <PasswordInput
          id="password"
          toggleId="toggle-password"
          hasError={Boolean(errors.password)}
          visible={showPassword}
          onToggle={() => setShowPassword((v) => !v)}
          autoComplete="current-password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </Field>

      <Checkbox id="remember-me" label="Remember me" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />

      <PrimaryButton type="submit" id="login-button" data-testid="login-button" className="w-full py-3 text-[15px]">
        Sign In
      </PrimaryButton>

      <p className="text-center text-sm text-slate-500 dark:text-slate-400">
        New to SecureBank?{" "}
        <Link
          href="/bank/register"
          id="create-account-link"
          data-testid="create-account-link"
          className="font-semibold text-brand-600 hover:text-brand-700 dark:text-brand-400"
        >
          Create an account
        </Link>
      </p>
    </form>
  );
}

function TestCredentials({ onReset, resetDone }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-100/60 p-5 dark:border-slate-800 dark:bg-slate-900/60">
      <h2 className="mb-3 text-sm font-medium text-slate-600 dark:text-slate-300">Test credentials</h2>
      <div className="overflow-x-auto">
        <table id="test-credentials" data-testid="test-credentials" className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 dark:border-slate-800 dark:text-slate-400">
              <th className="px-2.5 py-2 font-medium">Username</th>
              <th className="px-2.5 py-2 font-medium">Password</th>
              <th className="px-2.5 py-2 font-medium">Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
            {TEST_USERS.map((u) => (
              <tr key={u.username} data-testid="test-credential-row" data-username={u.username}>
                <td className="px-2.5 py-2 font-mono text-[13px] text-brand-600 dark:text-brand-400">{u.username}</td>
                <td className="px-2.5 py-2 font-mono text-[13px] text-slate-600 dark:text-slate-300">{u.password}</td>
                <td className="px-2.5 py-2 text-slate-500 dark:text-slate-400">{u.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
        Customers created via &ldquo;Create an account&rdquo; sign in with their email address.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-4 dark:border-slate-800">
        <button
          type="button"
          id="reset-demo-data"
          data-testid="reset-demo-data"
          onClick={onReset}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Reset demo data
        </button>
        {resetDone && (
          <span id="reset-demo-message" data-testid="reset-demo-message" role="status" className="text-sm text-emerald-600 dark:text-emerald-400">
            Demo data has been reset.
          </span>
        )}
      </div>
    </div>
  );
}

export default function LoginView() {
  const router = useRouter();
  const isClient = useIsClient();
  const username = useSessionUsername();
  const [resetCount, setResetCount] = useState(0);

  // Already signed in → straight to the dashboard.
  useEffect(() => {
    if (username) router.replace("/bank/dashboard");
  }, [username, router]);

  function handleReset() {
    resetDemoData();
    setResetCount((c) => c + 1);
  }

  return (
    <AuthLayout subtitle="Sign in to your account">
      <h1 className="sr-only">Sign in to SecureBank</h1>
      <AuthCard>
        {isClient ? (
          <LoginForm key={resetCount} />
        ) : (
          <div className="flex h-[360px] items-center justify-center">
            <LoaderCircle className="h-7 w-7 animate-spin text-brand-600" aria-hidden="true" />
          </div>
        )}
      </AuthCard>
      <TestCredentials onReset={handleReset} resetDone={resetCount > 0} />
    </AuthLayout>
  );
}
