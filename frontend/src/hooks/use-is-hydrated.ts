"use client";

import { useSyncExternalStore } from "react";

/** Never fires: the value only ever changes at the hydration boundary. */
const subscribe = () => () => undefined;
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

/**
 * False during server render and the hydrating client render, true afterwards.
 *
 * Useful for values that only exist in the browser, such as a token in
 * localStorage. Without it, the first client render reports "no token" for
 * anyone, and route guards act on that before the real value is read.
 */
export function useIsHydrated(): boolean {
  return useSyncExternalStore(subscribe, getClientSnapshot, getServerSnapshot);
}
