"use client";

import { Landmark } from "lucide-react";
import { ThemeToggle } from "@/app/(bank)/bank/_components/AppShell";
import { cn } from "@/lib/utils";

/** Centered logo + title + card column used by the public login / register pages. */
export default function AuthLayout({ subtitle, children }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center px-4 pb-16 pt-14 sm:pt-16">
      <div className="absolute right-4 top-4 sm:right-6 sm:top-6">
        <ThemeToggle />
      </div>
      <span className="flex h-[70px] w-[70px] items-center justify-center rounded-2xl bg-brand-600 text-white shadow-lg shadow-brand-600/25">
        <Landmark className="h-8 w-8" aria-hidden="true" />
      </span>
      <p className="mt-5 text-3xl font-bold tracking-tight text-slate-900 dark:text-white">SecureBank</p>
      <p className="mt-1.5 text-[17px] text-slate-500 dark:text-slate-400">{subtitle}</p>
      <div className="mt-10 w-full max-w-[480px] space-y-5">{children}</div>
    </div>
  );
}

export function AuthCard({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-8",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
