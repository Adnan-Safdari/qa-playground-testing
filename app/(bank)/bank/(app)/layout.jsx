import AppShell from "@/app/(bank)/bank/_components/AppShell";

/** Shared shell (header, sidebar, auth guard) for every protected SecureBank page. */
export default function ProtectedLayout({ children }) {
  return <AppShell>{children}</AppShell>;
}
