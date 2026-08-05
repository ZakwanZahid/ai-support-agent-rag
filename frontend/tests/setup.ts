import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

// jsdom cannot navigate, and the API client redirects to login on a 401.
// Stubbing assign keeps that path testable instead of emitting a warning.
export const locationAssign = vi.fn();

Object.defineProperty(window, "location", {
  configurable: true,
  value: { ...window.location, assign: locationAssign },
});

beforeEach(() => {
  // Several modules read the token from localStorage at call time. Starting
  // each test from an empty store keeps them independent of run order.
  window.localStorage.clear();
  locationAssign.mockClear();
});

afterEach(() => {
  cleanup();
});
