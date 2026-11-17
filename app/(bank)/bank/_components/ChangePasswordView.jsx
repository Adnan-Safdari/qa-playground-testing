"use client";

import { useState } from "react";
import { changePassword } from "@/lib/bankStorage";
import { useBank } from "@/app/(bank)/bank/_components/AppShell";
import { Field, FormAlert, PageHeader, Panel, PasswordInput, PrimaryButton } from "@/app/(bank)/bank/_components/ui";

const EMPTY_FORM = { currentPassword: "", newPassword: "", confirmPassword: "" };

export default function ChangePasswordView() {
  const { username } = useBank();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [changed, setChanged] = useState(false);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function handleSubmit(event) {
    event.preventDefault();
    const res = changePassword(username, form);
    if (!res.ok) {
      setErrors(res.errors);
      setChanged(false);
      return;
    }
    setErrors({});
    setForm(EMPTY_FORM);
    setChanged(true);
  }

  return (
    <>
      <PageHeader title="Change Password" subtitle="Use a strong password you don't use anywhere else." />
      <Panel className="max-w-xl p-6 sm:p-8">
        <form id="change-password-form" data-testid="change-password-form" noValidate onSubmit={handleSubmit} className="space-y-5">
          {changed && (
            <FormAlert id="password-success" variant="success">
              Password changed successfully.
            </FormAlert>
          )}

          <Field id="current-password" label="Current password" error={errors.currentPassword}>
            <PasswordInput
              id="current-password"
              hasError={Boolean(errors.currentPassword)}
              autoComplete="current-password"
              value={form.currentPassword}
              onChange={update("currentPassword")}
            />
          </Field>

          <Field
            id="new-password"
            label="New password"
            error={errors.newPassword}
            hint="At least 8 characters, including a letter and a number."
          >
            <PasswordInput
              id="new-password"
              hasError={Boolean(errors.newPassword)}
              autoComplete="new-password"
              value={form.newPassword}
              onChange={update("newPassword")}
            />
          </Field>

          <Field id="confirm-password" label="Confirm new password" error={errors.confirmPassword}>
            <PasswordInput
              id="confirm-password"
              hasError={Boolean(errors.confirmPassword)}
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={update("confirmPassword")}
            />
          </Field>

          <div className="flex justify-end border-t border-slate-200 pt-5 dark:border-slate-800">
            <PrimaryButton type="submit" id="change-password-submit" data-testid="change-password-submit">
              Update Password
            </PrimaryButton>
          </div>
        </form>
      </Panel>
    </>
  );
}
