"use client";

import { useEffect, useState } from "react";

/**
 * Trails a fast-changing value, so a request follows typing rather than keystrokes.
 *
 * Search moved to the server, which turns every keypress into a query. The
 * delay is the difference between one request per search and one per
 * character — and on a slow connection, between results that settle and
 * results that flicker as earlier responses land late.
 */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [settled, setSettled] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setSettled(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return settled;
}
