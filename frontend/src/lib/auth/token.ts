/**
 * Access token storage.
 *
 * The token lives in localStorage. This is a deliberate MVP tradeoff, not an
 * oversight: it matches the backend's bearer-token auth and keeps local setup
 * simple, but it is readable by any script on the page, so an XSS bug becomes
 * a session compromise. The production-grade version is a Secure, HttpOnly,
 * SameSite cookie set by the backend, which requires a server-side session
 * endpoint and CSRF protection. See docs/06-decisions.md (ADR-021).
 *
 * Writes publish a change event so React can subscribe to token changes rather
 * than reading localStorage once and going stale.
 */

const ACCESS_TOKEN_STORAGE_KEY = "supportmind.access-token";
const TOKEN_CHANGE_EVENT = "supportmind.token-change";

function canUseStorage(): boolean {
  return (
    typeof window !== "undefined" && typeof window.localStorage !== "undefined"
  );
}

function publishChange(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(TOKEN_CHANGE_EVENT));
}

export function getAccessToken(): string | null {
  if (!canUseStorage()) {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
  publishChange();
}

export function clearAccessToken(): void {
  if (!canUseStorage()) {
    return;
  }

  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  publishChange();
}

/**
 * Subscribe to token changes, including those made in another browser tab.
 * Shaped for `useSyncExternalStore`.
 */
export function subscribeToAccessToken(callback: () => void): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  window.addEventListener(TOKEN_CHANGE_EVENT, callback);
  window.addEventListener("storage", callback);

  return () => {
    window.removeEventListener(TOKEN_CHANGE_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

export { ACCESS_TOKEN_STORAGE_KEY, TOKEN_CHANGE_EVENT };
