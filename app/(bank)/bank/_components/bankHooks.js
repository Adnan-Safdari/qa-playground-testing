"use client";

import { useMemo, useSyncExternalStore } from "react";
import { getDbSnapshot, getSessionUsername, subscribe } from "@/lib/bankStorage";

const noopSubscribe = () => () => {};

/** false during SSR/hydration, true once running in the browser. */
export function useIsClient() {
  return useSyncExternalStore(noopSubscribe, () => true, () => false);
}

/** undefined = not known yet (server), null = logged out, string = username. */
export function useSessionUsername() {
  return useSyncExternalStore(subscribe, getSessionUsername, () => undefined);
}

/** Parsed bank database; re-renders whenever bankStorage saves. */
export function useBankDb() {
  const raw = useSyncExternalStore(subscribe, getDbSnapshot, () => null);
  return useMemo(() => (raw ? JSON.parse(raw) : null), [raw]);
}
