"use client";

import { useState } from "react";
import { updateProfile } from "@/lib/bankStorage";
import { initials, useBank } from "@/app/(bank)/bank/_components/AppShell";
import { Field, FormAlert, PageHeader, Panel, PrimaryButton, TextInput } from "@/app/(bank)/bank/_components/ui";

export default function ProfileView() {
  const { username, user } = useBank();
  const [form, setForm] = useState(() => ({
    fullName: user.profile.fullName || "",
    email: user.profile.email || "",
    phone: user.profile.phone || "",
    address: user.profile.address || "",
  }));
  const [errors, setErrors] = useState({});
  const [saved, setSaved] = useState(false);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function handleSubmit(event) {
    event.preventDefault();
    const res = updateProfile(username, form);
    if (!res.ok) {
      setErrors(res.errors);
      setSaved(false);
      return;
    }
    setErrors({});
    setForm(res.profile);
    setSaved(true);
  }

  return (
    <>
      <PageHeader title="Profile" subtitle="Manage your personal and contact information." />
      <Panel className="max-w-3xl">
        <div className="flex items-center gap-4 border-b border-slate-200 p-6 dark:border-slate-800 sm:px-8">
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-lg font-semibold text-white">
            {initials(user.profile.fullName)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-lg font-semibold text-slate-900 dark:text-white">{user.profile.fullName}</p>
            <p className="truncate text-sm text-slate-500 dark:text-slate-400">{user.profile.email}</p>
          </div>
        </div>

        <form id="profile-form" data-testid="profile-form" noValidate onSubmit={handleSubmit} className="space-y-5 p-6 sm:p-8">
          {saved && (
            <FormAlert id="profile-success" variant="success">
              Profile updated successfully.
            </FormAlert>
          )}

          <div className="grid gap-5 sm:grid-cols-2">
            <Field id="profile-username" label="Username" hint="Your username cannot be changed.">
              <TextInput id="profile-username" readOnly value={username} className="bg-slate-50 text-slate-500 dark:bg-slate-800 dark:text-slate-400" />
            </Field>

            <Field id="full-name" label="Full name" error={errors.fullName}>
              <TextInput id="full-name" hasError={Boolean(errors.fullName)} autoComplete="name" value={form.fullName} onChange={update("fullName")} />
            </Field>

            <Field id="email" label="Email" error={errors.email}>
              <TextInput id="email" hasError={Boolean(errors.email)} type="email" autoComplete="email" value={form.email} onChange={update("email")} />
            </Field>

            <Field id="phone" label="Phone number" error={errors.phone}>
              <TextInput
                id="phone"
                hasError={Boolean(errors.phone)}
                type="tel"
                autoComplete="tel"
                placeholder="+1 555 010 2030"
                value={form.phone}
                onChange={update("phone")}
              />
            </Field>
          </div>

          <Field id="address" label="Address (optional)" error={errors.address} hint="Up to 100 characters.">
            <TextInput id="address" hasError={Boolean(errors.address)} autoComplete="street-address" value={form.address} onChange={update("address")} />
          </Field>

          <div className="flex justify-end border-t border-slate-200 pt-5 dark:border-slate-800">
            <PrimaryButton type="submit" id="save-profile" data-testid="save-profile">
              Save Changes
            </PrimaryButton>
          </div>
        </form>
      </Panel>
    </>
  );
}
