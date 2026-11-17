import { ChevronDown, CircleAlert, CircleCheck, Eye, EyeOff, LoaderCircle, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatMoney } from "@/lib/bankStorage";

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 id="page-title" data-testid="page-title" className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
          {title}
        </h1>
        {subtitle && (
          <p id="page-subtitle" className="mt-1.5 text-slate-500 dark:text-slate-400">
            {subtitle}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

export function Panel({ className, children, ...props }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function SectionTitle({ children, id }) {
  return (
    <h2 id={id} className="text-lg font-semibold text-slate-900 dark:text-white">
      {children}
    </h2>
  );
}

export function inputClass(hasError) {
  return cn(
    "block w-full rounded-lg border bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition",
    "placeholder:text-slate-400 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/15",
    "disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500",
    "dark:bg-slate-950 dark:text-slate-100 dark:disabled:bg-slate-800",
    hasError ? "border-rose-500 focus:border-rose-500 focus:ring-rose-500/15" : "border-slate-300 dark:border-slate-700",
  );
}

export function Field({ id, label, error, hint, required, children }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
        {required && <span className="ml-0.5 text-rose-500">*</span>}
      </label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-xs text-slate-500 dark:text-slate-400">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} data-testid={`${id}-error`} role="alert" className="text-sm text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}

const ALERT_STYLES = {
  error: {
    icon: CircleAlert,
    className: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-200",
  },
  success: {
    icon: CircleCheck,
    className:
      "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-200",
  },
  warning: {
    icon: TriangleAlert,
    className: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200",
  },
};

export function FormAlert({ id, variant = "error", children, className }) {
  const { icon: Icon, className: styles } = ALERT_STYLES[variant];
  return (
    <div
      id={id}
      data-testid={id}
      role={variant === "error" ? "alert" : "status"}
      className={cn("flex items-start gap-3 rounded-xl border px-4 py-3 text-sm", styles, className)}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}

export function PrimaryButton({ className, children, ...props }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition",
        "hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30",
        "disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function SecondaryButton({ className, children, ...props }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition",
        "hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/20",
        "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function PageLoader() {
  return (
    <div
      id="page-loader"
      data-testid="page-loader"
      role="status"
      className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-slate-500"
    >
      <LoaderCircle className="h-8 w-8 animate-spin text-brand-600" aria-hidden="true" />
      <span className="text-sm">Loading…</span>
    </div>
  );
}

const CATEGORY_STYLES = {
  Income: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  Deposit: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  Groceries: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300",
  Utilities: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  Shopping: "bg-pink-100 text-pink-700 dark:bg-pink-950 dark:text-pink-300",
  Transfer: "bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-300",
};

export function CategoryBadge({ category }) {
  return (
    <span
      data-testid="transaction-category"
      className={cn(
        "inline-flex rounded-full px-2.5 py-0.5 text-sm font-medium",
        CATEGORY_STYLES[category] || "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
      )}
    >
      {category}
    </span>
  );
}

export function Amount({ cents, className, testId = "amount", signed = true }) {
  return (
    <span
      data-testid={testId}
      data-cents={cents}
      className={cn(
        "font-semibold tabular-nums",
        cents > 0 && signed ? "text-emerald-600 dark:text-emerald-400" : "text-slate-900 dark:text-slate-100",
        className,
      )}
    >
      {formatMoney(cents, { signed })}
    </span>
  );
}

export function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export const primaryButtonClass = cn(
  "inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition",
  "hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/30",
);

export const secondaryButtonClass = cn(
  "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition",
  "hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-500/20",
  "dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
);

/** Native <select> (Selenium-friendly) styled like the text inputs. */
export function SelectInput({ id, hasError, className, children, ...props }) {
  return (
    <div className="relative">
      <select
        id={id}
        data-testid={id}
        aria-invalid={hasError || undefined}
        aria-describedby={hasError ? `${id}-error` : undefined}
        className={cn(inputClass(hasError), "appearance-none pr-10", className)}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
        aria-hidden="true"
      />
    </div>
  );
}

/** Plain text-like input with id + data-testid + error wiring. */
export function TextInput({ id, hasError, className, ...props }) {
  return (
    <input
      id={id}
      name={id}
      data-testid={id}
      aria-invalid={hasError || undefined}
      aria-describedby={hasError ? `${id}-error` : undefined}
      className={cn(inputClass(hasError), className)}
      {...props}
    />
  );
}

/** Password input with an optional show/hide toggle button (`toggleId`). */
export function PasswordInput({ id, hasError, visible, onToggle, toggleId, ...props }) {
  return (
    <div className="relative">
      <TextInput id={id} hasError={hasError} type={visible ? "text" : "password"} className={toggleId && "pr-11"} {...props} />
      {toggleId && (
        <button
          type="button"
          id={toggleId}
          data-testid={toggleId}
          onClick={onToggle}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 transition hover:text-slate-600 dark:hover:text-slate-200"
        >
          {visible ? <EyeOff className="h-[18px] w-[18px]" /> : <Eye className="h-[18px] w-[18px]" />}
        </button>
      )}
    </div>
  );
}

/** Native checkbox with label and its own `#{id}-error`. */
export function Checkbox({ id, label, error, ...props }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="flex cursor-pointer items-center gap-2.5 text-sm text-slate-700 dark:text-slate-300">
        <input
          type="checkbox"
          id={id}
          name={id}
          data-testid={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${id}-error` : undefined}
          className="h-4 w-4 shrink-0 cursor-pointer rounded border-slate-300 accent-brand-600"
          {...props}
        />
        <span>{label}</span>
      </label>
      {error && (
        <p id={`${id}-error`} data-testid={`${id}-error`} role="alert" className="text-sm text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
    </div>
  );
}

/** Label / value row used by the success summaries. */
export function DetailRow({ label, valueId, children, ...props }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <dt className="text-sm text-slate-500 dark:text-slate-400">{label}</dt>
      <dd id={valueId} data-testid={valueId} className="text-sm font-semibold text-slate-900 dark:text-white" {...props}>
        {children}
      </dd>
    </div>
  );
}

/** Balance text: red when negative, never "+" prefixed. */
export function Balance({ cents, id, testId, className }) {
  return (
    <span
      id={id}
      data-testid={testId ?? id}
      data-cents={cents}
      className={cn("tabular-nums", className, cents < 0 && "text-rose-600 dark:text-rose-400")}
    >
      {formatMoney(cents)}
    </span>
  );
}

/** Text input with a "$" prefix (type="text" so any typed value reaches validation). */
export function MoneyInput({ id, hasError, ...props }) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-slate-400">$</span>
      <TextInput id={id} hasError={hasError} type="text" inputMode="decimal" autoComplete="off" placeholder="0.00" className="pl-7" {...props} />
    </div>
  );
}

/** Big check-mark header for success panels. */
export function SuccessHeader({ title, children }) {
  return (
    <div className="flex flex-col items-center text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400">
        <CircleCheck className="h-7 w-7" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-xl font-semibold text-slate-900 dark:text-white">{title}</h2>
      {children && <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">{children}</p>}
    </div>
  );
}
